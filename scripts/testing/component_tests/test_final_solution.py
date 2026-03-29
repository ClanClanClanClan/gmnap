#!/usr/bin/env python3
"""
Test the final working solution with 1M benchmark
Following the expert solution methodology from gmnap_v7_final_working_solution_2025-09-25
"""

import asyncio
import os
import time
import json
from datetime import datetime

# Set environment variables as specified in the solution
os.environ["GMNAP_STREAMING"] = "1"
os.environ["GMNAP_CHUNK"] = "2000"
os.environ["GMNAP_INFLIGHT"] = "4"
os.environ["GMNAP_STREAM_THRESHOLD"] = "10000"
os.environ["GMNAP_RETRIES"] = "1"
os.environ["GMNAP_SECURITY_MODE"] = "testing"  # Allow international names during perf

from src.core.pipeline_v7 import V7Pipeline
from src.quality.gates import QualityGateRunner


async def warm_up():
    """Warm-up (eliminate small-batch artifacts)"""
    print("🔥 Running warm-up...")
    p = V7Pipeline()
    entries = [
        {"ID": "warm", "CanonicalNative": "John Smith", "Region": "a1_anglo_sphere"}
        for _ in range(128)
    ]
    await p.process_batch(entries)
    print("✅ Warm-up completed")


async def run_1m_validation():
    """Official 1M run (pass/fail gate)"""
    print("🚀 Starting 1M validation test...")

    # Generate 1M test entries
    print("📝 Generating 1M test entries...")
    entries = []
    patterns = [
        {"CanonicalNative": "John Smith", "Region": "a1_anglo_sphere"},
        {"CanonicalNative": "Kim Jung-eun", "Region": "e4_korea"},
        {"CanonicalNative": "Zhang Wei", "Region": "e1_sinophone_mainland"},
        {"CanonicalNative": "Ahmed Hassan", "Region": "c3_arabic_levant_nile"},
        {"CanonicalNative": "Jose Garcia", "Region": "g1_latin_america"},
    ]

    for i in range(1_000_000):
        pattern = patterns[i % len(patterns)]
        entry = {
            "ID": f"test_{i:08d}",
            "CanonicalNative": pattern["CanonicalNative"],
            "Region": pattern["Region"],
            "SourceDatabase": "test_db",
            "Year": 2020 + (i % 5),
        }
        entries.append(entry)

    print(f"✅ Generated {len(entries):,} entries")

    # Initialize quality gate runner
    q = QualityGateRunner(minutes_1m_max=35.0, min_success_rate=0.95)
    q.start(len(entries))

    # Initialize pipeline with streaming
    pipeline = V7Pipeline()

    print("⚡ Starting streaming processing...")
    start_time = time.perf_counter()

    # Use streaming method for 1M entries
    results = await pipeline.process_stream(entries, chunk=2000, inflight=4, retries=1)

    end_time = time.perf_counter()

    # Ingest results into quality gates
    q.ingest(results)

    # Get final decision
    decision = q.decision()

    # Calculate statistics
    duration = end_time - start_time
    entries_per_sec = len(entries) / duration
    minutes_1m = duration / 60.0  # Actual time for 1M

    # Count successful entries
    successful = sum(1 for r in results if r.get("status") != "processing_error")
    success_rate = successful / len(entries)

    # Results
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_entries": len(entries),
        "successful_entries": successful,
        "failed_entries": len(entries) - successful,
        "duration_seconds": duration,
        "duration_minutes": minutes_1m,
        "entries_per_second": entries_per_sec,
        "success_rate": success_rate,
        "quality_gate_decision": decision,
        "meets_targets": {
            "time_under_35_min": minutes_1m <= 35.0,
            "success_rate_over_95": success_rate >= 0.95,
            "entries_per_sec_over_476": entries_per_sec >= 476,
        },
    }

    # Print results
    print(f"\n📊 FINAL RESULTS")
    print("=" * 50)
    print(f"Total entries: {result['total_entries']:,}")
    print(f"Successful entries: {result['successful_entries']:,}")
    print(f"Success rate: {result['success_rate']:.1%}")
    print(f"Duration: {result['duration_minutes']:.1f} minutes")
    print(f"Throughput: {result['entries_per_second']:.0f} entries/sec")

    print(f"\n🎯 TARGET ASSESSMENT")
    print("=" * 50)
    print(
        f"⏱️  Time ≤35 min: {'✅ PASS' if result['meets_targets']['time_under_35_min'] else '❌ FAIL'} ({result['duration_minutes']:.1f} min)"
    )
    print(
        f"✅ Success ≥95%: {'✅ PASS' if result['meets_targets']['success_rate_over_95'] else '❌ FAIL'} ({result['success_rate']:.1%})"
    )
    print(
        f"⚡ Speed ≥476 e/s: {'✅ PASS' if result['meets_targets']['entries_per_sec_over_476'] else '❌ FAIL'} ({result['entries_per_sec']:.0f} e/s)"
    )

    # Overall assessment
    all_targets_met = all(result["meets_targets"].values())
    print(f"\n🏆 OVERALL: {'✅ ALL TARGETS MET' if all_targets_met else '❌ TARGETS NOT MET'}")

    if all_targets_met:
        print("🎉 System is PRODUCTION READY!")
    else:
        print("⚠️  System needs further optimization")
        if not result["meets_targets"]["time_under_35_min"]:
            print("   - Reduce GMNAP_CHUNK to 1500")
        if not result["meets_targets"]["success_rate_over_95"]:
            print("   - Check error patterns and authority status")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"final_solution_results_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n📄 Results saved to: {filename}")

    return result


async def main():
    """Main test function"""
    print("🚀 GMNAP V7 Final Working Solution Test")
    print("=" * 60)
    print("Environment configuration:")
    print(f"  GMNAP_STREAMING={os.getenv('GMNAP_STREAMING')}")
    print(f"  GMNAP_CHUNK={os.getenv('GMNAP_CHUNK')}")
    print(f"  GMNAP_INFLIGHT={os.getenv('GMNAP_INFLIGHT')}")
    print(f"  GMNAP_SECURITY_MODE={os.getenv('GMNAP_SECURITY_MODE')}")
    print("=" * 60)

    try:
        # Step 1: Warm-up
        await warm_up()

        # Step 2: Official 1M run
        result = await run_1m_validation()

        return result

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(main())
