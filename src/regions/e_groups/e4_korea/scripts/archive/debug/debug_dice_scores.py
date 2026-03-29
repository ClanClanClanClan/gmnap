import yaml, unicodedata, sys
sys.path.append('src')
from converter import eng2kor, kor2eng

def norm(s): 
    # Remove punctuation and normalize for fair comparison
    s = s.replace(",", "").replace("-", " ")
    return unicodedata.normalize("NFC", s.casefold().replace(" ",""))

def dice(a,b):
    a,b=set(zip(a,a[1:])),set(zip(b,b[1:]))
    return 2*len(a&b)/(len(a)+len(b) or 1)

def find_hangul(variants):
    for v in variants:
        if any('\uac00' <= c <= '\ud7af' for c in v):
            return v.replace(" ", "")
    return None

# Test specific cases
test_cases = [
    "Kim, Baek-Jin",
    "Lee, Beom-Jun", 
    "Oh, Seong-Joon",
    "Shin, Jung-Soon",
    "Baek, Hyeong-Chan"
]

data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

for test_name in test_cases:
    # Find in data
    for k, v in data.items():
        rr = v.get("CanonicalLatin")
        if rr == test_name:
            ko_exp = find_hangul(v.get("AllCommonVariants", []))
            if ko_exp:
                ko = eng2kor(rr)
                if ko == ko_exp:
                    rr2 = kor2eng(ko, rr) or ""
                    score = dice(norm(rr), norm(rr2))
                    print(f"\n{rr}")
                    print(f"  Korean: {ko}")
                    print(f"  Round-trip: '{rr2}'")
                    print(f"  Normalized orig: '{norm(rr)}'")
                    print(f"  Normalized r-t:  '{norm(rr2)}'")
                    print(f"  Dice score: {score:.3f} {'✓' if score >= 0.97 else '✗'}")
                break