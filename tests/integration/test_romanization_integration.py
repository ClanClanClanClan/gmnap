import pytest

#!/usr/bin/env python3
"""
Test ULTRAFIX Phase 8: Romanization Detector Integration
Tests the fix for accuracy issues with romanized names.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

print("🎯 TESTING ROMANIZATION DETECTOR INTEGRATION")
print("=" * 60)

manager = RegionManager()

# Test cases for romanized names that were previously misclassified
test_cases = [
    # Chinese romanized names (should -> E1, not A1/A2)
    ({"name": "Zhang Wei"}, "E1", "Chinese surname + given name"),
    ({"name": "Li Ming"}, "E1", "Common Chinese name"),
    ({"name": "Wang, Xiaoli"}, "E1", "Chinese name with comma format"),
    ({"name": "Chen Yifan"}, "E1", "Chinese mathematician name"),
    ({"name": "Liu, Shing-Tung"}, "E1", "Chinese name with hyphen"),
    # Japanese romanized names (should -> E3, not A1/A2)
    ({"name": "Yamada Taro"}, "E3", "Japanese surname + given name"),
    ({"name": "Tanaka, Hiroshi"}, "E3", "Japanese name with comma"),
    ({"name": "Suzuki Akiko"}, "E3", "Japanese feminine name"),
    ({"name": "Sato, Jun-ichi"}, "E3", "Japanese hyphenated given name"),
    # Korean romanized names (should -> E4, not A1/A2)
    ({"name": "Kim Jong-un"}, "E4", "Korean political figure"),
    ({"name": "Park, Min-ho"}, "E4", "Korean name with comma"),
    ({"name": "Lee Sung-kyung"}, "E4", "Korean actress name"),
    ({"name": "Choi, Hyun-wook"}, "E4", "Korean hyphenated name"),
    # Arabic romanized names (should -> C3, not A1/A2)
    ({"name": "Al-Khwarizmi"}, "C3", "Famous mathematician"),
    ({"name": "Ibn Rushd"}, "C3", "Medieval philosopher"),
    ({"name": "Abdul Rahman"}, "C3", "Arabic name with Abdul"),
    ({"name": "Omar Al-Kindi"}, "C3", "Arabic historical name"),
    # Non-romanized names (should NOT be affected)
    ({"name": "John Smith"}, None, "English name should not be romanized"),
    ({"name": "García, José"}, None, "Spanish name should not be romanized"),
    ({"name": "Schmidt, Hans"}, None, "German name should not be romanized"),
]

romanization_detected = 0
romanization_correct = 0
romanization_wrong = 0
non_romanized_affected = 0

for entry, expected_region, description in test_cases:
    result = manager.detect_region(entry)

    is_romanized = expected_region is not None
    detection_method = result.detection_method
    detected_region = result.region_code

    if is_romanized:
        # This should be detected by romanization
        if detection_method == "romanization":
            romanization_detected += 1
            if detected_region == expected_region:
                print(f"PASS {description}: {entry['name']} -> {detected_region} (romanization)")
                romanization_correct += 1
            else:
                print(
                    f"FAIL {description}: {entry['name']} -> {detected_region} (expected {expected_region})"
                )
                romanization_wrong += 1
        else:
            # Romanized but not detected as such - might still be correct
            if detected_region == expected_region:
                print(
                    f"WARN  {description}: {entry['name']} -> {detected_region} (correct but via {detection_method})"
                )
                romanization_correct += 1
            else:
                print(
                    f"FAIL {description}: {entry['name']} -> {detected_region} (expected {expected_region}, via {detection_method})"
                )
                romanization_wrong += 1
    else:
        # This should NOT be affected by romanization
        if detection_method == "romanization":
            print(
                f"FAIL {description}: {entry['name']} -> {detected_region} (false romanization detection)"
            )
            non_romanized_affected += 1
        else:
            print(
                f"PASS {description}: {entry['name']} -> {detected_region} (via {detection_method}, not romanization)"
            )

# Summary
total_romanized = len([t for t in test_cases if t[1] is not None])
total_non_romanized = len([t for t in test_cases if t[1] is None])

print(f"\n📊 Romanization Detection Results:")
print(f"  Romanized names detected: {romanization_detected}/{total_romanized}")
print(f"  Romanized names correct: {romanization_correct}/{total_romanized}")
print(f"  Non-romanized falsely affected: {non_romanized_affected}/{total_non_romanized}")

accuracy = romanization_correct / total_romanized if total_romanized > 0 else 0
false_positive_rate = non_romanized_affected / total_non_romanized if total_non_romanized > 0 else 0

print(f"\n🎯 Accuracy Metrics:")
print(f"  Romanization accuracy: {accuracy:.1%}")
print(f"  False positive rate: {false_positive_rate:.1%}")

# Test specific improvements
print(f"\n🔍 Specific Improvements:")
print(f"  'Zhang Wei' -> {manager.detect_region({'name': 'Zhang Wei'}).region_code} (should be E1)")
print(
    f"  'Kim Jong-un' -> {manager.detect_region({'name': 'Kim Jong-un'}).region_code} (should be E4)"
)
print(
    f"  'Al-Khwarizmi' -> {manager.detect_region({'name': 'Al-Khwarizmi'}).region_code} (should be C3)"
)

if romanization_correct >= total_romanized * 0.8 and non_romanized_affected == 0:
    print("\nPASS ROMANIZATION INTEGRATION SUCCESS!")
    print("   - High accuracy for romanized names")
    print("   - No false positives for non-romanized names")
else:
    print(f"\nWARN  ROMANIZATION INTEGRATION NEEDS IMPROVEMENT")
    print(f"   - Accuracy: {accuracy:.1%} (target: 80%+)")
    print(f"   - False positives: {false_positive_rate:.1%} (target: 0%)")
