import pytest

#!/usr/bin/env python3
"""
Comprehensive Accuracy Test for GMNAP v7
Tests overall accuracy across all implemented regions and scenarios.
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

print("🎯 COMPREHENSIVE ACCURACY TEST")
print("=" * 60)

manager = RegionManager()

# Comprehensive test cases covering all implemented regions and scenarios
test_cases = [
    # A1 Anglo Sphere
    ({"name": "Smith, John"}, "A1", "Anglo surname"),
    ({"name": "Johnson, Mary"}, "A1", "Common Anglo name"),
    ({"name": "Newton, Isaac"}, "A1", "Historical mathematician"),
    # A2 Western Europe
    ({"name": "Müller, Hans"}, "A2", "German surname"),
    ({"name": "Gauss, Carl Friedrich"}, "A2", "German mathematician"),
    ({"name": "Dupont, Pierre"}, "A2", "French surname"),
    ({"name": "Poincaré, Henri"}, "A2", "French mathematician"),
    ({"name": "Rossi, Mario"}, "A2", "Italian surname"),
    # B1 East Slavic
    ({"name": "Petrov, Ivan"}, "B1", "Russian surname"),
    ({"name": "Kolmogorov, Andrey"}, "B1", "Russian mathematician"),
    ({"name": "Chebyshev, Pafnuty"}, "B1", "Russian mathematician"),
    # B2 South Slavic Central
    ({"name": "Jovanović, Milan"}, "B2", "Serbian surname"),
    ({"name": "Novak, Jan"}, "B2", "Czech surname"),
    ({"name": "Kowalski, Adam"}, "B2", "Polish surname"),
    # C2 Persian Tajik
    ({"name": "Ahmadi, Hassan"}, "C2", "Persian surname"),
    ({"name": "Khayyam, Omar"}, "C2", "Persian mathematician"),
    # C3 Arabic Levant
    ({"name": "Al-Khwarizmi"}, "C3", "Historical Arabic mathematician"),
    ({"name": "Ibn Rushd"}, "C3", "Medieval Arabic philosopher"),
    ({"name": "Hassan, Ahmad"}, "C3", "Arabic name"),
    ({"name": "Abdul Rahman"}, "C3", "Arabic name"),
    # C4 Arabic Gulf
    ({"name": "Al-Rashid, Khalid"}, "C4", "Gulf Arabic surname"),
    # D1 South Asia Hindi Belt
    ({"name": "Sharma, Raj"}, "D1", "Hindi Belt surname"),
    ({"name": "Ramanujan, Srinivasa"}, "D1", "Indian mathematician"),
    ({"name": "Patel, Anil"}, "D1", "Common Indian surname"),
    # E1 Sinophone Mainland
    ({"name": "Wang, Wei"}, "E1", "Chinese romanized"),
    ({"name": "Li Ming"}, "E1", "Chinese romanized"),
    ({"name": "Zhang, Yitang"}, "E1", "Chinese mathematician"),
    ({"name": "Chen Yifan"}, "E1", "Chinese romanized"),
    # E3 Japan
    ({"name": "Yamada Taro"}, "E3", "Japanese romanized"),
    ({"name": "Suzuki, Akiko"}, "E3", "Japanese romanized"),
    ({"name": "Tanaka, Hiroshi"}, "E3", "Japanese name"),
    # E4 Korea
    ({"name": "Kim Jong-un"}, "E4", "Korean romanized"),
    ({"name": "Park, Min-ho"}, "E4", "Korean romanized"),
    ({"name": "Lee Sung-kyung"}, "E4", "Korean romanized"),
    # G1 Latin America
    ({"name": "García, José"}, "G1", "Spanish surname"),
    ({"name": "Silva, Maria"}, "G1", "Portuguese surname"),
    ({"name": "Rodriguez, Carlos"}, "G1", "Latin American surname"),
    # Edge cases and challenging scenarios
    (
        {"name": "Kim, Michael"},
        "A1",
        "Cross-cultural name (Korean surname, English given name)",
    ),
    ({"name": "Lee, Christopher"}, "A1", "Cross-cultural name"),
    ({"name": "Wang, David"}, "E1", "Chinese surname with English given name"),
    ({"name": "Al-Smith, Ahmed"}, "C3", "Mixed Arabic-English surname"),
    # Names with particles
    ({"name": "van der Waerden, Bartel"}, "A2", "Dutch name with particles"),
    ({"name": "de la Cruz, Carlos"}, "G1", "Spanish name with particles"),
    # Historical mathematicians
    ({"name": "Euler, Leonhard"}, "A2", "Swiss mathematician"),
    ({"name": "Fibonacci, Leonardo"}, "A2", "Italian mathematician"),
    ({"name": "Al-Battani"}, "C3", "Arabic astronomer"),
    ({"name": "Brahmagupta"}, "D1", "Indian mathematician"),
]

correct = 0
total = 0
results_by_region = {}
method_counts = {}

for entry, expected_region, description in test_cases:
    result = manager.detect_region(entry)
    detected_region = result.region_code
    method = result.detection_method
    confidence = result.confidence

    total += 1
    is_correct = detected_region == expected_region

    # Track by region
    if expected_region not in results_by_region:
        results_by_region[expected_region] = {"correct": 0, "total": 0}
    results_by_region[expected_region]["total"] += 1

    # Track by detection method
    method_counts[method] = method_counts.get(method, 0) + 1

    if is_correct:
        correct += 1
        results_by_region[expected_region]["correct"] += 1
        print(
            f"PASS {description}: {entry.get('name')} -> {detected_region} (via {method}, {confidence:.2f})"
        )
    else:
        print(
            f"FAIL {description}: {entry.get('name')} -> {detected_region} (expected {expected_region}, via {method}, {confidence:.2f})"
        )

# Calculate overall accuracy
accuracy = correct / total if total > 0 else 0

print(f"\n📊 COMPREHENSIVE ACCURACY RESULTS:")
print(f"  Overall: {correct}/{total} = {accuracy:.1%}")

# Accuracy by region
print(f"\n📍 Accuracy by Region:")
for region in sorted(results_by_region.keys()):
    stats = results_by_region[region]
    region_accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
    print(f"  {region}: {stats['correct']}/{stats['total']} = {region_accuracy:.1%}")

# Detection method breakdown
print(f"\n🔍 Detection Methods Used:")
for method in sorted(method_counts.keys()):
    count = method_counts[method]
    percentage = count / total * 100 if total > 0 else 0
    print(f"  {method}: {count} ({percentage:.1f}%)")

# Assessment
print(f"\n🎯 ACCURACY ASSESSMENT:")
if accuracy >= 0.95:
    print(f"PASS TARGET ACHIEVED! {accuracy:.1%} accuracy meets 95%+ target")
    print("   System is ready for production deployment")
elif accuracy >= 0.90:
    print(f"WARN  CLOSE TO TARGET: {accuracy:.1%} accuracy (target: 95%+)")
    print("   System needs minor improvements")
else:
    print(f"FAIL BELOW TARGET: {accuracy:.1%} accuracy (target: 95%+)")
    print("   System needs significant improvements")

# Specific issues to address
low_accuracy_regions = [
    r
    for r, stats in results_by_region.items()
    if stats["correct"] / stats["total"] < 0.8
]

if low_accuracy_regions:
    print(f"\nWARN  Regions needing improvement:")
    for region in low_accuracy_regions:
        stats = results_by_region[region]
        acc = stats["correct"] / stats["total"]
        print(f"   {region}: {acc:.1%} accuracy")
