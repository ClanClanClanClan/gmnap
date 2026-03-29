#!/usr/bin/env python3
"""Analyze specific failure cases to identify what's fixable."""

import sys

sys.path.insert(0, "src")

from gmnap.core.pipeline import GMNAPPipeline
from gmnap.v7_compat import v7_manager, load_working_processors

# Load processors
if not v7_manager.list_regions():
    load_working_processors()

pipeline = GMNAPPipeline({"database_path": ":memory:"})

# Categorize failures
failures = [
    # Region validation failures
    {
        "name": "Čížek, Pavel",
        "category": "wrong_region",
        "detected": "G1",
        "should_be": "B2",
    },
    {
        "name": "Wang, Ming",
        "native": "王明",
        "category": "mixed_script",
        "detected": "E1",
    },
    {"name": "Test, Name", "region": "B1", "category": "forced_region"},
    # Normalization failures
    {"name": "Testﬃ", "category": "normalization", "issue": "ligature"},
    {"name": "Test№", "category": "normalization", "issue": "numero sign"},
    {"name": "Test½", "category": "normalization", "issue": "fraction"},
    # Script validation
    {
        "name": "王明",
        "category": "script_in_latin",
        "issue": "Chinese in CanonicalLatin",
    },
]

print("Failure Analysis - What Can We Fix?")
print("=" * 60)

fixable = []
architectural = []

for case in failures:
    entry = {"CanonicalLatin": case["name"]}
    if "native" in case:
        entry["CanonicalNative"] = case["native"]
    if "region" in case:
        entry["RegionCode"] = case["region"]

    try:
        result = pipeline.process_entry(entry)
        print(f"✓ {case['name']:20} - Actually works now!")
        continue
    except Exception as e:
        error_msg = str(e)

        print(f"\n{case['name']:20} ({case['category']})")
        print(f"  Error: {error_msg}")

        # Analyze if fixable
        if case["category"] == "wrong_region":
            print(f"  Fix: Improve region detection logic")
            print(
                f"  Current: {case.get('detected', '?')} → Should be: {case.get('should_be', '?')}"
            )
            fixable.append(case)

        elif case["category"] == "mixed_script":
            print(f"  Issue: E1 expects Chinese in Native, Latin in Latin")
            print(f"  Fix: Adjust validation or entry preparation")
            fixable.append(case)

        elif case["category"] == "forced_region":
            print(f"  Issue: B1 expects Cyrillic Native but got Latin")
            print(f"  Fix: Regional validation should be more flexible")
            architectural.append(case)

        elif case["category"] == "normalization":
            print(f"  Issue: A1 rejects normalized Unicode")
            print(f"  Fix: Regional validators should accept NFKC results")
            fixable.append(case)

        elif case["category"] == "script_in_latin":
            print(f"  Issue: Chinese characters in CanonicalLatin field")
            print(f"  Status: Working as intended (security feature)")
            print(f"  Note: This should fail - it's correct behavior")

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"Fixable issues: {len(fixable)}")
print(f"Architectural issues: {len(architectural)}")

print(f"\nFIXABLE (Quick wins):")
for case in fixable:
    print(f"  - {case['name']} ({case['category']})")

print(f"\nARCHITECTURAL (Need design decisions):")
for case in architectural:
    print(f"  - {case['name']} ({case['category']})")
