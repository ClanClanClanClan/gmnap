#!/usr/bin/env python3
"""Reproduce the R58 raw-fastText-promotion rejection table.

Question answered: if the pipeline promoted the surname-fastText leaf for
every scorer-abstained name whenever the model's confidence >= t (NO group
anchor), what would the verifiable-leaf precision be?

Data (committed under data/eval/, produced by the R58 pilot + the 40-agent
adjudication workflow):
  - pilot_abstained.json      271 scorer-abstained real arXiv author strings
  - pilot_ft_verdicts.json    the model's (label, prob) for each
  - pilot_adjudicated.json    multi-agent adjudicated ground truth
                              (2 independent lenses + reconciler per name)

Answer (this is why the ft_only_high_conf branch was removed and no
threshold knob may reinstate raw promotion — the project's contract is
100% emitted-leaf precision; 'overclaim' = leaf emitted where ground truth
is GROUP_ONLY):

    t      converted  correct  WRONG (cross-family)  overclaim  precision
    0.85   172        99       48     25             13         67.3%
    0.99    72        51       14      7              5         78.5%

Run: PYTHONPATH=. python3 tools/ft_threshold_sweep.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "data" / "eval"

# Leaf -> group letter for cross-family accounting (mirrors LEAF_TO_GROUP
# at the granularity adjudication uses).
_FAMILY = {
    "A1": "A",
    "A2": "A",
    "A3": "A",
    "A4": "A",
    "A5": "A",
    "B1": "B",
    "B2": "B",
    "B3": "B",
    "C1": "C",
    "C2": "C",
    "C3": "C",
    "C4": "C",
    "C5": "C",
    "C6": "C",
    "C7": "C",
    "C8": "C",
    "C9": "C",
    "D1": "D",
    "D2": "D",
    "D3": "D",
    "D4": "D",
    "D5": "D",
    "E1": "E",
    "E2": "E",
    "E3": "E",
    "E4": "E",
    "E5": "E",
    "E6": "E",
    "E7": "E",
    "F1": "F",
    "F2": "F",
    "F3": "F",
    "F4": "F",
    "G1": "G",
    "H1": "H",
}


def main() -> int:
    verdicts = json.loads((EVAL / "pilot_ft_verdicts.json").read_text())
    adjudicated = {
        a["name"]: a for a in json.loads((EVAL / "pilot_adjudicated.json").read_text())
    }

    print(
        f"{'t':>6} {'converted':>10} {'correct':>8} {'WRONG':>6} "
        f"{'(cross-family)':>14} {'overclaim':>10} {'unverif.':>9} {'precision':>10}"
    )
    for t in (0.85, 0.90, 0.95, 0.99, 0.999):
        conv = correct = wrong = cross = overclaim = unverifiable = 0
        for name, v in verdicts.items():
            if not v or v["prob"] < t:
                continue
            conv += 1
            adj = adjudicated.get(name)
            if adj is None or adj["leaf"] == "UNKNOWN":
                unverifiable += 1
            elif adj["leaf"] == "GROUP_ONLY":
                overclaim += 1  # any leaf emission over-claims group-only truth
            elif v["label"] == adj["leaf"]:
                correct += 1
            else:
                wrong += 1
                if _FAMILY.get(v["label"]) != _FAMILY.get(adj["leaf"]):
                    cross += 1
        verifiable = correct + wrong
        prec = correct / verifiable if verifiable else 0.0
        print(
            f"{t:>6} {conv:>10} {correct:>8} {wrong:>6} {cross:>14} "
            f"{overclaim:>10} {unverifiable:>9} {prec:>9.1%}"
        )

    print(
        "\nVerdict: raw promotion (no group anchor) is precision-unsafe at "
        "EVERY threshold — the model asserts wrong leaves at prob 1.0. "
        "fastText emits only behind a group anchor (scorer, weak-evidence, "
        "or orthographic). See docs/calibration.md (R58)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
