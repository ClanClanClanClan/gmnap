#!/usr/bin/env python3
"""
Test ULTRAFIX Phase 2 - FastText language detection fix
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

print("🔧 ULTRAFIX PHASE 2 VALIDATION")
print("=" * 60)

manager = RegionManager()

# Test cases that should now work
test_cases = [
    # Name, Expected Region, Expected Method
    ("Marie Curie", "A2", "French name should detect via language"),
    ("Vladimir Putin", "B1", "Russian name should detect via language"),
    ("Ahmed Al-Rashid", "C3", "Arabic name may still fall back"),
    ("Raj Patel", "D1", "Hindi name may fall back"),
    ("José García", "G1", "Spanish name should work"),
    ("Müller Schmidt", "A2", "German name should work via pattern/language"),
]

print("Testing language detection fixes...")
print("-" * 40)

passed = 0
total = len(test_cases)

for name, expected_region, description in test_cases:
    result = manager.detect_region({"name": name})

    if result.region_code == expected_region:
        print(f"PASS {description}")
        print(
            f"   {name} -> {result.region_code} (conf: {result.confidence:.3f}, method: {result.detection_method})"
        )
        passed += 1
    else:
        print(f"FAIL {description}")
        print(f"   {name} -> {result.region_code} (expected {expected_region})")
        print(
            f"   Confidence: {result.confidence:.3f}, Method: {result.detection_method}"
        )
        if result.metadata:
            print(f"   Metadata: {result.metadata}")

print("\n" + "=" * 60)
accuracy = (passed / total) * 100
print(f"📊 PHASE 2 RESULTS: {passed}/{total} ({accuracy:.1f}%)")

if accuracy >= 80:
    print("PASS ULTRAFIX PHASE 2 SUCCESSFUL - Language detection improved!")
elif accuracy >= 60:
    print("WARN ULTRAFIX PHASE 2 PARTIAL - Some improvements made")
else:
    print("FAIL ULTRAFIX PHASE 2 FAILED - Significant issues remain")

# Test original failing cases from Phase 1
print("\n🔄 Re-testing original failing cases...")
print("-" * 40)

original_failures = [
    ("Marie Curie", "A2", "Easy French name"),
    ("Vladimir Putin", "B1", "Medium Russian name"),
    ("Ahmed Al-Rashid", "C3", "Medium Arabic name"),
    ("Raj Patel", "D1", "Medium Indian name"),
]

original_passed = 0
for name, expected, desc in original_failures:
    result = manager.detect_region({"name": name})
    status = "PASS" if result.region_code == expected else "FAIL"
    if result.region_code == expected:
        original_passed += 1
    print(f"{status} {desc}: {name} -> {result.region_code}")

original_accuracy = (original_passed / len(original_failures)) * 100
improvement = original_accuracy - 0  # Was 0% before
print(f"\n📈 IMPROVEMENT: {original_accuracy:.1f}% (up from 0%)")
print(f"🎯 Net improvement: +{improvement:.1f} percentage points")
