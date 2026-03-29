#!/usr/bin/env python3
"""
Intelligent duplicate analysis for Korean romanization system.
Identifies truly redundant vs intentional duplicate romanizations.
"""

import csv
from collections import defaultdict


def analyze_romanization_duplicates():
    """Analyze duplicates to distinguish redundant vs intentional"""

    print("🔍 Intelligent Duplicate Analysis")
    print("=" * 40)

    csv_path = "resources/rr_syllable_map.csv"

    # Group by (hangul, roman) pair
    entries = defaultdict(list)

    with open(csv_path, "r", encoding="utf8") as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, 1):
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 2:
                continue

            hangul, roman = row[0], row[1]
            key = (hangul, roman)
            entries[key].append((line_num, row))

    # Analyze duplicates
    true_duplicates = []  # Exact same entries
    variant_duplicates = []  # Same hangul/roman but different weights/context

    for (hangul, roman), rows in entries.items():
        if len(rows) == 1:
            continue

        # Check if all rows are identical
        first_row = rows[0][1]
        all_identical = all(row[1] == first_row for _, row in rows)

        if all_identical:
            true_duplicates.append((hangul, roman, rows))
        else:
            variant_duplicates.append((hangul, roman, rows))

    print(f"📊 Analysis Results:")
    print(f"  • True duplicates (identical): {len(true_duplicates)}")
    print(
        f"  • Variant duplicates (different weights/context): {len(variant_duplicates)}"
    )

    # Show true duplicates (safe to remove)
    if true_duplicates:
        print(f"\n✅ TRUE DUPLICATES (safe to remove):")
        for hangul, roman, rows in true_duplicates[:10]:
            print(f"  {hangul},{roman} - {len(rows)} identical entries")
            for line_num, row in rows:
                print(f"    Line {line_num}: {row}")

    # Show variant duplicates (intentional - keep all)
    if variant_duplicates:
        print(f"\n⚠️  VARIANT DUPLICATES (intentional - keep all):")
        for hangul, roman, rows in variant_duplicates[:5]:
            print(f"  {hangul},{roman} - {len(rows)} different variants")
            for line_num, row in rows:
                weight = row[2] if len(row) > 2 else "0.0"
                pos = row[4] if len(row) > 4 else ""
                print(f"    Line {line_num}: weight={weight}, pos={pos}")

    # Summary and recommendation
    total_removable = sum(len(rows) - 1 for _, _, rows in true_duplicates)

    print(f"\n🎯 RECOMMENDATION:")
    print(f"  • Remove {total_removable} true duplicate entries")
    print(
        f"  • Keep all {len(variant_duplicates)} variant duplicates (they serve different purposes)"
    )
    print(
        f"  • This will reduce false 'duplicate' warnings while preserving functionality"
    )

    return true_duplicates


if __name__ == "__main__":
    analyze_romanization_duplicates()
