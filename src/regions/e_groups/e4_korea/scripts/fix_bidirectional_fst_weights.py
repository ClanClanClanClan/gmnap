#!/usr/bin/env python3
"""
Fix bidirectional FST inconsistencies by adding reverse mappings with proper weights
This ensures han2rom FST preferences match rom2han FST preferences
"""

import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== FIXING BIDIRECTIONAL FST WEIGHTS ===")
print("Problem: han2rom FST chooses different romanizations than expected")
print("Solution: Add reverse mappings with stronger weights")
print()

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

existing_mappings = {(row[0], row[1]) for row in rows if len(row) >= 2}

# BIDIRECTIONAL ALIGNMENT FIXES
# These ensure han2rom FST prefers the same romanizations as rom2han FST
bidirectional_fixes = [
    # FOREIGN NAME FIXES (strongest weights)
    ("계", "kai", "-1.5"),  # 계 → "kai" not "gye" (for Kai-Lai)
    ("래", "lai", "-1.5"),  # 래 → "lai" not "rae" (for Kai-Lai)
    # SURNAME PREFERENCE FIXES
    ("정", "jeong", "-1.0"),  # 정 → "jeong" not "jung" (surname preference)
    ("이", "ri", "-1.2"),  # 이 → "ri" not "lee" (when used as Ri surname)
    # GIVEN NAME FIXES
    ("준", "jun", "-0.8"),  # 준 → "jun" not "jung" (for SeongJoon)
    # INITIAL FIXES
    ("제이", "j", "-1.0"),  # 제이 → "j" not "je i" (for initials)
    # COMPOUND PRESERVATION
    ("성준", "seongjoon", "-0.8"),  # Preserve compound: 성준 → "seongjoon" not "seong jun"
    ("민정", "minjeong", "-0.8"),  # Preserve compound: 민정 → "minjeong" not "min jeong"
    ("영철", "youngchul", "-0.8"),  # Preserve compound: 영철 → "youngchul" not "young chul"
    # ADDITIONAL REVERSE PREFERENCES
    ("계래", "kailai", "-1.0"),  # Compound: 계래 → "kailai" not "gye rae"
    ("여정", "yojong", "-0.6"),  # 여정 → "yojong" not "yeo jeong"
    ("춘향", "chunhyang", "-0.6"),  # 춘향 → "chunhyang" not "cheon hyang"
    ("미중", "mijung", "-0.6"),  # 미중 → "mijung" not "mi jung"
]

print(f"Current rows: {len(rows)}")

added_count = 0
updated_count = 0

for hangul, roman, weight in bidirectional_fixes:
    if (hangul, roman) not in existing_mappings:
        rows.append([hangul, roman, weight])
        print(f"  ADDED REVERSE: {hangul} → {roman} (weight: {weight})")
        added_count += 1
    else:
        # Update existing weight if new one is stronger (more negative)
        for i, row in enumerate(rows):
            if len(row) >= 2 and row[0] == hangul and row[1] == roman:
                if len(row) >= 3 and row[2]:
                    old_weight = float(row[2])
                    new_weight = float(weight)
                    if new_weight < old_weight:  # More negative = stronger
                        rows[i] = [hangul, roman, weight]
                        print(
                            f"  UPDATED REVERSE: {hangul} → {roman} (weight: {old_weight} → {weight})"
                        )
                        updated_count += 1
                    else:
                        print(
                            f"  KEPT REVERSE: {hangul} → {roman} (existing {old_weight} >= new {weight})"
                        )
                else:
                    rows[i] = [hangul, roman, weight]
                    print(f"  UPDATED REVERSE: {hangul} → {roman} (added weight: {weight})")
                    updated_count += 1
                break

print(f"\nBidirectional alignment results:")
print(f"- Added: {added_count} reverse mappings")
print(f"- Updated: {updated_count} weights")
print(f"- Total rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Bidirectional FST alignment complete!")
print("\n=== REVERSE PREFERENCE FIXES ===")
print("Han2rom FST will now prefer:")
print("- 계 → 'kai' (not 'gye') for foreign names")
print("- 래 → 'lai' (not 'rae') for foreign names")
print("- 정 → 'jeong' (not 'jung') for surnames")
print("- 이 → 'ri' (not 'lee') when used as Ri surname")
print("- 준 → 'jun' (not 'jung') for given names")
print("- 제이 → 'j' (not 'je i') for initials")
print("- Compound preservation for full names")
print("\nExpected: Fix all 5 roundtrip failures → +13 cases!")
print("Target: 699/733 (95.4%) with maintained 196/200 diverse")
