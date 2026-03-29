#!/usr/bin/env python3
"""
Remove only true duplicates (identical entries) while preserving intentional variants.
"""

import csv
import shutil
from datetime import datetime
from collections import defaultdict


def remove_only_true_duplicates():
    """Remove only truly identical duplicate entries"""

    csv_path = "resources/rr_syllable_map.csv"

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{csv_path}.backup_true_dedup_{timestamp}"
    shutil.copy2(csv_path, backup_path)
    print(f"💾 Backup created: {backup_path}")

    # Read and analyze entries
    entries = defaultdict(list)
    all_lines = []

    with open(csv_path, "r", encoding="utf8") as f:
        for line_num, line in enumerate(f, 1):
            all_lines.append(line)

            line_clean = line.strip()
            if not line_clean or line_clean.startswith("#"):
                continue

            try:
                row = next(csv.reader([line_clean]))
                if len(row) >= 2:
                    key = (row[0], row[1])
                    entries[key].append((line_num, row, line))
            except:
                continue

    # Find true duplicates (completely identical rows)
    lines_to_remove = set()
    removed_count = 0

    for key, line_data_list in entries.items():
        if len(line_data_list) <= 1:
            continue

        # Group by complete row content
        row_groups = defaultdict(list)
        for line_num, row, line in line_data_list:
            row_key = tuple(row)  # Complete row as tuple
            row_groups[row_key].append((line_num, line))

        # Remove duplicates within each group (keep first occurrence)
        for row_key, occurrences in row_groups.items():
            if len(occurrences) > 1:
                # Keep first, remove others
                keep_first = occurrences[0]
                to_remove = occurrences[1:]

                print(
                    f"🗑️  Removing {len(to_remove)} true duplicates of: {key[0]},{key[1]}"
                )
                for line_num, line in to_remove:
                    lines_to_remove.add(line_num)
                    removed_count += 1

    # Write cleaned file
    if lines_to_remove:
        with open(csv_path, "w", encoding="utf8") as f:
            for line_num, line in enumerate(all_lines, 1):
                if line_num not in lines_to_remove:
                    f.write(line)

        print(f"✅ Removed {removed_count} true duplicate entries")
    else:
        print("✅ No true duplicates found")

    return removed_count


if __name__ == "__main__":
    print("🧹 True Duplicate Removal (Preserves Intentional Variants)")
    print("=" * 60)

    removed = remove_only_true_duplicates()

    if removed > 0:
        print(f"\n✅ Successfully removed {removed} true duplicates")
        print("ℹ️  Intentional variants (different weights/positions) preserved")
    else:
        print("\n✅ No true duplicates found")

    print("🎯 Intelligent cleanup complete")
