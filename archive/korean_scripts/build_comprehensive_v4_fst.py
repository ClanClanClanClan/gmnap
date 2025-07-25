#!/usr/bin/env python3
"""Build comprehensive V4 FST from Korean dataset analysis"""

import json
import pynini as pn
import yaml
from collections import defaultdict

print("Building comprehensive V4 FST...")

# Load the Korean V4 mappings (normalization data)
with open('korean_v4_mappings.yaml', 'r', encoding='utf-8') as f:
    v4_data = yaml.safe_load(f)

# Load reverse romanization maps to get Hangul mappings
with open('data/reverse_romanization_maps.json', 'r', encoding='utf-8') as f:
    reverse_maps = json.load(f)

# Load existing V4 mappings
with open('data/v4_mappings.json', 'r', encoding='utf-8') as f:
    existing_v4 = json.load(f)

# Flatten all mappings into roman->hangul pairs
all_mappings = {}

# First, add existing V4 mappings
for roman, hangul in existing_v4.items():
    all_mappings[roman.lower()] = hangul

# Get the korean_v4 data
korean_v4 = v4_data.get('korean_v4', {})

# Create a mapping from normalized forms to their Hangul
normalized_to_hangul = {}

# First, add all common Korean mappings with correct Hangul
common_korean_mappings = {
    # Surnames
    'kim': '김', 'gim': '김', 'ghim': '김',
    'lee': '이', 'yi': '이', 'rhee': '이', 'ri': '이', 'li': '이',
    'park': '박', 'pak': '박', 'bak': '박', 'bahk': '박',
    'choi': '최', 'choe': '최', "ch'oe": '최', 'chwe': '최',
    'jung': '정', 'jeong': '정', 'chung': '정', 'cheong': '정',
    'yoon': '윤', 'yun': '윤', 'youn': '윤',
    'kang': '강', 'gang': '강', 'kahng': '강',
    'cho': '조', 'jo': '조', 'joh': '조',
    'jang': '장', 'chang': '장', 'jahng': '장',
    'lim': '임', 'im': '임', 'yim': '임', 'rim': '림',
    'han': '한', 'hahn': '한',
    'oh': '오', 'o': '오', 'eo': '어',
    'shin': '신', 'sin': '신',
    'seo': '서', 'suh': '서', 'so': '소',
    'kwon': '권', 'kweon': '권', 'gwon': '권',
    'hwang': '황', 'whang': '황', 'hoang': '황',
    'ahn': '안', 'an': '안',
    'song': '송', 'soung': '송',
    'hong': '홍', 'houng': '홍',
    'yoo': '유', 'yu': '유', 'ryu': '류', 'ryoo': '류',
    'ko': '고', 'go': '고', 'goh': '고', 'koh': '고',
    'yang': '양', 'ryang': '양',
    'moon': '문', 'mun': '문',
    'bae': '배', 'pae': '배', 'bay': '배', 'bai': '배',
    'baek': '백', 'paek': '백', 'baik': '백', 'paik': '백', 'back': '백',
    'huh': '허', 'hur': '허', 'heo': '허',
    'noh': '노', 'no': '노', 'roh': '노', 'ro': '노',
    'ha': '하', 'hah': '하',
    'shim': '심', 'sim': '심',
    'ku': '구', 'gu': '구', 'koo': '구', 'goo': '구',
    'nam': '남', 'nahm': '남',
    'woo': '우', 'wu': '우', 'u': '우',
    
    # Common given name parts
    'young': '영', 'yeong': '영', 'yong': '용', 'yung': '영',
    'jin': '진', 'jean': '진',
    'soo': '수', 'su': '수',
    'min': '민',
    'hyun': '현', 'hyeon': '현', 'hyung': '형', 'hyon': '현',
    'hoon': '훈', 'hun': '훈',
    'ji': '지', 'jee': '지', 'chi': '지',
    'ho': '호', 'hoh': '호',
    'sang': '상',
    'jae': '재', 'je': '재', 'chae': '재',
    'kyung': '경', 'kyeong': '경', 'gyeong': '경', 'gyung': '경',
    'hee': '희', 'hui': '희', 'hi': '희',
    'woo': '우', 'u': '우',
    'seok': '석', 'suk': '석', 'seog': '석',
    'dong': '동', 'tong': '동',
    'seong': '성', 'sung': '성', 'song': '성',
    'jun': '준', 'joon': '준',
    'won': '원', 'weon': '원',
    'yong': '용',
    'moon': '문', 'mun': '문',
    'il': '일', 'eel': '일',
    'chul': '철', 'cheol': '철', 'chol': '철',
    'ki': '기', 'gi': '기', 'kee': '기',
    'tae': '태', 'tai': '태',
    'bum': '범', 'beom': '범', 'bom': '범',
    'kyu': '규', 'gyu': '규', 'kyoo': '규',
    'han': '한', 'hahn': '한'
}

