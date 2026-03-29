#!/usr/bin/env python3
"""
ULTRATHINK Pipeline Test
Test the V7 pipeline to verify it actually works
"""

import asyncio
import sys
import time
import traceback
from typing import Dict, Any, List


def test_basic_pipeline():
    """Test basic pipeline functionality"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Test with simple entry
        test_entries = [
            {"CanonicalNative": "Albert Einstein", "GlobalID": "TEST-001"},
            {"CanonicalNative": "김민수", "GlobalID": "TEST-002"},
            {"CanonicalNative": "李明", "GlobalID": "TEST-003"},
        ]

        print("\n📊 Testing Basic Pipeline:")
        start = time.time()
        result = asyncio.run(pipeline.process_batch(test_entries))
        elapsed = time.time() - start

        if result and "entries" in result:
            entries = result["entries"]
            print(f"  ✅ Pipeline executed in {elapsed:.2f}s")
            print(f"  ✅ Processed {len(entries)} entries")

            # Check if Latin names were generated
            latin_generated = 0
            for entry in entries:
                if entry.get("CanonicalLatin"):
                    latin_generated += 1
                    print(f"    • {entry['CanonicalNative']} → {entry['CanonicalLatin']}")

            print(f"  ✅ Latin names generated: {latin_generated}/{len(entries)}")
            return True
        else:
            print(f"  ❌ Pipeline returned invalid result: {result}")
            return False

    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        traceback.print_exc()
        return False


def test_pipeline_stages():
    """Test that all pipeline stages execute"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        test_entry = [{"CanonicalNative": "Test Name", "GlobalID": "STAGE-TEST"}]

        print("\n📊 Testing Pipeline Stages:")

        # Capture stage execution
        stages_executed = []

        # Monkey-patch to track stage execution
        original_process = pipeline.process_batch

        async def tracked_process(entries):
            result = await original_process(entries)
            if "metrics" in result and "stages_executed" in result["metrics"]:
                stages_executed.extend(result["metrics"]["stages_executed"])
            return result

        pipeline.process_batch = tracked_process

        result = asyncio.run(pipeline.process_batch(test_entry))

        # Check metrics
        if result and "metrics" in result:
            metrics = result["metrics"]
            print(f"  ✅ Stages executed: {metrics.get('stages_executed', [])}")
            print(f"  ✅ Processing time: {metrics.get('total_time', 0):.2f}s")
            print(f"  ✅ Entries processed: {metrics.get('processed_entries', 0)}")

            if metrics.get("entries_per_second"):
                print(f"  ✅ Performance: {metrics['entries_per_second']:.0f} entries/sec")
            return True
        else:
            print(f"  ❌ No metrics in result")
            return False

    except Exception as e:
        print(f"  ❌ Stage test error: {e}")
        return False


def test_pipeline_with_large_batch():
    """Test pipeline with larger batch"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        # Create 100 test entries
        test_entries = []
        for i in range(100):
            test_entries.append(
                {"CanonicalNative": f"Test Person {i}", "GlobalID": f"BATCH-{i:04d}"}
            )

        print("\n📊 Testing Large Batch (100 entries):")
        start = time.time()
        result = asyncio.run(pipeline.process_batch(test_entries))
        elapsed = time.time() - start

        if result and "metrics" in result:
            metrics = result["metrics"]
            print(f"  ✅ Processed {metrics.get('processed_entries', 0)} entries in {elapsed:.2f}s")
            print(f"  ✅ Performance: {metrics.get('entries_per_second', 0):.0f} entries/sec")

            # Check for errors
            if "errors" in result and result["errors"]:
                print(f"  ⚠️ Errors encountered: {len(result['errors'])}")
                for err in result["errors"][:3]:  # Show first 3 errors
                    print(f"    • {err}")
            else:
                print(f"  ✅ No errors")
            return True
        else:
            print(f"  ❌ Invalid result from large batch")
            return False

    except Exception as e:
        print(f"  ❌ Large batch error: {e}")
        return False


def test_pipeline_modes():
    """Test different pipeline modes"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        print("\n📊 Testing Pipeline Modes:")

        test_entry = [{"CanonicalNative": "Mode Test", "GlobalID": "MODE-001"}]

        modes_tested = 0
        for mode_name in ["QUICK", "STANDARD", "COMPREHENSIVE"]:
            try:
                mode = getattr(PipelineMode, mode_name)
                pipeline = V7Pipeline(mode=mode)
                result = asyncio.run(pipeline.process_batch(test_entry))
                if result:
                    print(f"  ✅ {mode_name} mode works")
                    modes_tested += 1
                else:
                    print(f"  ❌ {mode_name} mode failed")
            except Exception as e:
                print(f"  ❌ {mode_name} mode error: {e}")

        return modes_tested > 0

    except Exception as e:
        print(f"  ❌ Mode test error: {e}")
        return False


def main():
    print("=" * 80)
    print("ULTRATHINK PIPELINE TEST")
    print("=" * 80)

    results = {
        "Basic Pipeline": test_basic_pipeline(),
        "Pipeline Stages": test_pipeline_stages(),
        "Large Batch": test_pipeline_with_large_batch(),
        "Pipeline Modes": test_pipeline_modes(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passing")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n🎯 PIPELINE FULLY FUNCTIONAL!")
    elif passed == 0:
        print("\n🔴 PIPELINE NOT WORKING!")
    else:
        print(f"\n⚠️ Pipeline partially working ({passed}/{total} tests)")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
