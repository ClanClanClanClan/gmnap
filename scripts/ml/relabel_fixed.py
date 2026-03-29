#!/usr/bin/env python3
"""
FIXED Etymology Relabeling - No Dangerous Defaults

Key fixes:
1. NO default to A1 - return None for uncertain cases
2. Expanded surname patterns for better coverage
3. Validation checks for suspicious relabeling rates
4. Conservative approach: only relabel when confident

Usage:
    python3 relabel_fixed.py <input.json> <output.json>
"""

import json
import sys
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter


# EXPANDED Regional surname patterns
SURNAME_PATTERNS = {
    # E4 - Korean (comprehensive)
    "E4": [
        r"^(Kim|Park|Lee|Choi|Jung|Kang|Cho|Yoon|Jang|Lim|Han|Oh|Seo|Shin|Kwon|Song|Hong|Ahn|Jeon|Moon|Yang|Jo|Hwang|Yoo|Baek|Im|Noh|Seok|Kwak|Sim|Ha|Nam|Min|Cha|Koo|Ji|Bae|Chung|Won|Cheon|Tak|Pyo|Joo|Do|Goo|Son)\b",
        r"^(Rhee|Ryu|Seo|Seok|Shim|Sohn|Sung|Uhm|Woo|Yi|Yun)\b",
    ],
    # E3 - Japanese (comprehensive)
    "E3": [
        r"(moto|kawa|yama|hara|sawa|zaki|mura|shima|uchi|da|hashi|bayashi|mura|naka)$",
        r"^(Tanaka|Sato|Suzuki|Takahashi|Watanabe|Ito|Yamamoto|Nakamura|Kobayashi|Kato|Yoshida|Yamada|Sasaki|Yamaguchi|Saito|Matsumoto|Inoue|Kimura|Hayashi|Shimizu|Ikeda|Endo|Fujita|Okada|Goto|Hasegawa|Ishikawa|Murakami|Nakajima|Sakamoto|Ogawa|Fukuda|Nishimura|Morita|Takeuchi)\b",
    ],
    # E1 - Chinese (common surnames)
    "E1": [
        r"^(Wang|Li|Zhang|Liu|Chen|Yang|Huang|Zhao|Wu|Zhou|Xu|Sun|Ma|Zhu|Hu|Guo|He|Gao|Lin|Luo|Zheng|Liang|Song|Tang|Xu|Han|Feng|Dong|Cao|Cheng|Wei|Jiang|Pan|Yuan|Cai|Yu|Du|Ye|Su|Lu|Ding|Ren|Shi|Xie|Deng|Xiao|Fu|Shen|Qian|Bai|Kong|Tian|Xia|Wan|Gu|Dai|Jin|Meng|Qin|Cui|Tan|Qiu)\b",
    ],
    # A2 - Italian
    "A2_italian": [
        r"(ini|elli|etti|ucci|azzi|otto|aldi|ardi|oli|ori|zzi|one|ano|ino)$",
        r"^(Rossi|Russo|Ferrari|Esposito|Bianchi|Romano|Colombo|Ricci|Marino|Greco|Bruno|Gallo|Conti|De Luca|Mancini|Costa|Giordano|Rizzo|Lombardi|Moretti)\b",
    ],
    # A2 - German
    "A2_german": [
        r"(mann|stein|berg|feld|haus|schmidt|mueller|weber|wagner|becker|schulz|hoffmann|koch|bauer|klein|wolf|neumann|zimmermann|krueger|schroeder)$",
        r"^(Müller|Schmidt|Schneider|Fischer|Weber|Meyer|Wagner|Becker|Schulz|Hoffmann|Schäfer|Koch|Bauer|Richter|Klein|Wolf|Schröder|Neumann|Schwarz|Zimmermann|Braun|Krüger|Hofmann|Hartmann|Lange|Schmitt|Werner|Schmid|Krause|Meier|Lehmann|Schmitz|Schulze)\b",
    ],
    # A2 - French
    "A2_french": [
        r"^(de |du |le |la |des |d\')",
        r"(ard|ier|ière|eau|ais|ois|ain|on|et|ot|aux|oux)$",
        r"^(Martin|Bernard|Thomas|Petit|Robert|Richard|Durand|Dubois|Moreau|Laurent|Simon|Michel|Lefebvre|Leroy|Roux|David|Bertrand|Morel|Fournier|Girard|Bonnet|Dupont|Lambert|Fontaine|Rousseau|Vincent|Muller|Lefevre|Faure|Andre|Mercier|Blanc|Guerin|Boyer|Garnier|Chevalier|Francois|Legrand|Gauthier|Garcia|Perrin|Robin|Clement|Morin|Nicolas|Henry|Roussel|Mathieu|Gautier|Masson|Marchand|Duval|Denis|Dumont|Marie|Lemaire|Noel|Meyer|Dufour|Meunier)\b",
    ],
    # A2 - Dutch
    "A2_dutch": [
        r"^(van |de |den |der |ten |ter |vande |vanden |van de |van den )",
        r"^(de Vries|de Jong|Jansen|Bakker|Visser|Smit|Meijer|de Boer|Mulder|de Groot|Bos|Vos|Peters|Hendriks|van Dijk|Dekker|Brouwer|de Wit|Dijkstra|Smits|de Vos|Jacobs|van den Berg|van Leeuwen|Kok|Janssen|Maarten)\b",
    ],
    # A2 - Spanish (Iberian)
    "A2_spanish": [
        r"^(García|González|Rodríguez|Fernández|López|Martínez|Sánchez|Pérez|Gómez|Martín|Jiménez|Ruiz|Hernández|Díaz|Moreno|Álvarez|Muñoz|Romero|Alonso|Gutiérrez|Navarro|Torres|Domínguez|Vázquez|Ramos|Gil|Ramírez|Serrano|Blanco|Suárez|Molina|Morales|Ortega|Delgado|Castro|Ortiz|Rubio|Marín|Sanz|Núñez|Iglesias|Medina|Garrido|Santos|Castillo|Cortés|Lozano|Guerrero|Cano|Prieto|Méndez|Cruz|Flores|Herrera|Aguilar|Pascual|Santana|Vidal|León|Herrero|Carmona|Vicente|Arias|Crespo|Román|Ibáñez|Vargas|Reyes|Mora|Cabrera|Gallego|Calvo|Rojas|Parra|Soto|Carrasco|Fuentes|Vega|Campos|Caballero|Nieto|Reyes|Pastor|Santiago|Márquez|Montero)\b",
    ],
    # G1 - Latin America (Portuguese + Spanish Latin)
    "G1": [
        r"^(da |dos |de |das )",  # Portuguese particles
        r"(Silva|Santos|Oliveira|Souza|Lima|Costa|Ferreira|Rodrigues|Alves|Pereira|Ribeiro|Carvalho|Araújo|Almeida|Martins|Rocha|Fernandes|Dias|Castro|Gomes|Barbosa|Cardoso|Correia|Teixeira|Monteiro|Mendes|Nunes|Soares|Lopes|Freitas|Ramos|Moreira|Pinto|Cunha|Cavalcanti|Melo|Azevedo|Campos|Barros|Moura|Pires|Farias|Macedo|Fonseca)$",
    ],
    # A3 - Nordic
    "A3": [
        r"(sen|sson|son|dottir|dóttir|qvist|ström|berg|lund|gren)$",
        r"^(Johansson|Andersson|Karlsson|Nilsson|Eriksson|Larsson|Olsson|Persson|Svensson|Gustafsson|Pettersson|Jonsson|Jansson|Hansson|Bengtsson|Jørgensen|Møller|Nielsen|Hansen|Andersen|Pedersen|Christensen|Jensen|Sørensen|Rasmussen|Virtanen|Korhonen|Nieminen|Mäkinen|Hämäläinen|Laine|Heikkinen|Koskinen|Järvinen)\b",
    ],
    # B1 - East Slavic (Russian/Ukrainian/Belarusian)
    "B1": [
        r"(ov|ova|ev|eva|sky|skaya|skiy|skij|uk|yuk|enko|chuk|chenko)$",
        r"^(Ivanov|Smirnov|Kuznetsov|Popov|Vasilyev|Petrov|Sokolov|Mikhailov|Novikov|Fedorov|Morozov|Volkov|Alekseev|Lebedev|Semenov|Egorov|Pavlov|Kozlov|Stepanov|Nikolaev|Orlov|Andreev|Makarov|Nikitin|Zakharov|Kovalev|Ilyin|Gusev|Titov|Kuzmin|Kudryavshev|Baranov|Tarasov|Belov|Komarov|Solovyev|Antonov|Tikhonov|Markov|Gerasimov)\b",
    ],
    # B2 - South/Central Slavic (Polish/Czech/Slovak/Croatian/Serbian)
    "B2": [
        r"(ski|ska|wicz|owski|owska|ewski|ewska|ak|ek|ík|ová|ić|ovic|evic)$",
        r"^(Nowak|Kowalski|Wiśniewski|Wójcik|Kowalczyk|Kamiński|Lewandowski|Zieliński|Szymański|Woźniak|Dąbrowski|Kozłowski|Jankowski|Mazur|Wojciechowski|Kwiatkowski|Krawczyk|Piotrowski|Grabowski|Pawłowski|Michalski|Król|Nowakowski|Wieczorek|Majewski|Olszewski|Jabłoński|Malinowski|Adamczyk|Dudek|Stępień|Pavlović|Horvat|Novak|Kovačević|Marić|Jurić|Šimić|Babić|Matić)\b",
    ],
    # B3 - Greek
    "B3": [
        r"(opoulos|opoulou|akis|idis|ides|ou)$",
        r"^(Papadopoulos|Papadopoulou|Georgiou|Dimitriou|Nikolaou|Ioannou|Christodoulou|Andreou|Constantinou|Petrou|Athanasiou|Michail|Savva|Charalambous)\b",
    ],
    # C1 - Turkic
    "C1": [
        r"(oğlu|oglu|ov|ova)$",
        r"^(Yıldız|Kaya|Demir|Şahin|Çelik|Yılmaz|Öztürk|Aydın|Özdemir|Arslan|Doğan|Kılıç|Aslan|Çetin|Kara|Koç|Kurt|Özkan|Şimşek|Polat|Erdoğan|Yavuz|Güneş|Demirtaş|Bulut|Acar|Aktaş|Yalçın|Bayram|Duman|Akın|Güler|Özcan|Karabulut|Bozkurt|Aksoy|Türk|Tekin|Yıldırım)\b",
    ],
    # C2 - Persian/Iranian
    "C2": [
        r"(pour|zadeh|ian|i)$",
        r"^(Hosseini|Ahmadi|Mohammadi|Rahimi|Rezaei|Moradi|Karimi|Kazemi|Sadeghi|Akbari|Alavi|Mousavi|Rostami|Hashemi|Bagheri|Rahmani|Azizi|Ghorbani|Abbasi|Naderi|Soleimani|Mahmoudi|Jamshidi|Alizadeh|Asadi|Farahani|Ebrahimi|Fallah|Sharifi|Zamani)\b",
    ],
    # A1 - Anglo/English (ONLY clear Anglo patterns, NOT as default!)
    "A1": [
        r"(ton|ham|ley|ford|wood|field|worth|bury|by|shaw|ston|don|son)$",
        r"^(Smith|Johnson|Williams|Brown|Jones|Garcia|Miller|Davis|Rodriguez|Martinez|Hernandez|Lopez|Gonzalez|Wilson|Anderson|Thomas|Taylor|Moore|Jackson|Martin|Lee|Thompson|White|Harris|Sanchez|Clark|Ramirez|Lewis|Robinson|Walker|Young|Allen|King|Wright|Scott|Torres|Nguyen|Hill|Flores|Green|Adams|Nelson|Baker|Hall|Rivera|Campbell|Mitchell|Carter|Roberts)\b",
    ],
}


