#!/usr/bin/env python3
"""
Fix systematic surname romanization mapping errors
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

# Define fixes
wrong_mappings = {
    ("춘", "chun"),  # Keep 전,chun instead
    ("창", "chang"),  # Wrong character, should be 장
    ("팩", "paek"),  # Keep 백,paek instead
    ("팪", "paek"),  # Keep 백,paek instead
    ("팤", "pak"),  # Keep 박,pak instead
}

# Add correct mapping for chang → 장
new_mappings = [("장", "chang")]  # Chang should map to same as Jang

# Filter out wrong mappings
filtered_rows = []
removed_count = 0

for h, r in rows:
    if (h, r) in wrong_mappings:
        print(f"REMOVING: {h},{r}")
        removed_count += 1
    else:
        filtered_rows.append((h, r))

# Add new mappings
for h, r in new_mappings:
    print(f"ADDING: {h},{r}")
    filtered_rows.append((h, r))

print(f"Removed {removed_count} wrong mappings")
print(f"Added {len(new_mappings)} correct mappings")
print(f"Final rows: {len(filtered_rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for h, r in filtered_rows:
        writer.writerow([h, r])

print("✅ Fixed surname mappings!")
print("\nVerifying fixes...")

# Verify the fixes worked
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    new_rows = list(csv.reader(f))

test_roms = ["chun", "chang", "paek", "pak"]
for rom in test_roms:
    print(f"\n{rom}:")
    matches = [(h, r) for h, r in new_rows if r.lower() == rom]
    for h, r in matches:
        print(f"  {h},{r}")
