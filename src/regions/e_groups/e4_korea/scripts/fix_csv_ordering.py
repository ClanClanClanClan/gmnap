#!/usr/bin/env python3
"""Fix the ordering of hangul,roman in the incorrectly added entries."""
import csv
from pathlib import Path

csv_path = Path("resources/rr_syllable_map.csv")

# Read all rows
rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 5:
            rows.append(row)

# Fix the last entries that have wrong order
fixed = 0
for i in range(len(rows)):
    hangul, roman = rows[i][0], rows[i][1]
    # Check if this looks like it needs swapping
    # Hangul characters are in range \uac00-\ud7af
    if roman and all('\uac00' <= c <= '\ud7af' for c in roman):
        # Swap them
        rows[i][0], rows[i][1] = rows[i][1], rows[i][0]
        fixed += 1
        print(f"Fixed: {rows[i][1]} → {rows[i][0]}")

# Write back
with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"\nFixed {fixed} rows")
print(f"Total rows: {len(rows)}")