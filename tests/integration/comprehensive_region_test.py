#!/usr/bin/env python3
"""
Comprehensive Regional Coverage Test
Test all 19 implemented regions with representative names
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.regions.manager_optimized import RegionManager


def test_comprehensive_coverage():
    """Test all implemented regions with representative mathematician names."""

    print("🌍 COMPREHENSIVE REGIONAL COVERAGE TEST")
    print("=" * 80)

    manager = RegionManager()

    # Test cases by region
    test_cases = [
        # A Group - Western/Developed (4/5 regions)
        ("A1", "Smith, John", "Anglo Sphere"),
        ("A1", "Williams, Sarah", "Anglo Sphere"),
        ("A2", "Müller, Hans", "Western Europe"),
        ("A2", "Dubois, Marie", "Western Europe"),
        ("A3", "Andersson, Erik", "Nordic Baltic"),
        ("A3", "Olsson, Lars", "Nordic Baltic"),
        ("A4", "Te Kanawa, Kiri", "Oceania"),
        ("A4", "Williams, David", "Oceania"),
        # B Group - European/Slavic (3/3 regions - COMPLETE!)
        ("B1", "Ivanov, Vladimir", "East Slavic"),
        ("B1", "Petrov, Alexei", "East Slavic"),
        ("B2", "Nowak, Jan", "South Slavic Central"),
        ("B2", "Kowalski, Marek", "South Slavic Central"),
        ("B3", "Papadopoulos, Nikos", "Greek"),
        ("B3", "Georgiou, Maria", "Greek"),
        # C Group - Middle East/Central Asia (4/9 regions)
        ("C1", "Özkan, Ahmet", "Turkic"),
        ("C1", "Aliyev, Rashad", "Turkic"),
        ("C2", "Ahmadi, Hassan", "Persian Tajik"),
        ("C2", "Hosseini, Fatima", "Persian Tajik"),
        ("C3", "Al-Khwarizmi, Muhammad", "Arabic Levant Nile"),
        ("C3", "Hassan, Amira", "Arabic Levant Nile"),
        ("C4", "Al-Rashid, Omar", "Arabic Gulf"),
        ("C4", "Al-Zahra, Layla", "Arabic Gulf"),
        # D Group - South Asia (1/5 regions)
        ("D1", "Sharma, Raj", "South Asia Hindi Belt"),
        ("D1", "Gupta, Priya", "South Asia Hindi Belt"),
        # E Group - East Asia/Southeast Asia (5/7 regions)
        ("E1", "王伟", "Sinophone Mainland"),
        ("E1", "李明", "Sinophone Mainland"),
        ("E2", "陳小明", "Traditional Chinese"),
        ("E2", "林美華", "Traditional Chinese"),
        ("E3", "Tanaka, Hiroshi", "Japan"),
        ("E3", "Sato, Yuki", "Japan"),
        ("E4", "Kim, Jong-un", "Korea"),
        ("E4", "Park, Min-jung", "Korea"),
        ("E5", "Nguyen, Van Duc", "Vietnam"),
        ("E5", "Tran, Thi Mai", "Vietnam"),
        # F Group - Africa (1/4 regions)
        ("F1", "Diallo, Mamadou", "SSA Francophone"),
        ("F1", "Traoré, Aminata", "SSA Francophone"),
        # G Group - Latin America (1/1 regions - COMPLETE!)
        ("G1", "García, María", "Latin America"),
        ("G1", "Rodriguez, Carlos", "Latin America"),
    ]

    # Test each case
    results = {}
    successful_detections = 0
    total_tests = len(test_cases)

    for expected_region, name, description in test_cases:
        try:
            result = manager.detect_region({"name": name})
            detected_region = result.region_code
            confidence = result.confidence
            method = result.detection_method

            if expected_region not in results:
                results[expected_region] = []

            success = detected_region == expected_region
            if success:
                successful_detections += 1

            results[expected_region].append(
                {
                    "name": name,
                    "expected": expected_region,
                    "detected": detected_region,
                    "confidence": confidence,
                    "method": method,
                    "success": success,
                    "description": description,
                }
            )

            status = "PASS" if success else "FAIL"
            print(
                f"{status} {name} -> {detected_region} (expected {expected_region}, conf: {confidence:.2f})"
            )

        except Exception as e:
            print(f"💥 {name} -> ERROR: {e}")
            results.setdefault(expected_region, []).append(
                {
                    "name": name,
                    "expected": expected_region,
                    "detected": "ERROR",
                    "confidence": 0.0,
                    "method": "error",
                    "success": False,
                    "description": description,
                    "error": str(e),
                }
            )

    # Summary by region
    print(f"\n📊 REGIONAL PERFORMANCE SUMMARY:")
    print(f"=" * 60)

    for region_code in sorted(results.keys()):
        region_results = results[region_code]
        successes = sum(1 for r in region_results if r["success"])
        total = len(region_results)
        success_rate = successes / total if total > 0 else 0

        description = region_results[0]["description"] if region_results else "Unknown"
        status = (
            "PASS" if success_rate >= 0.5 else "WARN" if success_rate > 0 else "FAIL"
        )

        print(
            f"{status} {region_code} {description}: {successes}/{total} ({success_rate:.1%})"
        )

        if success_rate < 1.0:
            print(f"    Issues:")
            for r in region_results:
                if not r["success"]:
                    print(
                        f"      • {r['name']} -> {r['detected']} (method: {r['method']})"
                    )

    print(f"\n🎯 OVERALL PERFORMANCE:")
    print(f"  Total tests: {total_tests}")
    print(f"  Successful detections: {successful_detections}")
    print(f"  Overall accuracy: {successful_detections/total_tests:.1%}")
    print(f"  Regions tested: {len(results)}/19 implemented")

    # Coverage analysis
    print(f"\n🌍 COVERAGE ANALYSIS:")
    implemented_regions = manager.get_implemented_regions()
    print(
        f"  Implemented regions: {len(implemented_regions)}/37 ({len(implemented_regions)/37:.1%})"
    )
    print(
        f"  Regions tested: {len(results)}/{len(implemented_regions)} ({len(results)/len(implemented_regions):.1%})"
    )

    # Performance grade
    if successful_detections / total_tests >= 0.9:
        grade = "A+ Excellent"
        status = "🟢 PRODUCTION READY"
    elif successful_detections / total_tests >= 0.8:
        grade = "A Good"
        status = "🟡 MOSTLY READY"
    elif successful_detections / total_tests >= 0.7:
        grade = "B Fair"
        status = "🟡 NEEDS IMPROVEMENT"
    else:
        grade = "C Poor"
        status = "🔴 NOT READY"

    print(f"\n🏆 REGIONAL SYSTEM GRADE: {grade}")
    print(f"📈 STATUS: {status}")

    return successful_detections / total_tests


if __name__ == "__main__":
    test_comprehensive_coverage()
