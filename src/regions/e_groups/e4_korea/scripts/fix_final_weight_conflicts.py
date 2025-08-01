#!/usr/bin/env python3
"""
Fix the final weight conflicts for the last 3 problematic characters
"""
import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== FIXING FINAL WEIGHT CONFLICTS ===")
print("Remaining issues:")
print("- 오 → 'o' not 'oh' (both weight 0.0)")
print("- 준 → 'jung' (-0.9) beats 'jun' (-0.8)")  
print("- 제이 → 'je i' not 'j' (compound issue)")
print()

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# FINAL WEIGHT CONFLICT FIXES
final_weight_fixes = [
    # Fix 오 → "oh" preference
    ("오", "oh", "-1.0"),      # Make "oh" stronger than "o" (0.0)
    
    # Fix 준 → "jun" preference  
    ("준", "jun", "-1.2"),     # Make "jun" stronger than "jung" (-0.9)
    
    # Fix 제이 → "j" preference (compound)
    ("제이", "j", "-2.0"),     # Very strong weight for compound initial
    
    # Additional compound fixes for better segmentation
    ("성준", "seongjoon", "-1.5"), # Preserve SeongJoon compound
    ("오", "o", "0.5"),         # Make "o" weaker so "oh" wins
]

print(f"Current rows: {len(rows)}")

fixed_count = 0

for hangul, roman, weight in final_weight_fixes:
    found = False
    for i, row in enumerate(rows):
        if len(row) >= 2 and row[0] == hangul and row[1] == roman:
            if len(row) >= 3:
                old_weight = row[2] if row[2] else "0.0"
                rows[i] = [hangul, roman, weight]
                print(f"  FIXED: {hangul} → {roman} (weight: {old_weight} → {weight})")
                fixed_count += 1
            else:
                rows[i] = [hangul, roman, weight]
                print(f"  FIXED: {hangul} → {roman} (added weight: {weight})")
                fixed_count += 1
            found = True
            break
    
    if not found:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {hangul} → {roman} (weight: {weight})")
        fixed_count += 1

print(f"\nFinal conflict fixes: {fixed_count} changes")
print(f"Total rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Final weight conflicts resolved!")
print("\n=== EXPECTED FINAL FIXES ===")
print("- 오 → 'oh' (-1.0) should beat 'o' (0.5)")
print("- 준 → 'jun' (-1.2) should beat 'jung' (-0.9)")  
print("- 제이 → 'j' (-2.0) should work for initials")
print("- 성준 → 'seongjoon' (-1.5) should preserve compounds")
print("\nTarget: Fix remaining roundtrip failures → 95.4%!")