#!/usr/bin/env python3
"""
Generate a diverse Korean name test dataset covering various domains and romanization styles.
"""

import yaml
import random
from collections import defaultdict
from typing import List, Dict, Tuple

# Common Korean surnames with variations
SURNAMES = {
    "김": ["Kim", "Gim"],
    "이": ["Lee", "Yi", "I", "Rhee", "Li"],
    "박": ["Park", "Pak", "Bak", "Pak"],
    "최": ["Choi", "Choe"],
    "정": ["Jung", "Jeong", "Chung"],
    "강": ["Kang", "Gang"],
    "조": ["Cho", "Jo"],
    "윤": ["Yoon", "Yun", "Youn"],
    "장": ["Jang", "Chang"],
    "임": ["Lim", "Im", "Yim"],
    "한": ["Han"],
    "오": ["Oh", "O"],
    "서": ["Seo", "Suh"],
    "신": ["Shin", "Sin"],
    "권": ["Kwon", "Gwon"],
    "황": ["Hwang", "Whang"],
    "송": ["Song"],
    "전": ["Jeon", "Chun", "Chon"],
    "홍": ["Hong"],
    "유": ["Yoo", "Yu", "Ryu"],
    "고": ["Ko", "Go"],
    "문": ["Moon", "Mun"],
    "양": ["Yang"],
    "손": ["Son", "Sohn"],
    "배": ["Bae", "Pae"],
    "백": ["Baek", "Baik", "Paek", "Paik"],
    "허": ["Heo", "Hur", "Huh"],
    "남": ["Nam", "Lam"],
    "심": ["Shim", "Sim"],
    "노": ["Noh", "Roh", "No", "Ro"],
    "하": ["Ha"],
    "곽": ["Kwak", "Gwak"],
    "성": ["Sung", "Seong"],
    "차": ["Cha"],
    "주": ["Joo", "Ju"],
    "우": ["Woo", "Wu", "U"],
    "구": ["Koo", "Ku", "Gu"],
    "나": ["Na", "La"],
    "진": ["Jin", "Chin"],
    "원": ["Won", "Weon"]
}

# Common given name syllables with variations
GIVEN_NAME_SYLLABLES = {
    # Traditional male syllables
    "훈": ["Hun", "Hoon"],
    "현": ["Hyun", "Hyeon"],
    "형": ["Hyeong", "Hyung"],
    "호": ["Ho"],
    "환": ["Hwan"],
    "희": ["Hee", "Hui"],
    "혁": ["Hyuk", "Hyeok"],
    "준": ["Jun", "Joon"],
    "진": ["Jin", "Chin"],
    "재": ["Jae"],
    "정": ["Jung", "Jeong"],
    "종": ["Jong"],
    "중": ["Jung", "Joong"],
    "철": ["Chul", "Cheol"],
    "창": ["Chang"],
    "찬": ["Chan"],
    
    # Traditional female syllables
    "은": ["Eun", "Un"],
    "영": ["Young", "Yeong"],
    "연": ["Yeon", "Yon"],
    "윤": ["Yoon", "Yun"],
    "유": ["Yu", "Yoo"],
    "예": ["Ye", "Yae"],
    "아": ["Ah", "A"],
    "애": ["Ae"],
    "인": ["In"],
    "이": ["I", "Yi", "Lee"],
    
    # Modern unisex syllables
    "민": ["Min"],
    "서": ["Seo", "Suh"],
    "성": ["Sung", "Seong"],
    "수": ["Su", "Soo"],
    "시": ["Si", "Shi"],
    "우": ["Woo", "U"],
    "원": ["Won", "Weon"],
    "지": ["Ji", "Jee", "Chi"],
    "주": ["Ju", "Joo"],
    "하": ["Ha"],
    "한": ["Han"],
    "혜": ["Hye", "Hae"],
    "효": ["Hyo"],
    
    # Additional syllables for diversity
    "규": ["Gyu", "Kyu"],
    "기": ["Ki", "Gi"],
    "나": ["Na"],
    "대": ["Dae"],
    "동": ["Dong"],
    "라": ["Ra", "La"],
    "리": ["Ri", "Li", "Lee"],
    "미": ["Mi", "Mee"],
    "범": ["Bum", "Beom"],
    "병": ["Byung", "Byeong"],
    "보": ["Bo"],
    "빈": ["Bin"],
    "상": ["Sang"],
    "석": ["Seok", "Suk"],
    "선": ["Sun", "Seon"],
    "소": ["So"],
    "승": ["Seung"],
    "신": ["Sin", "Shin"],
    "양": ["Yang"],
    "용": ["Yong"],
    "욱": ["Wook", "Uk"],
    "운": ["Un", "Woon"],
    "일": ["Il"],
    "태": ["Tae"],
    "택": ["Taek", "Taik"],
    "필": ["Pil", "Phil"],
    "학": ["Hak"],
    "헌": ["Hun", "Heon"]
}

