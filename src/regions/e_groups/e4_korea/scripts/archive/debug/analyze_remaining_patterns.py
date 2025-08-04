#!/usr/bin/env python3
"""
Analyze remaining failure patterns to prioritize next improvements.
"""

import json
from collections import Counter, defaultdict

def analyze_remaining_failures():
    """Analyze the remaining diverse dataset failures."""
    with open('data/diverse_failures.json', 'r', encoding='utf-8') as f:
        failures = json.load(f)
    
    print(f"Total remaining failures: {len(failures)}")
    print("=" * 60)
    
    # Group by failure type
    by_type = defaultdict(list)
    for f in failures:
        by_type[f['fail_type']].append(f)
    
    print("\nFailures by type:")
    for ftype, items in by_type.items():
        print(f"  {ftype}: {len(items)}")
    
    # Analyze character substitutions
    char_errors = []
    substitution_patterns = defaultdict(list)
    
    for f in failures:
        if f['fail_type'] == 'eng→kor' and f['actual'] and 'character' in f['reason']:
            import re
            match = re.search(r'character (\d+) differs: (.) → (.)', f['reason'])
            if match:
                pos, expected, actual = match.groups()
                char_errors.append((expected, actual))
                substitution_patterns[(expected, actual)].append(f['name'])
    
    print("\n\nMost common character substitutions:")
    char_counter = Counter(char_errors)
    
    for (exp, act), count in char_counter.most_common(10):
        print(f"\n{exp} → {act}: {count} times")
        examples = substitution_patterns[(exp, act)][:3]
        for ex in examples:
            print(f"  - {ex}")
    
    # Analyze null conversions
    null_conversions = [f for f in failures if f['actual'] is None]
    print(f"\n\nNull conversions: {len(null_conversions)}")
    for f in null_conversions[:5]:
        print(f"  - {f['name']}")
    
    # Analyze specific problematic names
    print("\n\nProblematic name patterns:")
    
    # Names with 'sun' that should be 선 not 순
    sun_issues = [f for f in failures if '선 → 순' in f.get('reason', '')]
    if sun_issues:
        print(f"\n'sun' → 순 (should be 선): {len(sun_issues)} cases")
        for f in sun_issues[:3]:
            print(f"  - {f['name']}: {f['expected']} → {f['actual']}")
    
    # Compound surnames
    compound_surnames = [f for f in failures if any(comp in f['name'] for comp in ['SaGong', 'SunWoo', 'DokGo'])]
    if compound_surnames:
        print(f"\nCompound surnames: {len(compound_surnames)} cases")
        for f in compound_surnames:
            print(f"  - {f['name']}: {f['reason']}")

def analyze_fst_preferences():
    """Analyze why FST prefers certain mappings."""
    import subprocess
    
    print("\n\nFST mapping preferences:")
    print("=" * 60)
    
    # Check what mappings exist for problematic syllables
    problematic = {
        'sun': ['선', '순'],
        'ri': ['리', '이'],
        'chang': ['창', '장'],
        'heon': ['헌', '훈'],
        'jung': ['정', '중']
    }
    
    for rom, hanguls in problematic.items():
        print(f"\n'{rom}' mappings:")
        cmd = f"grep ',{rom}$' resources/rr_syllable_map.csv"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                print(f"  {line}")
        else:
            print(f"  No direct mappings found")

def suggest_fixes():
    """Suggest specific fixes based on analysis."""
    print("\n\nSuggested fixes in priority order:")
    print("=" * 60)
    
    fixes = [
        {
            'issue': '선/순 confusion (5 cases)',
            'solution': 'Remove 순,sun mapping or add context rules',
            'impact': '+5 diverse'
        },
        {
            'issue': '리/이 confusion (4 cases)', 
            'solution': 'Fix ri mappings - prioritize 리 over 이',
            'impact': '+4 diverse'
        },
        {
            'issue': '창/장 confusion (4 cases)',
            'solution': 'Fix chang mappings - prioritize 창 over 장',
            'impact': '+4 diverse'
        },
        {
            'issue': '헌/훈 confusion (4 cases)',
            'solution': 'Fix heon mappings - prioritize 헌 over 훈',
            'impact': '+4 diverse'
        },
        {
            'issue': 'Null conversions (10 cases)',
            'solution': 'Add missing syllables for Dr_, Prof_ titles',
            'impact': '+2-3 diverse'
        }
    ]
    
    total_potential = 0
    for i, fix in enumerate(fixes, 1):
        print(f"\n{i}. {fix['issue']}")
        print(f"   Solution: {fix['solution']}")
        print(f"   Potential impact: {fix['impact']}")
        
        # Extract number from impact
        import re
        match = re.search(r'\+(\d+)', fix['impact'])
        if match:
            total_potential += int(match.group(1))
    
    print(f"\n\nTotal potential improvement: +{total_potential} diverse")
    print(f"Would bring diverse accuracy to: {153 + total_potential}/200 = {(153 + total_potential)/200*100:.1f}%")

if __name__ == "__main__":
    analyze_remaining_failures()
    analyze_fst_preferences()
    suggest_fixes()