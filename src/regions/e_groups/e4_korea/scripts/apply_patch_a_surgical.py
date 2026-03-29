#!/usr/bin/env python3
"""
Apply Patch A: Surgical addition of ambiguous syllable mappings
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

# Patch A: Only the 8 specific ambiguous mappings that are guaranteed improvements
patch_a_mappings = [
    # Cases where current mapping is wrong and this fixes it
    ("숙", "suk"),  # For given names like Minsuk - adds alternative to existing suk→석
    ("균", "kyun"),  # For Jaekyun - adds missing mapping
    ("곽", "gwak"),  # For Gwak surnames - adds alternative to kwak→곽
    ("육", "yuk"),  # For Yook surnames - adds missing mapping
    ("어", "eoh"),  # For Eoh surnames - adds missing mapping
    ("정", "cheong"),  # For Cheong surnames - adds alternative to jeong→정
]

print("=== APPLYING PATCH A: SURGICAL AMBIGUOUS MAPPINGS ===")
print("Adding 6 specific mappings for known failure cases...")

# Read existing mappings
existing_mappings = set()
new_rows = []

with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    for row in csv.reader(f):
        if len(row) >= 2:
            hangul, roman = row[0], row[1]
            existing_mappings.add((hangul, roman))
            new_rows.append(row)

print(f"Existing mappings: {len(existing_mappings)}")

# Add only new mappings that don't already exist
added_count = 0
for hangul, roman in patch_a_mappings:
    if (hangul, roman) not in existing_mappings:
        new_rows.append([hangul, roman])
        print(f"  ADDED: {hangul},{roman}")
        added_count += 1
    else:
        print(f"  EXISTS: {hangul},{roman} (skipped)")

print(f"Added {added_count} new mappings")
print(f"Total rows: {len(new_rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in new_rows:
        writer.writerow(row)

print("✅ Patch A applied surgically!")
print("\n=== TARGET CASES ===")
print("- Wang_Minsuk: suk→숙 now available")
print("- Shim_Jaekyun: kyun→균 now available")
print("- Gwak_JungHoon: gwak→곽 now available")
print("- Yook_JiSun: yuk→육 now available")
print("- Eoh_Hyunji: eoh→어 now available")
print("- Cheong_Munho: cheong→정 now available")
