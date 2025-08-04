import yaml
import sys
sys.path.append('src')
from converter import eng2kor, kor2eng, _dice
import unicodedata

data=yaml.safe_load(open('data/korean.yaml',encoding='utf8'))

def norm(s): return unicodedata.normalize("NFC",s.casefold().replace(" ",""))

# Check top round-trip failures
top_surnames = ['kim', 'lee', 'shin', 'oh', 'jang']

for surname in top_surnames:
    print(f"\n=== {surname.upper()} round-trip failures ===")
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
                if k == k_exp:  # Only check round-trip if ENG→KOR works
                    e2 = kor2eng(k, e) or ""
                    if _dice(norm(e), norm(e2)) < 0.97:
                        print(f"  {e} → {k_exp} → '{e2}' (Dice: {_dice(norm(e), norm(e2)):.3f})")
                        print(f"    Expected normalized: '{norm(e)}'")
                        print(f"    Got normalized: '{norm(e2)}'")
                        
                        count += 1
                        if count >= 2:  # Show max 2 examples per surname
                            break