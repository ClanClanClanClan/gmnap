from __future__ import annotations

from typing import Any, Dict, List


def index_by_global_id(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for e in entries:
        gid = e.get("GlobalID")
        if gid:
            out[gid] = e
    return out


def dict_diff(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Return a minimal field‑level diff {added, removed, changed} between dicts a→b."""
    keys = set(a.keys()) | set(b.keys())
    added = {k: b[k] for k in keys - set(a.keys())}
    removed = {k: a[k] for k in keys - set(b.keys())}
    changed = {}
    for k in keys & set(a.keys()) & set(b.keys()):
        if a[k] != b[k]:
            changed[k] = {"from": a[k], "to": b[k]}
    return {"added": added, "removed": removed, "changed": changed}


def compute_entry_diffs(
    prev_entries: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]
):
    idx_prev = index_by_global_id(prev_entries)
    idx_new = index_by_global_id(new_entries)
    prev_ids = set(idx_prev.keys())
    new_ids = set(idx_new.keys())
    added_ids = sorted(list(new_ids - prev_ids))
    removed_ids = sorted(list(prev_ids - new_ids))
    common_ids = sorted(list(prev_ids & new_ids))

    changes = {}
    changed_count = 0
    for gid in common_ids:
        a = idx_prev[gid]
        b = idx_new[gid]
        if a != b:
            diff = dict_diff(a, b)
            if diff["added"] or diff["removed"] or diff["changed"]:
                changes[gid] = diff
                changed_count += 1

    return {
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "changed": changes,
        "changed_entries_count": changed_count,
    }
