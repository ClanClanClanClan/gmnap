#!/usr/bin/env python3
"""
Build comprehensive V4 mappings from the Korean dataset
"""

import yaml
from collections import defaultdict
import re

# Core romanization variations identified from the dataset
ROMANIZATION_PATTERNS = {
    # Vowel variations
    'eo': ['uh', 'o', 'aw'],
    'eu': ['u', 'oo'],
    'ae': ['e', 'ay'],
    'oe': ['we', 'oi'],
    'ui': ['wi', 'ee'],
    'wa': ['wha'],
    'wo': ['woo'],
    'ye': ['yuh'],
    'yo': ['yaw'],
    'yu': ['yoo'],
    
    # Consonant variations
    'g': ['k'],  # ㄱ
    'n': [''],   # ㄴ (can be silent in some positions)
    'd': ['t'],  # ㄷ
    'r': ['l'],  # ㄹ
    'b': ['p'],  # ㅂ
    'j': ['ch'], # ㅈ
    
    # Double consonants
    'kk': ['gg', 'k'],
    'tt': ['dd', 't'],
    'pp': ['bb', 'p'],
    'ss': ['s'],
    'jj': ['j'],
}

# Common given name variations found in the dataset
GIVEN_NAME_VARIATIONS = {
    'Young': ['Yeong', 'Yong', 'Yung'],
    'Jung': ['Jeong', 'Chong', 'Chung'],
    'Hyun': ['Hyeon', 'Hyung', 'Hyon'],
    'Sung': ['Seong', 'Song'],
    'Kyung': ['Gyeong', 'Kyeong', 'Gyung', 'Kyong'],
    'Jae': ['Je', 'Chae'],
    'Hee': ['Hui', 'Hi', 'Hye'],
    'Soo': ['Su'],
    'Woo': ['Wu', 'U'],
    'Jin': ['Chin'],
    'Min': ['Meen'],
    'Seung': ['Sung'],
    'Eun': ['Un', 'Eun'],
    'Chul': ['Cheol', 'Chol'],
    'Ho': ['Hoh'],
    'Dong': ['Tong'],
    'Sang': ['Sahng'],
    'Yeon': ['Yun', 'Yon'],
    'Hoon': ['Hun'],
    'Bong': ['Pong'],
    'Bok': ['Pok', 'Bog'],
    'Geun': ['Keun', 'Gun'],
    'Kwang': ['Gwang', 'Kwang'],
    'Myung': ['Myeong', 'Myong'],
    'Byung': ['Byeong', 'Pyung'],
    'Seok': ['Suk', 'Sok'],
    'Won': ['Weon', 'One'],
    'Tae': ['Tai', 'Te'],
    'Yong': ['Ryong'],
    'Kyu': ['Gyu', 'Kyu'],
    'Il': ['Eel', 'Il'],
    'Nam': ['Nahm'],
    'Han': ['Hahn'],
    'Baek': ['Paek', 'Baik', 'Paik', 'Back'],
    'Beom': ['Bum', 'Bom'],
}

# Surname variations found in the dataset
SURNAME_VARIATIONS = {
    'Kim': ['Gim', 'Ghim'],
    'Lee': ['Yi', 'Rhee', 'Ri', 'Li'],
    'Park': ['Pak', 'Bak', 'Bahk'],
    'Choi': ['Choe', "Ch'oe", 'Chwe'],
    'Jung': ['Jeong', 'Chung', 'Cheong'],
    'Kang': ['Gang', 'Kahng'],
    'Cho': ['Jo', 'Joh'],
    'Yoon': ['Yun', 'Youn'],
    'Jang': ['Chang', 'Jahng'],
    'Lim': ['Im', 'Rim', 'Yim'],
    'Han': ['Hahn'],
    'Oh': ['O', 'Eo'],
    'Seo': ['Suh', 'So'],
    'Shin': ['Sin'],
    'Kwon': ['Gwon', 'Kweon'],
    'Hwang': ['Whang', 'Hoang'],
    'Ahn': ['An', 'Ahn'],
    'Song': ['Soung'],
    'Hong': ['Houng'],
    'Yoo': ['Yu', 'Ryu', 'Ryoo'],
    'Ko': ['Go', 'Koh', 'Goh'],
    'Moon': ['Mun'],
    'Yang': ['Ryang'],
    'Bae': ['Pae', 'Bai', 'Bay'],
    'Baek': ['Paek', 'Baik', 'Paik', 'Back'],
    'Nam': ['Nahm'],
    'No': ['Noh', 'Ro', 'Roh'],
    'Ha': ['Hah'],
    'Chun': ['Cheon', 'Chon'],
    'Ryu': ['Ryoo', 'Yoo', 'Yu'],
    'Sim': ['Shim'],
    'Ku': ['Gu', 'Koo', 'Goo'],
    'Do': ['To', 'Doh'],
    'Pyo': ['Pyo', 'Pio'],
    'Byun': ['Byeon', 'Byon', 'Pyon', 'Pyun'],
}

