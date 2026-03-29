#!/usr/bin/env python3
"""
Week 1 Verification Script for ULTRATHINK V7 Reconstruction Plan

Checks:
1. Regional processors have process() method
2. At least 2 regions working
3. Performance cheats removed
4. All pipeline stages execute
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

print("\n" + "=" * 80)
print("🔍 WEEK 1 VERIFICATION - ULTRATHINK V7 RECONSTRUCTION")
print("=" * 80)


def check_regional_processors() -> Tuple[bool, str]:
    """Check if regional processors have process() method."""
    print("\n📍 Checking Regional Processors...")

    try:
        from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor
        from src.regions.e_groups.e1_sinophone_mainland import E1_SinophoneMainland
        from src.regions.b_groups.b1_east_slavic import B1_EastSlavic

        working_regions = []

        # Test E4 Korean
        try:
            e4 = E4KoreanProcessor()
            if hasattr(e4, "process"):
                test_entry = {"CanonicalNative": "김민수", "GlobalID": "TEST-001"}
                result = e4.process(test_entry)
                if result.get("CanonicalLatin"):
                    working_regions.append("E4 Korean")
                    print(
                        f"  ✅ E4 Korean: {test_entry['CanonicalNative']} → {result.get('CanonicalLatin')}"
                    )
                else:
                    print(f"  ⚠️ E4 Korean has process() but no output")
            else:
                print(f"  ❌ E4 Korean missing process() method")
        except Exception as e:
            print(f"  ❌ E4 Korean error: {e}")

        # Test E1 Chinese
        try:
            e1 = E1_SinophoneMainland()
            if hasattr(e1, "process"):
                test_entry = {"CanonicalNative": "李明", "GlobalID": "TEST-002"}
                result = e1.process(test_entry)
                if result.get("CanonicalLatin"):
                    working_regions.append("E1 Chinese")
                    print(
                        f"  ✅ E1 Chinese: {test_entry['CanonicalNative']} → {result.get('CanonicalLatin')}"
                    )
                else:
                    print(f"  ⚠️ E1 Chinese has process() but no output")
            else:
                print(f"  ❌ E1 Chinese missing process() method")
        except Exception as e:
            print(f"  ❌ E1 Chinese error: {e}")

        # Test B1 Russian
        try:
            b1 = B1_EastSlavic()
            if hasattr(b1, "process"):
                test_entry = {"CanonicalNative": "Иванов Иван", "GlobalID": "TEST-003"}
                result = b1.process(test_entry)
                if result.get("CanonicalLatin"):
                    working_regions.append("B1 Russian")
                    print(
                        f"  ✅ B1 Russian: {test_entry['CanonicalNative']} → {result.get('CanonicalLatin')}"
                    )
                else:
                    print(f"  ⚠️ B1 Russian has process() but no output")
            else:
                print(f"  ❌ B1 Russian missing process() method")
        except Exception as e:
            print(f"  ❌ B1 Russian error: {e}")

        success = len(working_regions) >= 2
        message = f"Working regions: {len(working_regions)}/3 ({', '.join(working_regions)})"

        if success:
            print(f"\n  ✅ PASS: {message}")
        else:
            print(f"\n  ❌ FAIL: {message} (need at least 2)")

        return success, message

    except Exception as e:
        return False, f"Import error: {e}"


def check_performance_cheats() -> Tuple[bool, str]:
    """Check if performance cheats have been removed."""
    print("\n⚡ Checking Performance Cheats Removed...")

    try:
        # Check for skip_heavy_stages in pipeline files
        pipeline_files = [
            "src/core/pipeline_v7.py",
            "src/core/pipeline_v7_complete_final.py",
            "src/core/pipeline_v7_complete.py",
        ]

        cheats_found = []
        for file_path in pipeline_files:
            if Path(file_path).exists():
                content = Path(file_path).read_text()
                if "skip_heavy_stages" in content:
                    cheats_found.append(file_path)

        if cheats_found:
            message = f"Performance cheats found in: {', '.join(cheats_found)}"
            print(f"  ❌ FAIL: {message}")
            return False, message
        else:
            print("  ✅ PASS: No performance cheats found")
            return True, "No skip_heavy_stages found"

    except Exception as e:
        return False, f"Error checking: {e}"


def check_pipeline_stages() -> Tuple[bool, str]:
    """Check if all pipeline stages execute."""
    print("\n🔄 Checking Pipeline Stages...")

    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode
        import asyncio

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        test_entries = [
            {"CanonicalNative": "Test Name", "GlobalID": "TEST-001"},
            {"CanonicalNative": "김민수", "GlobalID": "TEST-002"},
        ]

        result = asyncio.run(pipeline.process_batch(test_entries))

        if result and result.get("metrics"):
            metrics = result["metrics"]
            stage_timings = metrics.get("stage_timings", {})

            expected_stages = [
                "stage_1",
                "stage_2",
                "stage_3",
                "stage_4",
                "stage_5",
                "stage_6",
                "stage_7",
                "stage_8",
            ]

            executed_stages = list(stage_timings.keys())
            missing_stages = [s for s in expected_stages if s not in executed_stages]

            if not missing_stages:
                print(f"  ✅ PASS: All {len(expected_stages)} stages executed")
                return True, f"All {len(expected_stages)} stages executed"
            else:
                message = f"Missing stages: {', '.join(missing_stages)}"
                print(f"  ⚠️ PARTIAL: {message}")
                return False, message
        else:
            return False, "Pipeline didn't return metrics"

    except Exception as e:
        return False, f"Pipeline error: {e}"


def main():
    """Run all Week 1 verification checks."""

    results = {
        "timestamp": datetime.now().isoformat(),
        "week": 1,
        "checks": {},
        "overall_pass": False,
    }

    # Run checks
    checks = [
        ("regional_processors", check_regional_processors),
        ("performance_cheats", check_performance_cheats),
        ("pipeline_stages", check_pipeline_stages),
    ]

    passed_count = 0
    for check_name, check_func in checks:
        passed, message = check_func()
        results["checks"][check_name] = {"passed": passed, "message": message}
        if passed:
            passed_count += 1

    # Overall result
    results["overall_pass"] = passed_count == len(checks)
    results["score"] = f"{passed_count}/{len(checks)}"

    # Summary
    print("\n" + "=" * 80)
    print("📊 WEEK 1 VERIFICATION SUMMARY")
    print("=" * 80)

    for check_name, check_result in results["checks"].items():
        status = "✅" if check_result["passed"] else "❌"
        print(f"{status} {check_name}: {check_result['message']}")

    print(f"\n🎯 Overall Score: {results['score']}")

    if results["overall_pass"]:
        print("✅ WEEK 1 COMPLETE! Ready for Week 2.")
    else:
        print("❌ WEEK 1 INCOMPLETE. Fix remaining issues before proceeding.")

    # Save results
    results_file = f"week1_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Results saved to: {results_file}")

    return 0 if results["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
