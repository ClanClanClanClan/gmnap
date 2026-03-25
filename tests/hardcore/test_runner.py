"""
Hardcore test runner for GMNAP comprehensive testing.

Orchestrates all hardcore tests with proper reporting, resource monitoring,
and failure analysis.
"""

import gc
import json
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import pytest


class TestResourceMonitor:
    """Monitor system resources during test execution."""

    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.resource_data = []
        self.monitor_thread = None

    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.resource_data = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)

    def _monitor_loop(self):
        """Resource monitoring loop."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()

                data_point = {
                    "timestamp": time.time(),
                    "memory_rss_mb": memory_info.rss / 1024 / 1024,
                    "memory_vms_mb": memory_info.vms / 1024 / 1024,
                    "cpu_percent": cpu_percent,
                    "num_threads": self.process.num_threads(),
                    "num_fds": self.process.num_fds() if hasattr(self.process, "num_fds") else 0,
                    "gc_objects": len(gc.get_objects()),
                }

                self.resource_data.append(data_point)

            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")

            time.sleep(0.1)  # Monitor every 100ms

    def get_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics."""
        if not self.resource_data:
            return {}

        memory_values = [d["memory_rss_mb"] for d in self.resource_data]
        cpu_values = [d["cpu_percent"] for d in self.resource_data]

        return {
            "duration_seconds": self.resource_data[-1]["timestamp"]
            - self.resource_data[0]["timestamp"],
            "memory_peak_mb": max(memory_values),
            "memory_avg_mb": sum(memory_values) / len(memory_values),
            "cpu_peak_percent": max(cpu_values),
            "cpu_avg_percent": sum(cpu_values) / len(cpu_values),
            "max_threads": max(d["num_threads"] for d in self.resource_data),
            "max_fds": max(d["num_fds"] for d in self.resource_data),
            "gc_objects_peak": max(d["gc_objects"] for d in self.resource_data),
        }


