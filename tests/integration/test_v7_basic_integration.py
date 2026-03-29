import pytest

#!/usr/bin/env python3
"""
Basic V7 integration test that actually works.
Tests real functionality with proper imports.
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Enable live authority sources for testing
os.environ["OFFLINE"] = "0"

from src.core.pipeline_v7_complete_final import create_v7_pipeline


@pytest.mark.asyncio
async def test_basic_pipeline():
    """Test basic pipeline functionality."""
    print("\n" + "=" * 60)
    print("V7 BASIC INTEGRATION TEST")
    print("=" * 60)

    # Create pipeline
    pipeline = create_v7_pipeline(mode="quick")

    # Test data
    test_entries = [
        {
            "GlobalID": "TEST-001",
            "CanonicalLatin": "Albert Einstein",
            "Field": "Physics",
            "Source": "Test",
            "LastUpdated": "2025-09-10",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": "TEST-002",
            "CanonicalLatin": "Marie Curie",
            "Field": "Chemistry",
            "Source": "Test",
            "LastUpdated": "2025-09-10",
            "ValidationStatus": "pending",
        },
    ]

    # Process entries
    results = await pipeline.process(test_entries)

    # Validate results
    tests_passed = 0
    tests_failed = 0

    print("\n🧪 Testing pipeline outputs:")

    # Test 1: All entries processed
    if len(results) == len(test_entries):
        print("PASS Test 1: All entries processed")
        tests_passed += 1
    else:
        print(f"FAIL Test 1: Expected {len(test_entries)} results, got {len(results)}")
        tests_failed += 1

    # Test 2: GlobalIDs preserved
    result_ids = {r.get("GlobalID") for r in results}
    expected_ids = {e["GlobalID"] for e in test_entries}
    if result_ids == expected_ids:
        print("PASS Test 2: GlobalIDs preserved")
        tests_passed += 1
    else:
        print(f"FAIL Test 2: GlobalIDs mismatch")
        tests_failed += 1

    # Test 3: Authority enrichment
    has_authority = any(r.get("AuthoritySources") for r in results)
    if has_authority:
        print("PASS Test 3: Authority enrichment working")
        tests_passed += 1
    else:
        print("FAIL Test 3: No authority enrichment")
        tests_failed += 1

    # Test 4: Graph coherence
    has_coherence = all("GraphCoherence" in r for r in results)
    coherence_valid = all(0 <= r.get("GraphCoherence", 0) <= 1 for r in results)
    if has_coherence and coherence_valid:
        print("PASS Test 4: Graph coherence calculated")
        tests_passed += 1
    else:
        print("FAIL Test 4: Graph coherence missing or invalid")
        tests_failed += 1

    # Test 5: Short forms
    has_short_forms = any(r.get("ShortFormClusters") for r in results)
    if has_short_forms:
        print("PASS Test 5: Short forms generated")
        tests_passed += 1
    else:
        print("FAIL Test 5: No short forms")
        tests_failed += 1

    # Test 6: No pipeline errors
    has_errors = any("PipelineErrors" in r for r in results)
    if not has_errors:
        print("PASS Test 6: No pipeline errors")
        tests_passed += 1
    else:
        print("FAIL Test 6: Pipeline errors found")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_passed + tests_failed} tests passed")

    if tests_failed == 0:
        print("PASS ALL TESTS PASSED!")
    else:
        print(f"WARN {tests_failed} tests failed")

    print("=" * 60)

    return tests_passed, tests_failed


@pytest.mark.asyncio
async def test_with_advisors():
    """Test pipeline with advisor relationships."""
    print("\n" + "=" * 60)
    print("V7 ADVISOR RELATIONSHIP TEST")
    print("=" * 60)

    pipeline = create_v7_pipeline(mode="quick")

    # Test data with relationships
    test_entries = [
        {
            "GlobalID": "PROF-001",
            "CanonicalLatin": "Albert Einstein",
            "Field": "Physics",
            "Students": ["PROF-002", "PROF-003"],
            "Source": "Test",
            "LastUpdated": "2025-09-10",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": "PROF-002",
            "CanonicalLatin": "John Wheeler",
            "Field": "Physics",
            "Advisors": ["PROF-001"],
            "Source": "Test",
            "LastUpdated": "2025-09-10",
            "ValidationStatus": "pending",
        },
        {
            "GlobalID": "PROF-003",
            "CanonicalLatin": "Richard Feynman",
            "Field": "Physics",
            "Advisors": ["PROF-001"],
            "Source": "Test",
            "LastUpdated": "2025-09-10",
            "ValidationStatus": "pending",
        },
    ]

    results = await pipeline.process(test_entries)

    tests_passed = 0
    tests_failed = 0

    print("\n🧪 Testing advisor relationships:")

    # Test 1: Relationships preserved
    for r in results:
        if r["GlobalID"] == "PROF-001":
            if r.get("Students") == ["PROF-002", "PROF-003"]:
                print("PASS Test 1: Students preserved for PROF-001")
                tests_passed += 1
            else:
                print("FAIL Test 1: Students not preserved")
                tests_failed += 1
            break

    # Test 2: Graph coherence higher with relationships
    coherence_scores = [r.get("GraphCoherence", 0) for r in results]
    avg_coherence = sum(coherence_scores) / len(coherence_scores)
    if avg_coherence > 0:
        print(f"PASS Test 2: Graph coherence with relationships: {avg_coherence:.2f}")
        tests_passed += 1
    else:
        print("FAIL Test 2: Graph coherence should be > 0 with relationships")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_passed + tests_failed} tests passed")
    print("=" * 60)

    return tests_passed, tests_failed


@pytest.mark.asyncio
async def test_scale():
    """Test pipeline with more entries."""
    print("\n" + "=" * 60)
    print("V7 SCALE TEST (100 entries)")
    print("=" * 60)

    import time

    pipeline = create_v7_pipeline(mode="quick")

    # Generate 100 test entries
    test_entries = []
    for i in range(100):
        test_entries.append(
            {
                "GlobalID": f"SCALE-{i:03d}",
                "CanonicalLatin": f"Test Person {i}",
                "Field": ["Physics", "Chemistry", "Mathematics"][i % 3],
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
        )

    start_time = time.time()
    results = await pipeline.process(test_entries)
    elapsed = time.time() - start_time

    tests_passed = 0
    tests_failed = 0

    print("\n🧪 Testing scale performance:")

    # Test 1: All processed
    if len(results) == 100:
        print("PASS Test 1: All 100 entries processed")
        tests_passed += 1
    else:
        print(f"FAIL Test 1: Expected 100, got {len(results)}")
        tests_failed += 1

    # Test 2: Performance
    entries_per_sec = len(results) / elapsed if elapsed > 0 else 0
    if entries_per_sec > 50:  # Should process at least 50/sec
        print(f"PASS Test 2: Performance: {entries_per_sec:.1f} entries/sec")
        tests_passed += 1
    else:
        print(f"FAIL Test 2: Too slow: {entries_per_sec:.1f} entries/sec")
        tests_failed += 1

    # Test 3: No errors
    errors = sum(1 for r in results if "PipelineErrors" in r)
    if errors == 0:
        print("PASS Test 3: No pipeline errors")
        tests_passed += 1
    else:
        print(f"FAIL Test 3: {errors} entries had errors")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_passed + tests_failed} tests passed")
    print(f"Processing time: {elapsed:.2f}s ({entries_per_sec:.1f} entries/sec)")
    print("=" * 60)

    return tests_passed, tests_failed


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("V7 INTEGRATION TEST SUITE")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    # Run basic tests
    passed, failed = await test_basic_pipeline()
    total_passed += passed
    total_failed += failed

    # Run advisor tests
    passed, failed = await test_with_advisors()
    total_passed += passed
    total_failed += failed

    # Run scale test
    passed, failed = await test_scale()
    total_passed += passed
    total_failed += failed

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total tests passed: {total_passed}")
    print(f"Total tests failed: {total_failed}")

    if total_failed == 0:
        print("\nPASS ALL INTEGRATION TESTS PASSED!")
    else:
        print(f"\nWARN {total_failed} tests need attention")

    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
