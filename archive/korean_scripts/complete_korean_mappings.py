#!/usr/bin/env python3
"""
Complete all remaining TODO mappings in korean_given_name_mappings.json
"""

import json
import re

def complete_mappings():
    """Complete all TODO mappings with proper Hangul"""
    
    # Load current mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_given_name_mappings.json', 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    
    # Comprehensive mappings for all remaining TODO items
    completion_mappings = {
        # Special blocks (mark as non-convertible)
        "rareinitialsblock": "SKIP_RARE_INITIALS",
        "raresurnamesblock": "SKIP_RARE_SURNAMES", 
        "rarediasporablock": "SKIP_RARE_DIASPORA",
        
        # Complete person name mappings
        "youngtae": "영태",
        "seungyeon": "승연",
        "heejoon": "희준",
        "boram": "보람",
        "mook": "묵",
        "jongseong": "종성",
        "songyi": "송이",
        "sukja": "숙자",
        "dongsung": "동성",
        "eunkyung": "은경",
        "jihye": "지혜",
        "jongchol": "종철",
        "eunmi": "은미",
        "munho": "문호",
        "jungwook": "정욱",
        "jongmo": "종모",
        "namsoo": "남수",
        "hyejeong": "혜정",
        "hyungjun": "형준",
        "yeonsoo": "연수",
        "minkyung": "민경",
        "suhyeon": "수현",
        "yeseul": "예슬",
        "junhyeok": "준혁",
        "jihyun": "지현",
        "sangwon": "상원",
        "yuna": "유나",
        "jaehwan": "재환",
        "minkyu": "민규",
        "hong": "홍",
        "mok": "목",
        "hyunji": "현지",
        "sangwook": "상욱",
        "moonseong": "문성",
        "sungwook": "성욱",
        "sumin": "수민",
        "hyunkyung": "현경",
        "donggeon": "동건",
        "sunmi": "선미",
        "jungwon": "정원",
        "seunghyun": "승현",
        "sangjoon": "상준",
        "myungjin": "명진",
        "sangmin": "상민",
        "myungjun": "명준",
        "geunyoung": "근영",
        "hyunil": "현일",
        "sungjun": "성준",
        "youngsu": "영수",
        "yeonjun": "연준",
        "heechan": "희찬",
        "yeongjae": "영재",
        "minhyuk": "민혁",
        "haesoo": "해수",
        "sooyoung": "수영",
        "donghoon": "동훈",
        "jaehyuk": "재혁",
        "jisu": "지수",
        "hyungki": "형기",
        "jeonghwan": "정환",
        "minsuk": "민석",
        "jisoo": "지수",
        "seongmin": "성민",
        "jiyong": "지용",
        "heeyoung": "희영",
        
        # Common surnames (these should be surnames, not given names)
        "kim": "김",
        "park": "박", 
        "lee": "이",
        "jeongkim": "정김",  # compound surname
        
        "chanho": "찬호",
        "hyowon": "효원",
        "sungmoon": "성문",
        "hyunseung": "현승",
        "yongseok": "용석",
        "sungjoon": "성준",
        "donggyu": "동규",
        "sookhee": "숙희",
        "hyoseon": "효선",
        "dongwook": "동욱",
        "jiyeon": "지연",
        "sohee": "소희",
        "sookyoung": "숙영",
        "sanghwa": "상화",
        "jaewon": "재원",
        "chun": "춘",
        "gwang": "광",
        "hyojung": "효정",
        "yoonjung": "윤정",
        "hun": "훈",
        "kwang": "광",
        "joonho": "준호",
        "guk": "국",
        "bokyun": "복윤",
        "hyeongmin": "형민",
        "youngjun": "영준",
        "rim": "림",
        "sil": "실",
        "geon": "건",
        "mo": "모",
        "mee": "미",
        "in": "인",
        "se": "세",
        "gi": "기",
        "yi": "이",
        "hyo": "효",
        "brian": "브라이언",  # foreign name
        "jongyoon": "종윤",
        "youngil": "영일",
        "hyejung": "혜정",
        "sangjun": "상준",
        "hyunsu": "현수",
        "haeri": "해리",
        "younghun": "영훈",
        "hojin": "호진",
        "junghun": "정훈",
        "youngseok": "영석",
        "jaeil": "재일",
        "jinho": "진호",
        "soohyun": "수현",
        "jongwon": "종원",
        "haejin": "해진",
        "baekcheol": "백철",
        "soojung": "수정",
        "sunghee": "성희",
        "jonghun": "종훈",
        "sooyong": "수용",
        "junghwan": "정환",
        "hyeonjin": "현진",
        "minjeong": "민정",
        "sookja": "숙자",
        "yeonwoo": "연우",
        "yeongju": "영주",
        "hyojin": "효진",
        "eunju": "은주",
        "hyejin": "혜진",
        "yeongok": "연옥",
        "soonjung": "순정",
        "hyesu": "혜수",
        "meehyun": "미현",
        "haeun": "하은",
        "myeongjin": "명진",
        "soonhee": "순희",
        "junseok": "준석",
        "eunjoo": "은주",
        "jungsoo": "정수",
        "hyesook": "혜숙",
        "soonho": "순호",
        "yeonji": "연지",
        "yongsoo": "용수",
        "youngju": "영주"
    }
    
    # Apply completions
    updates_made = 0
    for key, value in mappings.items():
        if value.startswith("TODO_"):
            clean_key = key.lower()
            if clean_key in completion_mappings:
                mappings[key] = completion_mappings[clean_key]
                updates_made += 1
                print(f"✅ {key}: {value} -> {completion_mappings[clean_key]}")
            else:
                print(f"❌ Missing mapping for: {key}")
    
    # Save updated mappings
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_given_name_mappings.json', 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Updated {updates_made} mappings")
    
    # Count remaining TODOs
    remaining_todos = sum(1 for v in mappings.values() if v.startswith("TODO_"))
    print(f"📊 Remaining TODO items: {remaining_todos}")

if __name__ == "__main__":
    complete_mappings()