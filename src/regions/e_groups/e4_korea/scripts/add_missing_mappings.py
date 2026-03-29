#!/usr/bin/env python3
"""
Add missing romanization mappings that cause None failures
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

# Read current mappings
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

print(f"Original rows: {len(rows)}")

# New mappings to add
new_mappings = [
    ("고", "goh"),  # Goh surname variant (like Go)
    ("손", "sohn"),  # Sohn surname variant (like Son)
    ("린다", "linda"),  # Foreign given name Linda → 린다
    ("제이", "j"),  # Initial J → 제이 (phonetic)
]

# Add new mappings
for h, r in new_mappings:
    print(f"ADDING: {h},{r}")
    rows.append((h, r))

print(f"Added {len(new_mappings)} missing mappings")
print(f"Final rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for h, r in rows:
        writer.writerow([h, r])

print("✅ Added missing mappings!")

# Verify the additions
print("\nVerifying additions...")
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    new_lookup = {r.lower(): h for h, r in csv.reader(f)}

for h, r in new_mappings:
    result = new_lookup.get(r.lower())
    print(f"  {r} → {result} {'✅' if result == h else '❌'}")
