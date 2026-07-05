"""Persistent fastText CLI worker + model singleton.

Moved verbatim from ``manager_optimized.py`` (R45).
"""

import atexit
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional fasttext (mirrors the facade's guard; absent in Docker builds)
try:
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*load_model does not return.*")
        import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    fasttext = None
    FASTTEXT_AVAILABLE = False

# Singleton for FastText model to prevent multiple loads
_fasttext_model = None
_fasttext_load_attempted = False


def get_fasttext_model(config_dir: Path = Path("./config")):
    """Get or load the FastText model (singleton pattern)."""
    global _fasttext_model, _fasttext_load_attempted

    if _fasttext_model is not None:
        return _fasttext_model

    if _fasttext_load_attempted:
        # Already tried and failed, don't try again
        return None

    _fasttext_load_attempted = True

    try:
        # Try config directory first
        model_path = config_dir / "lid.176.bin"

        # Fallback to global cache directory for tests
        if not model_path.exists():
            global_model_path = Path("cache/config/lid.176.bin")
            if global_model_path.exists():
                model_path = global_model_path

        if model_path.exists():
            # Suppress fasttext C++ warning by redirecting stderr
            import os
            import sys

            old_stderr = sys.stderr
            try:
                # Redirect stderr to devnull during load
                sys.stderr = open(os.devnull, "w")
                _fasttext_model = fasttext.load_model(str(model_path))
            finally:
                sys.stderr.close()
                sys.stderr = old_stderr
            logger.info(f"Loaded FastText language detector from {model_path}")
            return _fasttext_model
        else:
            logger.warning(f"FastText model not found at {model_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to load language detector: {e}")
        return None


class FastTextCLIWorker:
    """Persistent fastText CLI subprocess for name-origin prediction.

    Replaces the naive ``subprocess.run([...fasttext..., predict-prob,
    model, "-", "2"], input=text)`` pattern which fork+exec+mmap-loaded
    the 50 MB quantized model for every single query. That path
    measured ~23 ms / query (~43 q/s) on an Apple M1; per-call this
    worker measures ~0.5 ms (2 k q/s) — a **~60×** speedup on the
    tiebreaker path, and a **~2.3×** end-to-end speedup on the full
    pipeline benchmark in CLI mode (190 → ~430 entries/s).

    Thread-safety: one lock serialises writes+reads so concurrent
    callers don't interleave on the shared stdin/stdout pipe. Idempotent
    respawn on subprocess death (broken pipe → respawn once per query).

    Shutdown: registered via ``atexit`` to close stdin and wait briefly
    for the subprocess to exit cleanly. If it doesn't, we SIGKILL.

    Input sanitisation: fastText's stdin protocol is line-oriented —
    one line in, one line out. Any ``\\n``/``\\r`` in the query would
    desynchronise the request/response pairing and poison subsequent
    predictions. We replace both with a space.

    Process-wide singleton: ``get(cli_path, model_path)`` returns the
    same worker instance for the same ``(cli_path, model_path)`` pair so
    re-instantiating ``RegionManager`` (common in test suites) does not
    leak a new subprocess per instance.
    """

    # (cli_path, model_path) -> FastTextCLIWorker
    _instances: Dict[Tuple[str, str], "FastTextCLIWorker"] = {}
    _instances_lock = threading.Lock()

    @classmethod
    def get(cls, cli_path: str, model_path: str) -> "FastTextCLIWorker":
        """Return the singleton worker for this CLI/model pair.

        Paths are resolved via ``realpath`` + ``expanduser`` so a
        caller that passes ``~/.local/bin/fasttext`` doesn't spawn a
        second subprocess alongside one that passed the absolute form
        or a symlinked equivalent.
        """
        key = (
            os.path.realpath(os.path.expanduser(cli_path)),
            os.path.realpath(os.path.expanduser(model_path)),
        )
        with cls._instances_lock:
            w = cls._instances.get(key)
            if w is None:
                w = cls(cli_path, model_path)
                cls._instances[key] = w
            return w

    def __init__(self, cli_path: str, model_path: str) -> None:
        self._cli_path = cli_path
        self._model_path = model_path
        # Popen object; poll() is None while alive.
        self._proc: Optional[subprocess.Popen] = None
        # Serialise the [write, flush, readline] critical section.
        self._io_lock = threading.Lock()
        # Cover the race between two threads both observing a dead proc
        # and both trying to respawn.
        self._spawn_lock = threading.Lock()
        self._shutdown_registered = False

    def _ensure_running(self) -> bool:
        """Spawn the subprocess if not alive. Returns True on success."""
        if self._proc is not None and self._proc.poll() is None:
            return True
        with self._spawn_lock:
            if self._proc is not None and self._proc.poll() is None:
                return True
            try:
                self._proc = subprocess.Popen(
                    [
                        self._cli_path,
                        "predict-prob",
                        self._model_path,
                        "-",  # read from stdin
                        "2",  # top-k = 2 (p1, p2)
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,  # line-buffered
                )
            except OSError as exc:
                logger.warning("FastText CLI worker spawn failed: %s", exc)
                self._proc = None
                return False

            if not self._shutdown_registered:
                atexit.register(self.shutdown)
                self._shutdown_registered = True
            return True

    # Hard cap on input length. fastText treats the input as a document
    # and we need it to fit in one line of the subprocess stdin pipe;
    # PIPE_BUF is typically 64 KB on Linux / 4 KB on macOS, so keep
    # individual messages well under that to avoid flush-vs-readline
    # deadlocks. Surnames are single tokens so 4 KB is generous.
    _MAX_INPUT_LEN = 4096

    def predict(self, text: str) -> Tuple[Optional[str], float, float]:
        """One-shot prediction. Returns ``(label, p1, p2)`` or
        ``(None, 0.0, 0.0)`` on any failure. Safe to call concurrently.
        """
        safe = (text or "").replace("\n", " ").replace("\r", " ").strip()
        if not safe:
            return None, 0.0, 0.0
        # Cap length before feeding the subprocess (see _MAX_INPUT_LEN)
        if len(safe) > self._MAX_INPUT_LEN:
            safe = safe[: self._MAX_INPUT_LEN]

        for attempt in (1, 2):
            if not self._ensure_running():
                return None, 0.0, 0.0
            try:
                with self._io_lock:
                    # Re-read _proc UNDER the lock — shutdown() (also
                    # holding this lock) may have nulled it between
                    # _ensure_running() and here. Don't use assert:
                    # python -O strips it and we'd crash on None.write.
                    proc = self._proc
                    if (
                        proc is None
                        or proc.stdin is None
                        or proc.stdout is None
                        or proc.poll() is not None
                    ):
                        self._proc = None
                        continue
                    proc.stdin.write(safe + "\n")
                    proc.stdin.flush()
                    line = proc.stdout.readline()
                if not line:
                    # EOF — child exited. Retry once.
                    self._proc = None
                    continue
                parts = line.strip().split()
                if len(parts) < 2:
                    return None, 0.0, 0.0
                # fasttext predict-prob emits alternating
                # "__label__X prob __label__Y prob ...". Take probabilities
                # as the odd-index tokens rather than hard-coding parts[3]
                # for p2: a build whose output spacing/order differs would
                # otherwise silently set p2=0.0 and INFLATE the (p1 - p2)
                # margin, weakening the same-group gate.
                probs = parts[1::2]
                label = parts[0].replace("__label__", "")
                p1 = float(probs[0])
                p2 = float(probs[1]) if len(probs) > 1 else 0.0
                return label, p1, p2
            except (BrokenPipeError, OSError, ValueError, AttributeError) as exc:
                # AttributeError: proc died and a reference went stale.
                # ValueError: "I/O on closed file" from a concurrent
                # shutdown — retry with a fresh subprocess.
                logger.debug(
                    "FastText CLI worker I/O failure (attempt %d): %s", attempt, exc
                )
                self._proc = None
                continue
        return None, 0.0, 0.0

    def shutdown(self) -> None:
        """Close the subprocess cleanly. Safe to call multiple times.

        Acquires ``_io_lock`` so in-flight ``predict()`` calls cannot
        race the close: either they finish their write+readline first,
        or shutdown wins and they observe the null ``_proc`` on their
        next iteration (and abstain).
        """
        with self._io_lock:
            proc = self._proc
            self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        except Exception:  # defensive, shutdown must not raise
            pass

