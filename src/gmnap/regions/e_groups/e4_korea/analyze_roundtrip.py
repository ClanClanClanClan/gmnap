#!/usr/bin/env python3
import yaml
import sys
sys.path.append('src')
from converter import eng2kor, kor2eng, _dice
import unicodedata
import collections

data = yaml.safe_load(open('data/korean.yaml', encoding='utf8'))

def norm(s): 
    return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))

# Analyze specific round-trip patterns
surname_patterns = collections.defaultdict(list)

for rec in data.values():
    e = rec["CanonicalLatin"]
    
    # Find Korean Hangul in variants
    k_exp = None
    for variant in rec.get("AllCommonVariants", []):
        if variant and any('\uac00' <= c <= '\ud7af' for c in variant):
            k_exp = variant.replace(" ", "")
            break
    
    if not k_exp:
        continue
        
    k = eng2kor(e)
    if k == k_exp:
        e2 = kor2eng(k, e) or ""
        if _dice(norm(e), norm(e2)) < 0.97:
            surname = e.split()[0].rstrip(",").lower()
            # Extract what romanization was returned
            returned_surname = e2.split()[0] if e2 else ""
            surname_patterns[surname].append((e, e2, returned_surname))

# Print patterns for top failing surnames
for surname in ['kim', 'lee', 'shin', 'oh', 'jang']:
    patterns = surname_patterns[surname]
    if patterns:
        print(f"\n=== {surname.upper()} patterns ===")
        # Group by returned surname variant
        variant_counts = collections.Counter(p[2] for p in patterns)
        for variant, count in variant_counts.most_common():
            print(f"  {surname} → {variant}: {count} cases")
        print(f"  Total failures: {len(patterns)}")