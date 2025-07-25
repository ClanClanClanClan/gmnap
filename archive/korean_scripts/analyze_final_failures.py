#!/usr/bin/env python3
"""
Analyze the remaining 34 failures to identify missing mappings
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import convert_blueprint
import yaml
import json
from collections import defaultdict
import re

def analyze_final_failures():
    """Analyze the final 34 failures to identify missing components"""
    print("=== ANALYZING FINAL 34 FAILURES ===\n")
    
    # Load Korean dataset
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        korean_data = yaml.safe_load(f)
    
    # Load current V4 mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'r', encoding='utf-8') as f:
        v4_mappings = json.load(f)
    
    failed_names = []
    missing_components = defaultdict(int)
    
    print("Identifying failed conversions...")
    
    for key, entry in korean_data.items():
        name = key.replace('_', ' ')
        
        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue
        
        # Test conversion
        result = convert_blueprint(name)
        if not result:
            failed_names.append(name)
            
            # Extract components
            components = []
            if ' ' in name:
                components.extend(name.split())
            elif '-' in name:
                components.extend(name.split('-'))
            else:
                # CamelCase
                parts = re.findall(r'[A-Z][a-z]*|[a-z]+', name)
                components.extend(parts if len(parts) > 1 else [name])
            
            # Check what's missing
            for component in components:
                component_lower = component.lower()
                if component_lower not in v4_mappings:
                    missing_components[component_lower] += 1
    
    print(f"Found {len(failed_names)} failed conversions")
    
    # Show all failed names for manual analysis
    print(f"\n=== ALL {len(failed_names)} FAILED NAMES ===")
    for i, name in enumerate(failed_names, 1):
        print(f"{i:2d}. {name}")
    
    # Show missing components
    print(f"\n=== MISSING COMPONENTS ===")
    if missing_components:
        sorted_missing = sorted(missing_components.items(), key=lambda x: x[1], reverse=True)
        for component, count in sorted_missing:
            print(f"  {component}: {count} occurrences")
    else:
        print("  No missing components found - issue may be with compound name handling")
    
    # Categorize failures by type
    categories = {
        'rare_surnames': [],
        'compound_surnames': [],
        'hyphenated_names': [],
        'special_blocks': [],
        'other': []
    }
    
    for name in failed_names:
        if 'RareInitialsBlock' in name or 'RareSurnamesBlock' in name or 'RareDiasporaBlock' in name:
            categories['special_blocks'].append(name)
        elif ' ' in name and len(name.split()[0]) > 4:  # Compound surname
            categories['compound_surnames'].append(name)
        elif '-' in name:
            categories['hyphenated_names'].append(name)
        elif name.split()[0].lower() in ['eom', 'uhm', 'you', 'sohn', 'eoh', 'hahm', 'eu', 'hwangbo']:
            categories['rare_surnames'].append(name)
        else:
            categories['other'].append(name)
    
    print(f"\n=== FAILURE CATEGORIES ===")
    for category, names in categories.items():
        if names:
            print(f"{category}: {len(names)} failures")
            for name in names[:5]:  # Show first 5
                print(f"  - {name}")
            if len(names) > 5:
                print(f"  ... and {len(names) - 5} more")
    
    # Create additional mappings for missing surnames
    additional_mappings = {
        # Rare surnames
        'eom': '엄',
        'uhm': '엄', 
        'you': '유',
        'sohn': '손',
        'eoh': '어',
        'hahm': '함',
        'eu': '어',
        'hwangbo': '황보',  # compound surname
        
        # Additional name components that might be missing  
        'jaehyeong': '재형',
        'jongmin': '종민',  # make sure this is lowercase
    }
    
    print(f"\n=== PROPOSED ADDITIONAL MAPPINGS ===")
    for roman, hangul in additional_mappings.items():
        if roman not in v4_mappings:
            print(f"  {roman} -> {hangul}")
        else:
            print(f"  {roman} -> already mapped to '{v4_mappings[roman]}'")
    
    return failed_names, missing_components, additional_mappings

if __name__ == "__main__":
    analyze_final_failures()