#!/usr/bin/env python3
"""Test Korean name detection in pipeline."""

import sys

sys.path.insert(
    0, "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src"
)

from src.core.pipeline import GMNAPPipeline

pipeline = GMNAPPipeline()

# Test Korean names that should be detected as E4
korean_test_names = [
    "Kim, Yuna",
    "Park, Ji-Sung",
    "Lee, Chong-Wei",
    "Choi, Min-Ho",
    "Ahn, Dae-Hoon",
    "Cho, Seung-Hee",
    "Bae, Yeon-Ju",
    "Ryu, Hyun-Jin",
    "Lee",  # Single name
    "Choi",
    "Cho",
]

print("Testing Korean name detection:")
print("=" * 60)

for name in korean_test_names:
    try:
        region = pipeline._detect_region_by_name_pattern(name)
        status = "✓" if region == "E4" else "✗"
        print(f"{name:20} -> {region:3} {status}")
    except Exception as e:
        print(f"{name:20} -> ERROR: {e}")

# Test names that should NOT be E4
non_korean_names = [
    "Smith, John",
    "Lee, Bruce",  # Should be A1 (Western context)
    "Wang, Lei",  # Chinese E1
    "Tanaka, Ito",  # Japanese E3
]

print("\n\nTesting non-Korean names (should NOT be E4):")
print("=" * 60)

for name in non_korean_names:
    try:
        region = pipeline._detect_region_by_name_pattern(name)
        status = "✓" if region != "E4" else "✗"
        print(f"{name:20} -> {region:3} {status}")
    except Exception as e:
        print(f"{name:20} -> ERROR: {e}")
