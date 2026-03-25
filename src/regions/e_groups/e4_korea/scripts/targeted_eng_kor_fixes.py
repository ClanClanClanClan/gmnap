#!/usr/bin/env python3
"""
Find targeted eng→kor fixes that won't hurt roundtrip quality
Focus on None results and unique context cases
"""
import yaml
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor


def find_hangul(variants):
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


# Load test data
data = yaml.safe_load(open("data/korean.yaml", encoding="utf8"))

print("=== TARGETED ENG→KOR FIXES (NO ROUNDTRIP DAMAGE) ===")

# Find current eng→kor failures
eng_kor_failures = []
for k, v in data.items():
    rr = v.get("CanonicalLatin")
    ko_exp = find_hangul(v.get("AllCommonVariants", []))
    if not rr or not ko_exp:
        continue

    ko = eng2kor(rr)
    if ko != ko_exp:
        eng_kor_failures.append({"name": k, "input": rr, "expected": ko_exp, "got": ko})

print(f"Current eng→kor failures: {len(eng_kor_failures)}")

# Categorize by safety for fixing
safe_fixes = []  # None results - adding mapping won't conflict
risky_fixes = []  # Wrong mappings - changing might hurt roundtrip

for f in eng_kor_failures:
    if f["got"] is None:
        safe_fixes.append(f)
    else:
        risky_fixes.append(f)

print(f"Safe fixes (None results): {len(safe_fixes)}")
print(f"Risky fixes (Wrong mappings): {len(risky_fixes)}")

print("\n=== SAFE FIXES (None results - can add mapping safely) ===")
for i, f in enumerate(safe_fixes[:10]):
    print(f"{i+1:2d}. {f['name']}")
    print(f"    Input: {f['input']}")
    print(f"    Expected: {f['expected']}")

    # Identify what specific segment is failing
    from preprocess import tokenise
    from segment import segment

    tokens = list(tokenise(f["input"]))
    print(f"    Tokens: {tokens}")

    for j, token in enumerate(tokens):
        segments = segment(token)
        for k, seg in enumerate(segments):
            seg_result = eng2kor(seg)
            if seg_result is None:
                print(f"    → MISSING: '{seg}' → need Korean mapping")
    print()

print("\n=== SAFE FIX RECOMMENDATIONS ===")
# Generate safe mappings that can be added without conflicts
safe_mappings = {
    # These are segments that return None and need Korean mappings
    "hahm": "함",  # Hahm, Jung-Ho → 함정호
    "law": "로",  # Law, Hyun-Jung → 로현정
    "koh": "고",  # Koh, Jae-Sung → 고재성
    "rho": "노",  # Rho, Jung-Hoon → 노정훈
    "rim": "임",  # Rim, Jun-Seok → 임준석 (not 림)
    "boo": "부",  # Boo, Kyung-Min → 부경민 (not 보오)
    "jee": "지",  # Jee, Sung-Min → 지성민 (not 제이이)
    "eoh": "어",  # Eoh, Hyun-Ji → 어현지 (not 에오)
    "gwak": "곽",  # Gwak, Jung-Hoon → 곽정훈 (not 괔)
    "um": "음",  # Um, Hyeong-Min → 음형민 (not 엄)
    "yook": "육",  # Yook, Ji-Sun → 육지선 (not 요옥)
    "to": "도",  # To, Yong-Hyun → 도용현 (not 토)
    "yom": "염",  # Yom, Ha-Rim → 염하림 (not 욤)
    "yum": "염",  # Yum, Young-Tae → 염영태 (not 윰)
    "pae": "배",  # Pae, Soon-Jung → 배순정 (not 패)
}

print("Recommended safe mappings (add without conflicts):")
for rom, han in safe_mappings.items():
    print(f"  {han},{rom}")

print(f"\n🎯 Potential safe improvement: ~{len(safe_mappings)} cases")
print("⚠️  These add new mappings without changing existing ones")
print("✅ Should not hurt roundtrip quality")
