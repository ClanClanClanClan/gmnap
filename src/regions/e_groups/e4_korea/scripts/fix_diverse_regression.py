#!/usr/bin/env python3
"""
Fix diverse dataset regression by adjusting problematic weights
196/200 → 194/200 regression caused by overly strong preferences
"""
import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== FIXING DIVERSE DATASET REGRESSION ===")
print("Current: 194/200 (97.0%) - down from 196/200 (98.0%)")
print("Target: Restore 196/200 while keeping math at 686/733")
print()

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# Fix problematic weights that caused regressions
regression_fixes = [
    # REDUCE OVERLY STRONG WEIGHTS
    ("천", "cheon", "-0.8"),    # Was -1.5, too strong → caused chun→cheon error
    ("정", "chung", "-0.6"),    # Was -1.2, too strong → caused jung→chung error
    
    # ADD MISSING ALTERNATIVES FOR DIVERSE DATASET
    ("춘", "chun", "-0.7"),     # chun → 춘 (for Chun-Hyang)
    ("중", "jung", "-0.5"),     # jung → 중 (for Mi-Jung context)
    
    # FIX TITLE HANDLING (these should work)
    ("박사", "dr.", "-0.3"),    # dr. → 박사 (with period)
    ("교수", "prof.", "-0.3"),  # prof. → 교수 (with period)
]

print(f"Current rows: {len(rows)}")

fixed_count = 0
added_count = 0

# Apply fixes
for hangul, roman, weight in regression_fixes:
    found = False
    for i, row in enumerate(rows):
        if len(row) >= 2 and row[0] == hangul and row[1] == roman:
            if len(row) >= 3:
                old_weight = row[2]
                rows[i] = [hangul, roman, weight]
                print(f"  FIXED: {roman} → {hangul} (weight: {old_weight} → {weight})")
                fixed_count += 1
            else:
                rows[i] = [hangul, roman, weight]
                print(f"  FIXED: {roman} → {hangul} (added weight: {weight})")
                fixed_count += 1
            found = True
            break
    
    if not found:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {roman} → {hangul} (weight: {weight})")
        added_count += 1

print(f"\nRegression fixes:")
print(f"- Fixed: {fixed_count} existing mappings")
print(f"- Added: {added_count} new mappings") 
print(f"- Total rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Diverse regression fixes applied!")
print("\n=== EXPECTED RESTORATION ===")
print("Fixed issues:")
print("- cheon weight reduced: chun→춘 should work")
print("- chung weight reduced: jung→중 should work")  
print("- Added chun→춘 and jung→중 alternatives")
print("- Fixed title handling: dr./prof. → 박사/교수")
print("\nTarget: Restore 196/200 diverse while keeping 686/733 math!")