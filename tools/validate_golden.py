#!/usr/bin/env python3
"""Validate pipeline against 500 golden mathematicians."""

import json
import sys
import time

sys.path.insert(0, ".")
from src.regions.manager_optimized import RegionManager

with open("tests/fixtures/golden_mathematicians.json") as f:
    data = json.load(f)

mgr = RegionManager()
correct = 0
failures = []
t0 = time.perf_counter()

for entry in data:
    r = mgr.detect_region(
        {
            "CanonicalLatin": entry["CanonicalLatin"],
            "CountryCodes": entry.get("CountryCodes", []),
        }
    )
    if r.region_code == entry["ExpectedRegion"]:
        correct += 1
    else:
        failures.append(
            f'{entry["CanonicalLatin"]} '
            f'(CC={entry.get("CountryCodes", ["?"])[0]}): '
            f'expected {entry["ExpectedRegion"]}, got {r.region_code}'
        )

elapsed = time.perf_counter() - t0
print("Golden Dataset Validation")
print("=" * 50)
print(f"Total:    {len(data)}")
print(f"Correct:  {correct}")
print(f"Failed:   {len(failures)}")
print(f"Accuracy: {correct / len(data):.1%}")
print(f"Time:     {elapsed:.2f}s")
if failures:
    print("\nFailures:")
    for f_msg in failures[:20]:
        print(f"  {f_msg}")
