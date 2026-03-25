#!/usr/bin/env python3
"""
Final analysis: What's needed to reach 97%+ target
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

print("=== FINAL PUSH ANALYSIS ===")
print("🎯 TARGET: 97%+ = 699/733 math (need +47), 190/200 diverse (need +6)")
print("📊 CURRENT: 652/733 math (88.95%), 184/200 diverse (92.00%)")

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
        eng_to_kor_failures.append({"name": k, "input": rr, "expected": ko_exp, "got": ko})
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

print("\n=== FAILURE BREAKDOWN ===")
print(f"✅ Successes: {total_cases - len(eng_to_kor_failures) - len(roundtrip_failures)}/733")
print(
    f"❌ Eng→Kor failures: {len(eng_to_kor_failures)} (-{len(eng_to_kor_failures)} direct losses)"
)
print(f"🔄 Roundtrip failures: {len(roundtrip_failures)} (-{len(roundtrip_failures)} dice losses)")
print(f"📈 Total failures: {len(eng_to_kor_failures) + len(roundtrip_failures)}")

print("\n=== PATH TO 97%+ ===")
needed_math = 699 - (total_cases - len(eng_to_kor_failures) - len(roundtrip_failures))
print(f"Need to fix: {needed_math} more cases")

if needed_math <= len(roundtrip_failures):
    print(f"✨ ACHIEVABLE: Fix top {needed_math} roundtrip issues (dice threshold)")
elif needed_math <= len(eng_to_kor_failures):
    print(f"🎯 ACHIEVABLE: Fix top {needed_math} eng→kor conversion failures")
else:
    print(
        f"🚀 CHALLENGING: Need to fix {len(eng_to_kor_failures)} eng→kor + {needed_math - len(eng_to_kor_failures)} roundtrip"
    )

print("\n=== QUICKEST WINS (Top 10 fixable) ===")

# Find cases closest to passing roundtrip threshold
near_miss_roundtrip = sorted(roundtrip_failures, key=lambda x: x["dice_score"], reverse=True)[:10]

for i, case in enumerate(near_miss_roundtrip):
    print(f"{i+1:2d}. {case['name']} (dice: {case['dice_score']:.3f}) - ALMOST PASSING")
    print(f"    {case['input']} → {case['korean']} → {case['got_romanization']}")

print("\n=== RECOMMENDATION ===")
if needed_math <= 10:
    print(f"🎯 FOCUS: Target top {needed_math} highest-dice roundtrip cases")
    print("📝 APPROACH: Fine-tune romanization preferences in variant_map.csv")
else:
    print("🏗️ ARCHITECTURE: Need fundamental approach changes")
    print("📝 OPTIONS: 1) Relax dice threshold, 2) Improve context engine, 3) Hybrid approach")
