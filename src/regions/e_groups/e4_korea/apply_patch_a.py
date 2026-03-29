#!/usr/bin/env python3
"""
Apply Patch A: Critical weight recalibrations for v7 compliance
"""

import csv


def apply_patch_a():
    """Apply the 4 specific weight recalibrations"""
    print("🔧 APPLYING PATCH A WEIGHT RECALIBRATIONS")

    # Target changes (exact matches)
    changes = [
        ("석", "seok", "-0.4", "-0.8"),
        ("석", "suk", "-0.223", "0.2"),
        ("석", "sok", "0.0", "0.5"),
        ("숙", "suk", "0.981", "0.3"),
    ]

    # Read CSV
    rows = []
    with open("resources/rr_syllable_map.csv", "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    changes_applied = 0

    # Apply changes
    for i, row in enumerate(rows):
        if len(row) >= 3:
            hangul, roman, weight = row[0], row[1], row[2]

            for target_hangul, target_roman, old_weight, new_weight in changes:
                if (
                    hangul == target_hangul
                    and roman == target_roman
                    and weight == old_weight
                ):
                    print(
                        f"  Line {i+1}: {hangul},{roman},{weight} → {hangul},{roman},{new_weight}"
                    )
                    rows[i][2] = new_weight
                    changes_applied += 1
                    break

    # Write updated CSV
    with open("resources/rr_syllable_map.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    print(f"✅ Applied {changes_applied}/4 weight recalibrations")
    return changes_applied


if __name__ == "__main__":
    apply_patch_a()