def generate_all_variations(base_name, variations_dict):
    """Generate all possible variations of a name component"""
    variations = {base_name}
    
    # Direct variations
    if base_name in variations_dict:
        variations.update(variations_dict[base_name])
    
    # Case variations
    case_variants = {base_name.lower(), base_name.upper(), base_name.capitalize()}
    variations.update(case_variants)
    
    # Handle hyphenation (for compound names)
    if len(base_name) > 4:
        # Try to split camelCase
        parts = re.findall(r'[A-Z][a-z]*', base_name)
        if len(parts) > 1:
            # Add hyphenated version
            hyphenated = '-'.join(parts)
            variations.add(hyphenated)
            # Add space-separated version
            spaced = ' '.join(parts)
            variations.add(spaced)
    
    return list(variations)

def build_v4_mappings():
    """Build comprehensive V4 mappings from the dataset"""
    
    # Load the analysis data
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_components_analysis.yaml', 'r') as f:
        analysis = yaml.safe_load(f)
    
    # Build surname mappings
    surname_mappings = {}
    for surname in analysis['surnames']:
        if surname and len(surname) > 1 and surname[0].isupper():  # Filter out invalid entries
            variations = generate_all_variations(surname, SURNAME_VARIATIONS)
            for var in variations:
                surname_mappings[var] = surname
    
    # Build given name mappings
    given_name_mappings = {}
    for part in analysis['given_name_parts']:
        if part and len(part) > 1 and part[0].isupper():  # Filter out invalid entries
            variations = generate_all_variations(part, GIVEN_NAME_VARIATIONS)
            for var in variations:
                given_name_mappings[var] = part
    
    # Create the V4 mapping structure
    v4_mappings = {
        'korean_v4': {
            'description': 'Comprehensive V4 mappings for Korean names based on actual dataset',
            'statistics': {
                'total_surnames': len(analysis['surnames']),
                'total_given_parts': len(analysis['given_name_parts']),
                'surname_mappings': len(surname_mappings),
                'given_name_mappings': len(given_name_mappings),
            },
            'surname_mappings': surname_mappings,
            'given_name_mappings': given_name_mappings,
            'romanization_patterns': ROMANIZATION_PATTERNS,
            'common_variations': {
                'surnames': SURNAME_VARIATIONS,
                'given_names': GIVEN_NAME_VARIATIONS,
            }
        }
    }
    
    # Save the mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_v4_mappings.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(v4_mappings, f, allow_unicode=True, default_flow_style=False, width=120)
    
    # Also create a Python module for direct use
    python_content = '''"""
Korean V4 name mappings generated from the actual dataset
"""

SURNAME_MAPPINGS = %s

GIVEN_NAME_MAPPINGS = %s

def normalize_korean_surname(surname):
    """Normalize a Korean surname to its standard form"""
    return SURNAME_MAPPINGS.get(surname, surname)

def normalize_korean_given_name_part(part):
    """Normalize a Korean given name part to its standard form"""
    return GIVEN_NAME_MAPPINGS.get(part, part)
''' % (repr(surname_mappings), repr(given_name_mappings))
    
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/v5/korean_v4_mappings.py', 'w') as f:
        f.write(python_content)
    
    return v4_mappings

def analyze_missing_mappings():
    """Analyze which names in the dataset would fail without proper mappings"""
    
    # Load the korean.yaml file
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Build mappings
    mappings = build_v4_mappings()
    surname_map = mappings['korean_v4']['surname_mappings']
    given_map = mappings['korean_v4']['given_name_mappings']
    
    # Test each entry
    failed_conversions = []
    successful_conversions = 0
    
    for key, entry in data.items():
        parts = key.split('_')
        if len(parts) >= 2:
            surname = parts[0]
            given_name = '_'.join(parts[1:])
            
            # Check if surname needs mapping
            surname_found = surname in surname_map or surname == surname_map.get(surname, surname)
            
            # Check given name parts
            given_parts = re.findall(r'[A-Z][a-z]*', given_name)
            all_parts_found = all(part in given_map or part == given_map.get(part, part) 
                                 for part in given_parts if part)
            
            if surname_found and all_parts_found:
                successful_conversions += 1
            else:
                failed_conversions.append({
                    'key': key,
                    'surname': surname,
                    'surname_found': surname_found,
                    'given_name': given_name,
                    'given_parts': given_parts,
                    'all_parts_found': all_parts_found,
                })
    
    print(f"\n=== MAPPING COVERAGE ANALYSIS ===")
    print(f"Total entries: {len(data)}")
    print(f"Successful mappings: {successful_conversions}")
    print(f"Failed mappings: {len(failed_conversions)}")
    print(f"Success rate: {successful_conversions / len(data) * 100:.1f}%")
    
    if failed_conversions:
        print(f"\n=== FIRST 10 FAILED CONVERSIONS ===")
        for i, fail in enumerate(failed_conversions[:10]):
            print(f"\n{i+1}. {fail['key']}")
            print(f"   Surname: {fail['surname']} (found: {fail['surname_found']})")
            print(f"   Given: {fail['given_name']}, parts: {fail['given_parts']}")
    
    return failed_conversions

if __name__ == '__main__':
    print("Building V4 mappings from Korean dataset...")
    mappings = build_v4_mappings()
    
    print(f"\nCreated {mappings['korean_v4']['statistics']['surname_mappings']} surname mappings")
    print(f"Created {mappings['korean_v4']['statistics']['given_name_mappings']} given name mappings")
    
    print("\nMappings saved to:")
    print("  - korean_v4_mappings.yaml")
    print("  - src/v5/korean_v4_mappings.py")
    
    # Analyze coverage
    analyze_missing_mappings()