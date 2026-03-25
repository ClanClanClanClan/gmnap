#!/usr/bin/env python3
"""
Debug cases that return None to understand segmentation failures
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor
from segment import segment
from preprocess import tokenise

# Cases that return None
none_cases = ["Kim, J.", "Kim, Linda", "Goh, Beom-Seok", "Sohn, Yoon-Ah"]

print("=== DEBUGGING NONE FAILURES ===")

for case in none_cases:
    print(f"\n{case}:")
    result = eng2kor(case)
    print(f"  Result: {result}")

    # Debug tokenization
    tokens = list(tokenise(case))
    print(f"  Tokens: {tokens}")

    # Debug segmentation for each token
    for i, tok in enumerate(tokens):
        segments = segment(tok)
        print(f"  Token {i} '{tok}' → segments: {segments}")

        # Test each segment individually
        for j, seg in enumerate(segments):
            seg_result = eng2kor(seg)
            print(f"    Segment {j} '{seg}' → {seg_result}")

print(f"\n=== INDIVIDUAL WORD TESTS ===")
individual_tests = ["Kim", "J", "Linda", "Goh", "Beom", "Seok", "Sohn", "Yoon", "Ah"]
for word in individual_tests:
    result = eng2kor(word)
    print(f"{word} → {result}")
