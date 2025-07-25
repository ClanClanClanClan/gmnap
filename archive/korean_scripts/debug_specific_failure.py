#!/usr/bin/env python3
"""
Debug specific failure case to understand why known components fail
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import BlueprintKoreanConverter
import json

def debug_specific_case(name):
    """Debug step by step why a specific case fails"""
    print(f"=== DEBUGGING SPECIFIC FAILURE: '{name}' ===\n")
    
    converter = BlueprintKoreanConverter()
    
    # Load V4 mappings to check
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json') as f:
        v4_mappings = json.load(f)
    
    print("Step 1: Split into components")
    components = converter._split_name_components(name)
    print(f"  Components: {components}")
    
    print("\nStep 2: Check each component in V4 mappings")
    for component in components:
        lower_comp = component.lower()
        if lower_comp in v4_mappings:
            print(f"  ✅ '{component}' -> '{v4_mappings[lower_comp]}' (found in V4)")
        else:
            print(f"  ❌ '{component}' -> MISSING from V4 mappings")
    
    print("\nStep 3: Test individual component conversion")
    for component in components:
        result = converter._convert_single_component(component)
        if result:
            print(f"  ✅ '{component}' -> '{result}' (converts successfully)")
        else:
            print(f"  ❌ '{component}' -> FAILED to convert")
    
    print("\nStep 4: Test full conversion process")
    final_result = converter.convert(name)
    if final_result:
        print(f"  ✅ Full conversion: '{name}' -> '{final_result}'")
    else:
        print(f"  ❌ Full conversion: '{name}' -> FAILED")
    
    # Manual step-by-step conversion attempt
    print("\nStep 5: Manual component-by-component conversion")
    manual_parts = []
    for component in components:
        result = converter._convert_single_component(component)
        if result:
            manual_parts.append(result)
            print(f"  '{component}' -> '{result}' ✅")
        else:
            print(f"  '{component}' -> FAILED ❌")
            manual_parts = None
            break
    
    if manual_parts:
        manual_result = ''.join(manual_parts)
        print(f"Manual result: '{manual_result}'")
    else:
        print("Manual conversion failed at component level")

def main():
    # Test several failed cases
    failed_cases = [
        "Kim Baekjin",  # Should work: kim->김, baekjin->백진
        "Bae Jungchul", # bae->배, jungchul->정철
        "Lee Sang-Gu", # lee->이, sang->상, gu->구
        "Choi Sunghoon" # choi->최, sunghoon->성훈
    ]
    
    for case in failed_cases:
        debug_specific_case(case)
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()