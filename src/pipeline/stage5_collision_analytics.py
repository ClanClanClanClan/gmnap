from __future__ import annotations
from typing import Dict, List, Tuple


def ensure_unique_global_ids(batch: List[Dict]) -> Tuple[List[Dict], Dict[str, int]]:
    seen = {}
    collisions = 0
    remap = {}
    out = []
    for e in batch:
        gid = e.get("GlobalID")
        if not gid:
            out.append(e)
            continue
        if gid not in seen:
            seen[gid] = 1
            out.append(e)
        else:
            # suffix --N
            seen[gid] += 1
            new_gid = f"{gid}--{seen[gid]-1}"
            collisions += 1
            remap[gid] = remap.get(gid, []) + [new_gid]
            e2 = dict(e)
            e2["GlobalID"] = new_gid
            # remap advisor/edge refs in this entry
            e2["Advisors"] = [
                (a if a != gid else new_gid) for a in (e.get("Advisors") or [])
            ]
            out.append(e2)
    # remap references across batch (simple pass)
    id_map = {old: new for old, arr in remap.items() for new in arr}
    for e in out:
        if "Advisors" in e:
            e["Advisors"] = [id_map.get(a, a) for a in (e["Advisors"] or [])]
    return out, {"collisions": collisions}
