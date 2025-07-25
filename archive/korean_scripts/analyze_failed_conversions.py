#!/usr/bin/env python3
"""
Analyze the 450 failed conversions to understand what V4 mappings we need
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v5.blueprint_converter import convert_blueprint
import yaml
import json
from collections import defaultdict
import re

def analyze_failed_conversions():
    """Analyze what components are causing failures"""
    print("=== ANALYZING FAILED CONVERSIONS ===\n")
    
    # Load Korean dataset
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        korean_data = yaml.safe_load(f)
    
    failed_names = []
    failed_components = defaultdict(int)
    
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
            
            # Count failed components
            for component in components:
                failed_components[component.lower()] += 1
    
    print(f"Found {len(failed_names)} failed conversions")
    
    # Analyze patterns
    print(f"\n=== FAILURE PATTERNS ===")
    
    # Categorize failures
    categories = {
        'multi_word': [],
        'hyphenated': [],
        'camel_case': [],
        'single_word': [],
        'mixed_case': []
    }
    
    for name in failed_names:
        if ' ' in name and '-' in name:
            categories['mixed_case'].append(name)
        elif ' ' in name:
            categories['multi_word'].append(name)
        elif '-' in name:
            categories['hyphenated'].append(name)
        elif any(c.isupper() for c in name[1:]):
            categories['camel_case'].append(name)
        else:
            categories['single_word'].append(name)
    
    for category, names in categories.items():
        if names:
            print(f"{category:12s}: {len(names):3d} failures ({len(names)/len(failed_names)*100:.1f}%)")
    
    # Show most common missing components
    print(f"\n=== TOP 50 MISSING COMPONENTS ===")
    sorted_components = sorted(failed_components.items(), key=lambda x: x[1], reverse=True)
    
    missing_mappings = {}
    
    for i, (component, count) in enumerate(sorted_components[:50]):
        print(f"{i+1:2d}. {component:15s}: {count:3d} failures")
        
        # Generate placeholder Hangul mapping (we'll need to research these)
        # For now, mark them as needing manual research
        missing_mappings[component] = f"RESEARCH_NEEDED_{component.upper()}"
    
    # Show some example failures
    print(f"\n=== EXAMPLE FAILURES (first 20) ===")
    for i, name in enumerate(failed_names[:20]):
        print(f"{i+1:2d}. {name}")
    
    # Save missing components for manual research
    with open('missing_v4_components.json', 'w') as f:
        json.dump(missing_mappings, f, indent=2)
    
    print(f"\n✅ Saved {len(missing_mappings)} missing components to missing_v4_components.json")
    print("Next step: Research correct Hangul mappings for these components")
    
    return failed_names, missing_mappings

if __name__ == "__main__":
    analyze_failed_conversions()