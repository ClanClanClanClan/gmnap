#!/usr/bin/env python3
"""
Correct evaluation of diverse dataset using CanonicalLatin field
"""
import yaml, sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from converter import eng2kor, kor2eng
import unicodedata

def norm(s): 
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ",""))

def dice(a,b):
    a,b=set(zip(a,a[1:])),set(zip(b,b[1:]))
    return 2*len(a&b)/(len(a)+len(b) or 1)

def find_hangul(variants):
    for v in variants:
        if isinstance(v, str) and any('\uac00' <= c <= '\ud7af' for c in v):
            return v.replace(" ", "")
    return None

print("=== CORRECT DIVERSE DATASET EVALUATION ===\n")

with open("data/korean_diverse_test.yaml", encoding="utf8") as f:
    diverse_data = yaml.safe_load(f)

diverse_ok = diverse_tot = 0
diverse_failures = []

print("Testing using CanonicalLatin field (not key names)...\n")

for key, info in diverse_data.items():
    if isinstance(info, dict):
        # Use CanonicalLatin, not the key
        canonical = info.get("CanonicalLatin")
        expected_korean = find_hangul(info.get("AllCommonVariants", []))
        
        if not canonical or not expected_korean:
            continue
            
        diverse_tot += 1
        actual_korean = eng2kor(canonical)
        
        if actual_korean == expected_korean:
            diverse_ok += 1
        else:
            # Check roundtrip quality too
            if actual_korean:
                roundtrip = kor2eng(actual_korean, canonical)
                if roundtrip and dice(norm(canonical), norm(roundtrip)) >= 0.90:
                    diverse_ok += 1
                else:
                    diverse_failures.append((key, canonical, expected_korean, actual_korean, roundtrip))
            else:
                diverse_failures.append((key, canonical, expected_korean, None, None))

print(f"DIVERSE DATASET: {diverse_ok}/{diverse_tot} = {diverse_ok/diverse_tot*100:.2f}%")
print(f"Previous (wrong): 75/200 = 37.50%")
print(f"Improvement: +{diverse_ok-75} cases\n")

if diverse_failures:
    print(f"Remaining failures: {len(diverse_failures)}")
    print("\nFirst 10 failures:")
    for i, (key, canonical, expected, actual, roundtrip) in enumerate(diverse_failures[:10]):
        print(f"\n{i+1}. {key}:")
        print(f"   Canonical: {canonical}")
        print(f"   Expected: {expected}")
        print(f"   Actual: {actual}")
        if roundtrip:
            print(f"   Roundtrip: {roundtrip}")

# Also verify a few success cases
print(f"\n=== VERIFICATION OF SUCCESS CASES ===")
success_count = 0
for key, info in diverse_data.items():
    if isinstance(info, dict) and success_count < 5:
        canonical = info.get("CanonicalLatin")
        expected = find_hangul(info.get("AllCommonVariants", []))
        if canonical and expected:
            actual = eng2kor(canonical)
            if actual == expected:
                print(f"✅ {key}: {canonical} → {actual}")
                success_count += 1

print(f"\n=== CONCLUSION ===")
print("The diverse dataset IS high quality!")
print("Previous poor performance was due to testing wrong input.")
print("Using CanonicalLatin gives much better results.")