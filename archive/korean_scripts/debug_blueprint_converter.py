#!/usr/bin/env python3
"""
Debug why blueprint converter is failing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import BlueprintKoreanConverter
from src.v5.segmenter import segment_with_freq, is_valid_syllable
from src.v5.variant_generator import generate_all_variants
import json
import pynini as pn

def debug_step_by_step(name):
    """Debug each step of the blueprint conversion process"""
    print(f"\n=== DEBUGGING: {name} ===")
    
    converter = BlueprintKoreanConverter()
    
    # Step 1: Generate variants
    print("Step 1: Generate variants")
    variants = generate_all_variants(name)
    print(f"  Variants: {list(variants)[:5]}...")  # Show first 5
    
    # Step 2: Test segmentation on each variant
    print("\nStep 2: Test segmentation")
    for i, variant in enumerate(list(variants)[:3]):  # Test first 3 variants
        print(f"  Variant {i+1}: '{variant}'")
        
        # Try segmentation
        try:
            segmentations = segment_with_freq(variant, converter.syll_freq, beam=24)
            if segmentations:
                cost, segments = min(segmentations, key=lambda x: x[0])
                print(f"    Segmentation: {segments} (cost: {cost:.2f})")
                
                # Test if segments are valid
                for seg in segments:
                    valid = is_valid_syllable(seg)
                    print(f"      '{seg}': {'✅ valid' if valid else '❌ invalid'}")
            else:
                print(f"    ❌ No segmentation found")
        except Exception as e:
            print(f"    ❌ Segmentation error: {e}")
    
    # Step 3: Test FST composition
    print("\nStep 3: Test FST composition")
    
    # Check if FSTs are loaded
    print(f"  Main FST loaded: {'✅' if converter.main_fst else '❌'}")
    print(f"  V4 FST loaded: {'✅' if converter.v4_fst else '❌'}")
    
    if converter.main_fst:
        print(f"  Main FST states: {converter.main_fst.num_states()}")
    if converter.v4_fst:
        print(f"  V4 FST states: {converter.v4_fst.num_states()}")
    
    # Step 4: Test simple lookup
    print("\nStep 4: Test simple FST lookup")
    simple_cases = [name.lower(), name.split()[0].lower() if ' ' in name else name.lower()]
    
    for case in simple_cases:
        print(f"  Testing '{case}':")
        
        # Test V4 FST
        if converter.v4_fst:
            try:
                input_fst = pn.accep(case, token_type="utf8")
                result = pn.compose(input_fst, converter.v4_fst)
                if result.num_states() > 0:
                    output = converter.extract_output(result)
                    print(f"    V4 FST: ✅ {case} → {output}")
                else:
                    print(f"    V4 FST: ❌ No match")
            except Exception as e:
                print(f"    V4 FST: ❌ Error: {e}")
        
        # Test main FST
        if converter.main_fst:
            try:
                input_fst = pn.accep(case, token_type="utf8")
                result = pn.compose(input_fst, converter.main_fst)
                if result.num_states() > 0:
                    output = converter.extract_output(result)
                    print(f"    Main FST: ✅ {case} → {output}")
                else:
                    print(f"    Main FST: ❌ No match")
            except Exception as e:
                print(f"    Main FST: ❌ Error: {e}")

def main():
    print("=== BLUEPRINT CONVERTER DEBUGGING ===")
    
    # Test cases
    test_cases = [
        "Kim",           # Simple case
        "Kim Young",     # Multi-word case  
        "KimYoung",      # CamelCase
        "Ahn DaeHoon"    # From failed list
    ]
    
    for case in test_cases:
        debug_step_by_step(case)

if __name__ == "__main__":
    main()