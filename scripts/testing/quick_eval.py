#!/usr/bin/env python3
"""Quick evaluation on subset of Korean dataset"""

import yaml
import sys

sys.path.append(".")

from scripts.dice_coefficient_impl import roundtrip_score

# Load Korean dataset
data = yaml.safe_load(open("korean.yaml"))

# Test first 10 entries
print("Testing first 10 Korean mathematician names:")
count = 0
for entry_id, entry in list(data.items())[:10]:
    canonical = entry.get("CanonicalLatin", "")
    if canonical:
        score = roundtrip_score(canonical)
        print(f"  {canonical}: {score:.3f}")
        count += 1

print(f"\nTested {count} names")
