#!/usr/bin/env python3
"""
Extract Korean given names from the dataset and create mappings
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import json
import re
from collections import defaultdict

def extract_given_names():
    """Extract given names from Korean mathematician dataset"""
    print("=== EXTRACTING KOREAN GIVEN NAMES ===\n")
    
    # Load Korean dataset
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean.yaml', 'r', encoding='utf-8') as f:
        korean_data = yaml.safe_load(f)
    
    # Extract given names
    given_name_components = defaultdict(int)
    surnames = set()
    
    # Known Korean surnames (most common)
    common_surnames = {
        'kim', 'lee', 'park', 'choi', 'jung', 'jeong', 'kang', 'jo', 'jang', 'chang',
        'yoon', 'yun', 'lim', 'im', 'han', 'oh', 'seo', 'shin', 'kwon', 'hwang',
        'ahn', 'song', 'hong', 'yu', 'yoo', 'bae', 'moon', 'mun', 'yang', 'sim',
        'nam', 'ko', 'go', 'choe', 'baek', 'paik', 'ha', 'huh', 'heo', 'noh',
        'roh', 'joo', 'cha', 'eom', 'uhm', 'byun', 'jeon', 'min', 'paek', 'rhee',
        'yi', 'ryu', 'chun', 'kwak', 'jin', 'tak', 'woo', 'suh', 'so'
    }
    
    print("Analyzing Korean mathematician names...")
    
    for key, entry in korean_data.items():
        name = key.replace('_', ' ')
        
        # Skip invalid entries
        if len(name) < 2 or any(c.isdigit() for c in name):
            continue
        
        # Split name into components
        components = []
        if ' ' in name:
            components = name.split()
        elif '-' in name:
            components = name.split('-')
        else:
            # CamelCase
            parts = re.findall(r'[A-Z][a-z]*|[a-z]+', name)
            components = parts if len(parts) > 1 else [name]
        
        if len(components) >= 2:
            surname = components[0].lower()
            surnames.add(surname)
            
            # Everything after first component is given name parts
            for given_part in components[1:]:
                # Handle hyphenated given names
                if '-' in given_part:
                    for sub_part in given_part.split('-'):
                        if sub_part and len(sub_part) > 1:
                            given_name_components[sub_part.lower()] += 1
                else:
                    if given_part and len(given_part) > 1:
                        given_name_components[given_part.lower()] += 1
    
    print(f"Found {len(surnames)} unique surnames")
    print(f"Found {len(given_name_components)} unique given name components")
    
    # Create mapping dictionaries based on common Korean romanization patterns
    given_name_mappings = {}
    
    # Map common given name components to Hangul
    # This is based on standard Korean romanization patterns
    common_given_mappings = {
        # Common syllables
        'jae': '재', 'hyun': '현', 'jung': '정', 'young': '영', 'min': '민',
        'ho': '호', 'soo': '수', 'jin': '진', 'hoon': '훈', 'woo': '우',
        'kyung': '경', 'seok': '석', 'dong': '동', 'sang': '상', 'won': '원',
        'il': '일', 'chul': '철', 'ki': '기', 'tae': '태', 'jun': '준',
        'hee': '희', 'sun': '선', 'mi': '미', 'ye': '예', 'eun': '은',
        'ji': '지', 'so': '소', 'na': '나', 'da': '다', 'ra': '라',
        
        # Extended mappings
        'baek': '백', 'bin': '빈', 'bo': '보', 'byung': '병', 'chan': '찬',
        'cheol': '철', 'cheon': '천', 'da': '다', 'dae': '대', 'duck': '덕',
        'geun': '근', 'gil': '길', 'gu': '구', 'gyu': '규', 'hae': '해',
        'hak': '학', 'han': '한', 'hwan': '환', 'hyeok': '혁', 'hyeon': '현',
        'hyeong': '형', 'hyuk': '혁', 'jang': '장', 'jik': '직', 'joo': '주',
        'joon': '준', 'joong': '중', 'jou': '주', 'jung': '정', 'kook': '국',
        'kwan': '관', 'kyu': '규', 'man': '만', 'myung': '명', 'nam': '남',
        'ok': '옥', 'ryong': '룡', 'seong': '성', 'sik': '식', 'soon': '순',
        'sub': '섭', 'suk': '석', 'sup': '섭', 'uk': '욱', 'yong': '용',
        
        # Compound components
        'jaeho': '재호', 'jaehyun': '재현', 'jaekyung': '재경', 'jaeyoung': '재영',
        'sunghoon': '성훈', 'sungmin': '성민', 'sungwoo': '성우', 'sungho': '성호',
        'hyunsoo': '현수', 'hyunjin': '현진', 'hyunwoo': '현우', 'hyunjung': '현정',
        'minsoo': '민수', 'minwoo': '민우', 'minho': '민호', 'minjung': '민정',
        'jiyoung': '지영', 'jiwon': '지원', 'jihoon': '지훈', 'jinhee': '진희',
        'youngho': '영호', 'youngsoo': '영수', 'youngmin': '영민', 'youngjae': '영재',
        'donghyun': '동현', 'dongwoo': '동우', 'dongho': '동호', 'dongmin': '동민',
        'seokhoon': '석훈', 'seokmin': '석민', 'seokwoo': '석우', 'seokho': '석호',
        'jongmin': '종민', 'jongwoo': '종우', 'jongho': '종호', 'jonghoon': '종훈',
        'kyungho': '경호', 'kyungmin': '경민', 'kyungwoo': '경우', 'kyungjin': '경진',
        'daehoon': '대훈', 'daewoo': '대우', 'daeho': '대호', 'daemin': '대민',
        'wonho': '원호', 'wonwoo': '원우', 'wonmin': '원민', 'wonjin': '원진',
        'jungchul': '정철', 'jungho': '정호', 'junghoon': '정훈', 'jungmin': '정민',
        'baekjin': '백진', 'baekho': '백호', 'baekhoon': '백훈', 'baekmin': '백민'
    }
    
    # Build comprehensive mapping
    for component, count in given_name_components.items():
        if component in common_given_mappings:
            given_name_mappings[component] = common_given_mappings[component]
        else:
            # For unknown components, we'll need to research or use phonetic mapping
            # For now, mark as needing research
            given_name_mappings[component] = f"TODO_{component.upper()}"
    
    print(f"\n=== TOP 30 GIVEN NAME COMPONENTS ===")
    sorted_components = sorted(given_name_components.items(), key=lambda x: x[1], reverse=True)
    
    mapped_count = 0
    for i, (component, count) in enumerate(sorted_components[:30]):
        mapping = given_name_mappings.get(component, "UNMAPPED")
        status = "✅" if not mapping.startswith("TODO_") else "❌"
        print(f"{i+1:2d}. {component:12s}: {count:3d} occurrences -> {mapping} {status}")
        if status == "✅":
            mapped_count += 1
    
    print(f"\nMapped: {mapped_count}/30 top components ({mapped_count/30*100:.1f}%)")
    
    # Save the mappings
    with open('korean_given_name_mappings.json', 'w', encoding='utf-8') as f:
        json.dump(given_name_mappings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved {len(given_name_mappings)} given name mappings to korean_given_name_mappings.json")
    
    return given_name_mappings

if __name__ == "__main__":
    extract_given_names()