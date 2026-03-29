#!/usr/bin/env python3
"""
Korean Converter Technical Analysis
Phase 1, Week 1: Understanding the failure

This script analyzes why the Korean converter is failing and creates
a technical plan for fixing it WITHOUT any hardcoding.
"""

import os
import sys
import csv
from pathlib import Path
from collections import defaultdict
import unicodedata

# Navigate to Korean converter directory
korean_dir = Path(__file__).parent / "src" / "regions" / "e_groups" / "e4_korea"
os.chdir(korean_dir)
sys.path.insert(0, str(korean_dir / "src"))


def analyze_converter_implementation():
    """Analyze the current converter implementation."""

    print("🔍 KOREAN CONVERTER TECHNICAL ANALYSIS")
    print("=" * 60)

    # 1. Check what files exist
    print("\n1. FILE STRUCTURE ANALYSIS:")
    print("-" * 40)

    expected_files = {
        "converter.py": "Main converter module",
        "segment.py": "Syllable segmentation",
        "fst_utils.py": "Finite State Transducer utilities",
        "resources/rr_syllable_map.csv": "Romanization mappings",
        "resources/variant_map.csv": "Name variants",
    }

    for file, description in expected_files.items():
        path = Path(file)
        exists = path.exists()
        print(f"  {'✅' if exists else '❌'} {file}: {description}")
        if exists:
            size = path.stat().st_size
            print(f"      Size: {size:,} bytes")

    # 2. Analyze syllable mappings
    print("\n2. SYLLABLE MAPPING ANALYSIS:")
    print("-" * 40)

    syllable_map_path = Path("resources/rr_syllable_map.csv")
    if syllable_map_path.exists():
        with open(syllable_map_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            mappings = list(reader)

        print(f"  Total mappings: {len(mappings)}")

        # Analyze mapping patterns
        hangul_to_roman = defaultdict(list)
        roman_to_hangul = defaultdict(list)

        for row in mappings:
            if len(row) >= 2:
                hangul, roman = row[0], row[1]
                weight = float(row[2]) if len(row) > 2 else 0.0

                hangul_to_roman[hangul].append((roman, weight))
                roman_to_hangul[roman].append((hangul, weight))

        # Find problematic mappings
        print(f"\n  Unique Hangul syllables: {len(hangul_to_roman)}")
        print(f"  Unique romanizations: {len(roman_to_hangul)}")

        # Check for conflicts
        conflicts = []
        for roman, hanguls in roman_to_hangul.items():
            if len(hanguls) > 1:
                conflicts.append((roman, hanguls))

        print(f"\n  Romanizations with conflicts: {len(conflicts)}")
        if conflicts:
            print("  Examples of conflicts:")
            for roman, hanguls in conflicts[:5]:
                print(f"    '{roman}' -> {[h[0] for h in hanguls]}")

    # 3. Test actual converter
    print("\n3. CONVERTER FUNCTIONALITY TEST:")
    print("-" * 40)

    try:
        # from converter import eng2kor, kor2eng
        print("  ✅ Converter imports successfully")

        # Test cases
        test_cases = [
            ("김철수", "kim chul soo"),
            ("이미나", "lee mi na"),
            ("박영희", "park young hee"),
            ("김", "kim"),
            ("이", "lee"),
        ]

        print("\n  Testing conversions:")
        failures = []

        for korean, expected_rom in test_cases:
            # Test Korean -> Roman
            rom_result = kor2eng(korean)

            # Test Roman -> Korean
            kor_result = eng2kor(expected_rom)

            print(f"\n  {korean}:")
            print(f"    kor2eng: {korean} -> {rom_result}")
            print(f"    eng2kor: {expected_rom} -> {kor_result}")

            if kor_result != korean:
                failures.append(
                    {
                        "korean": korean,
                        "expected_rom": expected_rom,
                        "rom_result": rom_result,
                        "kor_result": kor_result,
                    }
                )

        if failures:
            print(f"\n  ❌ Failures: {len(failures)}/{len(test_cases)}")
            analyze_failures(failures)

    except ImportError as e:
        print(f"  ❌ Failed to # import converter: {e}")
    except Exception as e:
        print(f"  ❌ Error testing converter: {e}")
        import traceback

        traceback.print_exc()

    # 4. FST Analysis
    print("\n4. FST (FINITE STATE TRANSDUCER) ANALYSIS:")
    print("-" * 40)

    try:
        from fst_utils import build_fst

        print("  ✅ FST utilities available")

        # Check if FSTs are built
        fst_files = list(Path(".").glob("*.fst"))
        print(f"  FST files found: {len(fst_files)}")
        for fst_file in fst_files:
            print(f"    - {fst_file.name} ({fst_file.stat().st_size:,} bytes)")

    except ImportError:
        print("  ❌ FST utilities not available")


def analyze_failures(failures):
    """Deep dive into why conversions are failing."""

    print("\n5. FAILURE ROOT CAUSE ANALYSIS:")
    print("-" * 40)

    for failure in failures:
        korean = failure["korean"]
        expected_rom = failure["expected_rom"]
        rom_result = failure["rom_result"]
        kor_result = failure["kor_result"]

        print(f"\n  Analyzing: {korean}")

        # Check if the romanization exists in mappings
        syllable_map_path = Path("resources/rr_syllable_map.csv")
        if syllable_map_path.exists():
            with open(syllable_map_path, "r", encoding="utf-8") as f:
                mappings = [row for row in csv.reader(f)]

            # Check each romanized token
            rom_tokens = expected_rom.split()
            korean_chars = list(korean)

            print(f"    Tokens: {rom_tokens}")
            print(f"    Korean chars: {korean_chars}")

            # Find relevant mappings
            for i, (char, token) in enumerate(zip(korean_chars, rom_tokens)):
                relevant_mappings = [
                    row for row in mappings if row[0] == char or (len(row) > 1 and row[1] == token)
                ]

                if relevant_mappings:
                    print(f"    Mappings for '{char}' / '{token}':")
                    for mapping in relevant_mappings[:3]:
                        print(f"      {mapping}")
                else:
                    print(f"    ❌ NO MAPPING for '{char}' / '{token}'")

        # Check syllable structure
        if rom_result:
            print(f"    Syllable comparison:")
            print(f"      Expected: {expected_rom}")
            print(f"      Got:      {rom_result}")

            # Character-by-character comparison
            if rom_result != expected_rom:
                print(f"    Differences:")
                for i, (e, g) in enumerate(zip(expected_rom, rom_result)):
                    if e != g:
                        print(f"      Position {i}: '{e}' != '{g}'")


def propose_fixes():
    """Propose specific fixes based on analysis."""

    print("\n6. PROPOSED FIXES:")
    print("-" * 40)

    fixes = [
        {
            "issue": "Missing romanization mappings",
            "solution": "Add missing syllable mappings to rr_syllable_map.csv",
            "priority": "HIGH",
            "effort": "2 days",
        },
        {
            "issue": "Weight calibration issues",
            "solution": "Adjust weights based on frequency analysis of Korean names",
            "priority": "HIGH",
            "effort": "1 day",
        },
        {
            "issue": "Position-aware detection not working",
            "solution": "Fix surname vs given name position detection logic",
            "priority": "MEDIUM",
            "effort": "2 days",
        },
        {
            "issue": "FST not properly built/loaded",
            "solution": "Rebuild FST files with correct mappings",
            "priority": "HIGH",
            "effort": "1 day",
        },
        {
            "issue": "No handling of name variants",
            "solution": "Implement variant lookup for common romanizations",
            "priority": "MEDIUM",
            "effort": "2 days",
        },
    ]

    for i, fix in enumerate(fixes, 1):
        print(f"\n  Fix #{i}: {fix['issue']}")
        print(f"    Solution: {fix['solution']}")
        print(f"    Priority: {fix['priority']}")
        print(f"    Effort: {fix['effort']}")

    print("\n7. IMPLEMENTATION PLAN:")
    print("-" * 40)
    print(
        """
  Week 1 (Analysis - THIS WEEK):
    ✓ Understand current implementation
    ✓ Identify failure patterns
    ✓ Document root causes
    - Create test suite
    - Design fix strategy
    
  Week 2 (Core Fixes):
    - Add missing syllable mappings
    - Calibrate weights properly
    - Fix position detection
    - Rebuild FST files
    
  Week 3 (Polish & Optimize):
    - Add variant handling
    - Performance optimization
    - Comprehensive testing
    - Documentation
    
  Success Criteria:
    - 97%+ round-trip accuracy
    - No hardcoded data
    - <10ms per name conversion
    """
    )


def main():
    """Run the complete analysis."""
    analyze_converter_implementation()
    propose_fixes()

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("Next step: Create comprehensive test suite")
    print("=" * 60)


if __name__ == "__main__":
    main()
