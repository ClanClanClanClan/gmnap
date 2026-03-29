#!/usr/bin/env python3
"""
ULTRATHINK DIAGNOSTIC TEST
Validates critical issues discovered in deep analysis.
"""

import time
import psutil
import asyncio
import tracemalloc
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline_v7 import V7Pipeline


class UltrathinkDiagnostic:
    def __init__(self):
        self.results = []

    def get_memory_detailed(self):
        """Get detailed memory information."""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }

    async def test_memory_explosion_at_50(self):
        """Test the critical 50-entry memory explosion."""
        print("🔍 TESTING: Memory explosion at 50 entries")

        # Test multiple batch sizes around the critical 50-entry point
        test_sizes = [25, 40, 45, 48, 49, 50, 51, 52, 55, 60, 75, 100]

        for size in test_sizes:
            print(f"  Testing {size} entries... ", end="")

            # Start memory tracking
            tracemalloc.start()
            mem_before = self.get_memory_detailed()

            # Create entries
            entries = [
                {
                    "ID": f"mem_test_{i}",
                    "CanonicalNative": "John Smith",
                    "Region": "a1_anglo_sphere",
                }
                for i in range(size)
            ]

            try:
                pipeline = V7Pipeline()
                start_time = time.time()
                results = await pipeline.process_batch(entries)
                duration = time.time() - start_time

                # Get memory after processing
                mem_after = self.get_memory_detailed()
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                memory_delta = mem_after["rss_mb"] - mem_before["rss_mb"]
                memory_per_entry = (
                    memory_delta / size * 1024 if size > 0 else 0
                )  # KB per entry

                result = {
                    "batch_size": size,
                    "memory_delta_mb": round(memory_delta, 2),
                    "memory_per_entry_kb": round(memory_per_entry, 2),
                    "tracemalloc_peak_mb": round(peak / 1024 / 1024, 2),
                    "processing_time": round(duration, 3),
                    "status": "success",
                }

                print(f"Δ{memory_delta:+.1f}MB ({memory_per_entry:.0f}KB/entry)")

                # Detect memory explosion
                if memory_per_entry > 1000:  # More than 1MB per entry
                    result["critical_issue"] = "MEMORY_EXPLOSION"
                    print(f"    🚨 CRITICAL: {memory_per_entry:.0f}KB per entry!")

                self.results.append(result)
                del pipeline

            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                self.results.append(
                    {"batch_size": size, "error": str(e), "status": "failed"}
                )

    async def test_timing_measurement_corruption(self):
        """Test for timing measurement issues."""
        print("\n🔍 TESTING: Timing measurement corruption")

        # Test the same batch size multiple times to check for consistency
        test_size = 25  # Known problematic size

        for run in range(5):
            print(f"  Run {run + 1}/5 with {test_size} entries... ", end="")

            entries = [
                {
                    "ID": f"timing_test_{run}_{i}",
                    "CanonicalNative": "Test Name",
                    "Region": "a1_anglo_sphere",
                }
                for i in range(test_size)
            ]

            try:
                pipeline = V7Pipeline()

                # Multiple timing measurements
                start_perf = time.perf_counter()
                start_time = time.time()
                start_monotonic = time.monotonic()

                results = await pipeline.process_batch(entries)

                end_perf = time.perf_counter()
                end_time = time.time()
                end_monotonic = time.monotonic()

                duration_perf = end_perf - start_perf
                duration_time = end_time - start_time
                duration_monotonic = end_monotonic - start_monotonic

                entries_per_sec_perf = (
                    test_size / duration_perf if duration_perf > 0 else float("inf")
                )
                entries_per_sec_time = (
                    test_size / duration_time if duration_time > 0 else float("inf")
                )

                result = {
                    "run": run + 1,
                    "batch_size": test_size,
                    "duration_perf": round(duration_perf, 6),
                    "duration_time": round(duration_time, 6),
                    "duration_monotonic": round(duration_monotonic, 6),
                    "entries_per_sec_perf": round(entries_per_sec_perf, 1),
                    "entries_per_sec_time": round(entries_per_sec_time, 1),
                    "timing_discrepancy": abs(duration_perf - duration_time),
                    "status": "success",
                }

                print(f"{entries_per_sec_perf:.0f} e/s ({duration_perf:.4f}s)")

                # Detect timing anomalies
                if duration_perf < 0.001:  # Less than 1ms
                    result["critical_issue"] = "IMPOSSIBLE_TIMING"
                    print(f"    🚨 CRITICAL: Impossible timing {duration_perf:.6f}s!")

                if entries_per_sec_perf > 5000:  # Impossibly fast
                    result["critical_issue"] = "IMPOSSIBLE_SPEED"
                    print(
                        f"    🚨 CRITICAL: Impossible speed {entries_per_sec_perf:.0f} e/s!"
                    )

                self.results.append(result)
                del pipeline

            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")

    async def test_security_false_positives(self):
        """Test security system false positive issues."""
        print("\n🔍 TESTING: Security system false positives")

        # Test cases that should be legitimate but trigger security violations
        problematic_cases = [
            {
                "name": "Hindi Name",
                "data": {
                    "CanonicalNative": "Ram Sharma",
                    "Region": "d1_south_asia_hindi_belt",
                },
            },
            {
                "name": "Korean Name",
                "data": {"CanonicalNative": "김정은", "Region": "e4_korea"},
            },
            {
                "name": "Arabic Name",
                "data": {
                    "CanonicalNative": "Ahmed Hassan",
                    "Region": "c3_arabic_levant_nile",
                },
            },
            {
                "name": "Chinese Name",
                "data": {"CanonicalNative": "张伟", "Region": "e1_sinophone_mainland"},
            },
            {
                "name": "Common Word",
                "data": {"CanonicalNative": "Sebastian", "Region": "a2_western_europe"},
            },  # Contains 'bash'
        ]

        for case in problematic_cases:
            print(
                f"  Testing {case['name']}: '{case['data']['CanonicalNative']}'... ",
                end="",
            )

            entries = [
                {"ID": "security_test_001", "SourceDatabase": "test", **case["data"]}
            ]

            try:
                pipeline = V7Pipeline()
                start_time = time.time()
                results = await pipeline.process_batch(entries)
                duration = time.time() - start_time

                # Check if processing succeeded
                if results and len(results) > 0:
                    entry = results[0]
                    if entry.get("Status") == "failed":
                        print(f"❌ BLOCKED (Status: failed)")
                        self.results.append(
                            {
                                "test_case": case["name"],
                                "input": case["data"]["CanonicalNative"],
                                "status": "security_blocked",
                                "critical_issue": "SECURITY_FALSE_POSITIVE",
                            }
                        )
                    else:
                        print(f"✅ Allowed")
                        self.results.append(
                            {
                                "test_case": case["name"],
                                "input": case["data"]["CanonicalNative"],
                                "status": "allowed",
                            }
                        )
                else:
                    print(f"❌ No results returned")
                    self.results.append(
                        {
                            "test_case": case["name"],
                            "input": case["data"]["CanonicalNative"],
                            "status": "no_results",
                            "critical_issue": "SECURITY_SYSTEM_FAILURE",
                        }
                    )

                del pipeline

            except Exception as e:
                error_msg = str(e)
                if (
                    "Security violation" in error_msg
                    or "Security threat blocked" in error_msg
                ):
                    print(f"❌ BLOCKED (Security violation)")
                    self.results.append(
                        {
                            "test_case": case["name"],
                            "input": case["data"]["CanonicalNative"],
                            "status": "security_exception",
                            "error": error_msg[:100],
                            "critical_issue": "SECURITY_FALSE_POSITIVE",
                        }
                    )
                else:
                    print(f"❌ Error: {error_msg[:30]}")
                    self.results.append(
                        {
                            "test_case": case["name"],
                            "input": case["data"]["CanonicalNative"],
                            "status": "error",
                            "error": error_msg[:100],
                        }
                    )

    def generate_report(self):
        """Generate diagnostic report."""
        print(f"\n📊 ULTRATHINK DIAGNOSTIC REPORT")
        print("=" * 50)

        # Memory explosion analysis
        memory_results = [r for r in self.results if "memory_per_entry_kb" in r]
        if memory_results:
            print(f"\n🧠 MEMORY ANALYSIS:")
            print("Size | Memory Δ | Per Entry | Status")
            print("-" * 40)
            for r in memory_results:
                status = (
                    "🚨 CRITICAL"
                    if r.get("critical_issue") == "MEMORY_EXPLOSION"
                    else "✅ Normal"
                )
                print(
                    f"{r['batch_size']:>4} | {r['memory_delta_mb']:>+8.1f}MB | {r['memory_per_entry_kb']:>7.0f}KB | {status}"
                )

        # Timing analysis
        timing_results = [r for r in self.results if "entries_per_sec_perf" in r]
        if timing_results:
            print(f"\n⏱️ TIMING ANALYSIS:")
            print("Run | Duration | Speed (e/s) | Status")
            print("-" * 40)
            for r in timing_results:
                status = (
                    "🚨 CRITICAL"
                    if r.get("critical_issue")
                    in ["IMPOSSIBLE_TIMING", "IMPOSSIBLE_SPEED"]
                    else "✅ Normal"
                )
                print(
                    f"{r['run']:>3} | {r['duration_perf']:>8.4f}s | {r['entries_per_sec_perf']:>9.0f} | {status}"
                )

        # Security analysis
        security_results = [r for r in self.results if "test_case" in r]
        if security_results:
            print(f"\n🛡️ SECURITY ANALYSIS:")
            print("Test Case | Input | Result")
            print("-" * 50)
            for r in security_results:
                status_icon = (
                    "❌"
                    if "SECURITY_FALSE_POSITIVE" in str(r.get("critical_issue", ""))
                    else "✅"
                )
                print(
                    f"{r['test_case']:<15} | {r['input']:<15} | {status_icon} {r['status']}"
                )

        # Critical issues summary
        critical_issues = [r for r in self.results if "critical_issue" in r]
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES FOUND: {len(critical_issues)}")
            for issue in critical_issues:
                print(
                    f"   • {issue['critical_issue']}: {issue.get('test_case', 'Batch ' + str(issue.get('batch_size', 'N/A')))}"
                )
        else:
            print(f"\n✅ No critical issues detected in this test run")


async def main():
    """Run ultrathink diagnostic tests."""
    print("🧠 ULTRATHINK DIAGNOSTIC SYSTEM")
    print("Validating critical issues discovered in deep analysis")
    print("=" * 60)

    diagnostic = UltrathinkDiagnostic()

    # Run all diagnostic tests
    await diagnostic.test_memory_explosion_at_50()
    await diagnostic.test_timing_measurement_corruption()
    await diagnostic.test_security_false_positives()

    # Generate comprehensive report
    diagnostic.generate_report()

    print(f"\n🎯 DIAGNOSTIC COMPLETE")
    print("Review results above to validate ultrathink analysis findings.")


if __name__ == "__main__":
    asyncio.run(main())
