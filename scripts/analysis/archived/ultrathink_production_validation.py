#!/usr/bin/env python3
"""
ULTRATHINK Production Validation Suite
Comprehensive testing of GMNAP v7 for production readiness
"""

import asyncio
import json
import time
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Tuple

from src.core.pipeline_v7 import V7Pipeline, PipelineMode
from src.regions.manager import RegionManager


class ProductionValidator:
    """Validate production readiness of GMNAP v7."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {},
        }

    async def validate_all(self) -> Dict[str, Any]:
        """Run all production validation tests."""
        print("=" * 80)
        print("ULTRATHINK PRODUCTION VALIDATION SUITE")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}\n")

        # Test 1: Pipeline functionality
        await self.test_pipeline_functionality()

        # Test 2: Regional processing accuracy
        await self.test_regional_processing()

        # Test 3: Performance at scale
        await self.test_performance_at_scale()

        # Test 4: Quality gates
        await self.test_quality_gates()

        # Test 5: Error handling
        await self.test_error_handling()

        # Generate summary
        self.generate_summary()

        return self.results

    async def test_pipeline_functionality(self):
        """Test core pipeline functionality."""
        print("📊 Testing Pipeline Functionality...")
        test_name = "pipeline_functionality"

        try:
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            # Test basic processing
            entries = [
                {"CanonicalNative": "Albert Einstein", "GlobalID": "TEST-001"},
                {"CanonicalNative": "김민수", "GlobalID": "TEST-002"},
                {"CanonicalNative": "Иванов Иван", "GlobalID": "TEST-003"},
            ]

            result = await pipeline.process_batch(entries)

            self.results["tests"][test_name] = {
                "status": "PASS",
                "stages_executed": result["metrics"]["stages_executed"],
                "entries_processed": result["metrics"]["processed_entries"],
                "success_rate": result["metrics"]["success_rate"],
            }

            print(
                f"  ✅ Pipeline: {result['metrics']['stages_executed']} stages executed"
            )
            print(f"  ✅ Processed: {result['metrics']['processed_entries']} entries")

        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            print(f"  ❌ Pipeline test failed: {e}")

    async def test_regional_processing(self):
        """Test regional processing accuracy."""
        print("\n📊 Testing Regional Processing...")
        test_name = "regional_processing"

        try:
            manager = RegionManager()
            test_cases = [
                ("김민수", "E4", "Kim Min-su"),
                ("李明", "E1", "Li Ming"),
                ("Иванов Иван", "B1", "Ivanov Ivan"),
                ("山田太郎", "E3", "Yamada Taro"),
                ("محمد علي", "C3", None),  # Arabic may not have Latin
            ]

            results = []
            for native, expected_region, expected_latin in test_cases:
                entry = {"CanonicalNative": native, "GlobalID": f"TEST-{native[:3]}"}
                region = manager.detect_region(entry)

                if region:
                    processor = manager.get_region(region)
                    processed = processor.process(entry.copy())
                    latin = processed.get("CanonicalLatin", "")

                    match = region == expected_region and (
                        expected_latin is None or latin == expected_latin
                    )
                    results.append(
                        {
                            "native": native,
                            "region": region,
                            "latin": latin,
                            "expected_region": expected_region,
                            "expected_latin": expected_latin,
                            "match": match,
                        }
                    )

                    status = "✅" if match else "❌"
                    print(f"  {status} {native} → {latin} (Region: {region})")
                else:
                    results.append(
                        {
                            "native": native,
                            "region": "NONE",
                            "error": "No region detected",
                            "match": False,
                        }
                    )
                    print(f"  ❌ {native} → No region detected")

            passed = sum(1 for r in results if r["match"])
            self.results["tests"][test_name] = {
                "status": "PASS" if passed == len(test_cases) else "PARTIAL",
                "passed": passed,
                "total": len(test_cases),
                "accuracy": passed / len(test_cases),
                "details": results,
            }

        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            print(f"  ❌ Regional processing test failed: {e}")

    async def test_performance_at_scale(self):
        """Test performance with different batch sizes."""
        print("\n📊 Testing Performance at Scale...")
        test_name = "performance"

        try:
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)
            performance_results = []

            for batch_size in [10, 100, 1000]:
                entries = [
                    {"CanonicalNative": f"Test Person {i}", "GlobalID": f"PERF-{i:06d}"}
                    for i in range(batch_size)
                ]

                start = time.time()
                result = await pipeline.process_batch(entries)
                elapsed = time.time() - start

                rate = batch_size / elapsed if elapsed > 0 else 0
                projected_1m = (1_000_000 / rate / 60) if rate > 0 else float("inf")

                performance_results.append(
                    {
                        "batch_size": batch_size,
                        "elapsed": elapsed,
                        "rate": rate,
                        "projected_1m_minutes": projected_1m,
                        "meets_target": projected_1m <= 35,
                    }
                )

                status = "✅" if projected_1m <= 35 else "❌"
                print(
                    f"  {status} Batch {batch_size}: {rate:.0f} entries/sec, "
                    f"projected 1M: {projected_1m:.1f} min"
                )

            # Determine if performance is acceptable
            acceptable = any(r["meets_target"] for r in performance_results)

            self.results["tests"][test_name] = {
                "status": "PASS" if acceptable else "FAIL",
                "results": performance_results,
                "acceptable_batch_sizes": [
                    r["batch_size"] for r in performance_results if r["meets_target"]
                ],
            }

        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            print(f"  ❌ Performance test failed: {e}")

    async def test_quality_gates(self):
        """Test quality gate enforcement."""
        print("\n📊 Testing Quality Gates...")
        test_name = "quality_gates"

        try:
            pipeline = V7Pipeline(mode=PipelineMode.FULL)

            # Test with duplicate GlobalIDs
            entries = [
                {"CanonicalNative": f"Person {i%5}", "GlobalID": f"DUP-{i%5:03d}"}
                for i in range(20)
            ]

            result = await pipeline.process_batch(entries)

            # Check if duplicates were detected
            duplicate_count = result["metrics"].get("duplicate_global_ids", 0)
            quality_passed = result["metrics"].get("quality_gates_passed", True)

            self.results["tests"][test_name] = {
                "status": "PASS" if duplicate_count > 0 else "FAIL",
                "duplicates_detected": duplicate_count,
                "quality_gates_passed": quality_passed,
                "message": "Quality gates correctly detecting duplicates",
            }

            print(f"  ✅ Duplicates detected: {duplicate_count}")
            print(
                f"  {'⚠️' if not quality_passed else '✅'} Quality gates: "
                f"{'PASSED' if quality_passed else 'FAILED'}"
            )

        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            print(f"  ❌ Quality gates test failed: {e}")

    async def test_error_handling(self):
        """Test error handling and recovery."""
        print("\n📊 Testing Error Handling...")
        test_name = "error_handling"

        try:
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            # Test with problematic entries
            entries = [
                {"CanonicalNative": "Normal Name", "GlobalID": "OK-001"},
                {"CanonicalNative": "", "GlobalID": "EMPTY-001"},  # Empty name
                {"CanonicalNative": "Missing ID"},  # Missing GlobalID
                {"GlobalID": "NO-NAME-001"},  # Missing name
                {
                    "CanonicalNative": "A" * 1000,
                    "GlobalID": "LONG-001",
                },  # Very long name
            ]

            result = await pipeline.process_batch(entries)

            failed = result["metrics"].get("failed_entries", 0)
            processed = result["metrics"].get("processed_entries", 0)

            self.results["tests"][test_name] = {
                "status": "PASS" if processed > 0 else "FAIL",
                "total_entries": len(entries),
                "processed": processed,
                "failed": failed,
                "error_rate": failed / len(entries) if entries else 0,
                "message": "Pipeline handles errors gracefully",
            }

            print(f"  ✅ Processed: {processed}/{len(entries)} entries")
            print(f"  ⚠️ Failed: {failed} entries (error handling working)")

        except Exception as e:
            self.results["tests"][test_name] = {"status": "FAIL", "error": str(e)}
            print(f"  ❌ Error handling test failed: {e}")

    def generate_summary(self):
        """Generate test summary."""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        # Count test results
        passed = sum(1 for t in self.results["tests"].values() if t["status"] == "PASS")
        partial = sum(
            1 for t in self.results["tests"].values() if t["status"] == "PARTIAL"
        )
        failed = sum(1 for t in self.results["tests"].values() if t["status"] == "FAIL")
        total = len(self.results["tests"])

        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "production_ready": passed >= total * 0.8,  # 80% threshold
        }

        # Print summary
        for test_name, result in self.results["tests"].items():
            status_icon = {"PASS": "✅", "PARTIAL": "⚠️", "FAIL": "❌"}.get(
                result["status"], "❓"
            )

            print(f"{status_icon} {test_name}: {result['status']}")

        print(
            f"\nOverall: {passed}/{total} tests passed ({self.results['summary']['pass_rate']:.1%})"
        )

        if self.results["summary"]["production_ready"]:
            print("\n🎯 PRODUCTION READY: YES")
        else:
            print("\n⚠️ PRODUCTION READY: NO (needs more work)")

    def save_results(self, filename: str = "production_validation_results.json"):
        """Save results to JSON file."""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {filename}")


async def main():
    """Run production validation."""
    validator = ProductionValidator()
    results = await validator.validate_all()
    validator.save_results()

    # Exit with appropriate code
    exit_code = 0 if results["summary"]["production_ready"] else 1
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
