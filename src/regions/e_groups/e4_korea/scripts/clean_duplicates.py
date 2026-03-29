#!/usr/bin/env python3
"""
Direct duplicate removal using set-based deduplication.
Keeps first occurrence of each (hangul, roman) pair.
"""

import csv
import shutil
from datetime import datetime


def clean_duplicates_direct():
    """Remove duplicates by keeping first occurrence of each pair"""

    csv_path = "resources/rr_syllable_map.csv"

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{csv_path}.backup_clean_{timestamp}"
    shutil.copy2(csv_path, backup_path)
    print(f"💾 Backup created: {backup_path}")

    # Read all lines
    with open(csv_path, "r", encoding="utf8") as f:
        lines = f.readlines()

    # Track seen pairs and clean lines
    seen_pairs = set()
    clean_lines = []
    removed_count = 0

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            clean_lines.append(line + "\n")
            continue

        try:
            row = next(csv.reader([line]))
            if len(row) < 2:
                clean_lines.append(line + "\n")
                continue

            hangul, roman = row[0], row[1]
            pair_key = (hangul, roman)

            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                clean_lines.append(line + "\n")
            else:
                print(f"🗑️  Removing duplicate line {line_num}: {line}")
                removed_count += 1

        except:
            # Keep malformed lines as-is
            clean_lines.append(line + "\n")

    # Write cleaned file
    with open(csv_path, "w", encoding="utf8") as f:
        f.writelines(clean_lines)

    print(f"✅ Removed {removed_count} duplicate entries")
    print(f"📊 Kept {len(seen_pairs)} unique pairs")

    return removed_count


if __name__ == "__main__":
    print("🧹 Direct Duplicate Cleanup")
    print("=" * 30)

    removed = clean_duplicates_direct()

    if removed > 0:
        print(f"\n✅ Successfully removed {removed} duplicates")
    else:
        print("\n✅ No duplicates found")

    print("🎯 Cleanup complete")
