"""Unit tests for ``FastTextCLIWorker``.

The class keeps a persistent fastText subprocess alive for the
process's lifetime instead of spawning one per prediction. These tests
verify:

- streaming protocol correctness (request/response pairing across many
  calls, including inputs with embedded newlines that would otherwise
  desync the pipe)
- respawn-on-death behaviour when the child exits
- thread safety under concurrent access
- the module-level singleton returns the same instance

The tests skip if the fastText CLI or the quantized model aren't
available on the test machine.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

import pytest

from src.regions.manager_optimized import FastTextCLIWorker

FT_CLI = shutil.which("fasttext") or str(Path.home() / ".local" / "bin" / "fasttext")
MODEL = Path("data/ml_training/ft_name_classifier.ftz")

pytestmark = pytest.mark.skipif(
    not (Path(FT_CLI).exists() and MODEL.exists()),
    reason=f"fasttext CLI or model missing: cli={FT_CLI} model={MODEL}",
)


@pytest.fixture
def worker():
    w = FastTextCLIWorker(cli_path=FT_CLI, model_path=str(MODEL))
    yield w
    w.shutdown()


def test_single_prediction_returns_label_and_probs(worker):
    label, p1, p2 = worker.predict("euler")
    assert label is not None and label.startswith(
        ("A", "B", "C", "D", "E", "F", "G", "H", "R", "Z")
    )
    assert 0.0 <= p2 <= p1 <= 1.0


def test_many_predictions_stay_in_sync(worker):
    """Request/response pairing must hold across many calls. If the
    worker desynced, a prediction for 'mueller' might come back as the
    response to an earlier 'euler' — this test would catch that because
    each surname has a stable top label on the trained model."""
    inputs = ["euler", "mueller", "tanaka", "kolmogorov", "patel"] * 20
    results = [worker.predict(s) for s in inputs]
    # Same input → same label across repeats
    by_input: dict[str, set[str]] = {}
    for s, (label, _, _) in zip(inputs, results):
        by_input.setdefault(s, set()).add(label or "")
    for s, labels in by_input.items():
        assert (
            len(labels) == 1
        ), f"worker desynced: {s!r} produced multiple labels {labels}"


def test_newline_in_input_is_sanitised(worker):
    """A raw newline in input would break the stdin-line-oriented
    protocol. Worker replaces \\n with space before sending."""
    label, _, _ = worker.predict("eu\nler\r")
    assert label is not None


def test_empty_input_returns_none_without_spawning_subprocess():
    w = FastTextCLIWorker(cli_path=FT_CLI, model_path=str(MODEL))
    assert w._proc is None
    label, p1, p2 = w.predict("")
    assert (label, p1, p2) == (None, 0.0, 0.0)
    assert w._proc is None, "empty input should not trigger subprocess spawn"


def test_respawn_after_subprocess_death(worker):
    """If the child dies, the next predict() should respawn and succeed."""
    # Warm up the worker so _proc is set
    worker.predict("euler")
    assert worker._proc is not None
    # Forcibly kill the subprocess
    worker._proc.kill()
    worker._proc.wait(timeout=3)
    # Next call must respawn transparently
    label, _, _ = worker.predict("euler")
    assert label is not None
    assert worker._proc is not None
    assert worker._proc.poll() is None, "worker did not respawn"


def test_singleton_returns_same_instance():
    a = FastTextCLIWorker.get(FT_CLI, str(MODEL))
    b = FastTextCLIWorker.get(FT_CLI, str(MODEL))
    assert a is b


def test_concurrent_access_is_safe(worker):
    """Eight threads hammering the same worker must not corrupt the
    stdin/stdout pipe. The io_lock serialises the critical section."""
    errors: list[str] = []

    def hammer():
        for _ in range(50):
            label, _, _ = worker.predict("euler")
            if label is None:
                errors.append("None label under concurrency")

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors


def test_shutdown_idempotent(worker):
    worker.predict("euler")
    worker.shutdown()
    # Second shutdown must not raise
    worker.shutdown()
    assert worker._proc is None


def test_predict_with_dead_proc_returns_null_tuple(worker):
    """Simulate the failure mode that crashed under ``python -O``:
    ``_ensure_running`` returns True but ``_proc`` has been externally
    nulled before the critical section. The old code had an ``assert``
    that got stripped by the optimizer and then crashed with
    ``AttributeError: 'NoneType' object has no attribute 'stdin'``.
    The hardened path must silently return ``(None, 0.0, 0.0)``.
    """
    # Warm up so _proc exists, then stub _ensure_running to pretend
    # the subprocess is alive even though we've nulled the handle.
    worker.predict("euler")
    worker._proc = None
    worker._ensure_running = lambda: True
    r = worker.predict("mueller")
    assert r == (None, 0.0, 0.0)


def test_predict_caps_absurdly_long_input(worker):
    """Input larger than a pipe buffer would deadlock the worker
    (the write blocks waiting for a reader while the reader is
    blocked behind the same io_lock). The hardened predict caps at
    _MAX_INPUT_LEN before hitting the subprocess."""
    # 100 KB surname — way beyond any pipe buffer
    huge = "x" * 100_000
    # Should not hang; returns within a normal prediction latency.
    import time

    t0 = time.time()
    r = worker.predict(huge)
    dt = time.time() - t0
    assert dt < 3.0, f"worker hung on long input ({dt:.1f}s)"
    # Result is label-ish (or None if the truncated form is gibberish);
    # we just require no exception + non-hang.
    assert r is not None


def test_singleton_normalises_paths():
    """Different spellings of the same path must not spawn duplicate
    subprocesses. The singleton dict keys on ``realpath(expanduser(...))``.
    """
    import os

    # The Path.home() form expanduser is a no-op, so also try the
    # tilde form explicitly. Both should hit the same key.
    a = FastTextCLIWorker.get(FT_CLI, str(MODEL))
    home = str(Path.home())
    if FT_CLI.startswith(home):
        tilded = "~" + FT_CLI[len(home) :]
        b = FastTextCLIWorker.get(tilded, str(MODEL))
        assert a is b, "tilde-vs-absolute spawned two workers"
    # Also try a relative dot-less-path form where possible
    absolute = os.path.realpath(FT_CLI)
    c = FastTextCLIWorker.get(absolute, str(MODEL))
    assert a is c
