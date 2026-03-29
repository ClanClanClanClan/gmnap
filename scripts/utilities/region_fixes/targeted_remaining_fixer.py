# \!/usr/bin/env python3
"""
Targeted fixes for the remaining 13 problematic regions.
These need special handling beyond the systematic approach.
"""

import sys
from pathlib import Path

# Add project root to path before importing src modules
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.regions.manager import RegionManager

# Remaining problematic regions
REMAINING_REGIONS = ["A3", "A4", "A5", "B3", "C1", "C5", "C6", "C7", "C8", "E6", "E7", "F1", "F3"]


def debug_specific_region_failures():
    """Debug each remaining region to understand specific failure patterns."""
    manager = RegionManager(Path("./config"))

    # Key edge cases to test
    edge_cases = [
        {"name": "Tab character", "test": {"CanonicalLatin": "Test\tName", "GlobalID": "tab"}},
        {
            "name": "Newline character",
            "test": {"CanonicalLatin": "Test\nName", "GlobalID": "newline"},
        },
        {"name": "Single char", "test": {"CanonicalLatin": "X", "GlobalID": "single"}},
        {
            "name": "Empty Latin",
            "test": {"CanonicalLatin": "", "CanonicalNative": "Test", "GlobalID": "empty"},
        },
    ]

    print("🔍 DEBUGGING REMAINING PROBLEMATIC REGIONS")
    print("=" * 60)

    region_patterns = {}

    for region_code in REMAINING_REGIONS:
        try:
            region = manager.get_region(region_code)
            if not region:
                print(f"❌ {region_code}: NOT LOADED")
                continue

            failures = []
            for case in edge_cases:
                try:
                    entry = case["test"].copy()
                    region.clean(entry)
                    region.augment(entry)
                    region.validate(entry)
                    region.order_key(entry)
                except Exception as e:
                    failures.append((case["name"], str(e)[:80]))

            if failures:
                print(f"\n❌ {region_code} failures:")
                for name, error in failures:
                    print(f"  - {name}: {error}")
                region_patterns[region_code] = failures

        except Exception as e:
            print(f"💥 {region_code}: BROKEN - {str(e)}")

    return region_patterns


# Main execution
if __name__ == "__main__":
    patterns = debug_specific_region_failures()

    print("\n" + "=" * 60)
    print("📊 FAILURE PATTERN ANALYSIS:")

    tab_failures = [r for r, f in patterns.items() if any("Tab" in fail[0] for fail in f)]
    newline_failures = [r for r, f in patterns.items() if any("Newline" in fail[0] for fail in f)]
    empty_failures = [r for r, f in patterns.items() if any("Empty" in fail[0] for fail in f)]

    print(f"Tab failures: {len(tab_failures)} regions - {tab_failures}")
    print(f"Newline failures: {len(newline_failures)} regions - {newline_failures}")
    print(f"Empty field failures: {len(empty_failures)} regions - {empty_failures}")

    print("\n🎯 NEXT STEPS:")
    print("1. Manually inspect remaining region files")
    print("2. Apply targeted fixes for each failure pattern")
    print("3. Re-test to achieve system-wide 95%+ edge cases")
