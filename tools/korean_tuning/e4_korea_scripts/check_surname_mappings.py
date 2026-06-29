#!/usr/bin/env python3
"""
Check how problematic surname romanizations are currently mapped
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from preprocess import tokenise

# from converter import eng2kor
from segment import segment

# Problem surnames identified
problem_surnames = {
    "Chun": {"current": "춘", "expected": "전"},
    "Chang": {"current": "창", "expected": "장"},
    "Paek": {"current": "팩", "expected": "백"},
    "Pak": {"current": "팤", "expected": "박"},
}

print("=== SURNAME MAPPING ANALYSIS ===")
for surname, mapping in problem_surnames.items():
    result = eng2kor(surname)
    print(f"\n{surname}:")
    print(f"  Current result: {result}")
    print(f"  Expected: {mapping['expected']}")
    print(f"  Status: {'✅ CORRECT' if result == mapping['expected'] else '❌ WRONG'}")

    # Check segmentation
    tokens = list(tokenise(surname))
    segments = []
    for tok in tokens:
        segments.extend(segment(tok))
    print(f"  Tokenization: {tokens}")
    print(f"  Segmentation: {segments}")

# Test a few specific failing cases
print("\n=== SPECIFIC FAILING CASES ===")
test_cases = ["Chun, Youngsup", "Chang, Bum-Hee", "Paek, Yong-Ho", "Pak, Hyeong-Ju"]

for case in test_cases:
    result = eng2kor(case)
    print(f"{case} → {result}")
