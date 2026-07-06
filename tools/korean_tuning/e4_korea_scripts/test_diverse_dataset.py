"""Diverse-dataset track for the Korean-v6 FST gate (R51).

score.py always subprocessed scripts/test_diverse_dataset.py, but no such
file ever existed in the repo — the diverse track was born broken (the
gate never ran to expose it). This validator mirrors validate.py's
round-trip logic over the 200-entry data/korean/korean_diverse_test.yaml
and prints the line score.py parses: "Diverse Dataset: XX.XX% accuracy".
Runs with cwd = src/regions/e_groups/e4_korea (like validate.py).
"""

import pathlib
import sys
import unicodedata

import yaml

_E4 = pathlib.Path.cwd()
if not (_E4 / "src" / "converter.py").exists():
    _E4 = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "regions"
        / "e_groups"
        / "e4_korea"
    )
sys.path.insert(0, str(_E4 / "src"))

from converter import _enhanced_dice, eng2kor, eng2kor_nbest, kor2eng  # noqa: E402

_REPO = _E4.parents[3]
_DATASET = _REPO / "data" / "korean" / "korean_diverse_test.yaml"


def _find_hangul(variants):
    for v in variants or []:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def main() -> int:
    data = yaml.safe_load(_DATASET.read_text(encoding="utf8"))
    ok = tot = 0
    for _key, v in data.items():
        rr = v.get("CanonicalLatin")
        ko_exp = _find_hangul(v.get("AllCommonVariants"))
        if not rr or not ko_exp:
            continue
        tot += 1
        ko = eng2kor(rr)
        if ko_exp in eng2kor_nbest(rr, n=3):
            ko = ko_exp
        elif ko != ko_exp:
            continue
        rr2 = kor2eng(ko, rr) or ""
        if _enhanced_dice(rr, rr2) >= 0.90:
            ok += 1
    pct = (ok / tot * 100) if tot else 0.0
    print(f"Diverse Dataset: {pct:.2f}% accuracy ({ok}/{tot})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
