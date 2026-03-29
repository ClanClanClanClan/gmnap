#!/usr/bin/env python3
"""
Name Normalization and Utilities

Based on expert guidance (Oct 30, 2025):
- NFC normalization for consistent Unicode handling
- Diacritics handling
- Surname extraction
- Unicode script detection
- Duplicate detection

Guarantees:
- Consistent name comparison across datasets
- Proper handling of accented characters
- Script-based feature extraction
"""

import unicodedata
import re
from typing import Tuple, Optional, Set


def normalize_nfc(text: str) -> str:
    """
    Normalize to NFC (Canonical Composition) form

    Ensures consistent Unicode representation:
    - "é" (single char) vs "é" (e + combining accent) → both become single char
    - Essential for duplicate detection and matching

    Args:
        text: Raw text

    Returns:
        NFC-normalized text
    """
    return unicodedata.normalize("NFC", text)


def remove_diacritics(text: str) -> str:
    """
    Remove diacritics from Latin-script text

    Converts: "José García" → "Jose Garcia"
    Preserves: Non-Latin scripts (Cyrillic, CJK, Arabic, etc.)

    Args:
        text: Input text

    Returns:
        Text with diacritics removed from Latin characters
    """
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize("NFD", text)

    # Keep only characters that are not combining marks
    result = "".join(
        char
        for char in nfd
        if unicodedata.category(char) != "Mn"  # Mn = Nonspacing_Mark
    )

    # Normalize back to NFC
    return unicodedata.normalize("NFC", result)


def extract_surname(full_name: str) -> str:
    """
    Extract surname from full name

    Heuristics:
    - Last word for Latin scripts
    - Handles prefixes: "de", "van", "von", "da", "dos", "del"
    - Returns full name for CJK (surname is typically first)

    Args:
        full_name: Full person name

    Returns:
        Extracted surname
    """
    name = full_name.strip()

    # Detect script
    script = detect_unicode_script(name)

    # CJK: surname is first character(s)
    if script in ["CJK", "Hangul", "Hiragana", "Katakana"]:
        # Return full name (proper extraction would need CJK knowledge)
        return name

    # Latin scripts: surname is last word(s)
    parts = name.split()
    if len(parts) == 0:
        return name

    # Handle surname prefixes
    prefixes = {"de", "van", "von", "da", "dos", "del", "della", "di", "du", "la", "le"}

    # Check if last 2-3 words form compound surname
    if len(parts) >= 2 and parts[-2].lower() in prefixes:
        return " ".join(parts[-2:])
    if len(parts) >= 3 and parts[-3].lower() in prefixes:
        return " ".join(parts[-3:])

    # Default: last word
    return parts[-1]


def detect_unicode_script(text: str) -> str:
    """
    Detect dominant Unicode script

    Returns one of:
    - 'Latin'
    - 'CJK' (Chinese, Japanese, Korean ideographs)
    - 'Hangul' (Korean alphabet)
    - 'Hiragana' / 'Katakana' (Japanese)
    - 'Cyrillic'
    - 'Greek'
    - 'Arabic'
    - 'Hebrew'
    - 'Devanagari' / 'Bengali' / 'Tamil' / etc. (Indic)
    - 'Unknown'

    Args:
        text: Input text

    Returns:
        Dominant script name
    """
    script_counts = {
        "Latin": 0,
        "CJK": 0,
        "Hangul": 0,
        "Hiragana": 0,
        "Katakana": 0,
        "Cyrillic": 0,
        "Greek": 0,
        "Arabic": 0,
        "Hebrew": 0,
        "Devanagari": 0,
        "Bengali": 0,
        "Tamil": 0,
        "Telugu": 0,
        "Unknown": 0,
    }

    for char in text:
        # Skip whitespace and punctuation
        if not char.strip() or unicodedata.category(char)[0] in ["P", "Z"]:
            continue

        try:
            name = unicodedata.name(char, "")

            if any(x in name for x in ["CJK", "IDEOGRAPH"]):
                script_counts["CJK"] += 1
            elif "HANGUL" in name:
                script_counts["Hangul"] += 1
            elif "HIRAGANA" in name:
                script_counts["Hiragana"] += 1
            elif "KATAKANA" in name:
                script_counts["Katakana"] += 1
            elif "CYRILLIC" in name:
                script_counts["Cyrillic"] += 1
            elif "GREEK" in name:
                script_counts["Greek"] += 1
            elif "ARABIC" in name:
                script_counts["Arabic"] += 1
            elif "HEBREW" in name:
                script_counts["Hebrew"] += 1
            elif "DEVANAGARI" in name:
                script_counts["Devanagari"] += 1
            elif "BENGALI" in name:
                script_counts["Bengali"] += 1
            elif "TAMIL" in name:
                script_counts["Tamil"] += 1
            elif "TELUGU" in name:
                script_counts["Telugu"] += 1
            elif "LATIN" in name:
                script_counts["Latin"] += 1
            else:
                script_counts["Unknown"] += 1
        except ValueError:
            script_counts["Unknown"] += 1

    # Return dominant script
    return max(script_counts.items(), key=lambda x: x[1])[0]


