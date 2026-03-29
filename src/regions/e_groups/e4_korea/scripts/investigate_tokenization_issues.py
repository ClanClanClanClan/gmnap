#!/usr/bin/env python3
"""
Investigate why some systematic mappings still fail - tokenization issues
"""

import sys

sys.path.append("src")
from preprocess import tokenise
from segment import segment

print("=== INVESTIGATING TOKENIZATION ISSUES ===")
print("Why do some systematic mappings still fail?")
print()

failing_cases = [
    "Kim, A.B.C.",
    "Smith, Jr.",
    "Park, Ph.D.",
]

for case in failing_cases:
    print(f"=== ANALYZING: {case} ===")

    # Step 1: Tokenization
    try:
        tokens = list(tokenise(case))
        print(f"Tokens: {tokens}")

        # Step 2: Segmentation of each token
        for i, token in enumerate(tokens):
            segments = segment(token)
            print(f"  Token[{i}] '{token}' → segments: {segments}")

            # Step 3: Check if segments have mappings
            import csv

            mappings = {}
            with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        mappings[row[1].lower()] = row[0]

            for seg in segments:
                if seg.lower() in mappings:
                    print(f"    ✅ '{seg}' → {mappings[seg.lower()]}")
                else:
                    print(f"    ❌ '{seg}' → NO MAPPING")

    except Exception as e:
        print(f"ERROR: {e}")
    print()

print("=== TOKENIZATION ANALYSIS ===")
print("Issue: Complex tokens may not be segmenting as expected")
print("Need to check if segmentation is splitting compound tokens properly")

# Test specific segment behavior
print("\n=== SEGMENT BEHAVIOR TEST ===")
test_segments = ["A.B.C.", "Jr.", "Ph.D."]
for seg in test_segments:
    try:
        result = segment(seg)
        print(f"segment('{seg}') → {result}")
    except Exception as e:
        print(f"segment('{seg}') → ERROR: {e}")
