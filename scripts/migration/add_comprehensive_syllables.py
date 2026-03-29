#!/usr/bin/env python3
"""
Add comprehensive syllable mappings to improve accuracy
"""

import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent.parent.rstrip(".").parent.rstrip(".").parent.rstrip(".")

# Common Korean name syllables that are missing
comprehensive_mappings = [
    # Missing from validation errors
    ("ahn", "안"),
    ("dae", "대"),
    ("hoon", "훈"),
    ("baek", "백"),
    ("bae", "배"),
    ("jung", "정"),
    ("sang", "상"),
    ("un", "운"),
    ("jaeho", "재호"),
    ("chae", "채"),
    ("sung", "성"),
    ("chang", "창"),
    ("bum", "범"),
    ("chung", "청"),
    ("oh", "오"),
    ("shin", "신"),
    ("suh", "서"),
    ("yong", "용"),
    # Double vowel variations for better round-trip
    ("soo", "수"),
    ("woo", "우"),
    ("oo", "우"),
    ("ee", "이"),
    ("ii", "이"),
    # Common variations
    ("hwan", "환"),
    ("kwan", "관"),
    ("gwan", "관"),
    ("won", "원"),
    ("weon", "원"),
    ("yeon", "연"),
    ("yon", "연"),
    ("jun", "준"),
    ("jin", "진"),
    ("chin", "진"),
    # More name syllables
    ("dong", "동"),
    ("han", "한"),
    ("hee", "희"),
    ("hui", "희"),
    ("kyung", "경"),
    ("kyeong", "경"),
    ("man", "만"),
    ("nam", "남"),
    ("sik", "식"),
    ("sok", "석"),
    ("seok", "석"),
    ("sun", "선"),
    ("tae", "태"),
    ("wan", "완"),
    ("yool", "율"),
    ("yul", "율"),
]


def main():
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"

    # Load existing syllables to avoid duplicates
    existing = set()
    with open(syllable_map_path, encoding="utf8") as f:
        for row in csv.reader(f):
            if row:
                existing.add(row[0].lower())

    # Add new mappings
    added = 0
    with open(syllable_map_path, "a", encoding="utf8") as f:
        writer = csv.writer(f)
        for rom, han in comprehensive_mappings:
            if rom.lower() not in existing:
                writer.writerow([rom, han])
                existing.add(rom.lower())
                added += 1

    print(f"✓ Added {added} new syllable mappings")
    print(f"✓ Total syllables: {len(existing)}")
    print("✓ Rebuild FSTs with: python scripts/build_fsts.py")


if __name__ == "__main__":
    main()