def detect_script(name: str) -> Optional[str]:
    """Detect dominant script in name"""
    for char in name:
        if not char.strip():
            continue

        script_name = unicodedata.name(char, "").split()[0] if char.strip() else ""

        if "HANGUL" in script_name:
            return "E4"  # Korean
        elif "HIRAGANA" in script_name or "KATAKANA" in script_name:
            return "E3"  # Japanese
        elif "CJK" in script_name:
            return "E1"  # Chinese
        elif "CYRILLIC" in script_name:
            return "B1"  # East Slavic (default for Cyrillic)
        elif "GREEK" in script_name:
            return "B3"  # Greek
        elif "ARABIC" in script_name:
            return "C3"  # Arabic (generic)
        elif "DEVANAGARI" in script_name:
            return "D1"  # Hindi Belt
        elif "BENGALI" in script_name:
            return "D3"  # Bengali
        elif "TAMIL" in script_name or "TELUGU" in script_name:
            return "D2"  # Dravidian

    return None  # Latin script, need pattern matching


def detect_by_patterns(name: str) -> Optional[str]:
    """Detect region by surname patterns"""
    name_lower = name.lower()
    parts = name.split()

    if len(parts) < 2:
        return None

    surname = parts[-1]
    surname_lower = surname.lower()

    # Track all matches with priority
    matches = []

    # Check each pattern set
    for region, patterns in SURNAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, surname_lower, re.IGNORECASE):
                # Handle A2 sub-patterns
                if region.startswith("A2_"):
                    matches.append("A2")
                else:
                    matches.append(region)
                break  # Only count first match per region

    # If multiple matches, return most specific
    # Prefer non-A1 matches to avoid false A1 assignments
    if matches:
        # Remove duplicates while preserving order
        unique_matches = list(dict.fromkeys(matches))

        # If A1 is only match, return it
        if len(unique_matches) == 1:
            return unique_matches[0]

        # If multiple matches, prefer non-A1
        non_a1 = [m for m in unique_matches if m != "A1"]
        if non_a1:
            return non_a1[0]

        return unique_matches[0]

    return None


