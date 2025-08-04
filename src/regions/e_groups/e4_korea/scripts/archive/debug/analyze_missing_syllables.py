#!/usr/bin/env python3
"""
Analyze which syllables are missing from the lexicon causing conversion failures.
"""

import sys
import pathlib
import json
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from syllable_lexicon import LEXICON
from segment import segment

def analyze_failed_names():
    """Load and analyze names that failed to convert."""
    # Load diverse failures
    with open('data/diverse_failures.json', 'r', encoding='utf-8') as f:
        failures = json.load(f)
    
    null_failures = []
    syllable_issues = []
    
    for fail in failures:
        if fail['actual'] is None:
            null_failures.append(fail['name'])
            # Try to segment the name to find missing syllables
            name_parts = fail['name'].split('_')
            for part in name_parts:
                segments = segment(part.lower())
                if segments == [part.lower()]:  # Couldn't segment
                    syllable_issues.append(part.lower())
    
    print(f"Names that returned null: {len(null_failures)}")
    for name in null_failures[:10]:
        print(f"  - {name}")
    if len(null_failures) > 10:
        print(f"  ... and {len(null_failures) - 10} more")
    
    print(f"\nPotential missing syllables:")
    syllable_counts = Counter(syllable_issues)
    for syl, count in syllable_counts.most_common():
        print(f"  {syl}: {count} occurrences")
    
    # Check specific problematic syllables
    print("\nChecking specific syllables in lexicon:")
    test_syllables = ['ah', 'sung', 'david', 'sarah', 'grace', 'eugene', 
                      'joseph', 'michelle', 'james', 'jessica', 'peter',
                      'chun', 'hyang', 'sagong', 'sunwoo', 'dokgo']
    
    for syl in test_syllables:
        in_lexicon = syl in LEXICON
        print(f"  {syl:15} {'✓' if in_lexicon else '✗'}")

def check_english_names():
    """Check how English names should be handled."""
    print("\n\nChecking English name patterns:")
    
    english_names = {
        'David': '데이비드',
        'Sarah': '사라',
        'Grace': '그레이스',
        'Eugene': '유진',
        'Joseph': '요셉',
        'Michelle': '미셸',
        'James': '제임스',
        'Jessica': '제시카',
        'Peter': '피터'
    }
    
    for eng, kor in english_names.items():
        print(f"\n{eng} → {kor}")
        # Try to segment
        segments = segment(eng.lower())
        print(f"  Segments: {segments}")
        
        # Check each potential syllable
        eng_lower = eng.lower()
        for i in range(len(eng_lower)):
            for j in range(i+1, len(eng_lower)+1):
                syl = eng_lower[i:j]
                if syl in LEXICON:
                    print(f"    '{syl}' ✓")

if __name__ == "__main__":
    analyze_failed_names()
    check_english_names()