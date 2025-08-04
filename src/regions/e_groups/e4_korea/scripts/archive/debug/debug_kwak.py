import yaml
import sys
sys.path.append('src')
from converter import eng2kor

data=yaml.safe_load(open('data/korean.yaml',encoding='utf8'))

# Check Kwak conversion issue
print("=== KWAK CONVERSION TEST ===")
test_kwak = eng2kor("Kwak")
print(f"eng2kor('Kwak') = {test_kwak}")

# Find Kwak examples
count = 0
for rec in data.values():
    e = rec["CanonicalLatin"]
    if e.split()[0].rstrip(",").lower() == "kwak":
        # Find Korean Hangul in variants
        k_exp = None
        for variant in rec.get("AllCommonVariants", []):
            if variant and any('\uac00' <= c <= '\ud7af' for c in variant):
                k_exp = variant.replace(" ", "")
                break
        
        if k_exp:
            k = eng2kor(e)
            print(f"\n{e} -> expected: {k_exp}, got: {k}")
            
        count += 1
        if count >= 3:
            break