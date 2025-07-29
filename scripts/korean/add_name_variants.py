#!/usr/bin/env python3
"""
Add common Korean name variants to the syllable map
"""
import csv
from pathlib import Path

def add_name_variants():
    """Add common Korean name romanization variants."""
    
    # Common name variants that don't follow standard Revised Romanization
    name_variants = [
        # Hangul, Common English spelling
        ("이", "lee"),      # Standard: i, Common: lee  
        ("박", "park"),     # Standard: bak, Common: park
        ("최", "choi"),     # Standard: choe, Common: choi
        ("류", "ryu"),      # Standard: ryu, but also ryoo
        ("류", "ryoo"),     # Alternative spelling
        ("정", "jung"),     # Standard: jeong, Common: jung
        ("정", "chung"),    # Alternative spelling
        ("김", "gim"),      # Alternative to kim
        ("수", "soo"),      # Alternative to su
        ("훈", "hoon"),     # Alternative to hun
        ("현", "hyun"),     # Alternative to hyeon  
        ("규", "gyu"),      # Alternative to gyu
        ("철", "chul"),     # Alternative to cheol
        ("찬", "chan"),     # Alternative to chan
    ]
    
    # Read existing syllable map
    syllable_path = Path("resources/rr_syllable_map.csv")
    existing_entries = []
    
    with open(syllable_path, encoding="utf8") as f:
        existing_entries = list(csv.reader(f))
    
    # Add new variants (avoid duplicates)
    existing_romans = {row[1].lower() for row in existing_entries}
    added_count = 0
    
    for hangul, roman in name_variants:
        if roman.lower() not in existing_romans:
            existing_entries.append([hangul, roman])
            existing_romans.add(roman.lower())
            added_count += 1
    
    # Write back to file
    with open(syllable_path, "w", encoding="utf8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(existing_entries)
    
    print(f"✓ Added {added_count} name variants")
    print(f"✓ Total entries: {len(existing_entries)}")
    
    return added_count

if __name__ == "__main__":
    add_name_variants()