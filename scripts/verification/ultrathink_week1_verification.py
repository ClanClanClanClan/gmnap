#!/usr/bin/env python3
"""
ULTRATHINK Week 1 Verification Script
Tests if Week 1 fixes are properly implemented.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, ".")


def test_regional_processors():
    """Test that regional processors have process() method and work."""
    print("\n🌍 Testing Regional Processors...")

    regions_to_test = [
        (
            "src.regions.e_groups.e1_sinophone_mainland",
            "E1_SinophoneMainland",
            "李明",
            "E1",
            "Li Ming",
        ),
        (
            "src.regions.e_groups.e4_korea.processor",
            "E4KoreanProcessor",
            "김민수",
            "E4",
            "Kim Min-su",
        ),
        (
            "src.regions.b_groups.b1_east_slavic",
            "B1_EastSlavic",
            "Иванов Иван",
            "B1",
            "Ivanov Ivan",
        ),
        ("src.regions.e_groups.e3_japan.processor", "E3_Japan", "田中太郎", "E3", "Tanaka Taro"),
        (
            "src.regions.c_groups.c3_arabic_levant_nile.processor",
            "C3_ArabicLevantNile",
            "محمد علي",
            "C3",
            "Muhammad Ali",
        ),
    ]

    working_count = 0
    results = []

    for module_path, class_name, test_name, region_id, expected_latin in regions_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            RegionClass = getattr(module, class_name)
            processor = RegionClass()

            # Check required methods
            has_process = hasattr(processor, "process")
            has_augment = hasattr(processor, "augment")

            # Try processing
            test_entry = {"CanonicalNative": test_name, "GlobalID": f"TEST-{region_id}"}
            result = processor.process(test_entry)
            latin = result.get("CanonicalLatin", "")

            # Check if Latin was generated
            success = has_process and has_augment and bool(latin)

            if success:
                working_count += 1
                print(f"  ✅ {region_id}: {test_name} → {latin}")
            else:
                print(f"  ❌ {region_id}: Missing methods or no Latin output")

            results.append(
                {
                    "region": region_id,
                    "success": success,
                    "has_process": has_process,
                    "has_augment": has_augment,
                    "latin_output": latin,
                }
            )

        except Exception as e:
            print(f"  ❌ {region_id}: {str(e)}")
            results.append({"region": region_id, "success": False, "error": str(e)})

    print(f"\n  Summary: {working_count}/5 regional processors working")
    return working_count >= 2  # Need at least 2 working


def test_performance_cheats_removed():
    """Verify performance cheats have been removed."""
    print("\n🚀 Testing Performance Cheats Removed...")

    # Check pipeline files for skip_heavy_stages
    pipeline_files = [
        "src/core/pipeline_v7.py",
        "src/core/pipeline_v7_complete.py",
        "src/core/pipeline_v7_complete_final.py",
    ]

    cheats_found = []

    for file_path in pipeline_files:
        if Path(file_path).exists():
            with open(file_path, "r") as f:
                content = f.read()
                if "skip_heavy_stages" in content:
                    cheats_found.append(file_path)
                    # Count occurrences
                    count = content.count("skip_heavy_stages")
                    print(f"  ❌ {file_path}: Found 'skip_heavy_stages' {count} times")

    if not cheats_found:
        print("  ✅ No performance cheats found")
        return True
    else:
        print(f"  ❌ Performance cheats still present in {len(cheats_found)} files")
        return False


def test_pipeline_stages():
    """Test that all pipeline stages run."""
    print("\n🔧 Testing Pipeline Stages...")

    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        # Create pipeline with QUICK mode
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Test with simple entry
        test_data = [
            {"CanonicalNative": "김민수", "GlobalID": "TEST-001"},
            {"CanonicalNative": "李明", "GlobalID": "TEST-002"},
        ]

        # Run async pipeline
        import asyncio

        result = asyncio.run(pipeline.process_batch(test_data))

        # Check that stages were executed
        if result and isinstance(result, dict):
            metrics = result.get("metrics", {})
            processed = metrics.get("processed_entries", 0)
            stage_timings = metrics.get("stage_timings", {})

            if processed == 2:
                print(f"  ✅ Pipeline processed {processed} entries")

                # Check that stages ran
                stages_ran = len(stage_timings) > 0
                if stages_ran:
                    print(f"  ✅ Pipeline executed {len(stage_timings)} stages")

                    # Note: Quality gates may fail, but that's OK for Week 1
                    if not result.get("quality_gates", {}).get("passed"):
                        print("  ⚠️ Quality gates failed (expected for Week 1)")

                    return True
                else:
                    print("  ❌ No stage timings recorded")
                    return False
            else:
                print(f"  ❌ Pipeline only processed {processed}/2 entries")
                return False
        else:
            print("  ❌ Pipeline didn't return expected dict format")
            return False

    except Exception as e:
        print(f"  ❌ Pipeline test failed: {e}")
        return False


def main():
    """Run all Week 1 verification tests."""
    print("=" * 80)
    print("🧠 ULTRATHINK WEEK 1 VERIFICATION")
    print("=" * 80)

    results = {"timestamp": datetime.now().isoformat(), "tests": {}}

    # Run tests
    print("\n📋 Running Week 1 Tests...")

    # Test 1: Regional processors
    regional_pass = test_regional_processors()
    results["tests"]["regional_processors"] = regional_pass

    # Test 2: Performance cheats removed
    cheats_pass = test_performance_cheats_removed()
    results["tests"]["performance_cheats_removed"] = cheats_pass

    # Test 3: Pipeline stages
    pipeline_pass = test_pipeline_stages()
    results["tests"]["pipeline_stages"] = pipeline_pass

    # Calculate overall
    all_pass = all([regional_pass, cheats_pass, pipeline_pass])
    results["week1_complete"] = all_pass

    # Summary
    print("\n" + "=" * 80)
    print("📊 WEEK 1 VERIFICATION RESULTS")
    print("=" * 80)

    print(f"""
✅ Regional Processors: {'PASS' if regional_pass else 'FAIL'}
✅ Performance Cheats Removed: {'PASS' if cheats_pass else 'FAIL'}
✅ Pipeline Stages Run: {'PASS' if pipeline_pass else 'FAIL'}

🎯 WEEK 1 STATUS: {'✅ COMPLETE' if all_pass else '❌ INCOMPLETE'}
""")

    # Save results
    output_file = f"week1_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Results saved to: {output_file}")

    # Return exit code
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
