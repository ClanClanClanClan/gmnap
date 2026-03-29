#!/usr/bin/env python3
"""
Analyze the specific failure cases mentioned in expert Patch A
"""

import yaml, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
# from converter import eng2kor, kor2eng

# Load test data
with open("data/korean.yaml", encoding="utf8") as f:
    data = yaml.safe_load(f)

# Expert-mentioned target cases for Patch A
target_cases = [
    "Wang_Minsuk",  # suk→숙 issue
    "Jeong_Sukmin",  # suk→석 issue
    "Suk_Hyunjoo",  # suk as surname
    "Shim_Jaekyun",  # kyun→균 missing
    "Gwak_JungHoon",  # gwak→곽 vs kwak
    "Yook_JiSun",  # yuk→육 missing
    "Eoh_Hyunji",  # eoh→어 missing
    "Cheong_Munho",  # cheong→정 vs 청
]

print("=== ANALYZING EXPERT TARGET CASES ===")
print("Cases that Patch A should specifically fix:")

for case_name in target_cases:
    if case_name in data:
        expected_korean = data[case_name]

        # Convert romanized form
        romanized = case_name.replace("_", ", ")
        actual_korean = eng2kor(romanized)

        if actual_korean:
            roundtrip = kor2eng(actual_korean)
            status = "✅ PASS" if actual_korean == expected_korean else "❌ FAIL"
        else:
            roundtrip = None
            status = "💥 NULL"

        print(f"\n{case_name}:")
        print(f"  Input: {romanized}")
        print(f"  Expected: {expected_korean}")
        print(f"  Actual: {actual_korean}")
        print(f"  Roundtrip: {roundtrip}")
        print(f"  Status: {status}")

        # Analyze specific issue
        if case_name.startswith("Wang_Minsuk"):
            print("  Issue: 'suk' in given name should → 숙, not 석")
        elif case_name.startswith("Jeong_Sukmin"):
            print("  Issue: 'suk' in given name should → 석, not 숙")
        elif case_name.startswith("Shim_Jaekyun"):
            print("  Issue: 'kyun' missing mapping → 균")
        elif case_name.startswith("Gwak_"):
            print("  Issue: 'gwak' vs 'kwak' preference → 곽")
    else:
        print(f"\n{case_name}: NOT FOUND in test data")

print(f"\n=== CURRENT MAPPINGS CHECK ===")
from lookup import rom2han

mappings = rom2han()

check_mappings = ["suk", "kyun", "gwak", "kwak", "yuk", "eoh", "cheong"]
for rom in check_mappings:
    if rom in mappings:
        print(f"  {rom} → {mappings[rom]}")
    else:
        print(f"  {rom} → MISSING")
