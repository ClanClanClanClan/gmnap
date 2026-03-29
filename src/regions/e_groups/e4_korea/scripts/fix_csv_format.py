#!/usr/bin/env python3
"""
Fix CSV format - ensure all entries are (hangul, romanization)
"""
import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent


def is_hangul(text):
    """Check if text contains Hangul characters."""
    return any("\uAC00" <= char <= "\uD7A3" for char in text)


def main():
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"
    temp_path = syllable_map_path.with_suffix(".tmp")

    fixed_count = 0
    total_count = 0

    with open(syllable_map_path, encoding="utf8") as f_in:
        with open(temp_path, "w", encoding="utf8") as f_out:
            writer = csv.writer(f_out)

            for row in csv.reader(f_in):
                if len(row) >= 2:
                    col1, col2 = row[0], row[1]
                    total_count += 1

                    # Check if columns are reversed
                    if is_hangul(col1):
                        # Correct format: (hangul, romanization)
                        writer.writerow([col1, col2])
                    else:
                        # Reversed format: (romanization, hangul)
                        writer.writerow([col2, col1])
                        fixed_count += 1
                elif row:
                    writer.writerow(row)

    # Replace original file
    temp_path.replace(syllable_map_path)

    print(f"✓ Fixed {fixed_count} reversed entries out of {total_count} total")
    print("✓ All entries now in format: (hangul, romanization)")
    print("✓ Rebuild FSTs with: python scripts/build_fsts.py")


if __name__ == "__main__":
    main()
