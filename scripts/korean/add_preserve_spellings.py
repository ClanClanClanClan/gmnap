#!/usr/bin/env python3
"""
Add mappings that preserve original English spellings for better round-trip accuracy
"""

import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent

# Add mappings that preserve common English spellings
preserve_mappings = [
    # Preserve 'h' in common names
    ("안", "ahn"),  # Keep 'h' in Ahn
    # Common double vowel preservations
    ("수", "soo"),  # Already added but ensure it's there
    ("우", "woo"),
    ("이", "ee"),  # For names like Lee
    # Preserve capitalized variations
    ("훈", "hoon"),  # Not hun
    ("현", "hyeon"),  # Alternative to hyun
    ("형", "hyeong"),  # Alternative to hyung
    # Common name-specific mappings
    ("박", "park"),  # Not pak
    ("이", "lee"),  # Not i or yi
    ("최", "choi"),  # Not choe
    ("조", "cho"),  # Not jo
    ("정", "jung"),  # Not jeong
    ("정", "jeong"),  # Both variants
    # Preserve exact spellings from test data
    ("대", "dae"),  # Not dae
    ("윤", "yoon"),  # Not yun
    ("성", "sung"),  # Not seong
    ("영", "young"),  # Not yeong
]


def main():
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"

    # Load existing to check for duplicates
    existing = {}
    rows = []

    with open(syllable_map_path, encoding="utf8") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                hangul, roman = row[0], row[1]
                rows.append(row)
                if hangul not in existing:
                    existing[hangul] = set()
                existing[hangul].add(roman.lower())

    # Add new mappings
    added = 0
    for hangul, roman in preserve_mappings:
        if hangul not in existing or roman.lower() not in existing[hangul]:
            rows.append([hangul, roman])
            if hangul not in existing:
                existing[hangul] = set()
            existing[hangul].add(roman.lower())
            added += 1

    # Write back
    with open(syllable_map_path, "w", encoding="utf8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    print(f"✓ Added {added} preservation mappings")
    print(f"✓ Total mappings: {len(rows)}")
    print("✓ Rebuild FSTs with: python scripts/build_fsts.py")


if __name__ == "__main__":
    main()
