# \!/usr/bin/env python3
"""
Comprehensive audit to identify which regions still fail edge cases.
"""

from src.regions.manager import RegionManager
from pathlib import Path
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Core edge cases that all regions should handle
core_edge_cases = [
    {
        "name": "Tab character",
        "test": {"CanonicalLatin": "Test\tName", "GlobalID": "tab"},
    },
    {
        "name": "Newline character",
        "test": {"CanonicalLatin": "Test\nName", "GlobalID": "newline"},
    },
    {"name": "Single char", "test": {"CanonicalLatin": "X", "GlobalID": "single"}},
    {
        "name": "Empty Latin",
        "test": {"CanonicalLatin": "", "CanonicalNative": "Test", "GlobalID": "empty"},
    },
    {"name": "Missing both", "test": {"GlobalID": "missing"}},
    {
        "name": "Very long name",
        "test": {"CanonicalLatin": "A" * 100, "GlobalID": "long"},
    },
    {
        "name": "Complex punctuation",
        "test": {"CanonicalLatin": "O'Brien-Smith, Jr.", "GlobalID": "complex"},
    },
    {
        "name": "Accented chars",
        "test": {"CanonicalLatin": "José María", "GlobalID": "accents"},
    },
]

manager = RegionManager(Path("./config"))

# Get all available regions
all_regions = [
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "B1",
    "B2",
    "B3",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "F1",
    "F2",
    "F3",
    "G1",
]

print("🔍 COMPREHENSIVE EDGE CASE AUDIT - ALL REGIONS")
print("=" * 60)

region_results = {}
problematic_regions = []

for region_code in all_regions:
    try:
        region = manager.get_region(region_code)
        if not region:
            print(f"❌ {region_code}: NOT LOADED")
            continue

        passes = 0
        failures = []

        for case in core_edge_cases:
            try:
                entry = case["test"].copy()
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)
                region.order_key(entry)
                passes += 1
            except Exception as e:
                failures.append((case["name"], str(e)[:60]))

        success_rate = 100 * passes / len(core_edge_cases)
        region_results[region_code] = success_rate

        if success_rate >= 95:
            print(
                f"✅ {region_code}: {passes}/{len(core_edge_cases)} ({success_rate:.0f}%) EXCELLENT"
            )
        elif success_rate >= 85:
            print(
                f"⚠️ {region_code}: {passes}/{len(core_edge_cases)} ({success_rate:.0f}%) GOOD"
            )
            problematic_regions.append(region_code)
        else:
            print(
                f"❌ {region_code}: {passes}/{len(core_edge_cases)} ({success_rate:.0f}%) NEEDS WORK"
            )
            problematic_regions.append(region_code)
            print(f"   Common failures: {[f[0] for f in failures[:3]]}")

    except Exception as e:
        print(f"💥 {region_code}: BROKEN - {str(e)[:60]}")

print("\n" + "=" * 60)
print("📊 SUMMARY:")
excellent = [r for r, s in region_results.items() if s >= 95]
good = [r for r, s in region_results.items() if 85 <= s < 95]
poor = [r for r, s in region_results.items() if s < 85]

print(f"✅ Excellent (95%+): {len(excellent)} regions - {excellent}")
print(f"⚠️ Good (85-94%): {len(good)} regions - {good}")
print(f"❌ Poor (<85%): {len(poor)} regions - {poor}")

print(f"\n🎯 NEED TO FIX: {len(problematic_regions)} regions")
print(f"Target: Get ALL regions to 95%+ edge case handling")

if problematic_regions:
    print(f"\nProblematic regions to fix: {problematic_regions}")
