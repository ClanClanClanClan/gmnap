#!/usr/bin/env python3
"""
Update missing syllables based on validation failures
"""

import csv
from pathlib import Path

import yaml

E4_ROOT = Path(__file__).parent.parent


def get_missing_syllables():
    """Extract missing syllables from validation failures."""
    data_path = E4_ROOT / "data" / "korean.yaml"

    with open(data_path, encoding="utf8") as f:
        data = yaml.safe_load(f)

    # Load existing syllables
    existing = set()
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"
    with open(syllable_map_path, encoding="utf8") as f:
        for row in csv.reader(f):
            if row:
                existing.add(row[0].lower())

    # Find missing syllables
    missing = []
    for k, v in data.items():
        if not isinstance(v, dict):
            continue

        rr = v.get("CanonicalLatin", "")
        ko_exp = v.get("CJK", "")

        if not rr or not ko_exp:
            continue

        # Tokenize the name
        tokens = rr.replace("-", " ").replace(",", "").split()

        for token in tokens:
            token_lower = token.lower()
            if token_lower not in existing and token_lower not in [
                s[0] for s in missing
            ]:
                # Try to find the expected Hangul
                missing.append((token_lower, ""))  # We'll need to map these manually

    return missing


def main():
    missing = get_missing_syllables()

    if not missing:
        print("No missing syllables found!")
        return

    print(f"Found {len(missing)} missing syllables:")
    for rom, han in missing[:20]:  # Show first 20
        print(f"  {rom} -> ?")

    # Common missing mappings based on validation errors
    common_missing = [
        ("hyun", "현"),
        ("hyeon", "현"),
        ("gyu", "규"),
        ("chul", "출"),
        ("joon", "준"),
        ("hyung", "형"),
        ("suh", "서"),
        ("chan", "찬"),
        ("lai", "라이"),
        ("kai", "카이"),
        ("jae", "재"),
        ("chung", "청"),
        ("cheol", "철"),
        ("seon", "선"),
        ("seong", "성"),
    ]

    # Add missing mappings
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"

    added = 0
    with open(syllable_map_path, "a", encoding="utf8") as f:
        writer = csv.writer(f)
        for rom, han in common_missing:
            writer.writerow([rom, han])
            added += 1

    print(f"✓ Added {added} common missing syllables")
    print("✓ Rebuild FSTs with: python scripts/build_fsts.py")


if __name__ == "__main__":
    main()