class HardcoreTestRunner:
    """Orchestrate hardcore test execution."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("test_results")
        self.output_dir.mkdir(exist_ok=True)

        self.resource_monitor = TestResourceMonitor()
        self.test_results = []
        self.start_time = None
        self.end_time = None

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.output_dir / "test_execution.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def run_test_suite(self, test_categories: List[str] = None) -> Dict[str, Any]:
        """Run the hardcore test suite."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting hardcore test suite at {self.start_time}")

        # Default test categories
        if test_categories is None:
            test_categories = [
                "invariant_verification",
                "real_world_data",
                "concurrent_chaos",
                "fuzzing_attacks",
                "performance_memory",
                "quality_requirements",
            ]

        # Start resource monitoring
        self.resource_monitor.start_monitoring()

        try:
            # Run each test category
            for category in test_categories:
                self.logger.info(f"Running {category} tests...")

                category_start = time.time()
                category_result = self._run_category(category)
                category_end = time.time()

                category_result["duration_seconds"] = category_end - category_start
                self.test_results.append(category_result)

                # Log results
                self.logger.info(f"Completed {category}: {category_result['status']}")
                if category_result["status"] == "FAILED":
                    self.logger.error(f"Failures in {category}: {category_result['failures']}")

                # Force garbage collection between categories
                gc.collect()

        finally:
            # Stop resource monitoring
            self.resource_monitor.stop_monitoring()
            self.end_time = datetime.now()

        # Generate final report
        return self._generate_final_report()

    def _run_category(self, category: str) -> Dict[str, Any]:
        """Run a specific test category."""
        test_file = f"test_{category}.py"
        test_path = Path(__file__).parent / test_file

        if not test_path.exists():
            return {
                "category": category,
                "status": "SKIPPED",
                "reason": f"Test file not found: {test_file}",
                "failures": [],
                "stats": {},
            }

        # Run pytest on the specific test file
        result = pytest.main(
            [
                str(test_path),
                "-v",
                "-x",  # Stop on first failure for critical tests
                "--tb=short",
                "--json-report",
                f"--json-report-file={self.output_dir / f'{category}_results.json'}",
            ]
        )

        # Parse results
        status = "PASSED" if result == 0 else "FAILED"
        failures = self._parse_failures(category)

        return {
            "category": category,
            "status": status,
            "failures": failures,
            "stats": self._get_category_stats(category),
        }

    def _parse_failures(self, category: str) -> List[Dict[str, Any]]:
        """Parse test failures from results."""
        results_file = self.output_dir / f"{category}_results.json"

        if not results_file.exists():
            return []

        try:
            with open(results_file, "r") as f:
                data = json.load(f)

            failures = []
            for test in data.get("tests", []):
                if test.get("outcome") == "failed":
                    failures.append(
                        {
                            "test_name": test.get("nodeid"),
                            "failure_message": test.get("call", {}).get(
                                "longrepr", "Unknown failure"
                            ),
                            "duration": test.get("call", {}).get("duration", 0),
                        }
                    )

            return failures

        except Exception as e:
            self.logger.error(f"Failed to parse results for {category}: {e}")
            return []

    def _get_category_stats(self, category: str) -> Dict[str, Any]:
        """Get statistics for a test category."""
        results_file = self.output_dir / f"{category}_results.json"

        if not results_file.exists():
            return {}

        try:
            with open(results_file, "r") as f:
                data = json.load(f)

            summary = data.get("summary", {})
            return {
                "total_tests": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "duration": summary.get("duration", 0),
            }

        except Exception as e:
            self.logger.error(f"Failed to get stats for {category}: {e}")
            return {}

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final test report."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        resource_stats = self.resource_monitor.get_stats()

        # Calculate overall stats
        total_tests = sum(result["stats"].get("total_tests", 0) for result in self.test_results)
        total_passed = sum(result["stats"].get("passed", 0) for result in self.test_results)
        total_failed = sum(result["stats"].get("failed", 0) for result in self.test_results)
        total_skipped = sum(result["stats"].get("skipped", 0) for result in self.test_results)

        # Overall status
        overall_status = "PASSED" if total_failed == 0 else "FAILED"

        # Critical failures (invariant violations)
        critical_failures = []
        for result in self.test_results:
            if result["category"] == "invariant_verification" and result["status"] == "FAILED":
                critical_failures.extend(result["failures"])

        report = {
            "overall_status": overall_status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_duration_seconds": total_duration,
            "resource_usage": resource_stats,
            "test_summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "pass_rate": (total_passed / total_tests) * 100 if total_tests > 0 else 0,
            },
            "category_results": self.test_results,
            "critical_failures": critical_failures,
            "quality_gates": self._check_quality_gates(),
        }

        # Save report
        report_file = self.output_dir / "hardcore_test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Generate human-readable report
        self._generate_human_report(report)

        return report

    def _check_quality_gates(self) -> Dict[str, Any]:
        """Check quality gates."""
        resource_stats = self.resource_monitor.get_stats()

        gates = {
            "memory_limit_2gb": {
                "threshold": 2048,  # 2GB in MB
                "actual": resource_stats.get("memory_peak_mb", 0),
                "passed": resource_stats.get("memory_peak_mb", 0) <= 2048,
            },
            "no_memory_leaks": {
                "threshold": 1000,  # Max 1000 additional objects
                "actual": resource_stats.get("gc_objects_peak", 0),
                "passed": resource_stats.get("gc_objects_peak", 0) <= 1000,
            },
            "no_fd_leaks": {
                "threshold": 50,  # Max 50 additional file descriptors
                "actual": resource_stats.get("max_fds", 0),
                "passed": resource_stats.get("max_fds", 0) <= 50,
            },
            "no_invariant_violations": {
                "threshold": 0,  # Zero tolerance for invariant violations
                "actual": len(
                    [
                        r
                        for r in self.test_results
                        if r["category"] == "invariant_verification" and r["status"] == "FAILED"
                    ]
                ),
                "passed": len(
                    [
                        r
                        for r in self.test_results
                        if r["category"] == "invariant_verification" and r["status"] == "FAILED"
                    ]
                )
                == 0,
            },
        }

        return gates

    def _generate_human_report(self, report: Dict[str, Any]):
        """Generate human-readable report."""
        report_file = self.output_dir / "hardcore_test_report.txt"

        with open(report_file, "w") as f:
            f.write("GMNAP HARDCORE TEST SUITE REPORT\n")
            f.write("=" * 50 + "\n\n")

            # Overall status
            f.write(f"Overall Status: {report['overall_status']}\n")
            f.write(f"Start Time: {report['start_time']}\n")
            f.write(f"End Time: {report['end_time']}\n")
            f.write(f"Duration: {report['total_duration_seconds']:.2f} seconds\n\n")

            # Test summary
            summary = report["test_summary"]
            f.write("Test Summary:\n")
            f.write(f"  Total Tests: {summary['total_tests']}\n")
            f.write(f"  Passed: {summary['passed']}\n")
            f.write(f"  Failed: {summary['failed']}\n")
            f.write(f"  Skipped: {summary['skipped']}\n")
            f.write(f"  Pass Rate: {summary['pass_rate']:.1f}%\n\n")

            # Resource usage
            resource = report["resource_usage"]
            f.write("Resource Usage:\n")
            f.write(f"  Peak Memory: {resource.get('memory_peak_mb', 0):.1f} MB\n")
            f.write(f"  Average Memory: {resource.get('memory_avg_mb', 0):.1f} MB\n")
            f.write(f"  Peak CPU: {resource.get('cpu_peak_percent', 0):.1f}%\n")
            f.write(f"  Max Threads: {resource.get('max_threads', 0)}\n")
            f.write(f"  Max File Descriptors: {resource.get('max_fds', 0)}\n\n")

            # Quality gates
            f.write("Quality Gates:\n")
            for gate_name, gate_data in report["quality_gates"].items():
                status = "PASS" if gate_data["passed"] else "FAIL"
                f.write(
                    f"  {gate_name}: {status} (actual: {gate_data['actual']}, threshold: {gate_data['threshold']})\n"
                )
            f.write("\n")

            # Category results
            f.write("Category Results:\n")
            for result in report["category_results"]:
                f.write(f"  {result['category']}: {result['status']}\n")
                if result["failures"]:
                    f.write(f"    Failures: {len(result['failures'])}\n")
                    for failure in result["failures"][:3]:  # Show first 3 failures
                        f.write(f"      - {failure['test_name']}\n")
                    if len(result["failures"]) > 3:
                        f.write(f"      ... and {len(result['failures']) - 3} more\n")
            f.write("\n")

            # Critical failures
            if report["critical_failures"]:
                f.write("CRITICAL FAILURES (INVARIANT VIOLATIONS):\n")
                for failure in report["critical_failures"]:
                    f.write(f"  {failure['test_name']}\n")
                    f.write(f"    {failure['failure_message']}\n")
                f.write("\n")

            # Recommendations
            f.write("Recommendations:\n")
            if report["overall_status"] == "FAILED":
                f.write("  - Address all test failures before deploying to production\n")
            if not report["quality_gates"]["no_invariant_violations"]["passed"]:
                f.write("  - CRITICAL: Fix invariant violations immediately\n")
            if not report["quality_gates"]["memory_limit_2gb"]["passed"]:
                f.write("  - Optimize memory usage to stay under 2GB limit\n")
            if not report["quality_gates"]["no_memory_leaks"]["passed"]:
                f.write("  - Fix memory leaks in long-running operations\n")
            if report["overall_status"] == "PASSED":
                f.write("  - All tests passed! System is ready for deployment\n")


def main():
    """Main entry point for hardcore test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Run GMNAP hardcore test suite")
    parser.add_argument("--output-dir", type=Path, help="Output directory for results")
    parser.add_argument("--categories", nargs="+", help="Test categories to run")
    parser.add_argument("--quick", action="store_true", help="Run quick subset of tests")

    args = parser.parse_args()

    # Determine test categories
    if args.quick:
        categories = ["invariant_verification", "real_world_data"]
    else:
        categories = args.categories

    # Run tests
    runner = HardcoreTestRunner(args.output_dir)
    report = runner.run_test_suite(categories)

    # Print summary
    print("\nHardcore Test Suite Complete!")
    print(f"Overall Status: {report['overall_status']}")
    print(f"Duration: {report['total_duration_seconds']:.2f} seconds")
    print(
        f"Tests: {report['test_summary']['total_tests']} total, {report['test_summary']['passed']} passed, {report['test_summary']['failed']} failed"
    )

    if report["critical_failures"]:
        print(f"\nCRITICAL: {len(report['critical_failures'])} invariant violations found!")
        return 1

    return 0 if report["overall_status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