def generate_name_variants(surname_kr: str, given_kr: str, surname_variants: List[str], 
                         given_variants: List[List[str]]) -> Tuple[str, str, List[str]]:
    """Generate various romanization variants for a name."""
    # Create canonical forms
    canonical_surname = surname_variants[0]
    canonical_given = "-".join([v[0] for v in given_variants])
    
    canonical_latin = f"{canonical_surname}, {canonical_given}"
    canonical_western = f"{canonical_given} {canonical_surname}"
    
    # Generate all variants
    all_variants = []
    
    # Add Korean original
    all_variants.append(f"{surname_kr}{given_kr}")
    
    for sur in surname_variants:
        for given_combo in generate_given_name_combinations(given_variants):
            # Western order variations
            all_variants.append(f"{given_combo} {sur}")
            
            # Eastern order variations
            all_variants.append(f"{sur} {given_combo}")
            all_variants.append(f"{sur}, {given_combo}")
            
            # Initial forms
            if "-" in given_combo:
                parts = given_combo.split("-")
                if len(parts) == 2:
                    all_variants.append(f"{sur}, {parts[0][0]}.-{parts[1][0]}.")
                    all_variants.append(f"{parts[0][0]}.-{parts[1][0]}. {sur}")
                    all_variants.append(f"{parts[0][0]}. {sur}")
            else:
                all_variants.append(f"{sur}, {given_combo[0]}.")
                all_variants.append(f"{given_combo[0]}. {sur}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in all_variants:
        if v not in seen:
            seen.add(v)
            unique_variants.append(v)
    
    return canonical_latin, canonical_western, unique_variants

def generate_given_name_combinations(syllable_variants: List[List[str]]) -> List[str]:
    """Generate different combinations of given name syllables."""
    combinations = []
    
    if len(syllable_variants) == 1:
        # Single syllable name
        return syllable_variants[0]
    
    elif len(syllable_variants) == 2:
        # Two syllable name (most common)
        for first in syllable_variants[0]:
            for second in syllable_variants[1]:
                # Hyphenated
                combinations.append(f"{first}-{second}")
                # Space separated
                combinations.append(f"{first} {second}")
                # Combined
                combinations.append(f"{first}{second}")
                # Lowercase second
                combinations.append(f"{first}-{second.lower()}")
                combinations.append(f"{first}{second.lower()}")
    
    return combinations

def create_test_entry(name_id: str, surname_kr: str, given_kr: str, 
                     surname_variants: List[str], given_variants: List[List[str]], 
                     domain: str, diaspora: List[str] = None) -> Dict:
    """Create a test entry for the YAML file."""
    canonical_latin, canonical_western, all_variants = generate_name_variants(
        surname_kr, given_kr, surname_variants, given_variants
    )
    
    entry = {
        "CanonicalLatin": canonical_latin,
        "CanonicalWestern": canonical_western,
        "AllCommonVariants": all_variants[:20],  # Limit to avoid too many variants
        "DiasporaFlags": diaspora or ["KR"],
        "Comments": f"{domain} domain; includes various romanization styles."
    }
    
    return entry

def generate_diverse_dataset():
    """Generate a diverse Korean name dataset."""
    dataset = {}
    
    # 1. Athletes
    athletes = [
        ("Son_HeungMin", "손", "흥민", ["Son", "Sohn"], [["Heung"], ["Min"]], "Sports (Football)"),
        ("Kim_YuNa", "김", "연아", ["Kim", "Gim"], [["Yeon", "Yun", "Yu"], ["A", "Ah"]], "Sports (Figure Skating)"),
        ("Park_JiSung", "박", "지성", ["Park", "Pak"], [["Ji", "Jee"], ["Sung", "Seong"]], "Sports (Football)"),
        ("Lee_ChongWei", "이", "청위", ["Lee", "Yi"], [["Chung", "Cheong"], ["Wei", "Wi"]], "Sports (Badminton)", ["MY", "KR"]),
        ("Ryu_HyunJin", "류", "현진", ["Ryu", "Lyu", "Yu"], [["Hyun", "Hyeon"], ["Jin", "Chin"]], "Sports (Baseball)"),
        ("Hwang_HeuiChan", "황", "희찬", ["Hwang", "Whang"], [["Hee", "Hui"], ["Chan"]], "Sports (Football)"),
        ("Bae_YeonJoo", "배", "연주", ["Bae", "Pae"], [["Yeon", "Yon"], ["Ju", "Joo"]], "Sports (Badminton)"),
        ("Shin_YuBin", "신", "유빈", ["Shin", "Sin"], [["Yu", "Yoo"], ["Bin"]], "Sports (Table Tennis)"),
        ("Ko_JinYoung", "고", "진영", ["Ko", "Go"], [["Jin", "Chin"], ["Young", "Yeong"]], "Sports (Golf)"),
        ("An_SanMi", "안", "산미", ["An", "Ahn"], [["San"], ["Mi", "Mee"]], "Sports (Archery)"),
    ]
    
    # 2. Entertainment (BTS, Blackpink, actors, etc.)
    entertainers = [
        ("Kim_NamJoon", "김", "남준", ["Kim", "Gim"], [["Nam"], ["Jun", "Joon"]], "Entertainment (BTS - RM)"),
        ("Kim_SeokJin", "김", "석진", ["Kim", "Gim"], [["Seok", "Suk"], ["Jin", "Chin"]], "Entertainment (BTS - Jin)"),
        ("Min_YoonGi", "민", "윤기", ["Min"], [["Yoon", "Yun"], ["Gi", "Ki"]], "Entertainment (BTS - Suga)"),
        ("Jung_HoSeok", "정", "호석", ["Jung", "Jeong", "Chung"], [["Ho"], ["Seok", "Suk"]], "Entertainment (BTS - J-Hope)"),
        ("Park_JiMin", "박", "지민", ["Park", "Pak"], [["Ji", "Jee"], ["Min"]], "Entertainment (BTS - Jimin)"),
        ("Kim_TaeHyung", "김", "태형", ["Kim", "Gim"], [["Tae"], ["Hyung", "Hyeong"]], "Entertainment (BTS - V)"),
        ("Jeon_JungKook", "전", "정국", ["Jeon", "Chun", "Chon"], [["Jung", "Jeong"], ["Kook", "Guk"]], "Entertainment (BTS - Jungkook)"),
        ("Kim_JiSoo", "김", "지수", ["Kim", "Gim"], [["Ji", "Jee"], ["Su", "Soo"]], "Entertainment (BLACKPINK - Jisoo)"),
        ("Park_ChaeYoung", "박", "채영", ["Park", "Pak"], [["Chae"], ["Young", "Yeong"]], "Entertainment (BLACKPINK - Rosé)"),
        ("Lee_MinHo", "이", "민호", ["Lee", "Yi", "I"], [["Min"], ["Ho"]], "Entertainment (Actor)"),
        ("Song_HyeKyo", "송", "혜교", ["Song"], [["Hye", "Hae"], ["Kyo", "Gyo"]], "Entertainment (Actress)"),
        ("Gong_Yoo", "공", "유", ["Gong", "Kong"], [["Yoo", "Yu"]], "Entertainment (Actor)"),
        ("Bae_SuZy", "배", "수지", ["Bae", "Pae"], [["Su", "Soo"], ["Ji", "Jee", "Zy"]], "Entertainment (Singer/Actress)"),
        ("IU_LeeJiEun", "이", "지은", ["Lee", "Yi"], [["Ji", "Jee"], ["Eun", "Un"]], "Entertainment (Singer - IU)"),
        ("Yoo_JaeSeok", "유", "재석", ["Yoo", "Yu"], [["Jae"], ["Seok", "Suk"]], "Entertainment (Comedian)"),
    ]
    
    # 3. Politicians and Public Figures
    politicians = [
        ("Moon_JaeIn", "문", "재인", ["Moon", "Mun"], [["Jae"], ["In"]], "Politics (Former President)"),
        ("Yoon_SeokYeol", "윤", "석열", ["Yoon", "Yun"], [["Seok", "Suk"], ["Yeol", "Youl"]], "Politics (President)"),
        ("Park_GeunHye", "박", "근혜", ["Park", "Pak"], [["Geun", "Keun"], ["Hye", "Hae"]], "Politics (Former President)"),
        ("Lee_MyungBak", "이", "명박", ["Lee", "Yi"], [["Myung", "Myeong"], ["Bak", "Park"]], "Politics (Former President)"),
        ("Ahn_CheolSoo", "안", "철수", ["Ahn", "An"], [["Chul", "Cheol"], ["Su", "Soo"]], "Politics/Business"),
        ("Ban_KiMoon", "반", "기문", ["Ban", "Pan"], [["Ki", "Gi"], ["Moon", "Mun"]], "Politics (Former UN Secretary-General)"),
        ("Han_DukSoo", "한", "덕수", ["Han"], [["Duk", "Deok"], ["Su", "Soo"]], "Politics (Prime Minister)"),
        ("Kim_YoJong", "김", "여정", ["Kim", "Gim"], [["Yo", "Yeo"], ["Jong", "Jeong"]], "Politics"),
        ("Chung_EuiSun", "정", "의선", ["Chung", "Jung", "Jeong"], [["Eui", "Ui"], ["Sun", "Seon"]], "Business (Hyundai)"),
        ("Lee_JaeYong", "이", "재용", ["Lee", "Yi"], [["Jae"], ["Yong"]], "Business (Samsung)"),
    ]
    
    # 4. Traditional and modern common names
    common_names = [
        ("Kim_MinJun", "김", "민준", ["Kim", "Gim"], [["Min"], ["Jun", "Joon"]], "Common name (popular boy name)"),
        ("Lee_SeoYeon", "이", "서연", ["Lee", "Yi"], [["Seo", "Suh"], ["Yeon", "Yon"]], "Common name (popular girl name)"),
        ("Park_HaJun", "박", "하준", ["Park", "Pak"], [["Ha"], ["Jun", "Joon"]], "Common name (modern boy name)"),
        ("Choi_JiWoo", "최", "지우", ["Choi", "Choe"], [["Ji", "Jee"], ["Woo", "U"]], "Common name (modern girl name)"),
        ("Jung_SiWoo", "정", "시우", ["Jung", "Jeong"], [["Si", "Shi"], ["Woo", "U"]], "Common name (modern boy name)"),
        ("Kang_YeJin", "강", "예진", ["Kang", "Gang"], [["Ye", "Yae"], ["Jin", "Chin"]], "Common name (girl name)"),
        ("Cho_EunJi", "조", "은지", ["Cho", "Jo"], [["Eun", "Un"], ["Ji", "Jee"]], "Common name (girl name)"),
        ("Yoon_DoHyun", "윤", "도현", ["Yoon", "Yun"], [["Do"], ["Hyun", "Hyeon"]], "Common name (boy name)"),
        ("Jang_YuRi", "장", "유리", ["Jang", "Chang"], [["Yu", "Yoo"], ["Ri", "Li"]], "Common name (girl name)"),
        ("Lim_JaeHyun", "임", "재현", ["Lim", "Im", "Yim"], [["Jae"], ["Hyun", "Hyeon"]], "Common name (boy name)"),
    ]
    
    # 5. Historical figures
    historical = [
        ("Yi_SunSin", "이", "순신", ["Yi", "Lee", "I"], [["Sun", "Soon"], ["Sin", "Shin"]], "Historical (Admiral)"),
        ("King_Sejong", "세", "종", ["Se"], [["Jong"]], "Historical (King Sejong the Great)", ["KR"]),
        ("Shin_SaImDang", "신", "사임당", ["Shin", "Sin"], [["Sa"], ["Im"], ["Dang"]], "Historical (Artist/Writer)"),
        ("Kim_Gu", "김", "구", ["Kim", "Gim"], [["Gu", "Ku", "Koo"]], "Historical (Independence activist)"),
        ("An_JungGeun", "안", "중근", ["An", "Ahn"], [["Jung", "Joong"], ["Geun", "Keun"]], "Historical (Independence activist)"),
        ("Yun_DongJu", "윤", "동주", ["Yun", "Yoon"], [["Dong"], ["Ju", "Joo"]], "Historical (Poet)"),
    ]
    
    # 6. Business leaders
    business = [
        ("Lee_KunHee", "이", "건희", ["Lee", "Yi"], [["Kun", "Geon"], ["Hee", "Hui"]], "Business (Samsung founder)"),
        ("Chung_JuYung", "정", "주영", ["Chung", "Jung", "Jeong"], [["Ju", "Joo"], ["Young", "Yeong"]], "Business (Hyundai founder)"),
        ("Kim_BeomSu", "김", "범수", ["Kim", "Gim"], [["Bum", "Beom"], ["Su", "Soo"]], "Business (Kakao founder)"),
        ("Lee_HaeJin", "이", "해진", ["Lee", "Yi"], [["Hae", "Hea"], ["Jin", "Chin"]], "Business (Naver founder)"),
        ("Seo_JungJin", "서", "정진", ["Seo", "Suh"], [["Jung", "Jeong"], ["Jin", "Chin"]], "Business (Celltrion)"),
    ]
    
    # 7. Single syllable names
    single_syllable = [
        ("Kim_Min", "김", "민", ["Kim", "Gim"], [["Min"]], "Single syllable name"),
        ("Lee_Jun", "이", "준", ["Lee", "Yi"], [["Jun", "Joon"]], "Single syllable name"),
        ("Park_Bin", "박", "빈", ["Park", "Pak"], [["Bin"]], "Single syllable name"),
        ("Choi_Sol", "최", "솔", ["Choi", "Choe"], [["Sol"]], "Single syllable name"),
        ("Jung_Han", "정", "한", ["Jung", "Jeong"], [["Han"]], "Single syllable name"),
    ]
    
    # 8. Challenging romanization cases
    challenging = [
        ("Kwak_DongYeon", "곽", "동연", ["Kwak", "Gwak"], [["Dong"], ["Yeon", "Yon"]], "Challenging romanization"),
        ("Baek_YeRin", "백", "예린", ["Baek", "Baik", "Paek", "Paik"], [["Ye", "Yae"], ["Rin", "Lin"]], "Challenging romanization"),
        ("Noh_HongChul", "노", "홍철", ["Noh", "Roh", "No", "Ro"], [["Hong"], ["Chul", "Cheol"]], "Challenging romanization"),
        ("Shim_ChangMin", "심", "창민", ["Shim", "Sim"], [["Chang"], ["Min"]], "Challenging romanization"),
        ("Ha_JungWoo", "하", "정우", ["Ha"], [["Jung", "Jeong"], ["Woo", "U"]], "Challenging romanization"),
        ("Heo_YoungJi", "허", "영지", ["Heo", "Hur", "Huh"], [["Young", "Yeong"], ["Ji", "Jee"]], "Challenging romanization"),
        ("Go_AhSung", "고", "아성", ["Go", "Ko"], [["Ah", "A"], ["Sung", "Seong"]], "Challenging romanization"),
        ("Na_MoonHee", "나", "문희", ["Na", "La"], [["Moon", "Mun"], ["Hee", "Hui"]], "Challenging romanization"),
        ("Won_Bin", "원", "빈", ["Won", "Weon"], [["Bin"]], "Challenging romanization"),
        ("Oh_YeonSoo", "오", "연수", ["Oh", "O"], [["Yeon", "Yon"], ["Su", "Soo"]], "Challenging romanization"),
    ]
    
    # 9. Diaspora names with Western influence
    diaspora = [
        ("Kim_David", "김", "데이비드", ["Kim", "Gim"], [["David"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Lee_Sarah", "이", "사라", ["Lee", "Yi"], [["Sarah", "Sara"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Park_Daniel", "박", "다니엘", ["Park", "Pak"], [["Daniel"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Jung_Grace", "정", "그레이스", ["Jung", "Jeong"], [["Grace"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Choi_Eugene", "최", "유진", ["Choi", "Choe"], [["Eugene", "Yujin", "Yu-jin"]], "Diaspora (Western/Korean)", ["US", "KR"]),
        ("Han_Joseph", "한", "요셉", ["Han"], [["Joseph", "Yosep"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Kang_Michelle", "강", "미셸", ["Kang", "Gang"], [["Michelle", "Mi-shell"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Yoon_James", "윤", "제임스", ["Yoon", "Yun"], [["James"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Lim_Jessica", "임", "제시카", ["Lim", "Im"], [["Jessica"]], "Diaspora (Western first name)", ["US", "KR"]),
        ("Shin_Peter", "신", "피터", ["Shin", "Sin"], [["Peter"]], "Diaspora (Western first name)", ["US", "KR"]),
    ]
    
    # 10. Traditional three-syllable names
    three_syllable = [
        ("Kim_HakSoon", "김", "학순", ["Kim", "Gim"], [["Hak"], ["Soon", "Sun"]], "Traditional name"),
        ("Lee_ChunHyang", "이", "춘향", ["Lee", "Yi"], [["Chun"], ["Hyang"]], "Traditional name"),
        ("Park_BokNam", "박", "복남", ["Park", "Pak"], [["Bok", "Pok"], ["Nam"]], "Traditional name"),
    ]
    
    # 11. Modern compound surnames
    compound_surnames = [
        ("NamGung_Min", "남궁", "민", ["Namgung", "Nam-gung", "Nam Gung"], [["Min"]], "Compound surname"),
        ("SaGong_HyunMoo", "사공", "현무", ["Sagong", "Sa-gong", "Sa Gong"], [["Hyun", "Hyeon"], ["Moo", "Mu"]], "Compound surname"),
        ("SunWoo_YongNyeo", "선우", "용녀", ["Sunwoo", "Sun-woo", "Seon-u", "Seonwoo"], [["Yong"], ["Nyeo", "Nyuh"]], "Compound surname"),
        ("DokGo_YoungJae", "독고", "영재", ["Dokgo", "Dok-go", "Dok Go"], [["Young", "Yeong"], ["Jae"]], "Compound surname"),
    ]
    
    # 12. Special cases with particles or titles
    special_cases = [
        ("Kim_PhD", "김", "박사", ["Kim", "Gim"], [["Park-sa", "Baksa"]], "Title included"),
        ("Dr_Lee", "이", "박사", ["Lee", "Yi"], [["Dr.", "Doctor"]], "Western title"),
        ("Prof_Park", "박", "교수", ["Park", "Pak"], [["Prof.", "Professor"]], "Western title"),
    ]
    
    # Combine all categories
    all_entries = (
        athletes + entertainers + politicians + common_names + 
        historical + business + single_syllable + challenging + 
        diaspora + three_syllable + compound_surnames + special_cases
    )
    
    # Generate entries
    for entry_data in all_entries:
        if len(entry_data) == 6:
            name_id, surname_kr, given_kr, surname_vars, given_vars, domain = entry_data
            diaspora = None
        else:
            name_id, surname_kr, given_kr, surname_vars, given_vars, domain, diaspora = entry_data
        
        dataset[name_id] = create_test_entry(
            name_id, surname_kr, given_kr, surname_vars, given_vars, domain, diaspora
        )
    
    # Add some random generated names for extra diversity
    random_surnames = list(SURNAMES.keys())
    random_syllables = list(GIVEN_NAME_SYLLABLES.keys())
    
    # Generate more random names to reach 200+ total
    num_random = max(70, 200 - len(dataset))  # At least 70 random names
    
    for i in range(num_random):
        surname_kr = random.choice(random_surnames)
        num_syllables = random.choice([1, 2, 2, 2])  # Favor 2-syllable names
        given_kr = "".join(random.sample(random_syllables, num_syllables))
        
        surname_vars = SURNAMES[surname_kr]
        given_vars = []
        for syl in given_kr:
            if syl in GIVEN_NAME_SYLLABLES:
                given_vars.append(GIVEN_NAME_SYLLABLES[syl])
            else:
                given_vars.append([syl])  # Fallback for unknown syllables
        
        name_id = f"Random_{i+1:03d}"
        dataset[name_id] = create_test_entry(
            name_id, surname_kr, given_kr, surname_vars, given_vars, 
            "Randomly generated name"
        )
    
    return dataset

def main():
    """Main function to generate and save the dataset."""
    print("Generating diverse Korean name test dataset...")
    
    dataset = generate_diverse_dataset()
    
    print(f"Generated {len(dataset)} test entries")
    
    # Save to YAML file
    output_file = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea/data/korean_diverse_test.yaml"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(dataset, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"Dataset saved to: {output_file}")
    
    # Print some statistics
    domains = defaultdict(int)
    for entry in dataset.values():
        domain = entry["Comments"].split(";")[0]
        domains[domain] += 1
    
    print("\nDataset statistics:")
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count}")
    print(f"  Total: {len(dataset)}")

if __name__ == "__main__":
    main()