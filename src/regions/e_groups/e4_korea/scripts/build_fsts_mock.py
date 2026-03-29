#!/usr/bin/env python3
"""
Mock FST builder for environments where PyNini is not available.
Creates placeholder FST files and fallback lookup tables.
"""
import csv, pathlib, json


def build_mock_fsts():
    """Build mock FST files and create lookup tables for fallback."""
    pathlib.Path("models").mkdir(exist_ok=True)

    # Build bidirectional lookup tables
    rom2han = {}
    han2rom = {}

    with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
        for hangul, roman in csv.reader(f):
            rom2han[roman.lower()] = hangul
            han2rom[hangul] = roman.lower()

    # Save lookup tables as JSON for fallback
    with open("models/rom2han_lookup.json", "w", encoding="utf8") as f:
        json.dump(rom2han, f, ensure_ascii=False, indent=2)

    with open("models/han2rom_lookup.json", "w", encoding="utf8") as f:
        json.dump(han2rom, f, ensure_ascii=False, indent=2)

    # Create placeholder FST files
    with open("models/rom2han.fst", "w") as f:
        f.write("# Mock FST file - PyNini not available\n")

    with open("models/han2rom.fst", "w") as f:
        f.write("# Mock FST file - PyNini not available\n")

    print("✓ Mock FSTs and lookup tables created")
    print(f"✓ Roman->Hangul mappings: {len(rom2han)}")
    print(f"✓ Hangul->Roman mappings: {len(han2rom)}")


if __name__ == "__main__":
    build_mock_fsts()
