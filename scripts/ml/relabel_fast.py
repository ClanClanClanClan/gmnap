#!/usr/bin/env python3
"""
Fast Etymology Relabeling using Pattern Matching

Uses script detection + surname patterns only (no ML)
Expected: 5-10 seconds for 10K profiles

Based on expert's Track A guidance (Oct 30, 2025)
"""

import json
import sys
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Regional surname patterns (from GMNAP's existing system)
SURNAME_PATTERNS = {
    # E4 - Korean
    "E4": [
        r"^(Kim|Park|Lee|Choi|Jung|Kang|Cho|Yoon|Jang|Lim|Han|Oh|Seo|Shin|Kwon|Song|Hong|Ahn|Jeon|Moon|Yang|Jo|Hwang|Yoo|Baek|Im|Noh|Seok|Kwak|Sim|Ha|Nam|Min|Cha|Koo|Ji|Bae|Chung|Won|Cheon|Tak|Pyo|Joo|Do|Goo|Son)\b",
    ],
    # E3 - Japanese
    "E3": [
        r"(moto|kawa|yama|hara|sawa|zaki|mura|shima|uchi|da)$",
        r"^(Tanaka|Sato|Suzuki|Takahashi|Watanabe|Ito|Yamamoto|Nakamura|Kobayashi|Kato|Yoshida|Yamada|Sasaki|Yamaguchi|Saito|Matsumoto|Inoue|Kimura|Hayashi|Shimizu)\b",
    ],
    # A2 - Italian
    "A2_italian": [
        r"(ini|elli|etti|ucci|azzo|azzo|otto|aldi|ardi|elli|oli|ori|zzi)$",
    ],
    # A2 - German
    "A2_german": [
        r"(mann|stein|berg|feld|haus|schmidt|mueller|weber|wagner|becker|schulz|hoffmann|koch|bauer|klein|wolf|neumann|zimmermann)$",
    ],
    # A2 - French
    "A2_french": [
        r"^(de|du|le|la) ",
        r"(ard|ier|ière|eau|ais|ois|ain|on|et|ot)$",
    ],
    # A2 - Dutch
    "A2_dutch": [
        r"^(van|de|den|der|ten|ter) ",
    ],
    # G1 - Spanish/Portuguese Latin America
    "G1": [
        r"(ez|es|az|iz|oz)$",
        r"^(da |dos |de )",  # Portuguese particles
        r"(Silva|Santos|Oliveira|Souza|Lima|Costa|Ferreira|Rodrigues|Alves|Pereira|Ribeiro|Carvalho|Araújo|Almeida|Martins|Rocha|Garcia|Fernandes|Dias|Castro)$",
    ],
    # A3 - Nordic
    "A3": [
        r"(sen|sson|son|dottir|qvist|ström|berg|lund|gren)$",
    ],
    # B1 - East Slavic (Russian/Ukrainian)
    "B1": [
        r"(ov|ova|ev|eva|sky|skaya|uk|yuk)$",
    ],
    # B2 - South Slavic
    "B2": [
        r"(ić|ic|ovic|evic|ski|ska)$",
    ],
    # A1 - Anglo/English
    "A1": [
        r"(ton|ham|ley|ford|wood|field|worth|bury|by|shaw)$",
    ],
}


def detect_script(name: str) -> str:
    """Detect dominant script in name"""
    for char in name:
        if not char.strip():
            continue

        script_name = unicodedata.name(char, "").split()[0]

        if "HANGUL" in script_name:
            return "E4"  # Korean
        elif "HIRAGANA" in script_name or "KATAKANA" in script_name:
            return "E3"  # Japanese
        elif "CJK" in script_name:
            return "E1"  # Chinese
        elif "CYRILLIC" in script_name:
            return "B1"  # East Slavic
        elif "GREEK" in script_name:
            return "B3"  # Greek
        elif "ARABIC" in script_name:
            return "C3"  # Arabic
        elif "DEVANAGARI" in script_name:
            return "D1"  # Hindi Belt
        elif "BENGALI" in script_name:
            return "D3"  # Bengali
        elif "TAMIL" in script_name or "TELUGU" in script_name:
            return "D2"  # Dravidian

    return None  # Latin script, need pattern matching


def detect_by_patterns(name: str) -> str:
    """Detect region by surname patterns"""
    name_lower = name.lower()
    parts = name.split()

    if len(parts) < 2:
        return None

    surname = parts[-1]
    surname_lower = surname.lower()

    # Check each pattern set
    for region, patterns in SURNAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, surname_lower, re.IGNORECASE):
                # Handle A2 sub-patterns
                if region.startswith("A2_"):
                    return "A2"
                return region

    return None


def detect_etymology_fast(name: str) -> str:
    """Fast etymology detection using script + patterns"""

    # 1. Script detection (strongest signal)
    script_region = detect_script(name)
    if script_region:
        return script_region

    # 2. Pattern matching for Latin scripts
    pattern_region = detect_by_patterns(name)
    if pattern_region:
        return pattern_region

    # 3. Default to A1 (Anglo) for unmatched Latin names
    return "A1"


def relabel_dataset_fast(input_path: Path, output_path: Path, dry_run: bool = False):
    """Fast relabeling using patterns only"""

    print("=" * 80)
    print("FAST ETYMOLOGY RELABELING (Pattern-Based)")
    print("=" * 80)

    # Load
    print(f"\n[1/4] Loading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", data if isinstance(data, list) else [])
    print(f"  Loaded {len(profiles):,} profiles")

    # Relabel
    print("\n[2/4] Relabeling...")
    changes = 0
    unchanged = 0
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
        profile["original_affiliation_region"] = old_region

        # Relabel
        if new_region != old_region:
            profile["region"] = new_region
            changes += 1

            key = f"{old_region}→{new_region}"
            relabel_stats[key] = relabel_stats.get(key, 0) + 1
        else:
            unchanged += 1

    print(f"\n  Changed: {changes:,} ({changes / len(profiles) * 100:.1f}%)")
    print(f"  Unchanged: {unchanged:,} ({unchanged / len(profiles) * 100:.1f}%)")

    # Stats
    print("\n[3/4] Top relabelings:")
    for key, count in sorted(relabel_stats.items(), key=lambda x: x[1], reverse=True)[
        :15
    ]:
        print(f"    {key:10s} {count:5,} changes")

    # Save
    if dry_run:
        print("\n[4/4] DRY RUN - Not saving")
    else:
        print(f"\n[4/4] Saving to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "metadata": {
                "total": len(profiles),
                "relabeling": {
                    "method": "pattern_based_etymology",
                    "changes": changes,
                    "pct_changed": changes / len(profiles) * 100,
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
        print("Usage: python relabel_fast.py <input.json> <output.json> [--dry-run]")
        sys.exit(1)

    relabel_dataset_fast(Path(sys.argv[1]), Path(sys.argv[2]), "--dry-run" in sys.argv)
