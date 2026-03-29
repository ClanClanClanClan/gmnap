from __future__ import annotations
import os, json, pathlib, random, hashlib
from typing import Dict, List, Tuple, Any

from ..ops.metrics import IDEMP_DIFF_BYTES, IDEMP_OK_TOTAL, IDEMP_FAIL_TOTAL
from ..ops.yaml_deterministic import to_canonical_bytes

_REPORT_NAME = "IDEMPOTENCY_REPORT.txt"
_CANON_BIN = "entries.canonical.bin"


def _write_report(dir_path: pathlib.Path, payload: Dict[str, Any]) -> str:
    p = dir_path / _REPORT_NAME
    lines = [
        "GMNAP V7 — Stage 11 IdempotencyCheck",
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


def _bytes_diff(a: bytes, b: bytes) -> Tuple[int, int | None]:
    n = 0
    first = None
    L = min(len(a), len(b))
    for i in range(L):
        if a[i] != b[i]:
            n += 1
            if first is None:
                first = i
    n += abs(len(a) - len(b))
    return n, first


def idempotency_check(
    batch: List[Dict[str, Any]],
    snapshot_dir: str | None = None,
    out_base: str = "snapshots",
    mode: str = "shuffled",
    strict: bool | None = None,
    gate_max: int | None = None,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Stage 11: Verify 0-byte idempotency.
      - mode="shuffled": recompute canonical bytes after deterministic shuffle; compare to original
      - mode="previous": compare current canonical bytes to previous snapshot's entries.json
      - mode="self": compare two consecutive canonical computations of same batch
    When strict (default from env GMNAP_IDEMPOTENCY_STRICT=1) and diff_bytes>gate_max (default 0), raises RuntimeError.
    Returns (batch, metrics_dict)
    """
    strict = (os.getenv("GMNAP_IDEMPOTENCY_STRICT", "1") == "1") if strict is None else bool(strict)
    if gate_max is None:
        try:
            gate_max = int(os.getenv("GMNAP_IDEMPOTENT_DIFF_BYTES_MAX", "0"))
        except Exception:
            gate_max = 0

    # Compute canonical bytes for current batch
    canon_a = to_canonical_bytes(batch)

    if mode == "previous":
        prev_dir = snapshot_dir or _load_prev_snapshot_dir(out_base)
        if not prev_dir:
            # fallback to shuffled if no previous snapshot
            mode = "shuffled"
        else:
            prev_json = pathlib.Path(prev_dir) / "entries.json"
            if prev_json.exists():
                prev_entries = json.loads(prev_json.read_text(encoding="utf-8"))
                canon_b = to_canonical_bytes(prev_entries)
            else:
                mode = "shuffled"

    if mode == "shuffled":
        # Deterministic shuffle (seeded) then canonicalise again
        seed = int(hashlib.sha256(b"gmnap-stage11").hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        shuffled = list(batch)
        rng.shuffle(shuffled)
        canon_b = to_canonical_bytes(shuffled)
    elif mode == "self":
        canon_b = to_canonical_bytes(batch)

    # Write canonical bytes for inspection
    sdir = pathlib.Path(snapshot_dir) if snapshot_dir else pathlib.Path(out_base) / "latest"
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / _CANON_BIN).write_bytes(canon_a)

    # Compute diff
    diff_bytes, first_idx = _bytes_diff(canon_a, canon_b)
    IDEMP_DIFF_BYTES.set(float(diff_bytes))
    payload = {
        "mode": mode,
        "diff_bytes": int(diff_bytes),
        "len_a": len(canon_a),
        "len_b": len(canon_b),
        "first_diff_at": first_idx,
    }
    _write_report(sdir, payload)

    if diff_bytes == 0:
        IDEMP_OK_TOTAL.inc()
    else:
        IDEMP_FAIL_TOTAL.inc()
        if strict and diff_bytes > (gate_max or 0):
            raise RuntimeError(
                f"Stage 11 idempotency gate failed: diff_bytes={diff_bytes} > {gate_max}"
            )

    metrics = {"idempotency_diff_bytes": float(diff_bytes), "idempotency_mode": mode}
    return batch, metrics


# Alias for compatibility
enforce_idempotency_gate = idempotency_check
