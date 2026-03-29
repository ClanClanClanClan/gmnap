#!/usr/bin/env python3
"""
ULTRATHINK Batch Performance Test Framework
Tests batches from 10 to 1M entries with complete accuracy.
NO FABRICATION - only reports actual measured results.
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline_v7 import V7Pipeline


class UltrathinkBatchTester:
    """Comprehensive batch performance tester with complete accuracy."""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.test_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_test_entries(self, count: int) -> List[Dict[str, Any]]:
        """Generate simple, safe test entries that won't trigger security issues."""
        entries = []
        base_names = [
            "John Smith",
            "Jane Doe",
            "Alice Johnson",
            "Bob Wilson",
            "Carol Brown",
            "David Davis",
            "Emily Miller",
            "Frank Moore",
        ]

        for i in range(count):
            name = base_names[i % len(base_names)]
            entry = {
                "ID": f"ultrathink_{i:08d}",
                "CanonicalNative": f"{name} {i}",
                "Region": "a1_anglo_sphere",
                "SourceDatabase": "ultrathink_test",
                "Year": 2020 + (i % 5),
            }
            entries.append(entry)

        return entries

    async def test_single_batch(self, batch_size: int) -> Dict[str, Any]:
        """Test a single batch size and return actual measured results."""
        print(f"Testing batch size {batch_size:,} entries...", end=" ", flush=True)

        # Generate test data
        entries = self.generate_test_entries(batch_size)

        # Initialize pipeline
        pipeline = V7Pipeline()

        # Measure actual execution
        start_time = time.time()

        try:
            # Execute pipeline
            pipeline_result = await pipeline.process_batch(entries)
            end_time = time.time()

            # Parse actual results
            duration = end_time - start_time
            entries_per_second = batch_size / duration if duration > 0 else 0
            time_for_1m_minutes = (
                (1_000_000 / entries_per_second / 60) if entries_per_second > 0 else float("inf")
            )

            # Extract actual data from pipeline result
            if isinstance(pipeline_result, dict):
                processed_entries = pipeline_result.get("entries", [])
                metrics = pipeline_result.get("metrics", {})
                quality_gates = pipeline_result.get("quality_gates", {})

                # Count actual successes based on Status field
                successful_count = 0
                failed_count = 0

                for entry in processed_entries:
                    if isinstance(entry, dict):
                        status = entry.get("Status", "unknown")
                        if status == "success":
                            successful_count += 1
                        elif status in ["failed", "error"]:
                            failed_count += 1

                success_rate = (successful_count / batch_size * 100) if batch_size > 0 else 0

                result = {
                    "batch_size": batch_size,
                    "duration_seconds": round(duration, 3),
                    "entries_per_second": round(entries_per_second, 1),
                    "time_for_1m_minutes": round(time_for_1m_minutes, 1),
                    "processed_entries_count": len(processed_entries),
                    "successful_entries": successful_count,
                    "failed_entries": failed_count,
                    "success_rate_percent": round(success_rate, 1),
                    "quality_gates_passed": quality_gates.get("passed", False),
                    "pipeline_metrics": metrics,
                    "status": "completed",
                }

                print(
                    f"✅ {entries_per_second:.0f} e/s, {success_rate:.1f}% success, gates: {'✅' if quality_gates.get('passed') else '❌'}"
                )

            else:
                # Unexpected result format
                result = {
                    "batch_size": batch_size,
                    "error": f"Unexpected pipeline result type: {type(pipeline_result)}",
                    "result_content": str(pipeline_result)[:200],
                    "status": "error",
                }
                print(f"❌ Unexpected result format")

        except Exception as e:
            # Actual error occurred
            end_time = time.time()
            duration = end_time - start_time

            result = {
                "batch_size": batch_size,
                "duration_seconds": round(duration, 3),
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "status": "failed",
            }
            print(f"❌ Error: {str(e)[:50]}")

        finally:
            # Clean up
            del pipeline

        return result

    async def run_comprehensive_test(self):
        """Run comprehensive tests from 10 to 1M entries."""
        print("🚀 ULTRATHINK Comprehensive Batch Performance Test")
        print("=" * 60)
        print("❗ This test reports ONLY actual measured results")
        print("❗ NO fabrication or estimation will be used")
        print("=" * 60)

        # Define test batch sizes
        batch_sizes = [
            # Very small
            10,
            25,
            50,
            75,
            100,
            # Small
            200,
            300,
            500,
            750,
            1000,
            # Medium
            2000,
            3000,
            5000,
            7500,
            10000,
            # Large
            25000,
            50000,
            75000,
            100000,
            # Very large
            250000,
            500000,
            750000,
            1000000,
        ]

        self.start_time = datetime.now()

        print(f"\nStarting test at: {self.start_time}")
        print(f"Testing {len(batch_sizes)} different batch sizes")
        print(f"Expected duration: 30-60 minutes for complete test")
        print()

        for i, batch_size in enumerate(batch_sizes, 1):
            print(f"[{i:2d}/{len(batch_sizes)}] ", end="")

            result = await self.test_single_batch(batch_size)
            self.results.append(result)

            # Short pause between tests to avoid system stress
            await asyncio.sleep(1)

            # Progress update every 5 tests
            if i % 5 == 0:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                avg_time_per_test = elapsed / i
                estimated_remaining = avg_time_per_test * (len(batch_sizes) - i)
                print(
                    f"    Progress: {i}/{len(batch_sizes)} complete, ~{estimated_remaining/60:.1f}min remaining"
                )

        end_time = datetime.now()

        print(f"\n✅ Test completed at: {end_time}")
        print(f"Total duration: {(end_time - self.start_time).total_seconds():.0f} seconds")

        # Generate comprehensive report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive report of actual results."""
        print("\n📊 ULTRATHINK BATCH PERFORMANCE REPORT")
        print("=" * 60)

        # Separate successful and failed tests
        successful_tests = [r for r in self.results if r.get("status") == "completed"]
        failed_tests = [r for r in self.results if r.get("status") != "completed"]

        print(f"Total tests run: {len(self.results)}")
        print(f"Successful tests: {len(successful_tests)}")
        print(f"Failed tests: {len(failed_tests)}")

        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   Batch size {test['batch_size']:,}: {test.get('error', 'Unknown error')}")

        if successful_tests:
            # Find best performance
            best_test = max(successful_tests, key=lambda x: x.get("entries_per_second", 0))

            print(f"\n🏆 Best Performance:")
            print(f"   Batch Size: {best_test['batch_size']:,} entries")
            print(f"   Speed: {best_test['entries_per_second']:,.0f} entries/sec")
            print(f"   Time for 1M: {best_test['time_for_1m_minutes']:.1f} minutes")
            print(f"   Success Rate: {best_test['success_rate_percent']:.1f}%")

            # Performance categories
            excellent = [t for t in successful_tests if t.get("entries_per_second", 0) >= 500]
            good = [t for t in successful_tests if 200 <= t.get("entries_per_second", 0) < 500]
            acceptable = [
                t for t in successful_tests if 100 <= t.get("entries_per_second", 0) < 200
            ]
            poor = [t for t in successful_tests if t.get("entries_per_second", 0) < 100]

            print(f"\n📈 Performance Distribution:")
            print(f"   Excellent (≥500 e/s): {len(excellent)} tests")
            print(f"   Good (200-500 e/s): {len(good)} tests")
            print(f"   Acceptable (100-200 e/s): {len(acceptable)} tests")
            print(f"   Poor (<100 e/s): {len(poor)} tests")

            # Detailed results table
            print(f"\n📋 Detailed Results (Successful Tests Only):")
            print("Batch Size | Speed (e/s) | 1M Time (min) | Success Rate | Quality Gates")
            print("-" * 75)

            for test in successful_tests:
                size = test["batch_size"]
                speed = test.get("entries_per_second", 0)
                time_1m = test.get("time_for_1m_minutes", 0)
                success = test.get("success_rate_percent", 0)
                gates = "✅" if test.get("quality_gates_passed") else "❌"

                print(
                    f"{size:>10,} | {speed:>11.0f} | {time_1m:>12.1f} | {success:>10.1f}% | {gates:>12}"
                )

        # Save detailed results
        self.save_results()

    def save_results(self):
        """Save complete results to JSON file."""
        filename = f"ultrathink_batch_results_{self.test_id}.json"

        report_data = {
            "test_metadata": {
                "test_id": self.test_id,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                "framework": "UltrathinkBatchTester",
                "version": "1.0",
                "note": "All results are actual measured values, no fabrication",
            },
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len(
                    [r for r in self.results if r.get("status") == "completed"]
                ),
                "failed_tests": len([r for r in self.results if r.get("status") != "completed"]),
            },
            "detailed_results": self.results,
        }

        with open(filename, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 Complete results saved to: {filename}")
        print(f"📊 Report contains {len(self.results)} test results with full details")


async def main():
    """Main execution function."""
    tester = UltrathinkBatchTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())
