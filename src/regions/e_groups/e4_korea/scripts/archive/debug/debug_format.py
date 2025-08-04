import sys
sys.path.append('src')
from converter import eng2kor, kor2eng

# Test some specific conversions
test_cases = [
    "Kim, Baek-Jin",
    "Lee, Beom-Jun", 
    "Oh, Seong-Joon",
    "Baek, Hyeong-Chan"
]

for name in test_cases:
    print(f"\nTesting: {name}")
    kor = eng2kor(name)
    print(f"  ENG→KOR: {kor}")
    if kor:
        eng = kor2eng(kor, name)
        print(f"  KOR→ENG: '{eng}'")
        print(f"  Original: '{name}'")