def normalize_name_for_comparison(name: str) -> str:
    """
    Normalize name for duplicate detection

    Applies:
    - NFC normalization
    - Lowercase
    - Remove extra whitespace
    - Remove diacritics (for Latin scripts only)

    Args:
        name: Input name

    Returns:
        Normalized name for comparison
    """
    # NFC normalization
    normalized = normalize_nfc(name)

    # Lowercase
    normalized = normalized.lower()

    # Remove diacritics (Latin scripts only)
    script = detect_unicode_script(normalized)
    if script == "Latin":
        normalized = remove_diacritics(normalized)

    # Collapse whitespace
    normalized = " ".join(normalized.split())

    return normalized


def find_duplicates(names: list[str]) -> dict[str, list[str]]:
    """
    Find duplicate names after normalization

    Args:
        names: List of names to check

    Returns:
        Dict mapping normalized name → list of original names
        Only includes entries with 2+ duplicates
    """
    normalized_map = {}

    for name in names:
        normalized = normalize_name_for_comparison(name)
        if normalized not in normalized_map:
            normalized_map[normalized] = []
        normalized_map[normalized].append(name)

    # Return only duplicates
    return {
        norm: originals
        for norm, originals in normalized_map.items()
        if len(originals) > 1
    }


def extract_surname_cluster(surname: str, min_length: int = 3) -> str:
    """
    Extract surname cluster for leakage-safe splitting

    Strategy:
    - Rare surnames (e.g., "Possamai") → full surname
    - Common surnames (e.g., "Smith", "García") → first N chars

    Args:
        surname: Extracted surname
        min_length: Minimum prefix length for common surnames

    Returns:
        Surname cluster identifier
    """
    normalized = normalize_name_for_comparison(surname)

    # Use full surname if short
    if len(normalized) <= min_length:
        return normalized

    # For longer surnames, use first N chars as cluster
    return normalized[:min_length]


if __name__ == "__main__":
    # Demo
    test_cases = [
        ("José García", "Latin"),
        ("Vladimir Putin", "Cyrillic"),
        ("张伟", "CJK"),
        ("김민준", "Hangul"),
        ("Αλέξανδρος Παπαδόπουλος", "Greek"),
        ("محمد علي", "Arabic"),
    ]

    print("=" * 70)
    print("NAME NORMALIZATION UTILITIES DEMO")
    print("=" * 70)

    print("\n1. Script Detection:")
    for name, expected in test_cases:
        detected = detect_unicode_script(name)
        status = "✅" if detected == expected else "❌"
        print(f"  {status} {name:30} → {detected:12} (expected: {expected})")

    print("\n2. Surname Extraction:")
    test_names = [
        "John Smith",
        "José García",
        "Marie de Montpellier",
        "Ludwig van Beethoven",
        "张伟",
    ]
    for name in test_names:
        surname = extract_surname(name)
        print(f"  {name:30} → {surname}")

    print("\n3. Normalization (NFC + diacritics):")
    test_normalization = [
        "José García",
        "François Müller",
        "Øyvind Sørensen",
    ]
    for name in test_normalization:
        normalized = normalize_name_for_comparison(name)
        no_diacritics = remove_diacritics(name)
        print(f"  {name:25} → {normalized:25} (no diacritics: {no_diacritics})")

    print("\n4. Duplicate Detection:")
    names_with_dups = [
        "José García",
        "Jose Garcia",  # Same after normalization
        "JOSE GARCIA",  # Same after normalization
        "John Smith",
        "Jane Doe",
    ]
    duplicates = find_duplicates(names_with_dups)
    if duplicates:
        for norm, originals in duplicates.items():
            print(f"  Duplicate group (normalized: {norm}):")
            for orig in originals:
                print(f"    - {orig}")
    else:
        print("  No duplicates found")

    print("\n" + "=" * 70)
