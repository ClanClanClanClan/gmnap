#!/usr/bin/env python3
"""
Analyze current Diverse dataset failures to identify remaining patterns
"""
import sys

sys.path.append('src')
import json

# Read diverse dataset
import yaml
from converter import eng2kor

with open('data/korean_diverse_test.yaml', 'r') as f:
    diverse_data = yaml.safe_load(f)

current_failures = []
passes = 0
total = 0

for key, data in diverse_data.items():
    name = data['CanonicalLatin'] 
    # Find hangul in AllCommonVariants
    expected_kor = None
    for variant in data['AllCommonVariants']:
        # Korean characters (hangul) have Unicode range
        if any('\uAC00' <= char <= '\uD7AF' for char in variant):
            expected_kor = variant
            break
    
    total += 1
    
    if expected_kor:
        actual = eng2kor(name)
        if actual != expected_kor:
            current_failures.append({
                'name': name,
                'expected': expected_kor,
                'actual': actual,
                'reason': f'expected {expected_kor}, got {actual}'
            })
        else:
            passes += 1

print(f"Current Diverse Performance: {passes}/{total} = {passes/total*100:.2f}%")
print(f"Current failures: {len(current_failures)}")
print("\nCurrent failure patterns:")

for i, failure in enumerate(current_failures[:10]):  # Show first 10
    print(f"{i+1:2d}. {failure['name']}")
    print(f"    Expected: {failure['expected']}")
    print(f"    Actual: {failure['actual']}")
    print()

# Save full failure list
with open('data/current_diverse_failures.json', 'w') as f:
    json.dump(current_failures, f, indent=2, ensure_ascii=False)

print("Full failure list saved to data/current_diverse_failures.json")