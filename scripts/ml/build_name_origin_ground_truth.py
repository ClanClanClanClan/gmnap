#!/usr/bin/env python3
"""
Build Name-Origin Ground Truth Dataset

Creates curated ground truth based on LINGUISTIC/ONOMASTIC origin,
NOT workplace affiliation.

Follows expert guidance from gmnap_stage2_origin_kit_v1.
"""

import json
from pathlib import Path


def build_ground_truth():
    """Build name-origin ground truth with high-confidence labels."""

    truth = []

    # =================================================================
    # PHASE 1: Native Script Examples (100% confidence)
    # =================================================================
    print("Phase 1: Building native script examples...")

    # E1 - Sinophone Mainland (Chinese characters → E1)
    chinese_names = [
        ("王伟", "Wang Wei"),
        ("张明", "Zhang Ming"),
        ("李娜", "Li Na"),
        ("刘洋", "Liu Yang"),
        ("陈静", "Chen Jing"),
        ("杨芳", "Yang Fang"),
        ("赵敏", "Zhao Min"),
        ("黄强", "Huang Qiang"),
        ("周杰", "Zhou Jie"),
        ("吴勇", "Wu Yong"),
        ("徐霞", "Xu Xia"),
        ("孙涛", "Sun Tao"),
        ("马超", "Ma Chao"),
        ("朱军", "Zhu Jun"),
        ("胡平", "Hu Ping"),
        ("郭磊", "Guo Lei"),
        ("林峰", "Lin Feng"),
        ("何敏", "He Min"),
        ("高阳", "Gao Yang"),
        ("罗华", "Luo Hua"),
    ]
    for native, romanized in chinese_names:
        truth.append(
            {
                "name": romanized,
                "native": native,
                "origin": "E1",
                "source": "native_script_chinese",
                "confidence": 1.0,
                "notes": "Chinese characters → Mainland Sinophone",
            }
        )

    # E3 - Japan (Japanese script → E3)
    japanese_names = [
        ("田中太郎", "Tanaka Taro"),
        ("佐藤愛子", "Sato Aiko"),
        ("鈴木健", "Suzuki Takeshi"),
        ("山本恵子", "Yamamoto Keiko"),
        ("中村博", "Nakamura Hiroshi"),
        ("小林真由美", "Kobayashi Mayumi"),
        ("加藤誠", "Kato Makoto"),
        ("吉田由美", "Yoshida Yumi"),
        ("渡辺浩二", "Watanabe Koji"),
        ("伊藤美穂", "Ito Miho"),
    ]
    for native, romanized in japanese_names:
        truth.append(
            {
                "name": romanized,
                "native": native,
                "origin": "E3",
                "source": "native_script_japanese",
                "confidence": 1.0,
                "notes": "Japanese Kanji/Kana → Japan",
            }
        )

    # E4 - Korea (Hangul → E4)
    korean_names = [
        ("김민준", "Kim Min-jun"),
        ("이서연", "Lee Seo-yeon"),
        ("박지훈", "Park Ji-hoon"),
        ("최수진", "Choi Soo-jin"),
        ("정현우", "Jung Hyun-woo"),
        ("강민서", "Kang Min-seo"),
        ("조윤아", "Cho Yun-a"),
        ("윤지호", "Yoon Ji-ho"),
        ("장서준", "Jang Seo-jun"),
        ("임하은", "Lim Ha-eun"),
    ]
    for native, romanized in korean_names:
        truth.append(
            {
                "name": romanized,
                "native": native,
                "origin": "E4",
                "source": "native_script_hangul",
                "confidence": 1.0,
                "notes": "Hangul → Korea",
            }
        )

    # B1 - East Slavic (Cyrillic → B1)
    russian_names = [
        ("Иван Петров", "Ivan Petrov"),
        ("Дмитрий Иванов", "Dmitri Ivanov"),
        ("Ольга Соколова", "Olga Sokolova"),
        ("Андрей Волков", "Andrei Volkov"),
        ("Наталья Попова", "Natalia Popova"),
    ]
    for native, romanized in russian_names:
        truth.append(
            {
                "name": romanized,
                "native": native,
                "origin": "B1",
                "source": "native_script_cyrillic",
                "confidence": 1.0,
                "notes": "Cyrillic → East Slavic",
            }
        )

    # B3 - Greek (Greek script → B3)
    greek_names = [
        ("Γεώργιος Παπαδόπουλος", "Georgios Papadopoulos"),
        ("Μαρία Κωνσταντίνου", "Maria Konstantinou"),
        ("Δημήτριος Γεωργίου", "Dimitrios Georgiou"),
    ]
    for native, romanized in greek_names:
        truth.append(
            {
                "name": romanized,
                "native": native,
                "origin": "B3",
                "source": "native_script_greek",
                "confidence": 1.0,
                "notes": "Greek script → Greece",
            }
        )

    print(
        f"  Added {len([t for t in truth if t['confidence'] == 1.0])} native script examples"
    )

    # =================================================================
    # PHASE 2: Clear Latin-Script Patterns (85-95% confidence)
    # =================================================================
    print("Phase 2: Building clear Latin-script patterns...")

    # A2 - Italian (clear patterns)
    italian_names = [
        "Luigi Ferrucci",
        "Marco Rossi",
        "Giovanni Bellini",
        "Paolo Bianchi",
        "Andrea Ferrari",
        "Francesco Russo",
        "Antonio Romano",
        "Alessandro Gallo",
        "Matteo Conti",
        "Lorenzo De Luca",
        "Gabriele Ricci",
        "Davide Marino",
        "Simone Greco",
        "Federico Costa",
        "Riccardo Giordano",
        "Luca Mancini",
        "Stefano Lombardi",
        "Nicola Fontana",
        "Tommaso Caruso",
        "Michele Esposito",
    ]
    for name in italian_names:
        truth.append(
            {
                "name": name,
                "origin": "A2",
                "source": "italian_patronymic_pattern",
                "confidence": 0.95,
                "notes": "Clear Italian surname pattern",
            }
        )

    # A2 - German (clear patterns)
    german_names = [
        "Hans Mueller",
        "Wolfgang Schmidt",
        "Friedrich Wagner",
        "Klaus Fischer",
        "Dieter Weber",
        "Helmut Becker",
        "Jurgen Schulz",
        "Manfred Hoffmann",
        "Gunter Koch",
        "Rolf Bauer",
        "Karl Richter",
        "Otto Klein",
        "Franz Neumann",
        "Wilhelm Zimmermann",
        "Heinrich Kruger",
        "Gerhard Wolf",
    ]
    for name in german_names:
        truth.append(
            {
                "name": name,
                "origin": "A2",
                "source": "german_surname_pattern",
                "confidence": 0.95,
                "notes": "Clear German surname pattern",
            }
        )

    # A2 - French (clear patterns)
    french_names = [
        "Jean Dubois",
        "Pierre Leroy",
        "Marie Martin",
        "Jacques Bernard",
        "Michel Thomas",
        "Philippe Petit",
        "Alain Robert",
        "Francois Richard",
        "Bernard Durand",
        "Claude Moreau",
        "Andre Simon",
        "Henri Laurent",
        "Georges Lefebvre",
        "Robert Michel",
        "Louis Girard",
        "Marcel Bonnet",
    ]
    for name in french_names:
        truth.append(
            {
                "name": name,
                "origin": "A2",
                "source": "french_surname_pattern",
                "confidence": 0.95,
                "notes": "Clear French surname pattern",
            }
        )

    # A1 - Anglo (clear patterns)
    anglo_names = [
        "John Smith",
        "Michael Johnson",
        "David Williams",
        "Robert Brown",
        "James Jones",
        "William Davis",
        "Richard Miller",
        "Thomas Wilson",
        "Charles Moore",
        "Joseph Taylor",
        "Christopher Anderson",
        "Daniel Thomas",
        "Matthew Jackson",
        "Anthony White",
        "Mark Harris",
        "Donald Martin",
    ]
    for name in anglo_names:
        truth.append(
            {
                "name": name,
                "origin": "A1",
                "source": "anglo_surname_pattern",
                "confidence": 0.90,
                "notes": "Clear Anglo/English surname pattern",
            }
        )

    # D1 - Hindi Belt (clear patterns)
    hindi_names = [
        "Raj Kumar",
        "Priya Sharma",
        "Amit Patel",
        "Anita Singh",
        "Rahul Gupta",
        "Sunita Verma",
        "Vijay Reddy",
        "Kavita Rao",
        "Anil Kumar",
        "Neha Joshi",
        "Sanjay Mishra",
        "Rekha Nair",
    ]
    for name in hindi_names:
        truth.append(
            {
                "name": name,
                "origin": "D1",
                "source": "hindi_belt_surname_pattern",
                "confidence": 0.90,
                "notes": "Clear Hindi belt surname pattern",
            }
        )

    print(
        f"  Added {len([t for t in truth if 0.85 <= t['confidence'] < 1.0])} Latin-script pattern examples"
    )

    # =================================================================
    # PHASE 3: Ambiguous Cases with Tie-breaks
    # =================================================================
    print("Phase 3: Building ambiguous tie-break examples...")

    # Spanish: Spain (A2) vs Latin America (G1)
    spanish_spain_names = [
        ("Miguel García", "ES"),
        ("Juan Rodríguez", "ES"),
        ("María López", "ES"),
        ("José Martínez", "ES"),
        ("Antonio Fernández", "ES"),
        ("Manuel González", "ES"),
        ("Francisco Sánchez", "ES"),
        ("Pedro Pérez", "ES"),
        ("Javier Gómez", "ES"),
        ("Fernando Ruiz", "ES"),
    ]
    for name, country in spanish_spain_names:
        truth.append(
            {
                "name": name,
                "origin": "A2",
                "affiliation": country,
                "source": "spanish_spain_affiliation",
                "confidence": 0.90,
                "is_ambiguous": True,
                "ambiguity_family": ["A2", "G1"],
                "notes": "Spanish name, Spain affiliation → A2",
            }
        )

    spanish_latam_names = [
        ("Miguel Rodríguez", "MX"),
        ("Juan López", "AR"),
        ("María García", "CL"),
        ("José Hernández", "CO"),
        ("Carlos González", "MX"),
        ("Ana Martínez", "BR"),
        ("Luis Pérez", "PE"),
        ("Sofia Fernández", "VE"),
        ("Diego Sánchez", "EC"),
        ("Valeria Torres", "UY"),
    ]
    for name, country in spanish_latam_names:
        truth.append(
            {
                "name": name,
                "origin": "G1",
                "affiliation": country,
                "source": "spanish_latam_affiliation",
                "confidence": 0.90,
                "is_ambiguous": True,
                "ambiguity_family": ["A2", "G1"],
                "notes": "Spanish name, Latin America affiliation → G1",
            }
        )

    # Chinese: Mainland (E1) vs Taiwan/HK (E2)
    chinese_mainland_names = [
        ("Wang Wei", "CN"),
        ("Zhang Ming", "CN"),
        ("Li Na", "CN"),
        ("Liu Yang", "CN"),
        ("Chen Jing", "CN"),
    ]
    for name, country in chinese_mainland_names:
        truth.append(
            {
                "name": name,
                "origin": "E1",
                "affiliation": country,
                "source": "chinese_mainland_affiliation",
                "confidence": 0.85,
                "is_ambiguous": True,
                "ambiguity_family": ["E1", "E2"],
                "notes": "Chinese name, Mainland affiliation → E1",
            }
        )

    chinese_taiwan_names = [
        ("Lin Mei-ling", "TW"),
        ("Chen Chih-wei", "TW"),
        ("Wu Hsiao-fen", "HK"),
        ("Huang Ming-chuan", "TW"),
        ("Lee Shu-chen", "HK"),
    ]
    for name, country in chinese_taiwan_names:
        truth.append(
            {
                "name": name,
                "origin": "E2",
                "affiliation": country,
                "source": "chinese_taiwan_hk_affiliation",
                "confidence": 0.85,
                "is_ambiguous": True,
                "ambiguity_family": ["E1", "E2"],
                "notes": "Chinese name, Taiwan/HK affiliation → E2",
            }
        )

    print(
        f"  Added {len([t for t in truth if t.get('is_ambiguous')])} ambiguous tie-break examples"
    )

    # =================================================================
    # PHASE 4: Hybrid Cases
    # =================================================================
    print("Phase 4: Building hybrid name examples...")

    # Hybrid: Latin given + CJK surname
    hybrid_latin_cjk = [
        ("Robert Chen", "E1", "Chinese surname primary"),
        ("David Wang", "E1", "Chinese surname primary"),
        ("Michael Kim", "E4", "Korean surname primary"),
        ("Jennifer Lee", "E4", "Korean surname primary"),
        ("Daniel Zhang", "E1", "Chinese surname primary"),
        ("Michelle Park", "E4", "Korean surname primary"),
    ]
    for name, origin, notes in hybrid_latin_cjk:
        truth.append(
            {
                "name": name,
                "origin": origin,
                "source": "hybrid_surname_primary",
                "confidence": 0.85,
                "hybrid": "given_latin",
                "notes": notes,
            }
        )

    print(f"  Added {len([t for t in truth if t.get('hybrid')])} hybrid examples")

    # =================================================================
    # PHASE 5: Expert's Canonical Test Cases
    # =================================================================
    print("Phase 5: Adding expert's canonical test cases...")

    expert_cases = [
        {
            "name": "P. Griffiths",
            "origin": "A1",
            "source": "expert_canonical",
            "confidence": 0.95,
            "notes": "Expert test: ensure no false 'ri'→Korean match",
        },
        {
            "name": "S. T. Yau",
            "origin": "E1",
            "source": "expert_canonical",
            "confidence": 0.95,
            "notes": "Expert test: Chinese name with hyphenated given",
        },
    ]
    truth.extend(expert_cases)

    print(f"  Added {len(expert_cases)} expert canonical examples")

    return truth


