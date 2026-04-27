"""Pipeline Stage 5 — collision analytics.

Catches three classes of GlobalID collisions:

1. **In-batch duplicates** — the same GlobalID appearing twice in
   the same submission. Second and later occurrences get a
   ``--N`` suffix on their GlobalID; references in advisor lists
   are re-pointed.
2. **Cross-batch collisions** — a GlobalID we already saw in an
   earlier run. The persisted registry under
   ``<workdir>/stage5_registry.json`` is consulted; matches get
   suffixed the same way.
3. **Genealogy edge emission** — every advisor reference becomes a
   row in ``<workdir>/stage5_edges.csv`` (CSV: from_gid, to_gid)
   so downstream tools can ingest the doctoral-advisor graph
   without re-walking the JSON.

Public API (pinned by ``tests/unit/test_collision_analytics.py``):

  ``stage5_collision_analytics(batch, workdir)`` →
      ``(out_batch, metrics)`` where ``metrics`` carries
      ``collisions`` (int) and ``edges`` (int).

  ``_load_registry(workdir)``  → ``set[str]`` of seen GlobalIDs.
  ``_save_registry(workdir, ids)`` → persist a registry.
  ``ensure_unique_global_ids(batch)`` (back-compat) → in-batch
      dedup only, returns ``(out, {"collisions": n})``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REGISTRY_FILE = "stage5_registry.json"
EDGES_FILE = "stage5_edges.csv"


# ---------------------------------------------------------------------------
# Cross-batch registry (persisted)
# ---------------------------------------------------------------------------


def _load_registry(workdir: str | Path) -> Set[str]:
    """Read the persisted set of GlobalIDs we've seen in prior batches.

    Returns an empty set if the registry doesn't exist (fresh
    workdir or first run).
    """
    p = Path(workdir) / REGISTRY_FILE
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        # Corrupt registry = treat as empty rather than crash; the
        # current batch's IDs will be re-added below.
        return set()


def _save_registry(workdir: str | Path, ids: Set[str]) -> None:
    """Persist the GlobalID set. Writes JSON-array, sorted for
    reproducibility (so registry files diff cleanly across runs).
    """
    p = Path(workdir) / REGISTRY_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(ids)), encoding="utf-8")


# ---------------------------------------------------------------------------
# In-batch dedup primitive (back-compat)
# ---------------------------------------------------------------------------


def ensure_unique_global_ids(
    batch: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Drop in-batch GlobalID collisions by suffixing all but the
    first occurrence with ``--N``. Returns the updated batch plus a
    metrics dict with the collision count. Does NOT touch any
    persisted registry.
    """
    seen: Dict[str, int] = {}
    collisions = 0
    out: List[Dict[str, Any]] = []
    remap: Dict[str, List[str]] = {}
    for e in batch:
        gid = e.get("GlobalID")
        if not gid:
            out.append(e)
            continue
        if gid not in seen:
            seen[gid] = 1
            out.append(e)
        else:
            seen[gid] += 1
            new_gid = f"{gid}--{seen[gid] - 1}"
            collisions += 1
            remap.setdefault(gid, []).append(new_gid)
            e2 = dict(e)
            e2["GlobalID"] = new_gid
            e2["Advisors"] = [
                (a if a != gid else new_gid) for a in (e.get("Advisors") or [])
            ]
            out.append(e2)
    id_map = {old: new for old, arr in remap.items() for new in arr}
    for e in out:
        if "Advisors" in e:
            e["Advisors"] = [id_map.get(a, a) for a in (e["Advisors"] or [])]
    return out, {"collisions": collisions}


# ---------------------------------------------------------------------------
# Edge emission
# ---------------------------------------------------------------------------


def _emit_edges_csv(workdir: str | Path, batch: List[Dict[str, Any]]) -> int:
    """Write one (from_gid, to_gid) row per advisor reference.
    Header is ``from,to``. Returns the row count.
    """
    p = Path(workdir) / EDGES_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Tuple[str, str]] = []
    for e in batch:
        src = e.get("GlobalID")
        if not src:
            continue
        for adv in e.get("Advisors") or []:
            if adv:
                rows.append((src, adv))
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["from", "to"])
        for r in rows:
            w.writerow(r)
    return len(rows)


# ---------------------------------------------------------------------------
# Top-level Stage 5 entry point
# ---------------------------------------------------------------------------


def stage5_collision_analytics(
    batch: List[Dict[str, Any]],
    *,
    workdir: str | Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Run all three collision-analytics tasks on ``batch``.

    1. Resolve in-batch GlobalID collisions (suffix with ``--N``).
    2. Resolve cross-batch GlobalID collisions against the persisted
       registry under ``<workdir>/stage5_registry.json``.
    3. Persist the updated registry (now including this batch's IDs).
    4. Emit a genealogy edges CSV under ``<workdir>/stage5_edges.csv``.

    Returns ``(out_batch, metrics)`` where ``metrics`` carries:
      - ``collisions``: total in-batch + cross-batch collisions
      - ``edges``: number of advisor references emitted
    """
    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    # 1. In-batch dedup.
    out, metrics = ensure_unique_global_ids(batch)
    collisions = metrics["collisions"]

    # 2. Cross-batch dedup. For each entry whose GlobalID is in the
    #    persisted registry, suffix with --N where N is the next
    #    available integer.
    registry = _load_registry(workdir_path)
    suffix_map: Dict[str, str] = {}
    for e in out:
        gid = e.get("GlobalID")
        if not gid or gid in suffix_map:
            continue
        if gid in registry:
            n = 1
            while f"{gid}--{n}" in registry:
                n += 1
            new_gid = f"{gid}--{n}"
            suffix_map[gid] = new_gid
            collisions += 1

    if suffix_map:
        for e in out:
            gid = e.get("GlobalID")
            if gid in suffix_map:
                e["GlobalID"] = suffix_map[gid]
            if "Advisors" in e:
                e["Advisors"] = [
                    suffix_map.get(a, a) for a in (e.get("Advisors") or [])
                ]

    # 3. Update registry on disk.
    new_ids = {e.get("GlobalID") for e in out if e.get("GlobalID")}
    _save_registry(workdir_path, registry | new_ids)

    # 4. Emit edges.
    edge_count = _emit_edges_csv(workdir_path, out)

    metrics_out = {"collisions": collisions, "edges": edge_count}
    return out, metrics_out
