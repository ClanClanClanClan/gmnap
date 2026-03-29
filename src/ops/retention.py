from __future__ import annotations
import time, pathlib


def rotate_snapshots(root: str, keep_days: int = 30, keep_n: int | None = None) -> list[str]:
    """
    Deletes snapshot directories older than keep_days and keeps at most keep_n most recent.
    Returns list of deleted directory paths.
    """
    now = time.time()
    base = pathlib.Path(root)
    if not base.exists():
        return []
    runs = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("run-")]
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    deleted = []

    # Age-based deletion
    for p in runs:
        age_days = (now - p.stat().st_mtime) / (24 * 3600)
        if age_days > keep_days:
            for sub in p.rglob("*"):
                if sub.is_file():
                    sub.unlink()
            p.rmdir()
            deleted.append(str(p))

    # Count-based deletion
    if keep_n is not None and len(runs) - len(deleted) > keep_n:
        survivors = [p for p in runs if str(p) not in deleted][:keep_n]
        rest = [p for p in runs if p not in survivors and str(p) not in deleted]
        for p in rest:
            for sub in p.rglob("*"):
                if sub.is_file():
                    sub.unlink()
            p.rmdir()
            deleted.append(str(p))
    return deleted
