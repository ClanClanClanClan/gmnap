#!/usr/bin/env python3
"""
Fix roundtrip preferences by adjusting variant map weights
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/variant_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/variant_map.csv", backup_name)
print(f"Backed up variant_map.csv to: {backup_name}")

# Read current variant mappings
with open("resources/variant_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

print(f"Original variant rows: {len(rows)}")

# Add stronger roundtrip preferences
new_variants = [
    # Fix jeong→jong issue (strongest roundtrip preference)
    ("정", "jeong", "SURNAME_0"),  # Prefer jeong for 정 in surnames
    # Fix yi/lee consistency
    ("이", "yi", "SURNAME_0"),  # Prefer yi for 이 in surnames
    # Fix foreign element consistency
    ("계", "gye", "FOREIGN_0"),  # Prefer gye for foreign 계
    ("래", "rae", "FOREIGN_0"),  # Prefer rae for foreign 래
]

# Add new variant mappings
for h, r, tag in new_variants:
    print(f"ADDING: {h},{r},{tag}")
    rows.append((h, r, tag))

print(f"Added {len(new_variants)} roundtrip preference variants")
print(f"Final rows: {len(rows)}")

# Write updated file
with open("resources/variant_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("✅ Added roundtrip preference variants!")

# Show current jeong/jong variants
print(f"\nCurrent 정 variants:")
jeong_variants = [row for row in rows if len(row) >= 2 and row[0] == "정"]
for h, r, *tag in jeong_variants:
    tag_str = tag[0] if tag else ""
    print(f"  {h},{r},{tag_str}")
