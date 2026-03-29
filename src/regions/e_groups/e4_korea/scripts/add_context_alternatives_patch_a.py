#!/usr/bin/env python3
"""
Add context-aware alternatives for the remaining Patch A cases
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = (
    f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== PATCH A: ADDING CONTEXT ALTERNATIVES ===")

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# Context-aware alternatives needed:
context_alternatives = [
    ("숙", "suk"),  # Alternative for given names like Wang_Minsuk
    ("정", "cheong"),  # Alternative for surnames like Cheong_Munho
]

print(f"Total rows before alternatives: {len(rows)}")

additions_made = 0
for hangul, roman in context_alternatives:
    # Check if this mapping already exists
    exists = any(len(r) >= 2 and r[0] == hangul and r[1] == roman for r in rows)

    if not exists:
        rows.append([hangul, roman])
        print(f"  ADDED: {roman} → {hangul} (context alternative)")
        additions_made += 1
    else:
        print(f"  EXISTS: {roman} → {hangul} (skipped)")

print(f"Total rows after alternatives: {len(rows)}")
print(f"Additions made: {additions_made}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("✅ Context alternatives added!")
print("\n=== EXPECTED BEHAVIOR ===")
print("Now FST has multiple paths:")
print("- suk → 석 (primary)")
print("- suk → 숙 (alternative for given names)")
print("- cheong → 청 (primary)")
print("- cheong → 정 (alternative for surnames)")
print("\nFST will choose the first path unless constrained by context.")
print("This should improve cases where the primary choice was wrong.")
