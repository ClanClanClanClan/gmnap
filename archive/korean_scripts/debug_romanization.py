#!/usr/bin/env python3
"""
Debug romanization tables to understand conversion issues.
"""

import json
import csv

def analyze_romanization_tables():
    """Analyze what's in our romanization tables"""
    
    # Load reverse mappings
    with open("data/reverse_romanization_maps.json", "r", encoding="utf-8") as f:
        reverse_maps = json.load(f)
    
    # Check specific problematic cases
    problematic = ["lee", "park", "choi", "yoon", "shin", "woo", "soo", "young", "hee"]
    
    print("Checking problematic syllables in reverse maps:")
    print("=" * 60)
    
    for syllable in problematic:
        print(f"\n'{syllable}':")
        found = False
        for system, mapping in reverse_maps.items():
            if syllable in mapping:
                hangul_list = mapping[syllable]
                print(f"  {system}: {', '.join(hangul_list)}")
                found = True
        if not found:
            print("  NOT FOUND in any system")
    
    # Check what romanizations we have for common Korean surnames
    print("\n\nChecking romanizations for common Korean surname syllables:")
    print("=" * 60)
    
    # Load forward mappings
    with open("data/all_romanization_systems.json", "r", encoding="utf-8") as f:
        all_systems = json.load(f)
    
    # Common surname hangul
    surname_hangul = {
        "이": "Lee/Yi/Rhee",
        "박": "Park/Pak/Bak", 
        "최": "Choi/Choe",
        "정": "Jung/Jeong/Chung",
        "윤": "Yoon/Yun",
        "신": "Shin/Sin",
        "우": "Woo/U",
        "수": "Soo/Su",
        "영": "Young/Yeong",
        "희": "Hee/Hui"
    }
    
    for hangul, common_romanizations in surname_hangul.items():
        print(f"\n{hangul} (common: {common_romanizations}):")
        for system, mapping in all_systems.items():
            if hangul in mapping:
                print(f"  {system}: {mapping[hangul]}")
    
    # Look for specific entries in RR table
    print("\n\nSearching RR table for specific patterns:")
    print("=" * 60)
    
    with open("data/rr_table.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rr_entries = list(reader)
    
    # Find entries that should match our problematic cases
    for hangul, roman in rr_entries[:50]:  # Check first 50
        if roman in ["i", "bak", "choe", "jeong", "yun", "sin", "u", "su", "yeong", "hui"]:
            print(f"  Found: {hangul} → {roman}")


def check_specific_conversions():
    """Check why specific conversions are failing"""
    import sys
    sys.path.append('.')
    from src.v5.core.korean_converter import KoreanConverter
    
    converter = KoreanConverter()
    
    print("\n\nDetailed conversion analysis:")
    print("=" * 60)
    
    test_cases = [
        ("i", "이"),      # Should be Lee
        ("bak", "박"),    # Should be Park
        ("choe", "최"),   # Should be Choi
        ("jeong", "정"),  # Should be Jung
        ("tae", "태"),    # Not 대
        ("hyeong", "형"), # Not 흉
    ]
    
    for roman, expected_hangul in test_cases:
        print(f"\nTesting '{roman}' (expecting {expected_hangul}):")
        candidates = converter.romanize_to_hangul_candidates(roman)
        if candidates:
            for hangul, weight in candidates[:3]:
                print(f"  → {hangul} (weight: {weight:.3f})")
        else:
            print("  → No candidates found")
        
        # Check reverse maps directly
        if hasattr(converter, 'reverse_maps'):
            for system in ['rr', 'mr', 'yale', 'mltr']:
                if system in converter.reverse_maps:
                    if roman in converter.reverse_maps[system]:
                        print(f"  Found in {system}: {converter.reverse_maps[system][roman]}")


if __name__ == "__main__":
    analyze_romanization_tables()
    check_specific_conversions()