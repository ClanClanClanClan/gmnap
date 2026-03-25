#!/usr/bin/env python3
"""
Create a high-quality independent validation dataset
Different from math/diverse datasets to test true generalization
"""
import json
import random
from datetime import datetime

print("=== CREATING INDEPENDENT VALIDATION DATASET ===")
print("Goal: Test true generalization, not overfitting to existing datasets")
print()

# HIGH-QUALITY INDEPENDENT TEST CASES
# Sources: Real Korean names from different domains (not math/entertainment focused)
independent_test_cases = [
    # POLITICAL FIGURES (different domain from math/entertainment)
    {
        "name": "Moon, Jae-In",
        "expected_korean": "문재인",
        "category": "political",
        "source": "Former President",
    },
    {
        "name": "Park, Geun-Hye",
        "expected_korean": "박근혜",
        "category": "political",
        "source": "Former President",
    },
    {
        "name": "Lee, Myung-Bak",
        "expected_korean": "이명박",
        "category": "political",
        "source": "Former President",
    },
    {
        "name": "Kim, Dae-Jung",
        "expected_korean": "김대중",
        "category": "political",
        "source": "Former President",
    },
    {
        "name": "Roh, Moo-Hyun",
        "expected_korean": "노무현",
        "category": "political",
        "source": "Former President",
    },
    {
        "name": "Yoon, Suk-Yeol",
        "expected_korean": "윤석열",
        "category": "political",
        "source": "Current President",
    },
    # BUSINESS LEADERS (different domain)
    {
        "name": "Lee, Jae-Yong",
        "expected_korean": "이재용",
        "category": "business",
        "source": "Samsung heir",
    },
    {
        "name": "Chung, Mong-Koo",
        "expected_korean": "정몽구",
        "category": "business",
        "source": "Hyundai Chairman",
    },
    {
        "name": "Shin, Dong-Bin",
        "expected_korean": "신동빈",
        "category": "business",
        "source": "Lotte Chairman",
    },
    {
        "name": "Kim, Beom-Su",
        "expected_korean": "김범수",
        "category": "business",
        "source": "Kakao founder",
    },
    {
        "name": "Bang, Si-Hyuk",
        "expected_korean": "방시혁",
        "category": "business",
        "source": "HYBE founder",
    },
    # HISTORICAL FIGURES (traditional names)
    {
        "name": "Yi, Sun-Sin",
        "expected_korean": "이순신",
        "category": "historical",
        "source": "Admiral",
    },
    {
        "name": "King, Sejong",
        "expected_korean": "세종",
        "category": "historical",
        "source": "Joseon King",
    },
    {
        "name": "Ahn, Jung-Geun",
        "expected_korean": "안중근",
        "category": "historical",
        "source": "Independence activist",
    },
    {
        "name": "Kim, Gu",
        "expected_korean": "김구",
        "category": "historical",
        "source": "Independence activist",
    },
    {
        "name": "Yu, Gwan-Sun",
        "expected_korean": "유관순",
        "category": "historical",
        "source": "Independence activist",
    },
    # LITERARY/CULTURAL FIGURES
    {"name": "Ko, Un", "expected_korean": "고은", "category": "literary", "source": "Poet"},
    {
        "name": "Park, Kyung-Ni",
        "expected_korean": "박경리",
        "category": "literary",
        "source": "Novelist",
    },
    {
        "name": "Hwang, Sok-Yong",
        "expected_korean": "황석영",
        "category": "literary",
        "source": "Novelist",
    },
    {
        "name": "Lee, Mun-Yol",
        "expected_korean": "이문열",
        "category": "literary",
        "source": "Novelist",
    },
    {"name": "Kim, So-Wol", "expected_korean": "김소월", "category": "literary", "source": "Poet"},
    # MODERN CULTURAL FIGURES (different from existing diverse dataset)
    {
        "name": "Bong, Joon-Ho",
        "expected_korean": "봉준호",
        "category": "culture",
        "source": "Film director",
    },
    {
        "name": "Park, Chan-Wook",
        "expected_korean": "박찬욱",
        "category": "culture",
        "source": "Film director",
    },
    {
        "name": "Kim, Ki-Duk",
        "expected_korean": "김기덕",
        "category": "culture",
        "source": "Film director",
    },
    {
        "name": "Lee, Chang-Dong",
        "expected_korean": "이창동",
        "category": "culture",
        "source": "Film director",
    },
    {
        "name": "Im, Kwon-Taek",
        "expected_korean": "임권택",
        "category": "culture",
        "source": "Film director",
    },
    # SPORTS FIGURES (different from existing)
    {"name": "Park, In-Bee", "expected_korean": "박인비", "category": "sports", "source": "Golfer"},
    {
        "name": "Kim, Yu-Na",
        "expected_korean": "김연아",
        "category": "sports",
        "source": "Figure skater",
    },
    {
        "name": "Lee, Seung-Yuop",
        "expected_korean": "이승엽",
        "category": "sports",
        "source": "Baseball player",
    },
    {
        "name": "Park, Tae-Hwan",
        "expected_korean": "박태환",
        "category": "sports",
        "source": "Swimmer",
    },
    {
        "name": "Ryu, Hyun-Jin",
        "expected_korean": "류현진",
        "category": "sports",
        "source": "Baseball pitcher",
    },
    # ACADEMIC/SCIENTIFIC FIGURES (different approach from math dataset)
    {
        "name": "Kim, Woo-Choong",
        "expected_korean": "김우중",
        "category": "academic",
        "source": "Former Daewoo founder",
    },
    {
        "name": "Lee, Hwi-So",
        "expected_korean": "이휘소",
        "category": "academic",
        "source": "Physicist",
    },
    {
        "name": "Suh, Nam-Pyo",
        "expected_korean": "서남표",
        "category": "academic",
        "source": "Engineer",
    },
    {
        "name": "Paik, Un-Gyu",
        "expected_korean": "백운규",
        "category": "academic",
        "source": "Scientist",
    },
    {
        "name": "Cho, Young-Je",
        "expected_korean": "조영제",
        "category": "academic",
        "source": "Researcher",
    },
    # EDGE CASES AND VARIATIONS
    {
        "name": "Rhee, Syngman",
        "expected_korean": "이승만",
        "category": "political",
        "source": "1st President (Rhee spelling)",
    },
    {
        "name": "Choi, Min-Sik",
        "expected_korean": "최민식",
        "category": "culture",
        "source": "Actor",
    },
    {
        "name": "Song, Kang-Ho",
        "expected_korean": "송강호",
        "category": "culture",
        "source": "Actor",
    },
    {
        "name": "Jeon, Do-Yeon",
        "expected_korean": "전도연",
        "category": "culture",
        "source": "Actress",
    },
    {"name": "Ha, Jung-Woo", "expected_korean": "하정우", "category": "culture", "source": "Actor"},
    # COMPOUND AND COMPLEX NAMES
    {
        "name": "Kim, Jong-Un",
        "expected_korean": "김정은",
        "category": "political",
        "source": "North Korean leader",
    },
    {
        "name": "Kim, Jong-Il",
        "expected_korean": "김정일",
        "category": "political",
        "source": "Former NK leader",
    },
    {
        "name": "Kim, Il-Sung",
        "expected_korean": "김일성",
        "category": "political",
        "source": "NK founder",
    },
    {"name": "Pak, Se-Ri", "expected_korean": "박세리", "category": "sports", "source": "Golfer"},
    {
        "name": "Lee, Young-Ae",
        "expected_korean": "이영애",
        "category": "culture",
        "source": "Actress",
    },
    # RARE SURNAMES AND PATTERNS
    {
        "name": "Noh, Sa-Yeon",
        "expected_korean": "노사연",
        "category": "culture",
        "source": "Singer",
    },
    {
        "name": "Shim, Eun-Ha",
        "expected_korean": "심은하",
        "category": "culture",
        "source": "Actress",
    },
    {"name": "Cha, In-Pyo", "expected_korean": "차인표", "category": "culture", "source": "Actor"},
    {"name": "Gong, Yoo", "expected_korean": "공유", "category": "culture", "source": "Actor"},
    {"name": "Won, Bin", "expected_korean": "원빈", "category": "culture", "source": "Actor"},
]

