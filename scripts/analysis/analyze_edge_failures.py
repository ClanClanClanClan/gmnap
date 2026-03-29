#!/usr/bin/env python3
"""Analyze specific edge case failures to understand patterns."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.regions.manager import RegionManager

# Edge case test set from brutal audit
edge_cases = [
    {
        "name": "Both empty",
        "entry": {
            "CanonicalLatin": "",
            "CanonicalNative": "",
            "GlobalID": "test-empty",
        },
    },
    {"name": "Missing canonical", "entry": {"GlobalID": "test-missing"}},
    {
        "name": "Single character",
        "entry": {"CanonicalLatin": "A", "GlobalID": "test-single-char"},
    },
    {
        "name": "Single number",
        "entry": {"CanonicalLatin": "1", "GlobalID": "test-single-num"},
    },
    {
        "name": "Single symbol",
        "entry": {"CanonicalLatin": ".", "GlobalID": "test-single-symbol"},
    },
    {
        "name": "Just spaces",
        "entry": {"CanonicalLatin": "   ", "GlobalID": "test-spaces"},
    },
    {
        "name": "Tabs and spaces",
        "entry": {"CanonicalLatin": "\t  \t", "GlobalID": "test-tabs"},
    },
    {
        "name": "Emoji in name",
        "entry": {"CanonicalLatin": "Test 😀 Name", "GlobalID": "test-emoji"},
    },
    {
        "name": "RTL text",
        "entry": {"CanonicalLatin": "محمد عبدالله", "GlobalID": "test-rtl"},
    },
]

manager = RegionManager(Path("./config"))

# Test worst regions
worst_regions = ["E3", "A1", "C9", "D4", "F2"]

print("🔍 ANALYZING EDGE CASE FAILURES IN WORST REGIONS")
print("=" * 60)

for region_code in worst_regions:
    print(f"\n📍 Testing {region_code}:")
    region = manager.get_region(region_code)
    failures = []

    for test_case in edge_cases:
        try:
            entry = test_case["entry"].copy()

            # Test full pipeline
            region.clean(entry)
            region.augment(entry)
            region.validate(entry)
            region.order_key(entry)

            print(f"  ✅ {test_case['name']}: PASS")

        except Exception as e:
            error_msg = str(e)
            failures.append((test_case["name"], error_msg[:60]))
            print(f"  ❌ {test_case['name']}: {error_msg[:60]}")

    success_rate = (len(edge_cases) - len(failures)) / len(edge_cases) * 100
    print(f"  📊 Success rate: {success_rate:.1f}%")

    if failures:
        print(f"  💥 Failures: {len(failures)}")
        for name, error in failures:
            print(f"     - {name}: {error}")

print("\n" + "=" * 60)
print("🎯 COMMON FAILURE PATTERNS:")

# Analyze patterns
patterns = {}
for region_code in worst_regions:
    region = manager.get_region(region_code)
    for test_case in edge_cases:
        try:
            entry = test_case["entry"].copy()
            region.clean(entry)
            region.augment(entry)
            region.validate(entry)
            region.order_key(entry)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # Categorize errors
            if "Tab character" in error_msg:
                pattern = "Tab rejection"
            elif "Family name too short" in error_msg:
                pattern = "Name length validation"
            elif "Security violation" in error_msg:
                pattern = "Security check"
            elif "Missing both" in error_msg or "Entry lacks sufficient" in error_msg:
                pattern = "Empty field handling"
            elif "Invalid characters" in error_msg:
                pattern = "Character validation"
            elif "list index out of range" in error_msg:
                pattern = "Array indexing error"
            else:
                pattern = "Other"

            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(f"{region_code}:{test_case['name']}")

for pattern, cases in patterns.items():
    print(f"\n{pattern}: {len(cases)} failures")
    for case in cases[:5]:  # Show first 5
        print(f"  - {case}")
    if len(cases) > 5:
        print(f"  ... and {len(cases)-5} more")