# Add these common mappings first
for roman, hangul in common_korean_mappings.items():
    all_mappings[roman] = hangul

# Process surname variations (but don't overwrite existing correct mappings)
surname_variations = korean_v4.get('common_variations', {}).get('surnames', {})
for normalized, variations in surname_variations.items():
    # Try to find Hangul for the normalized form
    normalized_lower = normalized.lower()
    
    # Check if we already have a mapping
    if normalized_lower in all_mappings:
        hangul = all_mappings[normalized_lower]
    else:
        # Skip if we don't have a mapping
        continue
    
    # Map all variations to the same Hangul (but don't overwrite existing)
    for variant in variations:
        variant_lower = variant.lower()
        if variant_lower not in all_mappings:
            all_mappings[variant_lower] = hangul

# Process given name variations (but don't overwrite existing correct mappings)
given_variations = korean_v4.get('common_variations', {}).get('given_names', {})
for normalized, variations in given_variations.items():
    # Try to find Hangul for the normalized form
    normalized_lower = normalized.lower()
    
    # Check if we already have a mapping
    if normalized_lower in all_mappings:
        hangul = all_mappings[normalized_lower]
    else:
        # Skip if we don't have a mapping
        continue
    
    # Map all variations to the same Hangul (but don't overwrite existing)
    for variant in variations:
        variant_lower = variant.lower()
        if variant_lower not in all_mappings:
            all_mappings[variant_lower] = hangul

# Remove any incorrect mappings that might have been added
# Keep only mappings where the value is actual Hangul (not romanization)
filtered_mappings = {}
for roman, value in all_mappings.items():
    # Check if value is Hangul (Korean characters are in range 0xAC00-0xD7A3)
    if value and any(0xAC00 <= ord(c) <= 0xD7A3 for c in value):
        filtered_mappings[roman] = value
    else:
        # Try to find the correct Hangul for this romanization
        if roman in common_korean_mappings:
            filtered_mappings[roman] = common_korean_mappings[roman]

all_mappings = filtered_mappings

print(f"Total mappings: {len(all_mappings)}")

# Build FST with penalty weight λ=3.0
v4_fst = pn.string_map([(roman, hangul) for roman, hangul in all_mappings.items()],
                       input_token_type="utf8", output_token_type="utf8")

# Apply weight to entire FST
lambda_weight = 3.0
weights = [pn.Weight('tropical', lambda_weight)] * v4_fst.num_states()
v4_fst.reweight(weights)

v4_fst = v4_fst.optimize()
v4_fst.write("data/v4_comprehensive.fst")

print(f"✅ Saved comprehensive V4 FST to data/v4_comprehensive.fst")
print(f"   FST has {v4_fst.num_states()} states")

# Save the mappings as JSON for inspection
with open('data/v4_comprehensive_mappings.json', 'w', encoding='utf-8') as f:
    json.dump(all_mappings, f, ensure_ascii=False, indent=2)
print(f"   Also saved mappings to data/v4_comprehensive_mappings.json")