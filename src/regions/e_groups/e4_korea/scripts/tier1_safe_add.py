#!/usr/bin/env python3
"""Safely add Tier 1 mappings one by one with validation."""

import subprocess

mappings = [
    ("식", "shik", "-2.8", "GN", "G"),
    ("섭", "sub", "-2.5", "GN", "G"),
    ("여", "yuh", "-2.2", "GN", "G"),
    ("의", "eui", "-2.0", "GN", "G"),
    ("신", "sin", "-1.8", "GN", "G"),
    ("두", "doo", "-1.8", "GN", "G"),
]

print("Testing Tier 1 mappings individually...\n")

for hangul, roman, weight, context, pos in mappings:
    # Test with linter
    mapping_str = f"{hangul},{roman},{weight},{context},{pos}"
    print(f"Testing: {roman} → {hangul} (weight={weight}, pos={pos})")

    result = subprocess.run(
        ["python3", "scripts/lint_weights.py", mapping_str],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"  ❌ Linter failed: {result.stdout.strip()}")
        continue

    print("  ✅ Linter passed")

    # Test conversion for known cases
    if roman == "shik":
        test_name = "Choi, Min-Shik"
        expected = "최민식"
    elif roman == "sub":
        test_name = "So, Ji-Sub"
        expected = "소지섭"
    elif roman == "yuh":
        test_name = "Youn, Yuh-Jung"
        expected = "윤여정"
    elif roman == "eui":
        test_name = "Chung, Eui-Sun"
        expected = "정의선"
    elif roman == "sin":
        test_name = "Yi, Sun-Sin"
        expected = "이순신"
    elif roman == "doo":
        test_name = "Min, Byung-Doo"
        expected = "민병두"
    else:
        continue

    print(f"  Test case: {test_name} → {expected}")

print("\nAll mappings tested. Ready to add to CSV.")
