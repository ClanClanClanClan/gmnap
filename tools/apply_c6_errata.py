#!/usr/bin/env python3
"""Apply the C6 errata to the corpus-N+2 labels (R60.2 ruling 1).

Reads the corrected-rule re-adjudication produced by the workflow that
`tools/gen_c6_errata_workflow.py` emits, and rewrites exactly those
names' labels in `heldout2_adjudicated.json`. Every rewritten row keeps
an audit trail: `errata` records the previous leaf and the ruling that
justified the change, so the file never silently disagrees with the
adjudication it came from.

Only names the errata pass actually returned are touched, and only if
they were labeled C6 in the first place — a name the corrected pass did
not cover keeps its original label rather than being guessed at.

Run:  PYTHONPATH=. python3 tools/apply_c6_errata.py <errata_journal.jsonl>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADJ = REPO / "data" / "eval" / "heldout2" / "heldout2_adjudicated.json"
RULING = (
    "R60.2 ruling 1 (2026-07-23): Ashkenazi-associated surnames follow "
    "the FORM; C6 reserved for Hebrew/Israeli name forms"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    journal = Path(sys.argv[1])
    if not journal.exists():
        print(f"ERROR: errata journal not found: {journal}", file=sys.stderr)
        return 2

    corrected: dict[str, dict] = {}
    for line in journal.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("type") != "result":
            continue
        payload = rec.get("result")
        if not isinstance(payload, dict):
            continue
        for lab in payload.get("labels") or []:
            if not isinstance(lab, dict) or "agreement" not in lab:
                continue  # reconciler rows only
            corrected[str(lab["name"]).strip()] = lab

    rows = json.load(open(ADJ))
    stats = Counter()
    moves = Counter()
    for r in rows:
        if r["leaf"] != "C6":
            continue
        stats["c6_before"] += 1
        new = corrected.get(r["name"])
        if new is None:
            stats["not_covered_kept_c6"] += 1
            continue
        leaf = str(new["leaf"]).strip()
        if leaf == "C6":
            stats["confirmed_c6"] += 1
            continue
        moves[f"C6 -> {leaf}"] += 1
        stats["rewritten"] += 1
        r["errata"] = {
            "was": "C6",
            "ruling": RULING,
            "note": new.get("note", ""),
            "agreement": new.get("agreement"),
        }
        r["leaf"] = leaf
        r["agreement"] = new.get("agreement", r["agreement"])

    ADJ.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"C6 labels before: {stats['c6_before']}")
    print(f"  confirmed C6 (Hebrew form): {stats['confirmed_c6']}")
    print(f"  rewritten to the form's leaf: {stats['rewritten']}")
    if stats["not_covered_kept_c6"]:
        print(f"  not covered by errata, kept as C6: {stats['not_covered_kept_c6']}")
    for k, n in moves.most_common():
        print(f"    {k}: {n}")
    print(f"wrote {ADJ.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