print(f"Created {len(independent_test_cases)} independent test cases")
print(f"Categories: {set(case['category'] for case in independent_test_cases)}")
print()

# Add metadata
dataset_info = {
    "name": "Independent Korean Name Validation Dataset",
    "version": "1.0",
    "created": datetime.now().isoformat(),
    "description": "High-quality Korean names from diverse domains for independent validation",
    "total_cases": len(independent_test_cases),
    "categories": {
        "political": len([c for c in independent_test_cases if c["category"] == "political"]),
        "business": len([c for c in independent_test_cases if c["category"] == "business"]),
        "historical": len([c for c in independent_test_cases if c["category"] == "historical"]),
        "literary": len([c for c in independent_test_cases if c["category"] == "literary"]),
        "culture": len([c for c in independent_test_cases if c["category"] == "culture"]),
        "sports": len([c for c in independent_test_cases if c["category"] == "sports"]),
        "academic": len([c for c in independent_test_cases if c["category"] == "academic"]),
    },
    "quality_criteria": [
        "Real Korean names from verified sources",
        "Diverse domains (not math/entertainment focused)",
        "Mix of common and rare surnames",
        "Various given name patterns",
        "Edge cases and spelling variations",
        "Historical and modern figures",
    ],
}

# Save dataset
dataset = {"info": dataset_info, "test_cases": independent_test_cases}

with open("data/independent_validation_dataset.json", "w", encoding="utf8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

print("✅ Independent validation dataset created!")
print(f"Saved to: data/independent_validation_dataset.json")
print()
print("=== DATASET STATISTICS ===")
for category, count in dataset_info["categories"].items():
    print(f"- {category.capitalize()}: {count} cases")
print()
print("=== QUALITY FEATURES ===")
for feature in dataset_info["quality_criteria"]:
    print(f"✓ {feature}")
print()
print("Ready to test current system performance on this independent dataset!")
