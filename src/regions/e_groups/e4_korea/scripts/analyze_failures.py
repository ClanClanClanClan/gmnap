#!/usr/bin/env python3
"""
Analyze validation failures systematically to identify patterns
"""
import yaml
import unicodedata
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor, kor2eng


def norm(s):
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


# Load test data
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

# Analyze failures by type
eng_to_kor_failures = []
roundtrip_failures = []
total_cases = 0

for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    total_cases += 1
    ko = eng2kor(rr)

    if ko != ko_exp:
        eng_to_kor_failures.append(
            {
                "name": k,
                "input": rr,
                "expected": ko_exp,
                "got": ko,
                "surname": rr.split("_")[0] if "_" in rr else rr.split()[0],
            }
        )
        continue

    # Check roundtrip
    rr2 = kor2eng(ko, rr) or ""
    if dice(norm(rr), norm(rr2)) < 0.97:
        roundtrip_failures.append(
            {
                "name": k,
                "input": rr,
                "korean": ko,
                "got_romanization": rr2,
                "dice_score": dice(norm(rr), norm(rr2)),
            }
        )

print("=== FAILURE ANALYSIS ===")
print(f"Total test cases: {total_cases}")
print(f"Eng→Kor failures: {len(eng_to_kor_failures)}")
print(f"Roundtrip failures: {len(roundtrip_failures)}")
print(f"Total failures: {len(eng_to_kor_failures) + len(roundtrip_failures)}")
print(
    f"Success rate: {(total_cases - len(eng_to_kor_failures) - len(roundtrip_failures))/total_cases*100:.1f}%"
)

print("\n=== ENG→KOR FAILURE PATTERNS ===")
# Group by surname
surname_failures = {}
for f in eng_to_kor_failures:
    surname = f["surname"]
    if surname not in surname_failures:
        surname_failures[surname] = []
    surname_failures[surname].append(f)

# Sort by frequency
sorted_surnames = sorted(surname_failures.items(), key=lambda x: len(x[1]), reverse=True)

print("Top surname failure patterns:")
for surname, failures in sorted_surnames[:10]:
    print(f"\n{surname} ({len(failures)} failures):")
    for f in failures[:3]:  # Show first 3 examples
        print(f"  {f['input']} → got:{f['got']} expected:{f['expected']}")

print("\n=== ROUNDTRIP FAILURE EXAMPLES ===")
for f in roundtrip_failures[:10]:
    print(
        f"{f['name']}: {f['input']} → {f['korean']} → {f['got_romanization']} (dice: {f['dice_score']:.3f})"
    )
