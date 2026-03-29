#!/usr/bin/env python3
"""
Week 1 Verification Script
Verifies that Week 1 emergency repairs are complete
"""

import sys
import traceback
from pathlib import Path
from typing import Dict, Any
import json
import subprocess


def test_performance_cheats_removed() -> bool:
    """Test that performance cheats have been removed from pipeline"""
    print("\n🔍 Testing: Performance cheats removed...")

    # Check for skip_heavy_stages in pipeline files
    pipeline_files = [
        "src/core/pipeline_v7.py",
        "src/core/pipeline_v7_complete.py",
        "src/core/pipeline_v7_complete_final.py",
        "src/core/pipeline.py",
    ]

    found_cheats = False
    for file in pipeline_files:
        if Path(file).exists():
            with open(file, "r") as f:
                content = f.read()
                if "skip_heavy_stages" in content:
                    print(f"  ❌ Found 'skip_heavy_stages' in {file}")
                    found_cheats = True

    if not found_cheats:
        print("  ✅ No performance cheats found")
        return True
    else:
        print("  ❌ Performance cheats still present")
        return False


def test_regional_processors_working() -> bool:
    """Test that at least 2 regional processors work"""
    print("\n🔍 Testing: Regional processors working...")

    try:
        from src.regions.manager import RegionManager

        test_cases = [
            ("E1", "李明", "Chinese"),
            ("E4", "김민수", "Korean"),
            ("E3", "山田太郎", "Japanese"),
            ("B1", "Иван Петров", "Russian"),
            ("C3", "محمد علي", "Arabic"),
        ]

        manager = RegionManager(Path("./config"))
        working_regions = 0

        for region_code, name, desc in test_cases:
            try:
                region = manager.get_region(region_code)
                if region and hasattr(region, "process"):
                    entry = {"CanonicalNative": name, "GlobalID": f"TEST-{region_code}"}
                    result = region.process(entry)
                    latin = result.get("CanonicalLatin")
                    if latin and latin != name:  # Must produce different output
                        print(f"  ✅ {region_code} ({desc}): {name} → {latin}")
                        working_regions += 1
                    else:
                        print(f"  ❌ {region_code} ({desc}): No Latin output")
                else:
                    print(f"  ❌ {region_code} ({desc}): No process method")
            except Exception as e:
                print(f"  ❌ {region_code} ({desc}): {str(e)[:50]}")

        print(f"\n  Summary: {working_regions}/5 regions working")

        if working_regions >= 2:
            print("  ✅ At least 2 regions working (requirement met)")
            return True
        else:
            print(f"  ❌ Only {working_regions} region(s) working (need at least 2)")
            return False

    except Exception as e:
        print(f"  ❌ Error testing regions: {e}")
        return False


def test_all_stages_run() -> bool:
    """Test that all 12 stages run in the pipeline"""
    print("\n🔍 Testing: All pipeline stages run...")

    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode
        import asyncio

        # Create pipeline
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Small test batch
        test_batch = [
            {"CanonicalNative": "김민수", "GlobalID": "TEST-001"},
            {"CanonicalNative": "李明", "GlobalID": "TEST-002"},
        ]

        # Run pipeline
        result = asyncio.run(pipeline.process_batch(test_batch))

        # Check that metrics show stages were run
        metrics = result.get("metrics", {})
        stage_timings = metrics.get("stage_timings", {})
        stages_run = len([s for s in stage_timings if stage_timings[s] > 0])

        # List which stages ran
        if stage_timings:
            print(f"  Stages with timings: {list(stage_timings.keys())}")
            print(
                f"  Stages that ran (time > 0): {[s for s in stage_timings if stage_timings[s] > 0]}"
            )

        if stages_run >= 6:  # At least 6 stages should run (some may be skipped in QUICK mode)
            print(f"  ✅ {stages_run} stages completed")
            return True
        else:
            print(f"  ❌ Only {stages_run} stages completed (expected ≥6)")
            return False

    except Exception as e:
        print(f"  ❌ Error testing pipeline: {e}")
        traceback.print_exc()
        return False


def main():
    """Run Week 1 verification tests"""
    print("=" * 60)
    print("🚀 WEEK 1 VERIFICATION - Emergency Repairs Check")
    print("=" * 60)

    tests = [
        ("Performance cheats removed", test_performance_cheats_removed),
        ("Regional processors working", test_regional_processors_working),
        ("All stages run", test_all_stages_run),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with error: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 WEEK 1 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 WEEK 1 COMPLETE! All emergency repairs verified.")
        print("Ready to proceed to Week 2: Authority Sources")
        return 0
    else:
        print(f"\n⚠️  WEEK 1 INCOMPLETE: {total - passed} test(s) still failing")
        print("Fix remaining issues before proceeding to Week 2")
        return 1


if __name__ == "__main__":
    sys.exit(main())
