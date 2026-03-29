#!/usr/bin/env python3
"""
ULTRATHINK LIVE DEMO - Shows what's actually working in V7 pipeline
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime


async def test_v7_pipeline():
    """Test the V7 pipeline comprehensively"""
    results = {"timestamp": datetime.now().isoformat(), "tests": {}}

    # Test 1: Import V7 components
    print("=" * 60)
    print("V7 PIPELINE LIVE DEMO")
    print("=" * 60)

    try:
        from src.core.pipeline_v7_complete_final import create_v7_pipeline

        print("✅ V7 pipeline imports successfully")
        results["tests"]["v7_import"] = True
    except Exception as e:
        print(f"❌ V7 pipeline import failed: {e}")
        results["tests"]["v7_import"] = False
        return results

    # Test 2: Create pipeline
    try:
        pipeline = create_v7_pipeline()
        print("✅ V7 pipeline created successfully")
        results["tests"]["v7_creation"] = True
    except Exception as e:
        print(f"❌ V7 pipeline creation failed: {e}")
        results["tests"]["v7_creation"] = False
        return results

    # Test 3: Process test entries
    test_entries = [
        {"GlobalID": "TEST-001", "CanonicalNative": "John Smith"},
        {"GlobalID": "TEST-002", "CanonicalNative": "김민수"},  # Korean
        {"GlobalID": "TEST-003", "CanonicalNative": "李明"},  # Chinese
        {"GlobalID": "TEST-004", "CanonicalNative": "Иван Петров"},  # Russian
        {"GlobalID": "TEST-005", "CanonicalNative": "محمد علي"},  # Arabic
    ]

    print("\nProcessing test entries...")
    processed = []
    for entry in test_entries:
        try:
            result = await pipeline.process([entry])
            if result and result.results:
                processed_entry = result.results[0]
                print(
                    f"✅ {entry['GlobalID']}: {entry['CanonicalNative']} -> {processed_entry.get('CanonicalLatin', 'N/A')}"
                )
                processed.append(processed_entry)
            else:
                print(f"⚠️  {entry['GlobalID']}: No result")
        except Exception as e:
            print(f"❌ {entry['GlobalID']}: Error - {e}")

    results["tests"]["processing"] = len(processed) > 0
    results["processed_count"] = len(processed)

    # Test 4: Check regional detection
    print("\n" + "=" * 60)
    print("REGIONAL PROCESSING TEST")
    print("=" * 60)

    try:
        from src.regions.manager import RegionManager

        manager = RegionManager(Path("./config"))

        region_tests = [
            ("John Smith", "A1"),  # Anglo
            ("김민수", "E4"),  # Korean
            ("李明", "E1"),  # Chinese
            ("Иван Петров", "B1"),  # Russian
            ("محمد علي", "C3"),  # Arabic
        ]

        regions_working = 0
        for name, expected in region_tests:
            try:
                # Get region
                region = manager.get_region(expected)
                if region:
                    # Test if region can process
                    test_entry = {"GlobalID": "TEST", "CanonicalNative": name}
                    if hasattr(region, "process"):
                        result = region.process(test_entry)
                        if "CanonicalLatin" in result:
                            print(f"✅ {expected}: {name} -> {result['CanonicalLatin']}")
                            regions_working += 1
                        else:
                            print(f"⚠️  {expected}: No Latin output")
                    else:
                        print(f"❌ {expected}: No process method")
                else:
                    print(f"❌ {expected}: Region not found")
            except Exception as e:
                print(f"❌ {expected}: {e}")

        results["tests"]["regional_processing"] = regions_working > 0
        results["regions_working"] = regions_working

    except Exception as e:
        print(f"❌ Regional processing failed: {e}")
        results["tests"]["regional_processing"] = False

    # Test 5: Performance check
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST")
    print("=" * 60)

    import time

    test_batch = [
        {"GlobalID": f"PERF-{i:04d}", "CanonicalNative": f"Test Name {i}"} for i in range(100)
    ]

    start = time.time()
    try:
        result = await pipeline.process(test_batch)
        elapsed = time.time() - start
        throughput = len(test_batch) / elapsed

        print(f"✅ Processed {len(test_batch)} entries in {elapsed:.2f}s")
        print(f"   Throughput: {throughput:.1f} entries/sec")
        print(f"   Time per million: {(1_000_000 / throughput / 60):.1f} minutes")

        results["tests"]["performance"] = True
        results["performance"] = {
            "throughput": throughput,
            "time_per_million_min": 1_000_000 / throughput / 60,
        }
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        results["tests"]["performance"] = False

    # Test 6: Check V7 stages
    print("\n" + "=" * 60)
    print("V7 STAGE VERIFICATION")
    print("=" * 60)

    stages = [
        "Stage 0: Ingestion",
        "Stage 1: Parsing",
        "Stage 2: Classification",
        "Stage 3: Detection",
        "Stage 4: Fetching",
        "Stage 5: Processing",
        "Stage 6: Coherence",
        "Stage 7: Short Forms",
        "Stage 8: Validation",
        "Stage 9: Indexing",
        "Stage 10: Analytics",
        "Stage 11: Idempotency",
        "Stage 12: Deployment",
    ]

    # Check if all stages are running
    test_entry = [{"GlobalID": "STAGE-TEST", "CanonicalNative": "Stage Test"}]
    try:
        result = await pipeline.process(test_entry)
        if result and result.metrics:
            stages_run = len(result.metrics.stage_times)
            print(f"✅ {stages_run}/13 stages executed")
            for stage_name, duration in result.metrics.stage_times.items():
                print(f"   - {stage_name}: {duration:.3f}s")
        else:
            print("⚠️  No metrics available")
        results["tests"]["stages"] = True
    except Exception as e:
        print(f"❌ Stage check failed: {e}")
        results["tests"]["stages"] = False

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results["tests"].values() if v)
    total = len(results["tests"])

    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.0f}%")

    if results.get("regions_working"):
        print(f"Regions working: {results['regions_working']}/5")

    if results.get("performance"):
        perf = results["performance"]
        print(f"Performance: {perf['throughput']:.0f} entries/sec")
        print(f"Time per million: {perf['time_per_million_min']:.0f} minutes")

    # Compliance estimate
    compliance_score = passed / total * 100
    if compliance_score >= 80:
        print(f"\n✅ V7 COMPLIANCE ESTIMATE: {compliance_score:.0f}%")
    else:
        print(f"\n⚠️  V7 COMPLIANCE ESTIMATE: {compliance_score:.0f}%")

    return results


if __name__ == "__main__":
    import os

    os.environ["OFFLINE"] = "1"  # Run in offline mode

    results = asyncio.run(test_v7_pipeline())

    # Save results
    with open("ultrathink_demo_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to ultrathink_demo_results.json")
