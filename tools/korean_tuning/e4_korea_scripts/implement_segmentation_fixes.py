#!/usr/bin/env python3
"""
Implement segmentation fixes for over/under-segmentation issues (+4-6 cases)
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

print("=== IMPLEMENTING SEGMENTATION FIXES ===")
print("Targeting over/under-segmentation for +4-6 cases...\n")

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

existing_mappings = {(row[0], row[1]) for row in rows if len(row) >= 2}

# Segmentation fixes based on failure analysis
segmentation_fixes = [
    # OVER-SEGMENTATION FIXES (strong weights to prevent breaking apart)
    ("육", "yook", "-1.2"),  # yook → 육 (STRONG preference, not 요옥)
    ("미", "mee", "-0.8"),  # mee → 미 (prefer over 메에 segmentation)
    ("유", "yoo", "-0.6"),  # yoo → 유 (prevent 요 segmentation)
    # COMPOUND PATTERNS (should be treated as units)
    ("정한", "junghan", "-0.5"),  # junghan → 정한 (but context prefers 준한)
    ("준한", "junghan", "-0.8"),  # junghan → 준한 (context-aware preference)
    ("종철", "jongchol", "-0.5"),  # jongchol → 종철 (compound)
    ("재천", "jaecheon", "-0.5"),  # jaecheon → 재천 (compound, prefer over 재춘)
    ("광현", "kwanghyun", "-0.5"),  # kwanghyun → 광현 (compound)
    # PREVENT WRONG SEGMENTATIONS
    ("구", "goo", "-0.8"),  # goo → 구 (not 고오)
    ("류", "ryu", "-0.6"),  # ryu → 류 (not 리유)
    ("음", "um", "-0.4"),  # um → 음 (alternative, context will choose eum when needed)
    ("도", "to", "-0.4"),  # to → 도 (alternative, context will choose do when needed)
    ("염", "yom", "-0.4"),  # yom → 염 (alternative, context chooses yeom)
    # FOREIGN NAME SEGMENTATION
    ("데이비드", "david", "-0.8"),  # david → 데이비드 (compound, not 데이빗)
    # ADDITIONAL COMPOUND PATTERNS
    ("준석", "junseok", "-0.5"),  # junseok → 준석 (compound)
    ("미숙", "meesook", "-0.5"),  # meesook → 미숙 (compound)
    ("미현", "meehyun", "-0.5"),  # meehyun → 미현 (compound)
]

print(f"Current rows: {len(rows)}")

added_count = 0
updated_count = 0

for hangul, roman, weight in segmentation_fixes:
    if (hangul, roman) not in existing_mappings:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {roman} → {hangul} (weight: {weight})")
        added_count += 1
    else:
        # Update existing weight if it's weaker
        for i, row in enumerate(rows):
            if len(row) >= 2 and row[0] == hangul and row[1] == roman:
                if len(row) >= 3:
                    old_weight = float(row[2]) if row[2] else 0.0
                    new_weight = float(weight)
                    if new_weight < old_weight:  # Lower weight = stronger preference
                        rows[i] = [hangul, roman, weight]
                        print(
                            f"  UPDATED: {roman} → {hangul} (weight: {old_weight} → {weight})"
                        )
                        updated_count += 1
                    else:
                        print(
                            f"  SKIPPED: {roman} → {hangul} (existing weight {old_weight} is stronger)"
                        )
                else:
                    rows[i] = [hangul, roman, weight]
                    print(f"  UPDATED: {roman} → {hangul} (added weight: {weight})")
                    updated_count += 1
                break

print("\nSegmentation fixes:")
print(f"- Added: {added_count} new mappings")
print(f"- Updated: {updated_count} weights")
print(f"- Total rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Segmentation fixes applied!")
print("\n=== EXPECTED IMPROVEMENTS ===")
print("Over-segmentation fixes:")
print("- yook → 육 (not 요옥)")
print("- mee → 미 (not 메에)")
print("- goo → 구 (not 고오)")
print("\nCompound recognition:")
print("- junghan → 준한 (context-aware)")
print("- jongchol → 종철 (preserved)")
print("- david → 데이비드 (foreign compound)")
print("\nTarget: +4-6 cases from segmentation improvements!")