def detect_etymology_fast(name: str) -> Optional[str]:
    """
    Fast etymology detection using script + patterns

    CRITICAL FIX: Returns None (not A1!) for uncertain cases
    """

    # 1. Script detection (strongest signal)
    script_region = detect_script(name)
    if script_region:
        return script_region

    # 2. Pattern matching for Latin scripts
    pattern_region = detect_by_patterns(name)
    if pattern_region:
        return pattern_region

    # 3. CRITICAL FIX: Return None for uncertain cases
    # Do NOT default to A1 - keep original affiliation-based label
    return None


def validate_relabeling_quality(
    profiles: List[Dict], relabel_stats: Dict[str, int]
) -> Tuple[bool, List[str]]:
    """
    Validate relabeling quality with safety checks

    Returns: (is_valid, list of warnings)
    """
    warnings = []

    # Check 1: Total relabeling rate
    total = len(profiles)
    changes = sum(relabel_stats.values())
    change_rate = changes / total * 100 if total > 0 else 0

    if change_rate > 40:
        warnings.append(f"⚠️  HIGH relabeling rate: {change_rate:.1f}% (>40% threshold)")

    # Check 2: A1 dominance
    a1_changes = sum(count for key, count in relabel_stats.items() if "→A1" in key)
    if a1_changes > changes * 0.4:  # More than 40% of changes to A1
        warnings.append(
            f"⚠️  SUSPICIOUS: {a1_changes} changes to A1 ({a1_changes/changes*100:.1f}% of all changes)"
        )

    # Check 3: Specific suspicious patterns
    suspicious_patterns = [
        ("E1→A1", "Chinese to Anglo"),
        ("E3→A1", "Japanese to Anglo"),
        ("G1→A1", "Latin America to Anglo"),
        ("C→A1", "Middle East to Anglo"),
    ]

    for pattern, description in suspicious_patterns:
        matching = sum(count for key, count in relabel_stats.items() if pattern in key)
        if matching > 10:
            warnings.append(f"⚠️  SUSPICIOUS: {matching} {description} relabelings")

    # Valid if no critical warnings
    is_valid = len(warnings) == 0

    return is_valid, warnings


