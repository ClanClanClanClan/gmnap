#!/usr/bin/env python3
"""
ULTRATHINK Production Validation Test - FIXED VERSION
Date: 2025-09-15
Goal: Validate GMNAP v7 for production readiness
"""

import asyncio
import time
import tracemalloc
import json
from datetime import datetime
from collections import Counter
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, "src")

from src.core.pipeline_v7 import V7Pipeline, PipelineMode


def generate_test_data(size: int) -> list:
    """Generate diverse test data with unique GlobalIDs."""
    entries = []

    # Mix of different regions
    test_names = [
        # Korean (E4)
        ("김민수", "KR"),
        ("박지성", "KR"),
        ("이순신", "KR"),
        # Chinese (E1)
        ("李明", "CN"),
        ("王伟", "CN"),
        ("张静", "CN"),
        # Russian (B1)
        ("Иванов Иван", "RU"),
        ("Петров Петр", "RU"),
        # Japanese (E3)
        ("山田太郎", "JP"),
        ("佐藤花子", "JP"),
        # Arabic (C3)
        ("محمد علي", "EG"),
        ("أحمد حسن", "SA"),
        # English (A1)
        ("John Smith", "US"),
        ("Mary Johnson", "GB"),
        # Spanish (G1)
        ("Juan García", "ES"),
        ("María López", "MX"),
    ]

    # Generate entries with unique GlobalIDs
    for i in range(size):
        name, country = test_names[i % len(test_names)]
        entries.append(
            {
                "CanonicalNative": name,
                "GlobalID": f"PROD-TEST-{i:08d}",  # Guaranteed unique
                "Country": country,
                "SourceID": f"SRC-{i:06d}",
            }
        )

    return entries


async def test_performance(batch_sizes: list) -> dict:
    """Test performance with different batch sizes."""
    results = {}

    for size in batch_sizes:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing with {size} entries...")
        logger.info(f"{'='*60}")

        # Generate test data
        entries = generate_test_data(size)

        # Check for duplicates in input
        gids = [e["GlobalID"] for e in entries]
        input_duplicates = len([k for k, v in Counter(gids).items() if v > 1])

        # Start memory tracking
        tracemalloc.start()

        # Run pipeline
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        start_time = time.time()

        try:
            result = await pipeline.process_batch(entries)
            elapsed = time.time() - start_time

            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Calculate metrics
            entries_per_sec = size / elapsed if elapsed > 0 else 0
            projected_1m_time = (
                (1_000_000 / entries_per_sec / 60) if entries_per_sec > 0 else float("inf")
            )

            results[size] = {
                "entries": size,
                "elapsed_seconds": elapsed,
                "entries_per_second": entries_per_sec,
                "projected_1m_minutes": projected_1m_time,
                "memory_peak_mb": peak / 1024 / 1024,
                "input_duplicates": input_duplicates,
                "processed_entries": result["metrics"]["processed_entries"],
                "status": "SUCCESS",
            }

            logger.info(f"✅ Processed {size} entries in {elapsed:.2f}s")
            logger.info(f"   Performance: {entries_per_sec:.0f} entries/sec")
            logger.info(f"   Projected 1M time: {projected_1m_time:.1f} minutes")
            logger.info(f"   Peak memory: {peak/1024/1024:.1f} MB")

        except Exception as e:
            logger.error(f"❌ Failed to process {size} entries: {e}")
            results[size] = {"entries": size, "status": "FAILED", "error": str(e)}

    return results


async def test_regions() -> dict:
    """Test all regional processors."""
    logger.info(f"\n{'='*60}")
    logger.info("Testing Regional Processors...")
    logger.info(f"{'='*60}")

    test_cases = [
        {"CanonicalNative": "김민수", "GlobalID": "REGION-001", "expected_region": "E4"},
        {"CanonicalNative": "李明", "GlobalID": "REGION-002", "expected_region": "E1"},
        {"CanonicalNative": "Иванов Иван", "GlobalID": "REGION-003", "expected_region": "B1"},
        {"CanonicalNative": "山田太郎", "GlobalID": "REGION-004", "expected_region": "E3"},
        {"CanonicalNative": "محمد علي", "GlobalID": "REGION-005", "expected_region": "C3"},
    ]

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    result = await pipeline.process_batch(test_cases)

    regional_results = {}
    for i, entry in enumerate(result.get("entries", [])):
        native = test_cases[i]["CanonicalNative"]
        latin = entry.get("CanonicalLatin", "ERROR")
        expected = test_cases[i]["expected_region"]
        detected = entry.get("DetectedRegion", "UNKNOWN")

        regional_results[expected] = {
            "native": native,
            "latin": latin,
            "detected": detected,
            "success": latin != "ERROR" and latin != native,
        }

        status = "✅" if regional_results[expected]["success"] else "❌"
        logger.info(f"{status} {expected}: {native} → {latin}")

    return regional_results


