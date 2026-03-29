import pytest

#!/usr/bin/env python3
"""
Test V7 Critical Fixes Implementation
Validates Korean converter + Enhanced pattern detection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_korean_converter_integration():
    """Test Korean converter is working and integrates with region detection."""

    print("🇰🇷 KOREAN CONVERTER INTEGRATION TEST")
    print("-" * 50)

    manager = RegionManager()

    korean_names = ["김철수", "박영희", "이미나", "최지우", "정다혜"]

    correct_detections = 0

    for name in korean_names:
        result = manager.detect_region({"name": name}, internal=True)
        if result.region_code == "E4":
            correct_detections += 1
            print(f"  PASS {name} -> E4 (conf: {result.confidence:.2f})")
        else:
            print(f"  FAIL {name} -> {result.region_code} (expected E4)")

    success_rate = correct_detections / len(korean_names)
    print(f"\n📊 Korean Detection: {correct_detections}/{len(korean_names)} ({success_rate:.0%})")

    return success_rate


@pytest.mark.timeout(15)
def test_enhanced_pattern_detection():
    """Test enhanced pattern detection for previously broken regions."""

    print("\n🔧 ENHANCED PATTERN DETECTION TEST")
    print("-" * 50)

    manager = RegionManager()

    # Test cases that should now work with enhanced patterns
    test_cases = {
        "B2": [
            ("Petar Petrović", "Serbian Latin name"),
            ("Ivan Horvat", "Croatian name"),
            ("Ana Marić", "South Slavic surname"),
        ],
        "C3": [
            ("محمد الأحمد", "Arabic Levantine with al- prefix"),
            ("أحمد محمد", "Common Levantine name"),
        ],
        "C4": [
            ("عبدالله آل سعود", "Gulf Arabic with tribal آل"),
            ("خالد القطري", "Qatari nationality indicator"),
        ],
        "E3": [
            ("山田太郎", "Japanese with 田 ending"),
            ("鈴木花子", "Japanese with 木 ending"),
            ("田中一郎", "Japanese with given name pattern"),
        ],
    }

    region_results = {}

    for expected_region, names in test_cases.items():
        correct = 0
        print(f"\n{expected_region} Enhanced Detection:")

        for name, description in names:
            result = manager.detect_region({"name": name}, internal=True)

            if result.region_code == expected_region:
                correct += 1
                method = result.detection_method
                conf = result.confidence
                print(f"  PASS {name} -> {expected_region} ({method}, {conf:.2f})")
            else:
                print(f"  FAIL {name} -> {result.region_code} (expected {expected_region})")

        success_rate = correct / len(names)
        region_results[expected_region] = success_rate
        print(f"  📊 {expected_region} Success: {correct}/{len(names)} ({success_rate:.0%})")

    return region_results


@pytest.mark.timeout(15)
def test_non_regression():
    """Test that existing working regions still work."""

    print("\n🛡️  NON-REGRESSION TEST")
    print("-" * 50)

    manager = RegionManager()

    # Test stable regions that should still work
    stable_cases = {
        "A1": [("John Smith", "Anglo name"), ("Mary Johnson", "English name")],
        "A2": [("Jean Dupont", "French name"), ("Hans Mueller", "German name")],
        "B1": [("Иван Петров", "Russian Cyrillic"), ("Владимир Смирнов", "Russian")],
        "C2": [("محمد رضایی", "Persian name"), ("علی احمدی", "Iranian name")],
        "E1": [("李明", "Chinese name"), ("王伟", "Mandarin name")],
        "G1": [("José García", "Spanish name"), ("Maria Silva", "Latin American")],
    }

    total_tests = 0
    total_success = 0

    for region, names in stable_cases.items():
        correct = 0
        for name, _ in names:
            result = manager.detect_region({"name": name}, internal=True)
            if result.region_code == region:
                correct += 1
            total_tests += 1

        total_success += correct
        success_rate = correct / len(names)
        print(f"  {region}: {correct}/{len(names)} ({success_rate:.0%})")

    overall_rate = total_success / total_tests
    print(f"\n📊 Non-regression: {total_success}/{total_tests} ({overall_rate:.0%})")

    return overall_rate


def run_comprehensive_test():
    """Run all critical fix tests."""

    print("🔥 V7 CRITICAL FIXES COMPREHENSIVE TEST")
    print("=" * 60)

    # Test 1: Korean converter
    korean_rate = test_korean_converter_integration()

    # Test 2: Enhanced pattern detection
    pattern_results = test_enhanced_pattern_detection()

    # Test 3: Non-regression
    regression_rate = test_non_regression()

    # Overall assessment
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)

    print(f"\nPASS Korean Integration: {korean_rate:.0%}")
    print(f"PASS Enhanced Patterns:")
    for region, rate in pattern_results.items():
        print(f"   {region}: {rate:.0%}")
    print(f"PASS Non-regression: {regression_rate:.0%}")

    # Calculate average pattern enhancement success
    avg_pattern_rate = sum(pattern_results.values()) / len(pattern_results)

    # Overall system health
    overall_score = (korean_rate + avg_pattern_rate + regression_rate) / 3

    print(f"\n📊 Overall System Health: {overall_score:.1%}")

    if overall_score >= 0.8:
        print("🎉 EXCELLENT: Critical fixes successful!")
        status = "EXCELLENT"
    elif overall_score >= 0.6:
        print("WARN  GOOD: Most fixes working, some issues remain")
        status = "GOOD"
    else:
        print("FAIL POOR: Critical issues still exist")
        status = "POOR"

    print(f"\n🎯 CRITICAL FIXES STATUS: {status}")

    # Specific achievements
    achievements = []
    if korean_rate >= 0.8:
        achievements.append("Korean converter fully restored")
    if avg_pattern_rate >= 0.7:
        achievements.append("Enhanced pattern detection working")
    if regression_rate >= 0.8:
        achievements.append("No regression in stable regions")

    if achievements:
        print(f"\n🏆 ACHIEVEMENTS:")
        for achievement in achievements:
            print(f"   • {achievement}")

    return {
        "overall_score": overall_score,
        "korean_rate": korean_rate,
        "pattern_results": pattern_results,
        "regression_rate": regression_rate,
        "status": status,
    }


if __name__ == "__main__":
    run_comprehensive_test()
