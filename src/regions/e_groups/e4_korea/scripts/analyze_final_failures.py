#!/usr/bin/env python3
"""
Analyze the remaining 53 failures to understand patterns
"""

import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# from converter import eng2kor, kor2eng

# Load test data
with open("data/korean.yaml", encoding="utf8") as f:
    data = yaml.safe_load(f)


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Categorize failures
eng_kor_failures = []
roundtrip_failures = []
total_failures = 0

print("=== ANALYZING REMAINING 53 FAILURES ===\n")

for name, info in data.items():
    if isinstance(info, dict):
        canonical = info.get("CanonicalLatin")
        expected_korean = find_hangul(info.get("AllCommonVariants", []))

        if canonical and expected_korean:
            actual_korean = eng2kor(canonical)

            # Check eng→kor failure
            if actual_korean != expected_korean:
                eng_kor_failures.append(
                    {
                        "name": name,
                        "input": canonical,
                        "expected": expected_korean,
                        "actual": actual_korean,
                    }
                )
                total_failures += 1
            elif actual_korean:
                # Check roundtrip
                roundtrip = kor2eng(actual_korean, canonical)
                if (
                    not roundtrip
                    or roundtrip.replace(" ", "").lower()
                    != canonical.replace(", ", "").replace(" ", "").lower()
                ):
                    roundtrip_failures.append(
                        {
                            "name": name,
                            "original": canonical,
                            "korean": actual_korean,
                            "roundtrip": roundtrip,
                        }
                    )
                    total_failures += 1

print(f"Total failures: {total_failures}")
print(f"Eng→Kor failures: {len(eng_kor_failures)}")
print(f"Roundtrip failures: {len(roundtrip_failures)}")

# Analyze eng→kor failures
print("\n=== ENG→KOR FAILURES ===")
if eng_kor_failures:
    print("First 10:")
    for i, fail in enumerate(eng_kor_failures[:10]):
        print(f"\n{fail['name']}:")
        print(f"  Input: {fail['input']}")
        print(f"  Expected: {fail['expected']}")
        print(f"  Actual: {fail['actual']}")

        # Analyze why it failed
        if fail["actual"] is None:
            print("  Issue: Conversion returned None")
        else:
            # Find character differences
            exp = fail["expected"]
            act = fail["actual"]
            if len(exp) == len(act):
                diffs = []
                for j, (e, a) in enumerate(zip(exp, act)):
                    if e != a:
                        diffs.append(f"pos {j}: {e}→{a}")
                if diffs:
                    print(f"  Differences: {', '.join(diffs[:3])}")

# Analyze roundtrip failures
print("\n=== ROUNDTRIP FAILURES ===")
if roundtrip_failures:
    print("Categorizing by pattern...")

    patterns = {
        "hyphen_loss": [],
        "variant_spelling": [],
        "spacing_issue": [],
        "other": [],
    }

    for fail in roundtrip_failures:
        orig = fail["original"].lower()
        rt = (fail["roundtrip"] or "").lower()

        # Categorize
        if "-" in orig and "-" not in rt:
            patterns["hyphen_loss"].append(fail)
        elif any(var in rt for var in ["jung", "jeong", "jong", "chung"]):
            patterns["variant_spelling"].append(fail)
        elif orig.replace(" ", "") == rt.replace(" ", ""):
            patterns["spacing_issue"].append(fail)
        else:
            patterns["other"].append(fail)

    for pattern, cases in patterns.items():
        if cases:
            print(f"\n{pattern.upper()}: {len(cases)} cases")
            for case in cases[:3]:
                print(f"  {case['name']}: {case['original']} → {case['roundtrip']}")

# Suggest targeted fixes
print("\n=== SUGGESTED FIXES ===")
print("1. Hyphen preservation in roundtrip conversion")
print("2. Handle 'j.' pattern correctly (Kim J. case)")
print("3. Add missing rare syllable mappings")
print("4. Improve context-sensitive conversions")
print(
    f"\nWith these fixes, we could potentially reach {680 + total_failures} / 733 = {(680 + total_failures)/733*100:.1f}%"
)
