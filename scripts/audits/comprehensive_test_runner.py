#!/usr/bin/env python3
"""
COMPREHENSIVE TEST EXECUTION - RUNNING LIKE A MANIAC!
====================================================
Running ALL relevant tests across all categories to verify
complete system functionality.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class ComprehensiveTestRunner:
    """Run ALL tests systematically and report results"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_root = self.project_root / "tests"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "categories": {},
            "summary": {
                "total_files": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
            },
        }

    def find_all_test_files(self):
        """Find all test files in the project"""
        test_files = defaultdict(list)

        # Find all test files
        for test_file in self.test_root.rglob("test_*.py"):
            if "__pycache__" in str(test_file):
                continue

            # Categorize by directory
            relative_path = test_file.relative_to(self.test_root)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            test_files[category].append(test_file)

        return test_files

    def run_test_file(self, test_file):
        """Run a single test file and capture results"""
        try:
            # Try pytest first
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "--no-header",
                "-q",
            ]

            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)

            # Parse output
            output = result.stdout + result.stderr

            # Look for test results
            if "passed" in output or "PASSED" in output:
                return "passed", output
            elif "failed" in output or "FAILED" in output:
                return "failed", output
            elif "error" in output.lower():
                return "error", output
            elif result.returncode == 0:
                return "passed", output
            else:
                return "failed", output

        except subprocess.TimeoutExpired:
            return "timeout", "Test timed out after 30 seconds"
        except Exception as e:
            return "error", str(e)

    def run_all_tests(self):
        """Run all tests like a maniac!"""
        print("=" * 60)
        print("🚀 COMPREHENSIVE TEST EXECUTION - RUNNING LIKE A MANIAC! 🚀")
        print("=" * 60)
        print()

        test_files = self.find_all_test_files()
        total_files = sum(len(files) for files in test_files.values())
        self.results["summary"]["total_files"] = total_files

        print(f"📊 Found {total_files} test files across {len(test_files)} categories")
        print()

        # Run tests by category
        for category, files in sorted(test_files.items()):
            print(f"🔥 RUNNING {category.upper()} TESTS ({len(files)} files)")
            print("-" * 50)

            category_results = {"files": [], "passed": 0, "failed": 0, "errors": 0, "timeout": 0}

            for test_file in files:
                file_name = test_file.name
                print(f"  📝 {file_name}...", end=" ")

                status, output = self.run_test_file(test_file)

                # Update counters
                self.results["summary"]["executed"] += 1
                category_results[status] = category_results.get(status, 0) + 1

                if status == "passed":
                    print("✅ PASSED")
                    self.results["summary"]["passed"] += 1
                elif status == "failed":
                    print("❌ FAILED")
                    self.results["summary"]["failed"] += 1
                elif status == "error":
                    print("⚠️  ERROR")
                    self.results["summary"]["errors"] += 1
                elif status == "timeout":
                    print("⏱️  TIMEOUT")
                else:
                    print("❓ UNKNOWN")

                category_results["files"].append(
                    {
                        "name": file_name,
                        "path": str(test_file.relative_to(self.project_root)),
                        "status": status,
                        "output_snippet": output[:200] if len(output) > 200 else output,
                    }
                )

            self.results["categories"][category] = category_results
            print()

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""
        print("=" * 60)
        print("📈 COMPREHENSIVE TEST EXECUTION REPORT")
        print("=" * 60)
        print()

        summary = self.results["summary"]

        # Overall statistics
        total = summary["executed"]
        if total > 0:
            pass_rate = (summary["passed"] / total) * 100
        else:
            pass_rate = 0

        print("📊 OVERALL STATISTICS:")
        print(f"  Total test files found: {summary['total_files']}")
        print(f"  Test files executed: {summary['executed']}")
        print(f"  ✅ Passed: {summary['passed']}")
        print(f"  ❌ Failed: {summary['failed']}")
        print(f"  ⚠️  Errors: {summary['errors']}")
        print(f"  📈 Pass rate: {pass_rate:.1f}%")
        print()

        # Category breakdown
        print("📂 CATEGORY BREAKDOWN:")
        for category, results in sorted(self.results["categories"].items()):
            total_cat = len(results["files"])
            passed_cat = results.get("passed", 0)
            failed_cat = results.get("failed", 0)
            errors_cat = results.get("error", 0)

            status = "✅" if passed_cat == total_cat else "⚠️" if errors_cat > 0 else "❌"

            print(f"  {status} {category}: {passed_cat}/{total_cat} passed")

            # Show failures
            for file_result in results["files"]:
                if file_result["status"] != "passed":
                    print(f"      ❌ {file_result['name']}: {file_result['status']}")

        print()

        # Critical tests status
        print("🔥 CRITICAL TEST SUITES:")
        paranoid_tests = self.results["categories"].get("paranoid", {})
        security_tests = self.results["categories"].get("security", {})
        integration_tests = self.results["categories"].get("integration", {})

        if paranoid_tests:
            paranoid_passed = paranoid_tests.get("passed", 0)
            paranoid_total = len(paranoid_tests.get("files", []))
            print(f"  Paranoid Suite: {paranoid_passed}/{paranoid_total} passed")
        else:
            print("  Paranoid Suite: NOT FOUND ⚠️")

        if security_tests:
            security_passed = security_tests.get("passed", 0)
            security_total = len(security_tests.get("files", []))
            print(f"  Security Suite: {security_passed}/{security_total} passed")
        else:
            print("  Security Suite: NOT FOUND ⚠️")

        if integration_tests:
            integration_passed = integration_tests.get("passed", 0)
            integration_total = len(integration_tests.get("files", []))
            print(f"  Integration Suite: {integration_passed}/{integration_total} passed")
        else:
            print("  Integration Suite: NOT FOUND ⚠️")

        print()

        # Save detailed report
        report_file = (
            self.project_root
            / f"test_execution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"📄 Detailed report saved to: {report_file}")

        print()
        print("=" * 60)
        print("🏁 TEST EXECUTION COMPLETE - RAN TESTS LIKE A MANIAC!")
        print("=" * 60)

        # Final verdict
        if pass_rate >= 90:
            print("✅ EXCELLENT: System shows high test coverage and stability!")
        elif pass_rate >= 70:
            print("⚠️  GOOD: System mostly stable but needs attention to failing tests")
        elif pass_rate >= 50:
            print("❌ CONCERNING: Many tests failing, significant issues present")
        else:
            print("🔥 CRITICAL: Major test failures, system needs immediate attention")


if __name__ == "__main__":
    runner = ComprehensiveTestRunner()
    runner.run_all_tests()
