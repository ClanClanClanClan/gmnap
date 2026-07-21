#!/usr/bin/env python3
"""Within-anchor model accuracy on the adjudicated R58 pilot (R59.5 gate).

Measures the QUANTITY THAT MATTERS for the runtime: the same-group gate
only ever lets fastText refine WITHIN an anchored group, so the model's
job is picking the right leaf among the truth's group siblings — not
open-set top-1. Protocol, per adjudicated pilot entry with a concrete
leaf (221 of 271):

  1. Truth is read through the R58.7 errata as a PER-NAME table
     (C6→C2 and H1→A2 unconditional; B3→B2 only for Castravet/Robu/
     Marinescu; C3→C5 only for the 9 named Maghrebi bearers — blanket
     remaps would corrupt genuine Greek/Levantine labels).
  2. The surname is extracted exactly as
     manager_optimized._detect_by_surname_fasttext does (pre-comma,
     else last token, lowercased).
  3. Predict all label probabilities via model.f.predict (the
     NumPy-2-safe low-level API), restrict to leaves whose group family
     matches the truth's (the anchor), take the argmax.
  4. Correct iff argmax == errata-corrected truth. Per-family rows are
     printed for the regression-floor gate (no family may drop > 3
     correct vs the reference row).

    PYTHONPATH=. python3 tools/eval_within_anchor.py <model.ftz|.bin>

The raw top-1 column is informational only (the runtime never uses
unanchored predictions).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

REMAP = {"C6": "C2", "H1": "A2"}
ROMANIAN_B3 = {"Ana-Maria Castravet", "Bogdan Robu", "George Marinescu"}
MAGHREBI_C3 = {
    "M. Nabil Kazi-Tani",
    "N. Touzi",
    "René Aïd",
    "Mehdi Talbi",
    "Madiha Nadri",
    "Nabil Kazi-Tani",
    "Wissal Sabbagh",
    "Imen Ben Tahar",
    "Ahmed El Alaoui",
}


def truth(entry: dict) -> str | None:
    leaf = entry["leaf"]
    if leaf in ("GROUP_ONLY", "UNKNOWN"):
        return None
    if leaf == "B3" and entry["name"] in ROMANIAN_B3:
        return "B2"
    if leaf == "C3" and entry["name"] in MAGHREBI_C3:
        return "C5"
    return REMAP.get(leaf, leaf)


def surname(name: str) -> str:
    if "," in name:
        return name.split(",")[0].strip().lower()
    parts = name.strip().split()
    return parts[-1].lower() if parts else ""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    import fasttext

    model = fasttext.load_model(sys.argv[1])

    def predict_all(text: str) -> list[tuple[str, float]]:
        pairs = model.f.predict(text, 40, 0.0, "strict")
        return [(str(l).replace("__label__", ""), float(p)) for p, l in pairs]

    entries = json.load(open(REPO / "data" / "eval" / "pilot_adjudicated.json"))
    n = ok = top1_ok = 0
    fam_n: dict[str, int] = defaultdict(int)
    fam_ok: dict[str, int] = defaultdict(int)
    wrongs: list[tuple[str, str, str, float]] = []
    for a in entries:
        t = truth(a)
        if t is None:
            continue
        s = surname(a["name"])
        preds = predict_all(s)
        if not preds:
            continue
        if preds[0][0] == t:
            top1_ok += 1
        in_group = [(l, p) for l, p in preds if l and l[0] == t[0]]
        if not in_group:
            continue
        n += 1
        fam_n[t[0]] += 1
        if in_group[0][0] == t:
            ok += 1
            fam_ok[t[0]] += 1
        else:
            wrongs.append((a["name"], t, in_group[0][0], round(in_group[0][1], 3)))

    print(f"{sys.argv[1]}")
    print(
        f"  within-anchor {ok}/{n} = {ok / n:.1%}   (raw top-1 {top1_ok}, informational)"
    )
    print(
        "  per-family:", "  ".join(f"{f}:{fam_ok[f]}/{fam_n[f]}" for f in sorted(fam_n))
    )
    for w in wrongs:
        print("   wrong:", w)
    print(f"  ({len(wrongs)} within-anchor errors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