def relabel_dataset_fast(input_path: Path, output_path: Path, dry_run: bool = False):
    """Fast relabeling using patterns only - FIXED VERSION"""

    print("=" * 80)
    print("FIXED ETYMOLOGY RELABELING (Pattern-Based)")
    print("=" * 80)

    # Load
    print(f"\n[1/5] Loading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", data if isinstance(data, list) else [])
    print(f"  Loaded {len(profiles):,} profiles")

    # Relabel
    print("\n[2/5] Relabeling...")
    changes = 0
    unchanged = 0
    uncertain = 0
    relabel_stats = {}

    for i, profile in enumerate(profiles):
        if (i + 1) % 1000 == 0:
            print(f"  Progress: {i + 1:,}/{len(profiles):,}")

        name = profile.get("name")
        old_region = profile.get("region")

        if not name or not old_region:
            continue

        # Detect etymology
        new_region = detect_etymology_fast(name)

        # Store original
        if "original_affiliation_region" not in profile:
            profile["original_affiliation_region"] = old_region

        # CRITICAL FIX: Only relabel if we have confidence
        if new_region and new_region != old_region:
            profile["region"] = new_region
            changes += 1

            key = f"{old_region}→{new_region}"
            relabel_stats[key] = relabel_stats.get(key, 0) + 1
        elif new_region is None:
            # Uncertain - keep original
            uncertain += 1
            unchanged += 1
        else:
            # Confident match that agrees with original
            unchanged += 1

    print(f"\n  Changed: {changes:,} ({changes / len(profiles) * 100:.1f}%)")
    print(f"  Unchanged: {unchanged:,} ({unchanged / len(profiles) * 100:.1f}%)")
    print(f"  Uncertain (kept original): {uncertain:,} ({uncertain / len(profiles) * 100:.1f}%)")

    # Stats
    print("\n[3/5] Top relabelings:")
    for key, count in sorted(relabel_stats.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"    {key:10s} {count:5,} changes")

    # VALIDATION
    print("\n[4/5] Validating quality...")
    is_valid, warnings = validate_relabeling_quality(profiles, relabel_stats)

    if warnings:
        print(f"\n  ⚠️  Validation warnings:")
        for warning in warnings:
            print(f"    {warning}")

    if not is_valid:
        print(f"\n  ❌ VALIDATION FAILED - Review warnings before proceeding")
        if not dry_run:
            response = input("\n  Continue anyway? (yes/no): ")
            if response.lower() != "yes":
                print("  Aborted.")
                return
    else:
        print(f"  ✅ Validation passed")

    # Save
    if dry_run:
        print("\n[5/5] DRY RUN - Not saving")
    else:
        print(f"\n[5/5] Saving to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "metadata": {
                "total": len(profiles),
                "relabeling": {
                    "method": "pattern_based_etymology_fixed",
                    "changes": changes,
                    "uncertain": uncertain,
                    "pct_changed": changes / len(profiles) * 100,
                    "pct_uncertain": uncertain / len(profiles) * 100,
                    "validation_passed": is_valid,
                },
            },
            "profiles": profiles,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Saved {len(profiles):,} profiles")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python relabel_fixed.py <input.json> <output.json> [--dry-run]")
        sys.exit(1)

    relabel_dataset_fast(Path(sys.argv[1]), Path(sys.argv[2]), "--dry-run" in sys.argv)
