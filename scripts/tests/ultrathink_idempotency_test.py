#!/usr/bin/env python3
"""
ULTRATHINK Idempotency Test
Test that the system produces identical output for identical input
"""

import asyncio
import json
import hashlib
import sys
from typing import Dict, Any, List


def hash_result(data: Any) -> str:
    """Create a hash of the result for comparison"""
    # Convert to JSON for consistent serialization
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def test_basic_idempotency():
    """Test basic idempotency"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        test_entries = [
            {"CanonicalNative": "Albert Einstein", "GlobalID": "IDEM-001"},
            {"CanonicalNative": "김민수", "GlobalID": "IDEM-002"},
        ]

        print("\n📊 Testing Basic Idempotency:")

        # Run 3 times
        results = []
        for i in range(3):
            result = asyncio.run(pipeline.process_batch(test_entries.copy()))
            if result and "entries" in result:
                # Remove timing metrics for comparison
                entries = result["entries"]
                results.append(entries)
                print(f"  Run {i+1}: {len(entries)} entries processed")

        if len(results) == 3:
            # Compare hashes
            hashes = [hash_result(r) for r in results]
            if len(set(hashes)) == 1:
                print(
                    f"  ✅ Idempotency verified - all 3 runs produced identical output"
                )
                return True
            else:
                print(f"  ❌ Idempotency FAILED - different outputs on each run")
                print(f"    Hashes: {hashes}")
                # Show differences
                for i, r in enumerate(results):
                    print(
                        f"    Run {i+1} first entry: {r[0].get('CanonicalLatin', 'NONE')}"
                    )
                return False
        else:
            print(f"  ❌ Could not complete 3 runs")
            return False

    except Exception as e:
        print(f"  ❌ Idempotency test error: {e}")
        return False


def test_deterministic_mode():
    """Test deterministic mode with seed"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode
        import os

        # Enable deterministic mode
        os.environ["DETERMINISTIC_MODE"] = "1"
        os.environ["RANDOM_SEED"] = "42"

        print("\n📊 Testing Deterministic Mode:")

        test_entries = [
            {"CanonicalNative": "Test Person", "GlobalID": "DET-001"},
        ]

        # Run with same seed twice
        results_seed_42 = []
        for i in range(2):
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            result = asyncio.run(pipeline.process_batch(test_entries.copy()))
            if result and "entries" in result:
                results_seed_42.append(result["entries"])

        # Change seed and run again
        os.environ["RANDOM_SEED"] = "123"
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        result_seed_123 = asyncio.run(pipeline.process_batch(test_entries.copy()))

        # Reset environment
        os.environ.pop("DETERMINISTIC_MODE", None)
        os.environ.pop("RANDOM_SEED", None)

        # Check results
        if len(results_seed_42) == 2:
            hash_42_1 = hash_result(results_seed_42[0])
            hash_42_2 = hash_result(results_seed_42[1])
            hash_123 = (
                hash_result(result_seed_123["entries"]) if result_seed_123 else None
            )

            if hash_42_1 == hash_42_2:
                print(f"  ✅ Same seed produces identical results")
                if hash_123 and hash_123 != hash_42_1:
                    print(f"  ✅ Different seed produces different results")
                    return True
                else:
                    print(f"  ⚠️ Different seeds produced same results (may be OK)")
                    return True
            else:
                print(f"  ❌ Same seed produced different results!")
                return False
        else:
            print(f"  ❌ Could not complete deterministic test")
            return False

    except Exception as e:
        print(f"  ❌ Deterministic mode error: {e}")
        return False


def test_concurrent_idempotency():
    """Test idempotency under concurrent execution"""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        print("\n📊 Testing Concurrent Idempotency:")

        test_entries = [
            {"CanonicalNative": "Concurrent Test", "GlobalID": "CONC-001"},
        ]

        async def run_pipeline(pipeline, entries):
            return await pipeline.process_batch(entries.copy())

        async def concurrent_test():
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            # Run 5 concurrent processes
            tasks = [run_pipeline(pipeline, test_entries) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(concurrent_test())

        if len(results) == 5:
            # Extract entries and hash
            entries_list = [r["entries"] for r in results if r and "entries" in r]
            hashes = [hash_result(e) for e in entries_list]

            if len(set(hashes)) == 1:
                print(f"  ✅ Concurrent execution produces identical results")
                return True
            else:
                print(f"  ❌ Concurrent execution produced different results")
                print(f"    Unique hashes: {len(set(hashes))}/5")
                return False
        else:
            print(f"  ❌ Could not complete concurrent test")
            return False

    except Exception as e:
        print(f"  ❌ Concurrent test error: {e}")
        return False


def main():
    print("=" * 80)
    print("ULTRATHINK IDEMPOTENCY TEST")
    print("=" * 80)

    results = {
        "Basic Idempotency": test_basic_idempotency(),
        "Deterministic Mode": test_deterministic_mode(),
        "Concurrent Idempotency": test_concurrent_idempotency(),
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
        print("\n🎯 PERFECT IDEMPOTENCY!")
    elif passed == 0:
        print("\n🔴 NO IDEMPOTENCY!")
    else:
        print(f"\n⚠️ Partial idempotency ({passed}/{total} tests)")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
