#!/usr/bin/env python3
"""
Korean name database with correct mappings for common names.
This ensures accurate conversion of well-known Korean names.
"""

# Common Korean surnames with correct Hangul
KOREAN_SURNAMES = {
    # Most common surnames
    "kim": "김",
    "gim": "김",
    "lee": "이", 
    "yi": "이",
    "rhee": "이",
    "park": "박",
    "pak": "박",
    "bak": "박",
    "choi": "최",
    "choe": "최",
    "jung": "정",
    "jeong": "정",
    "chung": "정",
    "cheong": "정",
    "kang": "강",
    "gang": "강",
    "jo": "조",
    "cho": "조",
    "yoon": "윤",
    "yun": "윤",
    "jang": "장",
    "chang": "장",
    "lim": "임",
    "im": "임",
    "han": "한",
    "oh": "오",
    "o": "오",
    "seo": "서",
    "suh": "서",
    "shin": "신",
    "sin": "신",
    "kwon": "권",
    "gwon": "권",
    "hwang": "황",
    "ahn": "안",
    "an": "안",
    "song": "송",
    "jeon": "전",
    "jun": "전",
    "chun": "전",
    "cheon": "천",
    "hong": "홍",
    "yu": "유",
    "yoo": "유",
    "ryu": "류",
    "ryoo": "류",
    "ko": "고",
    "go": "고",
    "koh": "고",
    "goh": "고",
    "moon": "문",
    "mun": "문",
    "yang": "양",
    "bae": "배",
    "pae": "배",
    "baek": "백",
    "paek": "백",
    "heo": "허",
    "hur": "허",
    "huh": "허",
    "nam": "남",
    "shim": "심",
    "sim": "심",
    "noh": "노",
    "no": "노",
    "roh": "노",
    "ro": "노",
    "ha": "하",
    "joo": "주",
    "ju": "주",
    "koo": "구",
    "gu": "구",
    "ku": "구",
    "min": "민",
    "jin": "진",
    "cha": "차",
    "yeo": "여",
    "yuh": "여",
    "chu": "추",
    "choo": "추",
    "bu": "부",
    "boo": "부",
    "won": "원",
    "weon": "원",
}

# Common given name syllables
KOREAN_GIVEN_NAMES = {
    # Male given names
    "tae": "태",
    "hyung": "형",
    "hyeong": "형",
    "ho": "호",
    "min": "민",
    "jun": "준",
    "joon": "준",
    "sung": "성",
    "seong": "성",
    "woo": "우",
    "u": "우",
    "jin": "진",
    "hyun": "현",
    "hyeon": "현",
    "jae": "재",
    "young": "영",
    "yeong": "영",
    "yong": "용",
    "hoon": "훈",
    "hun": "훈",
    "chan": "찬",
    "won": "원",
    "weon": "원",
    "seok": "석",
    "suk": "석",
    "dong": "동",
    "sang": "상",
    "hwan": "환",
    "kyu": "규",
    "gyu": "규",
    "kyun": "균",
    "gyun": "균",
    "ki": "기",
    "gi": "기",
    "han": "한",
    "il": "일",
    "chul": "철",
    "cheol": "철",
    
    # Female given names
    "ji": "지",
    "hee": "희",
    "hui": "희",
    "mi": "미",
    "soo": "수",
    "su": "수",
    "eun": "은",
    "sun": "선",
    "seon": "선",
    "hye": "혜",
    "hae": "해",
    "yeon": "연",
    "yun": "연",
    "kyung": "경",
    "gyeong": "경",
    "jung": "정",
    "jeong": "정",
    "na": "나",
    "in": "인",
    "ah": "아",
    "a": "아",
    "yoo": "유",
    "yu": "유",
    "bin": "빈",
    "rin": "린",
    
    # Unisex
    "min": "민",
    "jun": "준",
    "hyun": "현",
    "ji": "지",
    
    # Additional common syllables
    "guk": "국",
    "kook": "국",
    "gook": "국",
    "sik": "식",
    "shik": "식",
    "hak": "학",
    "man": "만",
    "bum": "범",
    "beom": "범",
    "sub": "섭",
    "seob": "섭",
    "sup": "섭",
    "seop": "섭",
    "pil": "필",
    "phil": "필",
    "gun": "건",
    "geon": "건",
    "kun": "건",
    "keon": "건",
}

# Combine both dictionaries
KOREAN_NAME_MAPPINGS = {**KOREAN_SURNAMES, **KOREAN_GIVEN_NAMES}

def get_hangul_for_name(romanized: str) -> str:
    """
    Get the correct Hangul for a romanized Korean name syllable.
    Returns the original string if no mapping found.
    """
    return KOREAN_NAME_MAPPINGS.get(romanized.lower(), romanized)

def is_korean_surname(romanized: str) -> bool:
    """Check if the romanized string is a known Korean surname"""
    return romanized.lower() in KOREAN_SURNAMES

def is_korean_given_name(romanized: str) -> bool:
    """Check if the romanized string is a known Korean given name syllable"""
    return romanized.lower() in KOREAN_GIVEN_NAMES

def split_korean_name(full_name: str) -> tuple:
    """
    Split a Korean name into surname and given name parts.
    Returns (surname, given_name) or (None, full_name) if can't determine.
    """
    parts = full_name.strip().split()
    
    if len(parts) >= 2:
        # Check if first part is a surname
        if is_korean_surname(parts[0]):
            return (parts[0], ' '.join(parts[1:]))
    
    # Try without spaces (compound)
    name_lower = full_name.lower().replace(' ', '').replace('-', '')
    
    # Check common surname lengths (1-4 characters typically)
    for i in range(1, min(5, len(name_lower))):
        potential_surname = name_lower[:i]
        if is_korean_surname(potential_surname):
            return (full_name[:i], full_name[i:])
    
    return (None, full_name)


if __name__ == "__main__":
    # Test the database
    test_names = [
        "kim", "lee", "park", "choi",
        "tae", "hyung", "min", "ho",
        "Kim Taehyung", "Park Jimin", "Lee Minho"
    ]
    
    print("Korean Name Database Test")
    print("=" * 40)
    
    for name in test_names:
        hangul = get_hangul_for_name(name)
        name_type = ""
        if is_korean_surname(name):
            name_type = " (surname)"
        elif is_korean_given_name(name):
            name_type = " (given name)"
        
        print(f"{name:15} -> {hangul}{name_type}")
    
    print("\nName splitting test:")
    print("=" * 40)
    
    full_names = ["Kim Taehyung", "kimtaehyung", "Park Ji Min", "leeminho"]
    
    for name in full_names:
        surname, given = split_korean_name(name)
        print(f"{name:15} -> Surname: {surname}, Given: {given}")