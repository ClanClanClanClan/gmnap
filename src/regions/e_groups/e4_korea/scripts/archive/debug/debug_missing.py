import sys

import yaml

sys.path.append('src')
from converter import eng2kor

data=yaml.safe_load(open('data/korean.yaml',encoding='utf8'))

# Find examples for the top failing surnames
failing_surnames = ['chun', 'hong']

for surname in failing_surnames:
    print(f"\n=== {surname.upper()} examples ===")
    count = 0
    for rec in data.values():
        e = rec["CanonicalLatin"]
        first_name = e.split()[0].rstrip(",").lower()
        if first_name == surname:
            # Find Korean Hangul in variants
            k_exp = None
            for variant in rec.get("AllCommonVariants", []):
                if variant and any('\uac00' <= c <= '\ud7af' for c in variant):
                    k_exp = variant.replace(" ", "")
                    break
            
            if k_exp:
                k = eng2kor(e)
                if k != k_exp:
                    print(f"  {e} -> expected: {k_exp}, got: {k}")
                    # Extract just the surname part
                    surname_korean = k_exp[0] if k_exp else "?"
                    surname_english = e.split()[0].rstrip(",")
                    print(f"    Need: {surname_korean},{surname_english.lower()}")
                    
                count += 1
                if count >= 3:  # Show max 3 examples per surname
                    break