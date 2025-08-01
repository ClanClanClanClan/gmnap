import yaml
import sys
sys.path.append('src')
from converter import eng2kor, kor2eng

# Load test data
data = yaml.safe_load(open('data/korean.yaml', encoding='utf8'))

def find_hangul(variants):
    for v in variants:
        if any('\uac00' <= c <= '\ud7af' for c in v):
            return v.replace(' ', '')
    return None

def _dice(a, b):
    import unicodedata
    a = '' if not a else a.replace(',', '').replace('-', ' ')
    b = '' if not b else b.replace(',', '').replace('-', ' ') 
    a = b'' if not a else unicodedata.normalize('NFC', a.casefold().replace(' ','')).encode()
    b = b'' if not b else unicodedata.normalize('NFC', b.casefold().replace(' ','')).encode()
    bigr = lambda s: {s[i:i+2] for i in range(len(s)-1)}
    x, y = bigr(a), bigr(b)
    return (2*len(x&y))/(len(x)+len(y) or 1)

# Analyze all failures
failures = []
total = 0

for name, info in data.items():
    rr = info.get('CanonicalLatin')
    ko_exp = find_hangul(info.get('AllCommonVariants', []))
    if not rr or not ko_exp: 
        continue
    
    total += 1
    ko = eng2kor(rr)
    
    if not ko:
        failures.append((name, 'eng-kor-fail', rr, ko_exp, 'None'))
        continue
    elif ko != ko_exp:
        failures.append((name, 'eng-kor', rr, ko_exp, ko))
        continue
        
    rr2 = kor2eng(ko, rr)
    if not rr2 or _dice(rr, rr2) < 0.90:
        dice_score = _dice(rr, rr2 or '') if rr2 else 0.0
        failures.append((name, 'roundtrip', rr, rr2 or 'None', f'dice={dice_score:.3f}'))

print(f'Total tested: {total}')
print(f'Failures: {len(failures)}')
print(f'Success rate: {(total-len(failures))/total*100:.2f}%')

print(f'\n=== ENG->KOR FAILURES (first 15) ===')
eng_failures = [f for f in failures if f[1].startswith('eng')]
for name, ftype, rr, expected, actual in eng_failures[:15]:
    print(f'{name}: {rr} -> {actual} (exp: {expected})')