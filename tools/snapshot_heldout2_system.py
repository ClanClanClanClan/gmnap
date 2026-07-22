#!/usr/bin/env python3
"""Snapshot the CURRENT system's verdicts on corpus N+2 (R60.2).

Recorded BEFORE adjudication and before any fixes derived from this
corpus — this file is the honest baseline the adjudicated labels will be
compared against. Name-only detection: no CountryCodes, no geo axis.

Run:  OFFLINE=1 PYTHONPATH=. python3 tools/snapshot_heldout2_system.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
IN = REPO / "data" / "eval" / "heldout2" / "heldout2_names.json"
OUT = REPO / "data" / "eval" / "heldout2" / "heldout2_system.json"


def main() -> int:
    from src.regions.manager_optimized import RegionManager

    names = json.load(open(IN))
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO,
    ).stdout.strip()
    m = RegionManager()
    rows = []
    for e in names:
        r = m.detect_region({"CanonicalLatin": e["name"]})
        rows.append(
            {
                "name": e["name"],
                "stratum": e["stratum"],
                "source": e["source"],
                "region": r.region_code,
                "confidence": round(float(r.confidence), 4),
                "method": r.detection_method,
                "group_region": r.group_region,
                "resolution_level": r.resolution_level,
            }
        )
    OUT.write_text(
        json.dumps({"head": head, "rows": rows}, indent=1, ensure_ascii=False)
    )
    from collections import Counter

    c = Counter(x["region"] for x in rows)
    n = len(rows)
    r0 = c.get("R0", 0)
    print(f"snapshot@{head}: {n} names, abstention {r0}/{n} = {r0 / n:.0%}")
    for stratum in sorted({x["stratum"] for x in rows}):
        sub = [x for x in rows if x["stratum"] == stratum]
        sr0 = sum(1 for x in sub if x["region"] == "R0")
        print(f"  {stratum}: {len(sub)} names, abstention {sr0 / len(sub):.0%}")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
