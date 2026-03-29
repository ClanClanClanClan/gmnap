#!/usr/bin/env python3
"""
Verify Test Set Corruption
"""

import json
from collections import Counter

# Load test set
with open("data/ml_training/test_split_etymo.json", "r") as f:
    data = json.load(f)

profiles = data["profiles"]
print("=" * 80)
print("TEST SET ANALYSIS - VERIFYING CORRUPTION")
print("=" * 80)

# Region distribution
regions = Counter(p["region"] for p in profiles)
total = len(profiles)

print(f"\nTotal profiles: {total}")
print(f"\nRegion distribution:")
for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True):
    pct = count / total * 100
    print(f"  {region}: {count:4} ({pct:5.2f}%)")

# Check A1 percentage
a1_count = regions.get("A1", 0)
a1_pct = a1_count / total * 100
print(f"\nA1 (Anglo) dominance: {a1_count}/{total} = {a1_pct:.2f}%")

# Check relabeling metadata
meta = data.get("metadata", {})
relabel_info = meta.get("relabeling", {})
print(f"\nRelabeling metadata:")
print(f'  Method: {relabel_info.get("method")}')
print(f'  Changes: {relabel_info.get("changes")}')
print(f'  Pct changed: {relabel_info.get("pct_changed"):.2f}%')

# Find examples where relabeling changed to A1
print(f"\nExamples of profiles relabeled TO A1:")
a1_relabels = []
for p in profiles:
    if p.get("region") == "A1" and p.get("original_affiliation_region") != "A1":
        a1_relabels.append(p)
        if len(a1_relabels) >= 20:
            break

for p in a1_relabels:
    orig = p.get("original_affiliation_region", "?")
    print(f'  {p["name"]:30} {p["country_code"]:3} | {orig} -> A1')

# Summary
print(f'\n{"="*80}')
print(f"VERDICT:")
if a1_pct > 50:
    print(f"  CORRUPTED - A1 dominates with {a1_pct:.1f}% (expected ~15-20%)")
else:
    print(f"  OK - A1 at {a1_pct:.1f}% (reasonable)")
