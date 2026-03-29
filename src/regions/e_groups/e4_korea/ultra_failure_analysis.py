import yaml
import sys

sys.path.append("src")
# from converter import eng2kor, kor2eng, eng2kor_nbest
import unicodedata
from collections import Counter, defaultdict


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

# Ultra-detailed failure analysis
failures = []
roundtrip_issues = []
conversion_issues = []

for name, info in data.items():
    rr = info.get("CanonicalLatin")
    ko_exp = find_hangul(info.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    hypos = eng2kor_nbest(rr, n=3)

    if ko_exp in hypos:
        ko = ko_exp  # Use expected for roundtrip test
    elif ko != ko_exp:
        conversion_issues.append(
            {
                "name": name,
                "input": rr,
                "expected": ko_exp,
                "actual": ko,
                "hypos": hypos,
            }
        )
        continue

    # Test roundtrip
    rr2 = kor2eng(ko, rr) or ""
    dice_score = dice(norm(rr), norm(rr2))

    if dice_score < 0.90:
        roundtrip_issues.append(
            {
                "name": name,
                "input": rr,
                "korean": ko,
                "roundtrip": rr2,
                "dice": dice_score,
                "norm_input": norm(rr),
                "norm_output": norm(rr2),
            }
        )

print(f"=== ULTRA FAILURE ANALYSIS ===")
print(f"Conversion failures: {len(conversion_issues)}")
print(f"Roundtrip failures: {len(roundtrip_issues)}")
print(f"Total failures: {len(conversion_issues) + len(roundtrip_issues)}")

print(f"\n=== CONVERSION FAILURES ANALYSIS ===")
for i, failure in enumerate(conversion_issues[:10]):
    print(
        f"{i+1}. {failure['name']}: {failure['input']} → {failure['actual']} (exp: {failure['expected']})"
    )
    if failure["hypos"]:
        print(f"   N-best: {failure['hypos']}")

print(f"\n=== ROUNDTRIP FAILURES ANALYSIS ===")
roundtrip_patterns = defaultdict(list)
for failure in roundtrip_issues:
    # Group by type of mismatch
    pattern = f"{failure['input'][:10]}... → {failure['roundtrip'][:10]}..."
    roundtrip_patterns[pattern].append(failure)

print("Top roundtrip failure patterns:")
for pattern, failures in list(roundtrip_patterns.items())[:10]:
    print(f"{len(failures)}x: {pattern}")
    if failures:
        example = failures[0]
        print(f"    Example: {example['name']} (dice={example['dice']:.3f})")
        print(f"    Input:  '{example['norm_input']}'")
        print(f"    Output: '{example['norm_output']}'")

print(f"\n=== ULTRA-SPECIFIC PATTERNS ===")
# Analyze specific character-level mismatches
char_mismatches = Counter()
for failure in roundtrip_issues:
    input_chars = set(failure["norm_input"])
    output_chars = set(failure["norm_output"])
    mismatches = input_chars.symmetric_difference(output_chars)
    for char in mismatches:
        char_mismatches[char] += 1

print("Most problematic characters in roundtrip:")
for char, count in char_mismatches.most_common(15):
    print(f"'{char}': {count} mismatches")

# Save detailed failure data for optimization
import json

with open("ultra_failure_data.json", "w", encoding="utf8") as f:
    json.dump(
        {
            "conversion_failures": conversion_issues,
            "roundtrip_failures": roundtrip_issues,
            "char_mismatches": dict(char_mismatches),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

print(f"\n✓ Detailed failure data saved to ultra_failure_data.json")
