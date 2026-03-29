#!/usr/bin/env python3
"""
Fix duplicate mappings found in comprehensive audit
Removes 10 duplicate entries to satisfy v7 idempotent_diff_bytes requirement
"""

import csv


def find_and_fix_duplicates():
    """Find and remove duplicate mappings"""
    print("🧹 FIXING DUPLICATE MAPPINGS")

    # Read all mappings
    rows = []
    with open("resources/rr_syllable_map.csv", "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    # Track mappings and duplicates
    seen_mappings = set()
    duplicates_removed = []
    filtered_rows = []

    for i, row in enumerate(rows):
        if len(row) >= 2 and not row[0].startswith("#"):
            mapping_key = (row[0], row[1])  # (hangul, roman)

            if mapping_key in seen_mappings:
                duplicates_removed.append((i + 1, row))
                print(
                    f"  Removing duplicate Line {i+1}: {row[0]},{row[1]},{row[2] if len(row)>2 else ''}"
                )
                continue  # Skip this duplicate row
            else:
                seen_mappings.add(mapping_key)

        filtered_rows.append(row)

    # Write cleaned CSV
    with open("resources/rr_syllable_map.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in filtered_rows:
            writer.writerow(row)

    print(f"✅ Removed {len(duplicates_removed)} duplicate mappings")
    print(f"   Original: {len(rows)} rows → Clean: {len(filtered_rows)} rows")

    return len(duplicates_removed)


if __name__ == "__main__":
    find_and_fix_duplicates()
