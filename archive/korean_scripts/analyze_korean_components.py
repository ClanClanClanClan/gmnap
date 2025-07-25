#!/usr/bin/env python3
"""
Analyze Korean name components from korean.yaml to identify what needs V4 mapping
"""

import yaml
from collections import defaultdict, Counter
import re

def extract_name_components(data):
    """Extract all unique surname and given name components from the data"""
    surnames = set()
    given_name_parts = set()
    full_names = []
    
    for key, entry in data.items():
        # Extract from the key (e.g., "Kim_Baekjin")
        parts = key.split('_')
        if len(parts) >= 2:
            surname = parts[0]
            given_name = '_'.join(parts[1:])
            surnames.add(surname)
            full_names.append((surname, given_name))
            
            # Split given name into components
            # Handle camelCase (e.g., "BaekJin" -> ["Baek", "Jin"])
            given_parts = re.findall(r'[A-Z][a-z]*', given_name)
            for part in given_parts:
                if part:  # Skip empty strings
                    given_name_parts.add(part)
        
        # Also extract from canonical forms
        if 'CanonicalLatin' in entry:
            canonical = entry['CanonicalLatin']
            # Extract surname (before comma)
            if ', ' in canonical:
                surname_part = canonical.split(', ')[0]
                surnames.add(surname_part)
                
                # Extract given name parts (after comma)
                given_part = canonical.split(', ')[1]
                # Split by hyphen
                for part in given_part.split('-'):
                    if part:
                        given_name_parts.add(part)
        
        # Extract from variants
        if 'AllCommonVariants' in entry:
            for variant in entry['AllCommonVariants']:
                # Skip Korean and initials
                if any(ord(char) > 127 for char in variant):
                    continue
                if '.' in variant:
                    continue
                    
                # Try to extract components
                if ', ' in variant:
                    # Format: "Surname, Given"
                    surname_part = variant.split(', ')[0]
                    surnames.add(surname_part)
                    given_part = variant.split(', ')[1]
                    for part in given_part.replace('-', ' ').split():
                        if part:
                            given_name_parts.add(part)
                else:
                    # Format: "Given Surname" or "Surname Given"
                    parts = variant.replace('-', ' ').split()
                    if len(parts) >= 2:
                        # Assume first part is surname if it matches known surnames
                        if parts[0] in ['Kim', 'Lee', 'Park', 'Choi', 'Jung', 'Cho', 'Yoon', 'Yun', 
                                       'Ahn', 'Bae', 'Baek', 'Chae', 'Chang', 'Chun', 'Chung',
                                       'Eom', 'Han', 'Hong', 'Hwang', 'Im', 'Jeon', 'Jeong', 'Jin',
                                       'Oh', 'Ryu', 'Shin', 'Song', 'Suh', 'Yim', 'Yoo', 'Yu']:
                            surnames.add(parts[0])
                            for part in parts[1:]:
                                if part:
                                    given_name_parts.add(part)
                        else:
                            # Assume last part is surname
                            surnames.add(parts[-1])
                            for part in parts[:-1]:
                                if part:
                                    given_name_parts.add(part)
    
    return surnames, given_name_parts, full_names

def main():
    # Load the korean.yaml file
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    surnames, given_name_parts, full_names = extract_name_components(data)
    
    print("=== ANALYSIS OF KOREAN NAME COMPONENTS ===\n")
    
    print(f"Total entries in dataset: {len(data)}")
    print(f"Unique surnames: {len(surnames)}")
    print(f"Unique given name parts: {len(given_name_parts)}")
    
    print("\n=== UNIQUE SURNAMES ===")
    sorted_surnames = sorted(surnames)
    for i, surname in enumerate(sorted_surnames):
        print(f"{surname:15}", end='')
        if (i + 1) % 5 == 0:
            print()
    print()
    
    print("\n=== UNIQUE GIVEN NAME PARTS ===")
    sorted_given_parts = sorted(given_name_parts)
    for i, part in enumerate(sorted_given_parts):
        print(f"{part:15}", end='')
        if (i + 1) % 5 == 0:
            print()
    print()
    
    # Count frequency of each component
    surname_counts = Counter()
    given_part_counts = Counter()
    
    for surname, given_name in full_names:
        surname_counts[surname] += 1
        given_parts = re.findall(r'[A-Z][a-z]*', given_name)
        for part in given_parts:
            if part:
                given_part_counts[part] += 1
    
    print("\n=== MOST COMMON SURNAMES ===")
    for surname, count in surname_counts.most_common(20):
        print(f"{surname:15} {count:4} occurrences")
    
    print("\n=== MOST COMMON GIVEN NAME PARTS ===")
    for part, count in given_part_counts.most_common(30):
        print(f"{part:15} {count:4} occurrences")
    
    # Identify components that need special handling
    print("\n=== COMPONENTS NEEDING SPECIAL V4 MAPPING ===")
    
    # Common variations that need mapping
    variations = {
        'Jung': ['Jeong', 'Chong'],
        'Young': ['Yeong', 'Yong'],
        'Hyun': ['Hyeon', 'Hyung'],
        'Woo': ['Wu', 'U'],
        'Hee': ['Hui', 'Hi'],
        'Soo': ['Su'],
        'Jae': ['Je'],
        'Chul': ['Cheol'],
        'Seung': ['Sung'],
        'Eun': ['Un'],
    }
    
    print("\nCommon romanization variations to handle:")
    for base, variants in variations.items():
        print(f"  {base} -> {', '.join(variants)}")
    
    # Create a comprehensive V4 mapping suggestion
    print("\n=== V4 MAPPING REQUIREMENTS ===")
    print(f"Total unique surnames to map: {len(surnames)}")
    print(f"Total unique given name parts to map: {len(given_name_parts)}")
    print(f"Total unique components: {len(surnames) + len(given_name_parts)}")
    
    # Export the components for further processing
    output = {
        'surnames': sorted(surnames),
        'given_name_parts': sorted(given_name_parts),
        'romanization_variations': variations,
        'statistics': {
            'total_entries': len(data),
            'unique_surnames': len(surnames),
            'unique_given_parts': len(given_name_parts),
        }
    }
    
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_components_analysis.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False)
    
    print("\nAnalysis complete. Results saved to korean_components_analysis.yaml")

if __name__ == '__main__':
    main()