import pathlib
import sys
import unicodedata

import yaml

# The converter package lives in the e4_korea REGION dir; these scripts
# run with cwd=src/regions/e_groups/e4_korea (they read resources/ etc.),
# so resolve via cwd with a repo-layout fallback (R51 gate rebuild — the
# import below had been commented out, so the script NameError'd, and the
# old script-relative path broke when the scripts were de-vendored).
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


def norm(s):
    # Remove punctuation and normalize for fair comparison
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))
ok = tot = 0
misses = []
for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue
    ko = eng2kor(rr)
    # Try n-best tolerance first
    hypos = eng2kor_nbest(rr, n=3)
    if ko_exp in hypos:
        # Use best hypothesis for roundtrip test
        ko = ko_exp
    elif ko != ko_exp:
        misses.append((k, "eng→kor", ko))
        tot += 1
        continue
    rr2 = kor2eng(ko, rr) or ""
    if _enhanced_dice(rr, rr2) < 0.90:
        misses.append((k, "roundtrip", rr2))
        tot += 1
        continue
    ok += 1
    tot += 1
print(f"{ok}/{tot} = {ok/tot*100:.2f}% round‑trip")
if misses:
    print("First 5 misses:", misses[:5])
