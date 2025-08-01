#!/usr/bin/env python3
"""Analyze patterns in diverse dataset failures."""

import json
from collections import defaultdict, Counter

def analyze_failures():
    # Load failures data
    with open('data/diverse_failures.json', 'r', encoding='utf-8') as f:
        failures = json.load(f)
    
    print(f"Total failures: {len(failures)}")
    print()
    
    # 1. Group by failure type
    by_type = defaultdict(list)
    for f in failures:
        by_type[f['fail_type']].append(f)
    
    print("Failures by type:")
    for ftype, items in by_type.items():
        print(f"  {ftype}: {len(items)}")
    print()
    
    # 2. Character-level error patterns
    char_errors = []
    for f in failures:
        if f['fail_type'] == 'eng→kor' and f['actual'] and 'character' in f['reason']:
            # Extract character error pattern
            import re
            match = re.search(r'character (\d+) differs: (.) → (.)', f['reason'])
            if match:
                pos, expected, actual = match.groups()
                char_errors.append((expected, actual))
    
    print("Most common character substitutions:")
    char_counter = Counter(char_errors)
    for (exp, act), count in char_counter.most_common(15):
        print(f"  {exp} → {act}: {count} times")
    print()
    
    # 3. Analyze specific patterns
    patterns = {
        'seok_error': [],
        'jung_error': [],
        'chang_error': [],
        'ri_error': [],
        'ki_error': [],
        'seon_error': [],
        'heon_error': [],
        'english_names': [],
        'compound_surnames': [],
        'titles': []
    }
    
    for f in failures:
        name = f['name']
        
        # Check for specific error patterns
        if '석 → 섞' in f.get('reason', ''):
            patterns['seok_error'].append(name)
        if '중 → 정' in f.get('reason', ''):
            patterns['jung_error'].append(name)
        if '창 → 장' in f.get('reason', ''):
            patterns['chang_error'].append(name)
        if '리 → 이' in f.get('reason', ''):
            patterns['ri_error'].append(name)
        if '기 → 키' in f.get('reason', ''):
            patterns['ki_error'].append(name)
        if '선 → 순' in f.get('reason', ''):
            patterns['seon_error'].append(name)
        if '헌 → 훈' in f.get('reason', ''):
            patterns['heon_error'].append(name)
        
        # Check for English names
        if any(eng in name for eng in ['David', 'Sarah', 'Grace', 'Eugene', 'Joseph', 'Michelle', 'James', 'Jessica', 'Peter']):
            patterns['english_names'].append(name)
        
        # Check for compound surnames
        if any(compound in name for compound in ['SaGong', 'SunWoo']):
            patterns['compound_surnames'].append(name)
        
        # Check for titles
        if any(title in name for title in ['Dr_', 'Prof_']):
            patterns['titles'].append(name)
    
    print("Pattern analysis:")
    for pattern, names in patterns.items():
        if names:
            print(f"\n{pattern}: {len(names)} cases")
            for name in names[:5]:  # Show first 5
                print(f"  - {name}")
            if len(names) > 5:
                print(f"  ... and {len(names) - 5} more")
    
    # 4. Names with null conversion
    null_conversions = [f['name'] for f in failures if f['actual'] is None]
    if null_conversions:
        print(f"\nNames that failed to convert (null): {len(null_conversions)}")
        for name in null_conversions[:10]:
            print(f"  - {name}")
    
    # 5. Roundtrip failures
    roundtrip = [f for f in failures if f['fail_type'] == 'roundtrip']
    if roundtrip:
        print(f"\nRoundtrip failures: {len(roundtrip)}")
        for f in roundtrip[:5]:
            print(f"  {f['name']}: {f['expected']} → {f['actual']}")

if __name__ == '__main__':
    analyze_failures()