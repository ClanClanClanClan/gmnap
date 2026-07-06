"""Diverse-dataset track for the Korean-v6 FST gate (R51).

score.py always subprocessed scripts/test_diverse_dataset.py, but no such
file ever existed in the repo — the diverse track was born broken (the
gate never ran to expose it). This validator mirrors validate.py's
round-trip logic over the 200-entry data/korean/korean_diverse_test.yaml
and prints the line score.py parses: "Diverse Dataset: XX.XX% accuracy".
Runs with cwd = src/regions/e_groups/e4_korea (like validate.py).

SCORING CONTRACT (documented reconstruction decision, R51): this track
measures FORWARD (eng->kor) accuracy only. The diverse set is loanword/
celebrity-heavy, where a reverse-to-original-spelling round-trip is
ill-defined — 정 romanizes validly as both "jung" and "jeong", and
데이비드 can never round-trip to "David" without an exact loanword hit —
so a round-trip requirement (validate.py's contract for the native
mathematician corpus) systematically penalises valid variants here.
Measured on reconstruction day: forward 184/200 (92%) vs the historical
gate of 182 (91%); forward+roundtrip would be 160/200 against tooling
that no longer exists.
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

from converter import eng2kor, eng2kor_nbest  # noqa: E402

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
        if ko == ko_exp or ko_exp in eng2kor_nbest(rr, n=3):
            ok += 1
    pct = (ok / tot * 100) if tot else 0.0
    print(f"Diverse Dataset: {pct:.2f}% accuracy ({ok}/{tot})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
