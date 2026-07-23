#!/usr/bin/env python3
"""Score the system snapshot against corpus N+2 adjudication (R60.2).

Buckets per name (system verdict from heldout2_system.json, truth from
heldout2_adjudicated.json):
  - abstained            system R0
  - right / wrong        emitted leaf vs concrete adjudicated leaf
  - group_credit / group_wrong   emitted leaf vs GROUP_ONLY:* truth
    (right iff the leaf's family letter matches)
  - unverifiable         truth UNKNOWN (or unresolved)

Reports overall, per-stratum, and per-family; wrong lists are printed
in full — they are the next round's work list. Truths with
agreement=="unresolved" count as UNKNOWN.

Run:  PYTHONPATH=. python3 tools/score_heldout2.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
D = REPO / "data" / "eval" / "heldout2"

GROUP_LETTER = {"ANGLO": "A"}  # fallback map built below from taxonomy letters


def truth_of(label: dict) -> str | None:
    """Concrete leaf, 'GROUP:X' with family letter, or None (unknown)."""
    leaf = label["leaf"].strip()
    if label.get("agreement") == "unresolved" or leaf == "UNKNOWN":
        return None
    if leaf.startswith("GROUP_ONLY"):
        rest = leaf.split(":", 1)[1].strip().upper() if ":" in leaf else ""
        # accept a letter ('A') or a group name ('ARABIC' -> C, etc.)
        if len(rest) == 1 and rest in "ABCDEFG":
            return "GROUP:" + rest
        name_to_letter = {
            "ANGLO_SPHERE": "A",
            "ANGLO": "A",
            "GERMANIC_WESTERN": "A",
            "NORDIC_BALTIC": "A",
            "OCEANIA_PACIFIC": "A",
            "CARIBBEAN_FRENCH": "A",
            "SLAVIC_EAST": "B",
            "SLAVIC_CENTRAL": "B",
            "SLAVIC": "B",
            "HELLENIC": "B",
            "TURKIC": "C",
            "PERSIAN": "C",
            "ARABIC": "C",
            "HEBREW": "C",
            "ARMENIAN": "C",
            "GEORGIAN": "C",
            "BALTIC": "C",
            "SOUTH_ASIAN": "D",
            "SINOPHONE": "E",
            "JAPANESE": "E",
            "KOREAN": "E",
            "VIETNAMESE": "E",
            "SEA": "E",
            "SSA": "F",
            "LATIN_AMERICAN": "G",
            "CJK": "E",
            "EAST_ASIAN": "E",
        }
        if rest in name_to_letter:
            return "GROUP:" + name_to_letter[rest]
        return None
    if len(leaf) == 2 and leaf[0] in "ABCDEFG" and leaf[1].isdigit():
        return leaf
    return None


def main() -> int:
    snap = json.load(open(D / "heldout2_system.json"))
    adj = json.load(open(D / "heldout2_adjudicated.json"))
    # tools/assemble_heldout2_adjudication.py writes a flat list; older
    # snapshots used a {"labels": [...]} wrapper. Accept both.
    adj_rows = adj["labels"] if isinstance(adj, dict) else adj
    truths = {a["name"]: a for a in adj_rows}
    rows = snap["rows"]

    buckets = Counter()
    fam_stats: dict[str, Counter] = defaultdict(Counter)
    strat_stats: dict[str, Counter] = defaultdict(Counter)
    wrongs: list[tuple[str, str, str, str]] = []

    for r in rows:
        name, sysleaf, stratum = r["name"], r["region"], r["stratum"]
        lab = truths.get(name)
        t = truth_of(lab) if lab else None
        if sysleaf in (None, "R0", "XX"):
            b = "abstained"
        elif t is None:
            b = "unverifiable_emit"
        elif t.startswith("GROUP:"):
            b = "group_credit" if sysleaf[0] == t[-1] else "wrong"
            if b == "wrong":
                wrongs.append((name, sysleaf, t, stratum))
        else:
            b = "right" if sysleaf == t else "wrong"
            if b == "wrong":
                wrongs.append((name, sysleaf, t, stratum))
            fam_stats[t[0]][b] += 1
        buckets[b] += 1
        strat_stats[stratum][b] += 1

    n = len(rows)
    emitted = n - buckets["abstained"]
    verif = buckets["right"] + buckets["group_credit"] + buckets["wrong"]
    ok = buckets["right"] + buckets["group_credit"]
    print(
        f"N={n} emitted={emitted} abstained={buckets['abstained']} "
        f"({buckets['abstained'] / n:.0%})"
    )
    print(
        f"verifiable emissions={verif}: ok={ok} wrong={buckets['wrong']} "
        f"-> precision {ok / verif:.1%}"
        if verif
        else "none verifiable"
    )
    print(f"unverifiable emissions={buckets['unverifiable_emit']}")
    print("\nper-family (concrete-leaf truths):")
    for f in sorted(fam_stats):
        c = fam_stats[f]
        tot = c["right"] + c["wrong"]
        print(
            f"  {f}: {c['right']}/{tot} = {c['right'] / tot:.0%}"
            if tot
            else f"  {f}: -"
        )
    print("\nper-stratum:")
    for s in sorted(strat_stats):
        c = strat_stats[s]
        tot = sum(c.values())
        v = c["right"] + c["group_credit"] + c["wrong"]
        oks = c["right"] + c["group_credit"]
        p = f"{oks}/{v}={oks / v:.0%}" if v else "-"
        print(f"  {s}: n={tot} abstain={c['abstained'] / tot:.0%} precision {p}")
    print(f"\nWRONG ({len(wrongs)}):")
    for w in sorted(wrongs, key=lambda x: x[3]):
        print(f"  {w[0]:34s} sys={w[1]:4s} truth={w[2]:8s} [{w[3]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
