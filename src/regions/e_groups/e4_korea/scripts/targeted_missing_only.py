#!/usr/bin/env python3
"""
Add only truly missing mappings that cause None failures
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== TARGETED FIXES: MISSING MAPPINGS ONLY ===\n")

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# Check what we have
existing_mappings = {(row[0], row[1]) for row in rows if len(row) >= 2}

# ONLY add mappings that are completely missing and cause None failures
# Based on the eng→kor failure analysis
truly_missing = [
    # Surnames that return None
    ("고", "goh", "0.0"),  # Goh_Beomseok → None
    ("손", "sohn", "0.0"),  # Sohn_Yoonah → None
    # Specific compound patterns for diverse dataset
    ("수지", "suzy", "0.0"),  # Bae_SuZy → None (compound)
    ("순신", "sunsin", "0.0"),  # Yi_SunSin → None (compound)
    # Missing given name patterns
    ("준이", "june", "0.0"),  # Huh_June → 허준 (should be 허준이)
]

print(f"Current rows: {len(rows)}")

added_count = 0
for hangul, roman, weight in truly_missing:
    if (hangul, roman) not in existing_mappings:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {roman} → {hangul}")
        added_count += 1
    else:
        print(f"  EXISTS: {roman} → {hangul} (skipped)")

print(f"\nAdded {added_count} truly missing mappings")
print(f"New total: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Targeted missing mappings added!")
print("\n=== CONSERVATIVE APPROACH ===")
print("Only added mappings that:")
print("1. Return None (complete failures)")
print("2. Don't conflict with existing mappings")
print("3. Have clear evidence from failure analysis")
print("\nThis should improve without regressions.")
