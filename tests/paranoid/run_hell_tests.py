"""
import pytest
from typing import List
from typing import Optional
from typing import Any
HELL-LEVEL PARANOID TEST RUNNER
===============================

This script runs all hell-level paranoid tests and generates a comprehensive
security and robustness report for the GMNAP system.

Usage:
    python tests/paranoid/run_hell_tests.py [--quick] [--category CATEGORY]
    
Categories:
    - security: Security and injection tests
    - regional: Regional detection tests  
    - performance: Performance and memory tests
    - korean: Korean-specific tests
    - fuzzing: Fuzzing and property tests
    - all: All categories (default)
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import datetime
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class HellTestRunner:
    """Runs all hell-level paranoid tests and generates reports."""

    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode
        self.results = {
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "categories": {},
            "summary": {},
            "system_info": {},
            "recommendations": [],
        }

        # Test categories and their files
        self.test_categories = {
            "security": {
                "name": "Security & Injection Tests",
                "files": ["security/test_injection_hell.py"],
                "description": "Tests for SQL injection, XSS, path traversal, and other security vulnerabilities",
                "critical": True,
            },
            "regional": {
                "name": "Regional Detection Tests",
                "files": ["regional/test_regional_hell.py"],
                "description": "Tests for regional classification accuracy and edge cases",
                "critical": True,
            },
            "performance": {
                "name": "Performance & Memory Tests",
                "files": ["performance/test_performance_hell.py"],
                "description": "Tests for memory leaks, performance degradation, and resource exhaustion",
                "critical": False,
            },
            "korean": {
                "name": "Korean Language Tests",
                "files": ["korean/test_korean_hell.py"],
                "description": "Comprehensive tests for Korean name processing and romanization",
                "critical": False,
            },
            "fuzzing": {
                "name": "Fuzzing & Property Tests",
                "files": ["fuzzing/test_fuzzing_hell.py"],
                "description": "Random input generation and property-based testing",
                "critical": False,
            },
        }

    def collect_system_info(self):
        """Collect system information for the report."""
        import psutil
        import platform

        try:
            self.results["system_info"] = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage("/").free / (1024**3), 2),
                "timestamp": datetime.datetime.now().isoformat(),
            }
        except Exception as e:
            self.results["system_info"] = {"error": str(e)}

    def run_test_category(self, category: str, category_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests for a specific category."""

        print(f"\n{'='*60}")
        print(f"🔥 RUNNING {category_info['name'].upper()} 🔥")
        print(f"{'='*60}")

        category_results = {
            "name": category_info["name"],
            "description": category_info["description"],
            "critical": category_info["critical"],
            "files": [],
            "start_time": time.time(),
            "end_time": None,
            "duration": 0,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "warnings": [],
            "failures": [],
            "status": "running",
        }

        for test_file in category_info["files"]:
            print(f"\n📁 Running {test_file}...")

            file_result = self.run_test_file(test_file)
            category_results["files"].append(file_result)

            # Aggregate results
            category_results["total_tests"] += file_result["total_tests"]
            category_results["passed"] += file_result["passed"]
            category_results["failed"] += file_result["failed"]
            category_results["errors"] += file_result["errors"]
            category_results["skipped"] += file_result["skipped"]
            category_results["warnings"].extend(file_result["warnings"])
            category_results["failures"].extend(file_result["failures"])

        category_results["end_time"] = time.time()
        category_results["duration"] = category_results["end_time"] - category_results["start_time"]

        # Determine status
        if category_results["errors"] > 0:
            category_results["status"] = "error"
        elif category_results["failed"] > 0:
            category_results["status"] = "failed"
        elif category_results["passed"] == 0:
            category_results["status"] = "no_tests"
        else:
            category_results["status"] = "passed"

        print(f"\nPASS {category_info['name']} completed:")
        print(f"   📊 {category_results['passed']}/{category_results['total_tests']} tests passed")
        print(f"   ⏱️  Duration: {category_results['duration']:.1f}s")
        print(f"   📈 Status: {category_results['status']}")

        return category_results

    def run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a specific test file."""

        file_path = Path(__file__).parent / test_file

        file_result = {
            "file": test_file,
            "path": str(file_path),
            "start_time": time.time(),
            "end_time": None,
            "duration": 0,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "warnings": [],
            "failures": [],
            "output": "",
            "return_code": None,
        }

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(file_path),
            "-v",
            "--tb=short",
            "--junit-xml=/tmp/junit_results.xml",
            "-m",
            "paranoid",
        ]

        if self.quick_mode:
            cmd.extend(["--maxfail=5", "-x"])  # Stop on first 5 failures in quick mode

        # Run pytest
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800 if not self.quick_mode else 600,  # 30min / 10min timeout
            )

            file_result["return_code"] = process.returncode
            file_result["output"] = process.stdout + process.stderr

            # Parse output for basic stats
            output_lines = file_result["output"].split("\n")
            for line in output_lines:
                if "failed" in line and "passed" in line:
                    # Try to parse pytest summary line
                    try:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "failed,":
                                file_result["failed"] = int(parts[i - 1])
                            elif part == "passed":
                                file_result["passed"] = int(parts[i - 1])
                            elif part == "error" or part == "errors":
                                file_result["errors"] = int(parts[i - 1])
                            elif part == "skipped":
                                file_result["skipped"] = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass

                elif "FAILED" in line or "ERROR" in line:
                    file_result["failures"].append(line.strip())
                elif "WARNING" in line:
                    file_result["warnings"].append(line.strip())

            file_result["total_tests"] = (
                file_result["passed"]
                + file_result["failed"]
                + file_result["errors"]
                + file_result["skipped"]
            )

        except subprocess.TimeoutExpired:
            file_result["output"] = "Test timed out"
            file_result["return_code"] = -1
            file_result["errors"] = 1
            file_result["failures"].append("Test execution timed out")

        except Exception as e:
            file_result["output"] = f"Error running test: {str(e)}"
            file_result["return_code"] = -1
            file_result["errors"] = 1
            file_result["failures"].append(f"Test execution error: {str(e)}")

        file_result["end_time"] = time.time()
        file_result["duration"] = file_result["end_time"] - file_result["start_time"]

        return file_result

    def generate_recommendations(self):
        """Generate recommendations based on test results."""

        recommendations = []

        # Security recommendations
        security_results = self.results["categories"].get("security", {})
        if security_results.get("status") == "failed":
            recommendations.append(
                {
                    "category": "security",
                    "priority": "CRITICAL",
                    "title": "Security Vulnerabilities Detected",
                    "description": "Hell-level security tests found vulnerabilities that must be fixed before production deployment.",
                    "action": "Review security test failures and implement proper input validation, sanitization, and parameterized queries.",
                }
            )

        # Regional detection recommendations
        regional_results = self.results["categories"].get("regional", {})
        if regional_results.get("status") == "failed":
            recommendations.append(
                {
                    "category": "regional",
                    "priority": "HIGH",
                    "title": "Regional Detection Issues",
                    "description": "Regional classification has significant accuracy issues or edge case failures.",
                    "action": "Review regional detection failures and improve surname matching, script detection, and ambiguity resolution.",
                }
            )

        # Performance recommendations
        performance_results = self.results["categories"].get("performance", {})
        if performance_results.get("status") == "failed":
            recommendations.append(
                {
                    "category": "performance",
                    "priority": "MEDIUM",
                    "title": "Performance or Memory Issues",
                    "description": "System shows performance degradation, memory leaks, or resource exhaustion under stress.",
                    "action": "Profile code for bottlenecks, implement resource limits, and add memory leak detection.",
                }
            )

        # Korean processing recommendations
        korean_results = self.results["categories"].get("korean", {})
        if korean_results.get("status") == "failed":
            recommendations.append(
                {
                    "category": "korean",
                    "priority": "MEDIUM",
                    "title": "Korean Processing Issues",
                    "description": "Korean name processing has accuracy or conversion issues.",
                    "action": "Review Korean romanization mappings, improve bidirectional conversion, and test with more Korean linguistic experts.",
                }
            )

        # Fuzzing recommendations
        fuzzing_results = self.results["categories"].get("fuzzing", {})
        if fuzzing_results.get("status") == "failed":
            recommendations.append(
                {
                    "category": "fuzzing",
                    "priority": "MEDIUM",
                    "title": "Robustness Issues",
                    "description": "System crashes or fails unexpectedly on random or malformed input.",
                    "action": "Add better input validation, error handling, and graceful degradation for edge cases.",
                }
            )

        # Overall recommendations
        total_failures = sum(
            cat.get("failed", 0) + cat.get("errors", 0)
            for cat in self.results["categories"].values()
        )

        if total_failures == 0:
            recommendations.append(
                {
                    "category": "general",
                    "priority": "INFO",
                    "title": "Excellent Hell-Test Results",
                    "description": "System passed all hell-level paranoid tests. Ready for production deployment.",
                    "action": "Continue monitoring in production and run these tests regularly during development.",
                }
            )
        elif total_failures < 10:
            recommendations.append(
                {
                    "category": "general",
                    "priority": "LOW",
                    "title": "Minor Issues Detected",
                    "description": f"System has {total_failures} test failures but is generally robust.",
                    "action": "Address the specific failures found, but system is largely production-ready.",
                }
            )
        else:
            recommendations.append(
                {
                    "category": "general",
                    "priority": "HIGH",
                    "title": "Significant Issues Detected",
                    "description": f"System has {total_failures} test failures indicating systemic issues.",
                    "action": "Conduct thorough review and fixes before considering production deployment.",
                }
            )

        self.results["recommendations"] = recommendations

    def generate_summary(self):
        """Generate overall test summary."""

        total_tests = sum(cat.get("total_tests", 0) for cat in self.results["categories"].values())
        total_passed = sum(cat.get("passed", 0) for cat in self.results["categories"].values())
        total_failed = sum(cat.get("failed", 0) for cat in self.results["categories"].values())
        total_errors = sum(cat.get("errors", 0) for cat in self.results["categories"].values())
        total_skipped = sum(cat.get("skipped", 0) for cat in self.results["categories"].values())

        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        # Determine overall status
        critical_failures = sum(
            (cat.get("failed", 0) + cat.get("errors", 0))
            for cat in self.results["categories"].values()
            if cat.get("critical", False)
        )

        if critical_failures > 0:
            overall_status = "CRITICAL_FAILURES"
        elif total_errors > 0:
            overall_status = "ERRORS"
        elif total_failed > 0:
            overall_status = "FAILURES"
        elif total_tests == 0:
            overall_status = "NO_TESTS"
        else:
            overall_status = "PASSED"

        self.results["summary"] = {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "pass_rate": round(pass_rate, 2),
            "overall_status": overall_status,
            "categories_run": len(self.results["categories"]),
            "critical_failures": critical_failures,
        }

    def print_report(self):
        """Print comprehensive test report."""

        print(f"\n\n{'='*80}")
        print("🔥 HELL-LEVEL PARANOID TEST REPORT 🔥")
        print(f"{'='*80}")

        # Summary
        summary = self.results["summary"]
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   Status: {summary['overall_status']}")
        print(
            f"   Tests: {summary['passed']}/{summary['total_tests']} passed ({summary['pass_rate']:.1f}%)"
        )
        print(f"   Duration: {self.results['duration']:.1f} seconds")
        print(f"   Categories: {summary['categories_run']}")

        if summary["critical_failures"] > 0:
            print(f"   WARN  CRITICAL FAILURES: {summary['critical_failures']}")

        # Category breakdown
        print(f"\n📂 CATEGORY BREAKDOWN:")
        for category, results in self.results["categories"].items():
            status_emoji = {
                "passed": "PASS",
                "failed": "FAIL",
                "error": "💥",
                "no_tests": "⚪",
            }.get(results["status"], "❓")

            critical_marker = " [CRITICAL]" if results.get("critical", False) else ""

            print(f"   {status_emoji} {results['name']}{critical_marker}")
            print(f"      Tests: {results['passed']}/{results['total_tests']} passed")
            print(f"      Duration: {results['duration']:.1f}s")

            if results["failures"]:
                print(f"      Failures: {len(results['failures'])}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if not self.results["recommendations"]:
            print("   No specific recommendations.")
        else:
            for rec in self.results["recommendations"]:
                priority_emoji = {
                    "CRITICAL": "🚨",
                    "HIGH": "WARN",
                    "MEDIUM": "⚡",
                    "LOW": "💡",
                    "INFO": "ℹ️",
                }.get(rec["priority"], "❓")

                print(f"   {priority_emoji} {rec['title']} [{rec['priority']}]")
                print(f"      {rec['description']}")
                print(f"      Action: {rec['action']}")
                print()

        # System info
        print(f"\n🖥️  SYSTEM INFO:")
        sys_info = self.results["system_info"]
        if "error" not in sys_info:
            print(f"   Platform: {sys_info.get('platform', 'Unknown')}")
            print(f"   Python: {sys_info.get('python_version', 'Unknown')}")
            print(f"   CPU: {sys_info.get('cpu_count', 'Unknown')} cores")
            print(
                f"   Memory: {sys_info.get('memory_available_gb', 'Unknown')}/{sys_info.get('memory_total_gb', 'Unknown')} GB available"
            )

        print(f"\n{'='*80}")

        # Final verdict
        if summary["overall_status"] == "PASSED":
            print("🎉 HELL TESTS PASSED! System is extremely robust and ready for production.")
        elif summary["overall_status"] == "FAILURES":
            print("WARN  SOME ISSUES FOUND. Review failures and fix before production.")
        elif summary["overall_status"] == "CRITICAL_FAILURES":
            print("🚨 CRITICAL ISSUES FOUND! DO NOT DEPLOY TO PRODUCTION.")
        else:
            print(f"❓ UNKNOWN STATUS: {summary['overall_status']}")

        print(f"{'='*80}")

    def save_report(self, filename: str = None):
        """Save detailed report to JSON file."""

        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hell_test_report_{timestamp}.json"

        report_path = Path(__file__).parent / filename

        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_path}")
        return report_path

    def run(self, categories: List[str] = None):
        """Run hell tests for specified categories."""

        if categories is None:
            categories = list(self.test_categories.keys())

        print("🔥 HELL-LEVEL PARANOID TESTING INITIATED 🔥")
        print(f"Mode: {'QUICK' if self.quick_mode else 'FULL'}")
        print(f"Categories: {', '.join(categories)}")

        self.results["start_time"] = time.time()
        self.collect_system_info()

        # Run each category
        for category in categories:
            if category not in self.test_categories:
                print(f"WARN  Unknown category: {category}")
                continue

            try:
                category_results = self.run_test_category(category, self.test_categories[category])
                self.results["categories"][category] = category_results

            except Exception as e:
                print(f"💥 Error running category {category}: {e}")
                traceback.print_exc()

                self.results["categories"][category] = {
                    "name": self.test_categories[category]["name"],
                    "status": "error",
                    "error": str(e),
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 1,
                }

        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]

        self.generate_summary()
        self.generate_recommendations()
        self.print_report()

        return self.results


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(description="Run GMNAP hell-level paranoid tests")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run in quick mode (fewer iterations, shorter timeouts)",
    )
    parser.add_argument(
        "--category",
        choices=["security", "regional", "performance", "korean", "fuzzing", "all"],
        default="all",
        help="Test category to run (default: all)",
    )
    parser.add_argument("--output", help="Output file for detailed JSON report")

    args = parser.parse_args()

    # Determine categories to run
    if args.category == "all":
        categories = None  # Run all categories
    else:
        categories = [args.category]

    # Run tests
    runner = HellTestRunner(quick_mode=args.quick)
    results = runner.run(categories=categories)

    # Save report
    report_path = runner.save_report(args.output)

    # Exit with appropriate code
    if results["summary"]["overall_status"] in ["PASSED"]:
        sys.exit(0)
    elif results["summary"]["overall_status"] in ["FAILURES", "ERRORS"]:
        sys.exit(1)
    else:  # CRITICAL_FAILURES or unknown
        sys.exit(2)


if __name__ == "__main__":
    main()