def save_ground_truth(truth):
    """Save ground truth to JSONL format."""
    output_path = Path("data/ml_training/origin_truth.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in truth:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return output_path


def print_statistics(truth):
    """Print statistics about the ground truth dataset."""
    print(f"\n{'='*80}")
    print("GROUND TRUTH STATISTICS")
    print(f"{'='*80}\n")

    print(f"Total entries: {len(truth)}")
    print()

    # By origin
    from collections import Counter

    origins = Counter(t["origin"] for t in truth)
    print("By origin region:")
    for origin, count in origins.most_common():
        percentage = count / len(truth) * 100
        print(f"  {origin}: {count} ({percentage:.1f}%)")
    print()

    # By confidence
    confidence_ranges = {
        "1.0 (native script)": len([t for t in truth if t["confidence"] == 1.0]),
        "0.90-0.99": len([t for t in truth if 0.90 <= t["confidence"] < 1.0]),
        "0.85-0.89": len([t for t in truth if 0.85 <= t["confidence"] < 0.90]),
        "< 0.85": len([t for t in truth if t["confidence"] < 0.85]),
    }
    print("By confidence:")
    for range_name, count in confidence_ranges.items():
        percentage = count / len(truth) * 100
        print(f"  {range_name}: {count} ({percentage:.1f}%)")
    print()

    # Ambiguous cases
    ambiguous = len([t for t in truth if t.get("is_ambiguous")])
    print(f"Ambiguous (tie-break) cases: {ambiguous} ({ambiguous/len(truth)*100:.1f}%)")

    # Hybrid cases
    hybrid = len([t for t in truth if t.get("hybrid")])
    print(f"Hybrid cases: {hybrid} ({hybrid/len(truth)*100:.1f}%)")


def main():
    """Build and save name-origin ground truth."""
    print("=" * 80)
    print("BUILDING NAME-ORIGIN GROUND TRUTH")
    print("=" * 80)
    print()

    # Build
    truth = build_ground_truth()

    # Save
    print(f"\nSaving to JSONL...")
    output_path = save_ground_truth(truth)
    print(f"✅ Saved to: {output_path}")

    # Stats
    print_statistics(truth)

    print(f"\n{'='*80}")
    print("✅ GROUND TRUTH DATASET CREATED")
    print(f"{'='*80}\n")
    print("Next step: Validate Phase 2 model with:")
    print("  python3 scripts/ml/validate_on_name_origin.py\n")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