async def test_quality_gates() -> dict:
    """Test quality gate enforcement."""
    logger.info(f"\n{'='*60}")
    logger.info("Testing Quality Gates...")
    logger.info(f"{'='*60}")

    # Test with intentional duplicates
    entries = [
        {"CanonicalNative": "Test Name 1", "GlobalID": "DUP-001"},
        {"CanonicalNative": "Test Name 2", "GlobalID": "DUP-001"},  # Duplicate!
        {"CanonicalNative": "Test Name 3", "GlobalID": "DUP-002"},
    ]

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)

    try:
        result = await pipeline.process_batch(entries)
        # Check if duplicates were handled
        processed_gids = [e.get("GlobalID") for e in result.get("entries", [])]
        unique_gids = len(set(processed_gids))

        return {
            "input_entries": len(entries),
            "unique_input_ids": len(set(e["GlobalID"] for e in entries)),
            "processed_entries": len(processed_gids),
            "unique_processed_ids": unique_gids,
            "duplicates_handled": unique_gids == len(processed_gids),
        }
    except Exception as e:
        return {"error": str(e)}


async def main():
    """Run all production validation tests."""
    logger.info("=" * 60)
    logger.info("ULTRATHINK PRODUCTION VALIDATION")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = {"timestamp": datetime.now().isoformat(), "tests": {}}

    # Test 1: Performance at different scales
    logger.info("\n📊 Test 1: Performance Scaling")
    perf_results = await test_performance([10, 100, 1000])
    results["tests"]["performance"] = perf_results

    # Test 2: Regional processors
    logger.info("\n🌍 Test 2: Regional Processing")
    regional_results = await test_regions()
    results["tests"]["regions"] = regional_results

    # Test 3: Quality gates
    logger.info("\n✅ Test 3: Quality Gates")
    quality_results = await test_quality_gates()
    results["tests"]["quality_gates"] = quality_results

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("VALIDATION SUMMARY")
    logger.info(f"{'='*60}")

    # Performance summary
    if 1000 in perf_results and perf_results[1000]["status"] == "SUCCESS":
        perf = perf_results[1000]
        target_met = perf["projected_1m_minutes"] < 35
        status = "✅" if target_met else "❌"
        logger.info(f"{status} Performance: {perf['entries_per_second']:.0f} entries/sec")
        logger.info(f"   Projected 1M: {perf['projected_1m_minutes']:.1f} min (target: <35 min)")

    # Regional summary
    regions_working = sum(1 for r in regional_results.values() if r["success"])
    total_regions = len(regional_results)
    status = "✅" if regions_working == total_regions else "⚠️"
    logger.info(f"{status} Regional Processing: {regions_working}/{total_regions} working")

    # Quality gates summary
    if "duplicates_handled" in quality_results:
        status = "✅" if quality_results["duplicates_handled"] else "❌"
        logger.info(
            f"{status} Quality Gates: Duplicates {'handled' if quality_results['duplicates_handled'] else 'NOT handled'}"
        )

    # Save results
    output_file = f"production_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n📄 Results saved to: {output_file}")

    # Final verdict
    logger.info(f"\n{'='*60}")
    all_passed = (
        1000 in perf_results
        and perf_results[1000]["status"] == "SUCCESS"
        and perf_results[1000]["projected_1m_minutes"] < 35
        and regions_working == total_regions
        and quality_results.get("duplicates_handled", False)
    )

    if all_passed:
        logger.info("🎯 PRODUCTION READY: All tests passed!")
    else:
        logger.info("❌ NOT PRODUCTION READY: Some tests failed")

    logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
