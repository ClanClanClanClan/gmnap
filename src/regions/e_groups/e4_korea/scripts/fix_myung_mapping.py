#!/usr/bin/env python3
"""
Surgical fix: Correct myung → 명 mapping (affects 5 cases)
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

# Remove wrong mapping and add correct one
filtered_rows = []
removed_count = 0

for h, r in rows:
    if h == "뮹" and r.lower() == "myung":
        print(f"REMOVING wrong mapping: {h},{r}")
        removed_count += 1
    else:
        filtered_rows.append((h, r))

# Add correct mapping
print(f"ADDING correct mapping: 명,myung")
filtered_rows.append(("명", "myung"))

print(f"Removed {removed_count} wrong mappings")
print(f"Added 1 correct mapping")
print(f"Final rows: {len(filtered_rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for h, r in filtered_rows:
        writer.writerow([h, r])

print("✅ Fixed myung mapping!")

# Verify the fix
print(f"\nVerifying myung mappings:")
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    new_lookup = {r.lower(): h for h, r in csv.reader(f)}

myung_result = new_lookup.get("myung")
myeong_result = new_lookup.get("myeong")
print(f"  myung → {myung_result}")
print(f"  myeong → {myeong_result}")
print(f"  Match: {'✅' if myung_result == myeong_result == '명' else '❌'}")
