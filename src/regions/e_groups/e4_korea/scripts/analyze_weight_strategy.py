#!/usr/bin/env python3
"""Analyze weight adjustment strategy for conflicting mappings."""
import csv
import json
from collections import defaultdict

# Load current mappings
mappings = defaultdict(list)
with open("resources/rr_syllable_map.csv", 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 2 and not row[0].startswith('#'):
            hangul = row[0]
            roman = row[1]
            weight = float(row[2]) if len(row) > 2 and row[2] else 0.0
            pos = row[4] if len(row) > 4 else ""
            mappings[hangul].append((roman, weight, pos))

# Analyze conflicts
print("=== CONFLICTING MAPPINGS FOR TARGET CHARACTERS ===\n")

# Check 식 (sik vs shik)
print("1. 식 (for Min-Shik):")
for roman, weight, pos in mappings.get('식', []):
    pos_desc = pos or "general"
    print(f"   {roman} (weight={weight}, pos={pos_desc})")
print("   Need: shik (for Min-Shik)")

# Check 섭 (seop/sup vs sub)  
print("\n2. 섭 (for Ji-Sub):")
for roman, weight, pos in mappings.get('섭', []):
    pos_desc = pos or "general"
    print(f"   {roman} (weight={weight}, pos={pos_desc})")
print("   Need: sub (for Ji-Sub)")

# Load failure data
with open("data/expanded_independent_test_results.json") as f:
    results = json.load(f)

# Find all failures that might benefit from weight adjustments
print("\n\n=== OTHER FAILURES THAT MIGHT BENEFIT FROM WEIGHTS ===")
failures_by_issue = defaultdict(list)
for cat_data in results['results_by_category'].values():
    for failure in cat_data['failures']:
        failures_by_issue[failure['issue']].append(failure)

# Low dice scores often benefit from weight adjustments
print("\nLow dice score failures:")
for f in failures_by_issue.get('low_dice_score', [])[:10]:
    print(f"  {f['name']}: {f['expected']} → {f['actual']} (dice={f['dice']:.3f})")

print("\n\n=== WEIGHT ADJUSTMENT STRATEGY ===")
print("1. For conflicts like 식 (sik vs shik), we have options:")
print("   a) Add higher weight to preferred mapping")
print("   b) Use negative weight on less preferred")  
print("   c) Add position-specific override")
print("\n2. For dice score improvements:")
print("   - Boost weights on correct character mappings")
print("   - Reduce weights on incorrect alternatives")

# Check if we can use position-specific overrides
print("\n\n=== POSITION-SPECIFIC OVERRIDE CHECK ===")
print("Checking if position-specific mappings can override general ones...")

# For 식
sik_general = any(pos == "" for r, w, pos in mappings.get('식', []) if r == 'sik')
print(f"\n식→sik is general mapping: {sik_general}")
print("  → Could add 식→shik with pos=G to override for given names")

# For 섭
seop_general = any(pos == "" for r, w, pos in mappings.get('섭', []) if r == 'seop')
sup_general = any(pos == "" for r, w, pos in mappings.get('섭', []) if r == 'sup')
print(f"\n섭→seop is general mapping: {seop_general}")
print(f"섭→sup is general mapping: {sup_general}")
print("  → Could add 섭→sub with pos=G to override for given names")