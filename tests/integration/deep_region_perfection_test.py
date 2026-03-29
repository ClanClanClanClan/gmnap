#!/usr/bin/env python3
"""
DEEP REGION PERFECTION TEST
Test each working region extensively to achieve 100% quality
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.regions.manager_optimized import RegionManager
import traceback


def deep_test_region(region_code, test_cases):
    """Deep test a region with comprehensive edge cases."""
    try:
        manager = RegionManager()
        # Force load regions
        manager._ensure_regions_loaded()

        if region_code not in manager._regions:
            return {"success": False, "error": f"Region {region_code} not loaded"}

        region_processor = manager._regions[region_code]

        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "errors": [],
            "success": True,
        }

        for i, test_case in enumerate(test_cases):
            try:
                # Test full pipeline
                test_entry = test_case.copy()
                test_entry["CanonicalLatin"] = test_case.get("name", "")

                # Step 1: Clean
                region_processor.clean(test_entry)

                # Step 2: Validate
                region_processor.validate(test_entry)

                # Step 3: Augment
                region_processor.augment(test_entry)

                # Step 4: Order key
                order_key = region_processor.order_key(test_entry)

                # Verify order key is not empty
                if not order_key or order_key.strip() == "":
                    results["errors"].append(
                        f"Test {i+1}: Empty order key for {test_case.get('name', 'unknown')}"
                    )
                    results["failed"] += 1
                    continue

                results["passed"] += 1

            except Exception as e:
                results["errors"].append(
                    f"Test {i+1}: {test_case.get('name', 'unknown')} - {str(e)}"
                )
                results["failed"] += 1

        success_rate = (
            results["passed"] / results["total_tests"] * 100 if results["total_tests"] > 0 else 0
        )
        results["success_rate"] = success_rate
        results["success"] = success_rate >= 100.0  # Require 100% for perfection

        return results

    except Exception as e:
        return {"success": False, "error": f"Deep test failed: {str(e)}"}


def perfection_audit():
    """Run deep perfection tests on all 6 working regions."""
    print("🔥 DEEP REGION PERFECTION AUDIT")
    print("=" * 60)

    # Comprehensive test cases for each region
    region_test_cases = {
        "A3": [  # Nordic Baltic
            {"name": "Lars Andersen"},
            {"name": "Erik Nilsson"},
            {"name": "Anna Korhonen"},
            {"name": "Björn Svensson"},
            {"name": "Ingrid Larsson"},
            {"name": "Mikko Virtanen"},
            {"name": "Astrid Nielsen"},
            {"name": "Jørgen Hansen"},
            {"name": "Maarit Koskinen"},
            {"name": "Ragnar Ólafsson"},
            # Edge cases
            {"name": ""},  # Empty
            {"name": "A"},  # Single char
            {"name": "Lars-Erik Andersen"},  # Hyphenated
            {"name": "von Nielsen"},  # Noble prefix
            {"name": "Søren Åkesson"},  # Nordic characters
        ],
        "B2": [  # South Slavic Central
            {"name": "Marko Petrović"},
            {"name": "Ana Novak"},
            {"name": "Petar Jovanović"},
            {"name": "Milica Stojanović"},
            {"name": "Stefan Popović"},
            {"name": "Jovana Nikolić"},
            {"name": "Aleksandar Đorđević"},
            {"name": "Nataša Mitrović"},
            {"name": "Dragan Stanković"},
            {"name": "Jelena Marković"},
            # Edge cases
            {"name": ""},
            {"name": "M"},
            {"name": "Marko-Stefan Petrović"},
            {"name": "Dr. Petrović"},
            {"name": "Žarko Čović"},  # Slavic diacritics
        ],
        "E2": [  # Traditional Chinese
            {"name": "李明華"},
            {"name": "王小明"},
            {"name": "陳美玲"},
            {"name": "張志偉"},
            {"name": "劉建國"},
            {"name": "黃淑娟"},
            {"name": "林志豪"},
            {"name": "吳雅芳"},
            {"name": "鄭文雄"},
            {"name": "蔡錦華"},
            # Edge cases
            {"name": ""},
            {"name": "李"},
            {"name": "歐陽志豪"},  # Compound surname
            {"name": "司馬相如"},  # Classical name
            {"name": "李・明華"},  # With middle dot
        ],
        "E4": [  # Korea
            {"name": "김철수"},
            {"name": "박영희"},
            {"name": "이민수"},
            {"name": "최미영"},
            {"name": "정대현"},
            {"name": "한소영"},
            {"name": "윤지훈"},
            {"name": "임수진"},
            {"name": "조민호"},
            {"name": "강은지"},
            # Edge cases
            {"name": ""},
            {"name": "김"},
            {"name": "남궁민수"},  # Compound surname
            {"name": "황보영희"},  # Compound surname
            {"name": "김・철수"},  # With separator
        ],
        "E5": [  # Vietnam
            {"name": "Nguyễn Văn Nam"},
            {"name": "Trần Thị Lan"},
            {"name": "Lê Văn Hùng"},
            {"name": "Phạm Thị Mai"},
            {"name": "Hoàng Văn Đức"},
            {"name": "Vũ Thị Hoa"},
            {"name": "Đỗ Văn Minh"},
            {"name": "Bùi Thị Nga"},
            {"name": "Đinh Văn Long"},
            {"name": "Ngô Thị Thu"},
            # Edge cases
            {"name": ""},
            {"name": "N"},
            {"name": "Nguyễn-Văn Nam"},  # Hyphenated
            {"name": "Dr. Nguyễn"},  # Title
            {"name": "Nguyễn Thị Minh-Hạnh"},  # Compound given name
        ],
        "G1": [  # Latin America
            {"name": "José García"},
            {"name": "María López"},
            {"name": "Carlos Rodríguez"},
            {"name": "Ana Martínez"},
            {"name": "Luis Hernández"},
            {"name": "Carmen Gómez"},
            {"name": "Pedro Díaz"},
            {"name": "Rosa Jiménez"},
            {"name": "Miguel Moreno"},
            {"name": "Isabel Muñoz"},
            # Edge cases
            {"name": ""},
            {"name": "J"},
            {"name": "José-María García"},  # Compound given
            {"name": "García López, Juan"},  # Compound surname
            {"name": "de la Cruz, María"},  # Prepositional surname
        ],
    }

    working_regions = ["A3", "B2", "E2", "E4", "E5", "G1"]
    perfect_regions = []
    imperfect_regions = []

    print(f"Testing {len(working_regions)} regions for PERFECTION...")
    print()

    for region in working_regions:
        if region not in region_test_cases:
            print(f"⚪ {region}: No comprehensive test cases")
            continue

        test_cases = region_test_cases[region]
        results = deep_test_region(region, test_cases)

        if results.get("success", False):
            perfect_regions.append(region)
            print(
                f"PASS {region}: PERFECT - {results['passed']}/{results['total_tests']} tests passed ({results['success_rate']:.1f}%)"
            )
        else:
            imperfect_regions.append(region)
            passed = results.get("passed", 0)
            total = results.get("total_tests", 0)
            rate = results.get("success_rate", 0)
            print(f"FAIL {region}: NEEDS WORK - {passed}/{total} tests passed ({rate:.1f}%)")

            # Show error message if it's a loading error
            if "error" in results:
                print(f"   💥 {results['error']}")

            # Show first few errors
            for error in results.get("errors", [])[:3]:
                print(f"   🚨 {error}")
            if len(results.get("errors", [])) > 3:
                print(f"   ... and {len(results.get('errors', [])) - 3} more errors")

    print()
    print("=" * 60)
    print("PERFECTION AUDIT SUMMARY")
    print("=" * 60)

    perfect_count = len(perfect_regions)
    imperfect_count = len(imperfect_regions)
    total_count = len(working_regions)

    print(
        f"🎯 PERFECT REGIONS: {perfect_count}/{total_count} ({perfect_count/total_count*100:.1f}%)"
    )
    print(
        f"WARN  IMPERFECT REGIONS: {imperfect_count}/{total_count} ({imperfect_count/total_count*100:.1f}%)"
    )

    if perfect_regions:
        print(f"PASS PERFECT: {perfect_regions}")
    if imperfect_regions:
        print(f"FAIL NEEDS WORK: {imperfect_regions}")

    print()
    if perfect_count == total_count:
        print("🏆 STATUS: ALL REGIONS PERFECT")
    else:
        print("🔧 STATUS: PERFECTION WORK NEEDED")

    return {
        "perfect_regions": perfect_regions,
        "imperfect_regions": imperfect_regions,
        "perfect_count": perfect_count,
        "total_count": total_count,
    }


if __name__ == "__main__":
    results = perfection_audit()
