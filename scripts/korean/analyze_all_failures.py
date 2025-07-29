#!/usr/bin/env python3
"""Analyze all failures from diverse dataset"""

import yaml
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path().resolve().parent / 'src'))
from converter import eng2kor

# Load diverse dataset
with open('../data/korean_diverse_test.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Test all names and collect failures
failures = []
for name, entry in data.items():
    canonical = entry.get('CanonicalLatin')
    expected = entry.get('Hangul')
    if canonical and expected:
        try:
            actual = eng2kor(canonical)
            if actual != expected:
                failures.append({
                    'name': canonical,
                    'expected': expected,
                    'actual': actual,
                    'type': 'eng→kor',
                    'category': entry.get('Categories', ['Other'])[0]
                })
        except Exception as e:
            failures.append({
                'name': canonical,
                'expected': expected,
                'actual': None,
                'type': 'eng→kor',
                'category': entry.get('Categories', ['Other'])[0],
                'error': str(e)
            })

# Sort by name for consistency
failures.sort(key=lambda x: x['name'])

# Print all failures for the auto-fix system
print(f'Found {len(failures)} failures in diverse dataset')
print('All failures for auto-fix analysis:')
for i, f in enumerate(failures):
    print(f"{{\"name\": \"{f['name']}\", \"expected\": \"{f['expected']}\", \"actual\": \"{f['actual']}\", \"type\": \"eng→kor\"}},")