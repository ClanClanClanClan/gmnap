import pytest

#!/usr/bin/env python3
"""
Test improved region detection with name field support
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_region_detection():
    """Test region detection with various name formats."""

    print("🌍 IMPROVED REGION DETECTION TEST")
    print("=" * 50)

    manager = RegionManager()

    # Test entries - mix of scripts and regions
    test_entries = [
        # Latin names
        {"name": "John Smith", "year": 2024},
        {"name": "José García", "year": 2024},
        {"name": "Jean-Pierre Dubois", "year": 2024},
        {"name": "Giuseppe Verdi", "year": 2024},
        # Korean
        {"name": "김철수", "year": 2024},
        {"name": "박영희", "year": 2024},
        # Chinese
        {"name": "李明", "year": 2024},
        {"name": "王小明", "year": 2024},
        # Japanese
        {"name": "山田太郎", "year": 2024},
        {"name": "鈴木花子", "year": 2024},
        # Arabic
        {"name": "محمد الأحمد", "year": 2024},
        {"name": "فاطمة الزهراء", "year": 2024},
        # Cyrillic
        {"name": "Иван Петров", "year": 2024},
        {"name": "Александр Пушкин", "year": 2024},
        # With canonical fields
        {"CanonicalLatin": "Kim, Chul-Soo", "year": 2024},
        {"CanonicalNative": "김철수", "year": 2024},
    ]

    print("\nREGION DETECTION RESULTS:")
    print("-" * 60)
    print(f"{'Name':30} {'Region':6} {'Confidence':10} {'Method':20}")
    print("-" * 60)

    for entry in test_entries:
        result = manager.detect_region(entry, internal=True)
        name = entry.get("name", entry.get("CanonicalLatin", entry.get("CanonicalNative", "???")))
        print(
            f"{name:30} {result.region_code:6} {result.confidence:10.2f} {result.detection_method:20}"
        )

    # Show cache statistics
    print("\n" + "-" * 60)
    stats = manager.get_cache_stats()
    print(
        f"Cache Performance: {stats['cache_hits']}/{stats['total_requests']} hits ({stats['hit_rate']:.1%})"
    )

    # Test surname detection
    print("\n\nSURNAME PATTERN DETECTION:")
    print("-" * 50)

    surname_tests = [
        {"name": "Kim Chul-Soo", "year": 2024},
        {"name": "Park Young-Hee", "year": 2024},
        {"name": "Tanaka Taro", "year": 2024},
        {"name": "Li Ming", "year": 2024},
        {"name": "Wang Xiaoming", "year": 2024},
    ]

    for entry in surname_tests:
        result = manager.detect_region(entry, internal=True)
        print(f"{entry['name']:20} -> {result.region_code} (confidence: {result.confidence:.2f})")
        if "surname_pattern" in result.metadata:
            print(f"  Detected surname: {result.metadata['surname_pattern']}")


def check_implemented_regions():
    """Show which regions are actually implemented."""

    print("\n\nIMPLEMENTED REGIONS:")
    print("-" * 30)

    manager = RegionManager()
    implemented = manager.get_implemented_regions()

    region_names = {
        "A1": "Anglo Sphere",
        "A2": "Western Europe",
        "B1": "East Slavic",
        "B2": "South Slavic Central",
        "C2": "Persian Tajik",
        "C3": "Arabic Levant Nile",
        "C4": "Arabic Gulf",
        "D1": "South Asia Hindi Belt",
        "E1": "Sinophone Mainland",
        "E3": "Japan",
        "E4": "Korea",
        "G1": "Latin America",
    }

    for code in sorted(implemented):
        name = region_names.get(code, "Unknown")
        print(f"  {code}: {name}")

    print(f"\nTotal: {len(implemented)}/37 regions implemented")


def main():
    """Run all tests."""

    test_region_detection()
    check_implemented_regions()

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
