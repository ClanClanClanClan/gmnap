#!/usr/bin/env python3
"""
Check performance on both math and diverse datasets
"""
import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from converter import eng2kor, kor2eng
import unicodedata


def norm(s):
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))


def dice(a, b):
    a, b = set(zip(a, a[1:])), set(zip(b, b[1:]))
    return 2 * len(a & b) / (len(a) + len(b) or 1)


def find_hangul(variants):
    for v in variants:
        if isinstance(v, str) and any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


print("=== CHECKING BOTH DATASETS ===\n")

# Check math dataset
print("1. MATH DATASET (data/korean.yaml)")
with open("data/korean.yaml", encoding="utf8") as f:
    math_data = yaml.safe_load(f)

math_ok = math_tot = 0
math_failures = []

for k, v in math_data.items():
    if isinstance(v, dict):
        rr = v.get("CanonicalLatin")
        ko_exp = find_hangul(v.get("AllCommonVariants", []))
        if not rr or not ko_exp:
            continue

        ko = eng2kor(rr)
        if ko != ko_exp:
            math_failures.append((k, "eng→kor", rr, ko_exp, ko))
            math_tot += 1
            continue

        rr2 = kor2eng(ko, rr) or ""
        if dice(norm(rr), norm(rr2)) < 0.90:
            math_failures.append((k, "roundtrip", rr, ko, rr2))
            math_tot += 1
            continue

        math_ok += 1
        math_tot += 1

print(f"Math: {math_ok}/{math_tot} = {math_ok/math_tot*100:.2f}%")
print(f"Failures: {len(math_failures)}")

# Check diverse dataset
print("\n2. DIVERSE DATASET (data/korean_diverse_test.yaml)")
with open("data/korean_diverse_test.yaml", encoding="utf8") as f:
    diverse_data = yaml.safe_load(f)

diverse_ok = diverse_tot = 0
diverse_failures = []

for k, v in diverse_data.items():
    if isinstance(v, dict):
        # For diverse dataset, the key itself is the romanized form
        rr = k.replace("_", ", ")
        ko_exp = find_hangul(v.get("AllCommonVariants", []))

        if not ko_exp:
            # Sometimes Korean is in a different field
            if "CanonicalLatin" in v:
                # Try to find Korean in variants
                for variant in v.get("AllCommonVariants", []):
                    if isinstance(variant, str) and all(
                        ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in variant.replace(" ", "")
                    ):
                        ko_exp = variant
                        break

        if not ko_exp:
            continue

        diverse_tot += 1
        ko = eng2kor(rr)

        if ko == ko_exp:
            diverse_ok += 1
        else:
            diverse_failures.append((k, rr, ko_exp, ko))

print(f"Diverse: {diverse_ok}/{diverse_tot} = {diverse_ok/diverse_tot*100:.2f}%")
print(f"Failures: {len(diverse_failures)}")

# Analyze diverse failures
print("\n=== DIVERSE DATASET FAILURE ANALYSIS ===")
print("First 10 failures:")
for i, (name, rom, expected, actual) in enumerate(diverse_failures[:10]):
    print(f"\n{i+1}. {name}:")
    print(f"   Input: {rom}")
    print(f"   Expected: {expected}")
    print(f"   Actual: {actual}")

    # Check if it's a segmentation issue
    if actual and len(actual) != len(expected):
        print(f"   Issue: Length mismatch ({len(actual)} vs {len(expected)})")

# Categorize diverse failures
categories = {
    "foreign_names": [],
    "company_names": [],
    "place_names": [],
    "special_chars": [],
    "other": [],
}

for name, rom, exp, act in diverse_failures:
    lower_name = name.lower()
    if any(x in lower_name for x in ["david", "michael", "john", "mary", "linda"]):
        categories["foreign_names"].append(name)
    elif any(x in lower_name for x in ["company", "corp", "inc", "samsung", "hyundai"]):
        categories["company_names"].append(name)
    elif any(x in lower_name for x in ["seoul", "busan", "street", "road"]):
        categories["place_names"].append(name)
    elif any(x in rom for x in ["@", "#", "&", "%"]):
        categories["special_chars"].append(name)
    else:
        categories["other"].append(name)

print("\n=== DIVERSE FAILURE CATEGORIES ===")
for cat, names in categories.items():
    if names:
        print(f"{cat}: {len(names)} cases")
        print(f"  Examples: {', '.join(names[:3])}")

# Math dataset specific issues
print("\n=== MATH DATASET SPECIFIC ISSUES ===")
eng_kor_fails = [f for f in math_failures if f[1] == "eng→kor"]
roundtrip_fails = [f for f in math_failures if f[1] == "roundtrip"]

print(f"Eng→Kor failures: {len(eng_kor_fails)}")
if eng_kor_fails:
    print("First 5:")
    for f in eng_kor_fails[:5]:
        print(f"  {f[0]}: {f[2]} → {f[4]} (expected: {f[3]})")
