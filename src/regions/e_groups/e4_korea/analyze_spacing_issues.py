#!/usr/bin/env python3
"""
Analyze spacing and segmentation issues in name conversion.
"""

import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from converter import eng2kor, tokenise
from segment_fixed import segment

def analyze_multisyllable_failures():
    """Analyze failures involving multi-syllable names."""
    with open('data/diverse_failures.json', 'r', encoding='utf-8') as f:
        failures = json.load(f)
    
    multisyllable_issues = []
    
    for fail in failures:
        if fail['fail_type'] == 'eng→kor' and 'syllable count mismatch' in fail.get('reason', ''):
            multisyllable_issues.append(fail)
    
    print(f"Multi-syllable segmentation issues: {len(multisyllable_issues)}")
    print("=" * 60)
    
    for issue in multisyllable_issues[:10]:
        name = issue['name']
        expected = issue['expected']
        actual = issue['actual']
        
        print(f"\n{name}:")
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")
        print(f"  Reason: {issue['reason']}")
        
        # Debug tokenization and segmentation
        name_parts = name.split('_')
        print(f"  Tokenization: {name} → {name_parts}")
        
        for part in name_parts:
            segments = segment(part.lower())
            print(f"    {part} → {segments}")

def check_compound_surnames():
    """Check compound surname handling."""
    compound_names = [
        ("SaGong_HyunMoo", "사공현무"),
        ("SunWoo_YongNyeo", "선우용녀"),
        ("DokGo_YoungJae", "독고영재")
    ]
    
    print("\n\nCompound Surname Analysis:")
    print("=" * 60)
    
    for eng, expected_kor in compound_names:
        actual = eng2kor(eng)
        
        print(f"\n{eng}:")
        print(f"  Expected: {expected_kor}")
        print(f"  Actual: {actual}")
        
        # Debug tokenization
        tokens = tokenise(eng)
        print(f"  Tokens: {tokens}")
        
        for tok in tokens:
            segments = segment(tok.lower())
            print(f"    {tok} → segments: {segments}")

def check_specific_problems():
    """Check specific problematic conversions."""
    problems = [
        ("ChongWei", "청위"),   # Being converted to 정웨이
        ("JungKook", "정국"),   # Being converted to 정고옥
        ("HyeKyo", "혜교"),     # Being converted to 혜쿄
    ]
    
    print("\n\nSpecific Problem Analysis:")
    print("=" * 60)
    
    for eng, expected in problems:
        actual = eng2kor(eng)
        segments = segment(eng.lower())
        
        print(f"\n{eng} → {actual} (expected: {expected})")
        print(f"  Segments: {segments}")
        
        # Check each segment
        from converter import _rr2han
        for seg in segments:
            han = _rr2han(seg)
            print(f"    {seg} → {han}")

if __name__ == "__main__":
    analyze_multisyllable_failures()
    check_compound_surnames()
    check_specific_problems()