#!/usr/bin/env python3
"""
Validate V5 Korean conversion system components.
"""

import sys
sys.path.append('src')

def test_basic_conversions():
    """Test basic Korean name conversions"""
    print("=== TESTING BASIC CONVERSIONS ===")
    
    from v5.converter_with_backoff import convert_with_backoff
    
    test_names = ["kim", "lee", "park", "choi", "jung", "han"]
    
    for name in test_names:
        result = convert_with_backoff(name)
        if result:
            print(f"✅ {name} → {result}")
        else:
            print(f"❌ {name} → [FAILED]")

def test_dice_coefficient():
    """Test Dice coefficient calculation"""
    print("\n=== TESTING DICE COEFFICIENT ===")
    
    from scripts.dice_coefficient import dice_coefficient
    
    test_pairs = [
        ("kim", "kim"),     # Perfect match
        ("lee", "li"),      # Close match  
        ("park", "pak"),    # Very close
        ("xyz", "abc"),     # No match
    ]
    
    for a, b in test_pairs:
        score = dice_coefficient(a, b)
        print(f"  {a} vs {b}: {score:.3f}")

def test_file_existence():
    """Test that required data files exist"""
    print("\n=== TESTING FILE EXISTENCE ===")
    
    import os
    
    required_files = [
        "data/roman2hangul.fst",
        "data/v4_backoff.fst", 
        "data/reverse_romanization_maps.json",
        "data/all_romanization_systems.json",
        "data/syllable_freq.json",
        "korean.yaml"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")

def test_v5_components():
    """Test V5 component loading"""
    print("\n=== TESTING V5 COMPONENTS ===")
    
    try:
        from v5.core.korean_converter import KoreanConverter
        converter = KoreanConverter()
        print("✅ KoreanConverter loaded")
        
        # Test basic conversion
        result = converter.convert_syllable("kim")
        if result:
            print(f"✅ Basic syllable conversion: kim → {result}")
        else:
            print("❌ Basic syllable conversion failed")
            
    except Exception as e:
        print(f"❌ KoreanConverter failed: {e}")
    
    try:
        from v5.core.hangul_to_roman import HangulToRomanConverter
        h2r = HangulToRomanConverter()
        print("✅ HangulToRomanConverter loaded")
        
        # Test reverse conversion
        result = h2r.convert_text("김")
        print(f"✅ Reverse conversion: 김 → {result}")
        
    except Exception as e:
        print(f"❌ HangulToRomanConverter failed: {e}")

if __name__ == "__main__":
    print("V5 KOREAN CONVERSION SYSTEM VALIDATION")
    print("=" * 50)
    
    test_file_existence()
    test_v5_components()
    test_basic_conversions()
    test_dice_coefficient()
    
    print("\n" + "=" * 50)
    print("Validation complete. Check results above.")