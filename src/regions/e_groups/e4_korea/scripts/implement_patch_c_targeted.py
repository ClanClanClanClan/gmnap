#!/usr/bin/env python3
"""
Patch C: Targeted loanword handling without interfering with Korean names
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== PATCH C: TARGETED LOANWORD HANDLING ===")
print("Adding specific foreign name mappings without breaking Korean names...")

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# Only add specific, unambiguous foreign name components
# Avoid single letters and patterns that conflict with Korean romanization
targeted_loanwords = [
    # Full foreign names only (no ambiguity)
    ("린다", "linda", "0.0"),  # Linda
    ("데이빗", "david", "0.0"),  # David
    ("그레이스", "grace", "0.0"),  # Grace
    ("마이클", "michael", "0.0"),  # Michael
    # Unambiguous consonant clusters not used in Korean
    ("브", "br", "0.1"),  # Brian, Brad (but higher weight to avoid conflicts)
    ("프", "fr", "0.1"),  # Frank, Fred
    ("그", "gr", "0.1"),  # Grace, Greg (but only in clusters)
    # Special handling for "J." pattern (Korean practice for initials)
    ("제이", "j.", "0.0"),  # Kim J. → 김제이
]

print(f"Current rows: {len(rows)}")

# Add targeted mappings
added_count = 0
existing_mappings = {(row[0], row[1]) for row in rows if len(row) >= 2}

for hangul, roman, weight in targeted_loanwords:
    if (hangul, roman) not in existing_mappings:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {roman} → {hangul} (weight: {weight})")
        added_count += 1

print(f"\nTotal rows: {len(rows)}")
print(f"Targeted mappings added: {added_count}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Patch C targeted loanword mappings applied!")
print("\n=== SMART APPROACH ===")
print("1. Only full foreign names (linda, david, etc.) - no ambiguity")
print("2. Consonant clusters with higher weights to avoid conflicts")
print("3. Special 'j.' pattern for Korean initial convention")
print("4. No single letters that conflict with Korean surnames (y, i, etc.)")
print("\nThis should improve foreign names without breaking Korean ones.")
