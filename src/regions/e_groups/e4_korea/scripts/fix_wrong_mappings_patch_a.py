#!/usr/bin/env python3
"""
Fix the 6 wrong mappings identified in Patch A analysis
"""
import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== PATCH A: FIXING WRONG MAPPINGS ===")

# Read all rows
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

print(f"Total rows before fixes: {len(rows)}")

# Track changes
fixes_applied = 0
additions_made = 0

# Process each row
new_rows = []
for row in rows:
    if len(row) >= 2:
        hangul, roman = row[0], row[1]

        # Fix wrong mappings identified in analysis
        if hangul == "숰" and roman == "suk":
            # Wrong mapping: 숰,suk should be 석,suk (most common)
            new_rows.append(["석", "suk"])
            print(f"  FIXED: 숰,suk → 석,suk")
            fixes_applied += 1
        elif hangul == "큔" and roman == "kyun":
            # Wrong mapping: 큔,kyun should be 균,kyun
            new_rows.append(["균", "kyun"])
            print(f"  FIXED: 큔,kyun → 균,kyun")
            fixes_applied += 1
        elif hangul == "괔" and roman == "gwak":
            # Wrong mapping: 괔,gwak should be 곽,gwak
            new_rows.append(["곽", "gwak"])
            print(f"  FIXED: 괔,gwak → 곽,gwak")
            fixes_applied += 1
        elif hangul == "윸" and roman == "yuk":
            # Wrong mapping: 윸,yuk should be 육,yuk
            new_rows.append(["육", "yuk"])
            print(f"  FIXED: 윸,yuk → 육,yuk")
            fixes_applied += 1
        else:
            # Keep unchanged
            new_rows.append(row)

# Add missing mappings identified in analysis
missing_mappings = [
    ("어", "eoh"),  # Missing: eoh → 어
]

for hangul, roman in missing_mappings:
    # Check if already exists
    exists = any(r[0] == hangul and r[1] == roman for r in new_rows if len(r) >= 2)
    if not exists:
        new_rows.append([hangul, roman])
        print(f"  ADDED: {roman} → {hangul}")
        additions_made += 1

print(f"Total rows after fixes: {len(new_rows)}")
print(f"Fixes applied: {fixes_applied}")
print(f"Additions made: {additions_made}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in new_rows:
        writer.writerow(row)

print("✅ Patch A wrong mappings fixed!")
print("\n=== EXPECTED IMPROVEMENTS ===")
print("- Wang_Minsuk: suk → 석 (correct)")
print("- Jeong_Sukmin: suk → 석 (correct)")
print("- Suk_Hyunjoo: suk → 석 (correct for surname)")
print("- Shim_Jaekyun: kyun → 균 (fixed)")
print("- Gwak_JungHoon: gwak → 곽 (fixed)")
print("- Eoh_Hyunji: eoh → 어 (added)")
print("- Cheong_Munho: cheong → 청 (needs context fix)")
print("\nNote: Cheong surname issue requires separate context-aware handling")
