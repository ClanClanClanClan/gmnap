from __future__ import annotations

import json
import sys
from collections import Counter

EXT_DUP_GID_MAX = 0
EXT_DUP_EXTID_PCT_MAX = 0.0


def pct_dup_external(entries):
    sids = [e.get("SourceID") for e in entries if e.get("SourceID")]
    if not sids:
        return 0.0
    c = Counter(sids)
    dups = sum(v - 1 for v in c.values() if v > 1)
    return 100.0 * dups / max(1, len(sids))


def dup_gid(entries):
    gids = [e.get("GlobalID") for e in entries if e.get("GlobalID")]
    c = Counter(gids)
    bad = 0
    for g, v in c.items():
        if v > 1 and not any(g.endswith(f"--{i}") for i in range(1, 100)):
            bad += 1
    return bad


if __name__ == "__main__":
    entries = json.load(open(sys.argv[1], encoding="utf-8"))
    dgid = dup_gid(entries)
    pext = pct_dup_external(entries)
    print(
        json.dumps(
            {"duplicate_global_id": dgid, "duplicate_external_id_pct": pext}, indent=2
        )
    )
    assert dgid == EXT_DUP_GID_MAX, "duplicate_global_id must be 0 (Extreme)"
    assert (
        pext <= EXT_DUP_EXTID_PCT_MAX
    ), "duplicate_external_id_pct must be 0.00% (Extreme)"
