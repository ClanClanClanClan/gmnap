#!/usr/bin/env python3
"""Debug the 석 → 섞 conversion issue."""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from converter import eng2kor, kor2eng

def test_seok_conversions():
    """Test various seok-related conversions."""
    test_cases = [
        "seok",
        "HoSeok", 
        "JaeSeok",
        "SeokYeol",
        "SeokJin"
    ]
    
    print("Testing 'seok' conversions:")
    print("=" * 50)
    
    for name in test_cases:
        result = eng2kor(name)
        print(f"{name:15} → {result}")
        
        # Also test specific characters
        if "석" in result:
            print(f"  Contains 석 (correct)")
        elif "섞" in result:
            print(f"  Contains 섞 (WRONG!)")
    
    print("\nChecking syllable mappings...")
    # Check what romanizations map to 석 and 섞
    import csv
    
    seok_mappings = []
    with open('resources/rr_syllable_map.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1] == 'seok':
                seok_mappings.append(row[0])
    
    print(f"\nSyllables that romanize to 'seok': {seok_mappings[:10]}")
    
    # Test reverse mapping
    print("\nReverse mappings:")
    for hangul in ['석', '섞']:
        rom = kor2eng(hangul)
        print(f"  {hangul} → {rom}")

if __name__ == "__main__":
    test_seok_conversions()