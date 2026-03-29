#!/usr/bin/env python3
"""Debug Korean processor issues."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor


def debug_korean_names():
    processor = E4KoreanProcessor()

    test_cases = [
        {"CanonicalNative": "김민수", "GlobalID": "TEST-001"},
        {"CanonicalNative": "박지성", "GlobalID": "TEST-002"},
        {"CanonicalNative": "이순신", "GlobalID": "TEST-003"},
        {"CanonicalNative": "김정은", "GlobalID": "TEST-004"},
        {"CanonicalNative": "문재인", "GlobalID": "TEST-005"},
    ]

    print("Debug Korean Processor")
    print("=" * 60)

    for test in test_cases:
        native = test["CanonicalNative"]
        print(f"\nProcessing: {native}")
        print("-" * 30)

        # Parse the name
        family, given = processor._parse_hangul_name(native)
        print(f"  Parsed: Family='{family}', Given='{given}'")

        # Extract components
        components = processor._extract_components(native)
        print(f"  Components: {components}")

        # Try fallback romanization
        romanized = processor._fallback_romanize(native, components)
        print(f"  Romanized: {romanized}")

        # Process the full entry
        result = processor.process(test.copy())
        latin = result.get("CanonicalLatin", "ERROR")
        print(f"  Final Result: {latin}")


if __name__ == "__main__":
    debug_korean_names()
