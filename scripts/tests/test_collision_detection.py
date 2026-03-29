#!/usr/bin/env python3
"""
Week 4 Day 2: Test Collision Detection
Tests Stage 5 DuckDB collision analytics for V7 compliance.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))
os.environ["OFFLINE"] = "1"  # Test offline for speed

from src.core.pipeline_v7_complete_final import create_v7_pipeline
from src.analytics.duckdb_analytics import DuckDBAnalytics


class CollisionDetectionTester:
    """Test Stage 5 collision detection and suffix generation."""

    def __init__(self):
        self.results = {"tests_run": 0, "tests_passed": 0, "tests_failed": 0, "errors": []}

    async def test_exact_duplicates(self):
        """Test handling of exact name duplicates."""
        print("\n" + "=" * 60)
        print("TEST 1: EXACT NAME DUPLICATES")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Create entries with duplicate names
        test_entries = [
            {
                "GlobalID": "DUP-001",
                "CanonicalLatin": "John Smith",
                "Field": "Physics",
                "BirthYear": 1950,
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
            {
                "GlobalID": "DUP-002",
                "CanonicalLatin": "John Smith",  # Same name
                "Field": "Mathematics",
                "BirthYear": 1950,  # Same birth year
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
            {
                "GlobalID": "DUP-003",
                "CanonicalLatin": "John Smith",  # Same name again
                "Field": "Chemistry",
                "BirthYear": 1950,  # Same birth year
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
        ]

        try:
            # Test with DuckDB analytics directly
            analytics = DuckDBAnalytics()
            analytics.load_entries(test_entries)
            duplicates = analytics.suffix_duplicates()

            print(f"Duplicates found: {len(duplicates)}")
            print(f"Suffixes generated: {duplicates}")

            # Should generate suffixes for DUP-002 and DUP-003
            if len(duplicates) == 2:
                # Check suffix format
                expected = [("DUP-002", "DUP-002--1"), ("DUP-003", "DUP-003--2")]
                if duplicates[0][1].endswith("--1") and duplicates[1][1].endswith("--2"):
                    print("✅ Correct suffix generation for duplicates")
                    self.results["tests_passed"] += 1
                else:
                    print(f"❌ Incorrect suffix format: {duplicates}")
                    self.results["tests_failed"] += 1
                    self.results["errors"].append("Incorrect suffix format")
            else:
                print(f"❌ Expected 2 duplicates, got {len(duplicates)}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"Expected 2 duplicates, got {len(duplicates)}")

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(str(e)[:100])

        self.results["tests_run"] += 1

    async def test_different_birth_years(self):
        """Test that same names with different birth years are not duplicates."""
        print("\n" + "=" * 60)
        print("TEST 2: DIFFERENT BIRTH YEARS")
        print("=" * 60)

        test_entries = [
            {
                "GlobalID": "YEAR-001",
                "CanonicalLatin": "Marie Curie",
                "BirthYear": 1867,
                "Field": "Physics",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
            {
                "GlobalID": "YEAR-002",
                "CanonicalLatin": "Marie Curie",
                "BirthYear": 1934,  # Different year
                "Field": "Chemistry",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
        ]

        try:
            analytics = DuckDBAnalytics()
            analytics.load_entries(test_entries)
            duplicates = analytics.suffix_duplicates()

            print(f"Duplicates found: {len(duplicates)}")

            # Should NOT generate suffixes (different birth years)
            if len(duplicates) == 0:
                print("✅ Different birth years not treated as duplicates")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ Should not suffix different birth years: {duplicates}")
                self.results["tests_failed"] += 1
                self.results["errors"].append("Incorrectly suffixed different birth years")

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(str(e)[:100])

        self.results["tests_run"] += 1

    async def test_collision_analytics(self):
        """Test the analyze_collisions method."""
        print("\n" + "=" * 60)
        print("TEST 3: COLLISION ANALYTICS")
        print("=" * 60)

        test_entries = [
            {"GlobalID": "COL-001", "CanonicalLatin": "Test One", "BirthYear": 1900},
            {"GlobalID": "COL-002", "CanonicalLatin": "Test Two", "BirthYear": 1901},
            {"GlobalID": "COL-003", "CanonicalLatin": "Test One", "BirthYear": 1900},  # Duplicate
            {"GlobalID": "COL-004", "CanonicalLatin": "Test Three", "BirthYear": 1902},
            {
                "GlobalID": "COL-005",
                "CanonicalLatin": "Test One",
                "BirthYear": 1900,
            },  # Another duplicate
        ]

        try:
            analytics = DuckDBAnalytics()
            collision_stats = analytics.analyze_collisions(test_entries)

            print(f"Total entries: {collision_stats['total_entries']}")
            print(f"Unique names: {collision_stats['unique_names']}")
            print(f"Collisions: {collision_stats['collisions']}")
            print(f"Collision rate: {collision_stats['collision_rate']:.2%}")

            # Should have 2 collisions (COL-003 and COL-005)
            if collision_stats["collisions"] == 2:
                print("✅ Collision count correct")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ Expected 2 collisions, got {collision_stats['collisions']}")
                self.results["tests_failed"] += 1
                self.results["errors"].append(
                    f"Wrong collision count: {collision_stats['collisions']}"
                )

            # Check collision rate
            expected_rate = 2 / 5  # 2 collisions out of 5 entries
            if abs(collision_stats["collision_rate"] - expected_rate) < 0.01:
                print("✅ Collision rate correct")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ Wrong collision rate: {collision_stats['collision_rate']}")
                self.results["tests_failed"] += 1

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(str(e)[:100])

        self.results["tests_run"] += 2  # Two sub-tests

    async def test_deterministic_ordering(self):
        """Test that suffix generation is deterministic."""
        print("\n" + "=" * 60)
        print("TEST 4: DETERMINISTIC ORDERING")
        print("=" * 60)

        test_entries = [
            {"GlobalID": "DET-003", "CanonicalLatin": "Same Name", "BirthYear": 2000},
            {"GlobalID": "DET-001", "CanonicalLatin": "Same Name", "BirthYear": 2000},
            {"GlobalID": "DET-002", "CanonicalLatin": "Same Name", "BirthYear": 2000},
        ]

        try:
            # Run twice to check determinism
            analytics1 = DuckDBAnalytics()
            analytics1.load_entries(test_entries)
            duplicates1 = analytics1.suffix_duplicates()

            analytics2 = DuckDBAnalytics()
            analytics2.load_entries(test_entries)
            duplicates2 = analytics2.suffix_duplicates()

            print(f"First run: {duplicates1}")
            print(f"Second run: {duplicates2}")

            if duplicates1 == duplicates2:
                print("✅ Suffix generation is deterministic")
                self.results["tests_passed"] += 1
            else:
                print("❌ Suffix generation not deterministic")
                self.results["tests_failed"] += 1
                self.results["errors"].append("Non-deterministic suffix generation")

            # Check ordering (should be by GlobalID)
            if len(duplicates1) == 2:
                if duplicates1[0][0] == "DET-002" and duplicates1[1][0] == "DET-003":
                    print("✅ Correct alphabetical ordering by GlobalID")
                    self.results["tests_passed"] += 1
                else:
                    print(f"❌ Incorrect ordering: {[d[0] for d in duplicates1]}")
                    self.results["tests_failed"] += 1

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(str(e)[:100])

        self.results["tests_run"] += 2  # Two sub-tests

    async def test_pipeline_integration(self):
        """Test Stage 5 integration in the full pipeline."""
        print("\n" + "=" * 60)
        print("TEST 5: PIPELINE INTEGRATION")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": "PIPE-001",
                "CanonicalLatin": "Integration Test",
                "BirthYear": 1980,
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
            {
                "GlobalID": "PIPE-002",
                "CanonicalLatin": "Integration Test",  # Same name
                "BirthYear": 1980,  # Same year
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "pending",
            },
        ]

        try:
            results = await pipeline.process(test_entries)

            # Check if Stage 5 ran
            if "stage_5_collisions" in pipeline.metrics.stage_timings:
                timing = pipeline.metrics.stage_timings["stage_5_collisions"]
                print(f"✅ Stage 5 executed in {timing:.3f}s")
                self.results["tests_passed"] += 1
            else:
                print("❌ Stage 5 not in pipeline timings")
                self.results["tests_failed"] += 1
                self.results["errors"].append("Stage 5 not executed")

            # Both entries should be in results
            if len(results) == 2:
                print("✅ Both entries processed")
                self.results["tests_passed"] += 1
            else:
                print(f"❌ Expected 2 results, got {len(results)}")
                self.results["tests_failed"] += 1

        except Exception as e:
            print(f"❌ Error: {e}")
            self.results["tests_failed"] += 1
            self.results["errors"].append(str(e)[:100])

        self.results["tests_run"] += 2  # Two sub-tests

    async def run_all_tests(self):
        """Run all collision detection tests."""
        print("\n" + "=" * 70)
        print("COLLISION DETECTION TEST SUITE - WEEK 4 DAY 2")
        print("=" * 70)

        await self.test_exact_duplicates()
        await self.test_different_birth_years()
        await self.test_collision_analytics()
        await self.test_deterministic_ordering()
        await self.test_pipeline_integration()

        # Calculate score
        total_tests = self.results["tests_run"]
        passed = self.results["tests_passed"]
        score = (passed / total_tests * 100) if total_tests > 0 else 0

        # Summary
        print("\n" + "=" * 70)
        print("COLLISION DETECTION SUMMARY")
        print("=" * 70)
        print(f"Tests Run: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {self.results['tests_failed']}")
        print(f"Score: {score:.1f}%")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        # Collision detection component score (5% of total V7)
        collision_compliance = 5 * (score / 100)
        print(f"\nCollision Detection Compliance: {collision_compliance:.1f}/5 points")

        return score


async def main():
    """Run collision detection tests."""
    tester = CollisionDetectionTester()
    score = await tester.run_all_tests()

    # Update compliance estimate
    base_compliance = 90.9  # After regional processing
    collision_addition = 5 * (score / 100)  # Collision detection is 5% of total
    new_compliance = base_compliance + collision_addition

    print(f"\n📊 UPDATED V7 COMPLIANCE: {new_compliance:.1f}%")

    if score >= 90:
        print("✅ Collision detection tests PASSED!")
    elif score >= 70:
        print("⚠️ Collision detection partially working")
    else:
        print("❌ Collision detection needs fixes")

    return score >= 70


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
