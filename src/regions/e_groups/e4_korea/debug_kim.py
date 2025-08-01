import yaml
import sys
sys.path.append('src')
from converter import eng2kor

data=yaml.safe_load(open('data/korean.yaml',encoding='utf8'))
kim_fails = []
for rec in data.values():
    e=rec['CanonicalLatin']; k_exp=rec['CJK']
    if e.split()[0].lower() == 'kim':
        k=eng2kor(e)
        if k != k_exp:
            kim_fails.append((e, k_exp, k))

# Check Kim failures with Hangul expectations
kim_fails = []
for rec in data.values():
    e = rec['CanonicalLatin']
    if e.split()[0].rstrip(",").lower() == "kim":
        # Find Korean Hangul in variants
        k_exp = None
        for variant in rec.get("AllCommonVariants", []):
            if variant and any('\uac00' <= c <= '\ud7af' for c in variant):
                k_exp = variant.replace(" ", "")
                break
        
        if k_exp:
            k = eng2kor(e)
            if k != k_exp:
                kim_fails.append((e, k_exp, k))

print(f'Kim failures: {len(kim_fails)}')
print('All Kim failures:')
for i, (e, k_exp, k) in enumerate(kim_fails):
    print(f'{i+1}. {e} -> expected: {k_exp}, got: {k}')