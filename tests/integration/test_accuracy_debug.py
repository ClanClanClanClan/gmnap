#!/usr/bin/env python3
"""Debug accuracy test failures"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

manager = RegionManager()

# Test cases that failed
test_cases = [
    ("Marie Curie", "A2", "French name"),
    ("Vladimir Putin", "B1", "Russian name"),
    ("Ahmed Al-Rashid", "C3", "Arabic name"),
    ("Raj Patel", "D1", "Indian name"),
    ("محمد الخليجي", "C4", "Gulf Arabic name"),
]

print("🔍 Debugging accuracy test failures...")
print("=" * 60)

for name, expected, desc in test_cases:
    result = manager.detect_region({"name": name})
    status = "PASS" if result.region_code == expected else "FAIL"
    print(f"\n{status} {desc}: {name}")
    print(f"   Expected: {expected}")
    print(f"   Got: {result.region_code} (confidence: {result.confidence:.3f})")
    print(f"   Method: {result.detection_method}")
    if result.metadata:
        print(f"   Metadata: {result.metadata}")

# Check implemented regions
print("\n" + "=" * 60)
print("📋 Currently implemented regions:")
print(manager.IMPLEMENTED_REGIONS)
