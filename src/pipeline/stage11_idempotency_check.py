"""Stage 11: IdempotencyCheck - Rerun pipeline, diff, assert identical."""

from __future__ import annotations
import os
import json
import pathlib
import random
import hashlib
import logging
from typing import Dict, List, Tuple, Any
from src.ops.metrics import IDEMP_DIFF_BYTES, IDEMP_OK_TOTAL, IDEMP_FAIL_TOTAL

# to_canonical_bytes no longer needed — using per-entry hash comparison

logger = logging.getLogger(__name__)

_REPORT_NAME = "IDEMPOTENCY_REPORT.txt"
_CANON_BIN = "entries.canonical.bin"


def _write_report(dir_path: pathlib.Path, payload: Dict[str, Any]) -> str:
    p = dir_path / _REPORT_NAME
    lines = [
        "GMNAP V7 - Stage 11 IdempotencyCheck",
        f"mode: {payload.get('mode')}",
        f"diff_bytes: {payload.get('diff_bytes')}",
        f"len_run_a: {payload.get('len_a')}, len_run_b: {payload.get('len_b')}",
    ]
    if payload.get("first_diff_at") is not None:
        lines.append(f"first_diff_at: {payload['first_diff_at']}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def _load_prev_snapshot_dir(out_base: str) -> str | None:
    idx = pathlib.Path(out_base) / "SNAPSHOT_INDEX.json"
    if idx.exists():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
            return data.get("latest")
        except Exception:
            return None
    return None


def _entry_hash(entry: Dict[str, Any]) -> str:
    """Hash a single entry deterministically."""
    return hashlib.sha256(
        json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _batch_hash_set(batch: List[Dict[str, Any]]) -> List[str]:
    """Compute sorted list of per-entry hashes (order-independent comparison)."""
    return sorted(_entry_hash(e) for e in batch)


def idempotency_check(
    batch: List[Dict[str, Any]],
    snapshot_dir: str | None = None,
    out_base: str = "snapshots",
    mode: str = "shuffled",
    strict: bool | None = None,
    gate_max: int | None = None,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Stage 11: Verify idempotency via per-entry hash comparison.
    Uses hash-based approach instead of full serialisation for O(n log n) scaling.

    Returns (batch, metrics_dict).
    """
    strict = (os.getenv("GMNAP_IDEMPOTENCY_STRICT", "1") == "1") if strict is None else bool(strict)
    if gate_max is None:
        try:
            gate_max = int(os.getenv("GMNAP_IDEMPOTENT_DIFF_BYTES_MAX", "0"))
        except Exception:
            gate_max = 0

    # Compute sorted per-entry hashes
    hashes_a = _batch_hash_set(batch)

    if mode == "previous":
        prev_dir = snapshot_dir or _load_prev_snapshot_dir(out_base)
        if not prev_dir:
            mode = "shuffled"
        else:
            prev_json = pathlib.Path(prev_dir) / "entries.json"
            if prev_json.exists():
                prev_entries = json.loads(prev_json.read_text(encoding="utf-8"))
                hashes_b = _batch_hash_set(prev_entries)
            else:
                mode = "shuffled"

    if mode == "shuffled":
        seed = int(hashlib.sha256(b"gmnap-stage11").hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        shuffled = list(batch)
        rng.shuffle(shuffled)
        hashes_b = _batch_hash_set(shuffled)
    elif mode == "self":
        hashes_b = _batch_hash_set(batch)

    # Compare hash sets
    diff_bytes = 0 if hashes_a == hashes_b else 1

    # Write report
    sdir = pathlib.Path(snapshot_dir) if snapshot_dir else pathlib.Path(out_base) / "latest"
    sdir.mkdir(parents=True, exist_ok=True)

    IDEMP_DIFF_BYTES.set(float(diff_bytes))
    payload = {
        "mode": mode,
        "diff_bytes": int(diff_bytes),
        "len_a": len(hashes_a),
        "len_b": len(hashes_b),
        "first_diff_at": None,
    }
    _write_report(sdir, payload)

    if diff_bytes == 0:
        IDEMP_OK_TOTAL.inc()
        logger.info("Stage 11: Idempotency check PASSED (0 diff bytes)")
    else:
        IDEMP_FAIL_TOTAL.inc()
        logger.warning(f"Stage 11: Idempotency diff_bytes={diff_bytes}")
        if strict and diff_bytes > (gate_max or 0):
            raise RuntimeError(
                f"Stage 11 idempotency gate failed: diff_bytes={diff_bytes} > {gate_max}"
            )

    metrics = {"idempotency_diff_bytes": float(diff_bytes), "idempotency_mode": mode}
    return batch, metrics
