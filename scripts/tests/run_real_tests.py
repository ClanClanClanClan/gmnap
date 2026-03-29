#!/usr/bin/env python3
"""
HONEST TEST RUNNER
Shows the real state of all tests - no cherry-picking, no deception.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


class HonestTestRunner:
    """Run all tests and report honestly."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "categories": {},
            "summary": {
                "total_files": 0,
                "files_with_tests": 0,
                "files_empty": 0,
                "files_with_errors": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
            },
        }

    def find_test_files(self):
        """Find all test files in the project."""
        test_dirs = [
            "tests/unit",
            "tests/integration",
            "tests/security",
            "tests/performance",
            "tests/paranoid",
            "tests/validation",
            "tests/cjk",
            "tests/v7",
            "tests/compliance",
            "tests",
        ]

        all_test_files = []
        for test_dir in test_dirs:
            path = Path(test_dir)
            if path.exists():
                # Find all test_*.py files
                test_files = list(path.glob("**/test_*.py"))
                all_test_files.extend(test_files)

        # Remove duplicates
        all_test_files = list(set(all_test_files))
        return sorted(all_test_files)

    def check_if_empty(self, file_path):
        """Check if a test file has actual tests."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Check for actual test functions/classes
            has_tests = False
            if "def test_" in content:
                has_tests = True
            elif "class Test" in content and "def test_" in content:
                has_tests = True
            elif "@pytest.mark" in content and "def test_" in content:
                has_tests = True

            # Check for import errors that would prevent running
            has_import_issues = False
            if "from src." in content or "import src.":
                # Try to import the module to check
                try:
                    module_name = file_path.stem
                    spec = __import__(module_name)
                except:
                    has_import_issues = True

            return not has_tests, has_import_issues

        except Exception as e:
            return False, True

    def run_test_file(self, test_path):
        """Run a single test file and get results."""
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        env["GMNAP_OFFLINE"] = "1"
        env["GMNAP_TEST_MODE"] = "true"

        cmd = [sys.executable, "-m", "pytest", str(test_path), "--tb=no", "--no-header", "-q"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)

            output = result.stdout + result.stderr

            # Parse output for results
            passed = failed = skipped = 0

            if "passed" in output:
                # Extract counts
                import re

                match = re.search(r"(\d+) passed", output)
                if match:
                    passed = int(match.group(1))

                match = re.search(r"(\d+) failed", output)
                if match:
                    failed = int(match.group(1))

                match = re.search(r"(\d+) skipped", output)
                if match:
                    skipped = int(match.group(1))

            # Check for import errors
            if "ImportError" in output or "ModuleNotFoundError" in output:
                return "import_error", 0, 0, 0
            elif "ERROR" in output and passed == 0 and failed == 0:
                return "error", 0, 0, 0
            elif passed > 0 or failed > 0:
                return "has_tests", passed, failed, skipped
            else:
                return "no_tests", 0, 0, 0

        except subprocess.TimeoutExpired:
            return "timeout", 0, 0, 0
        except Exception:
            return "error", 0, 0, 0

    def run_all_tests(self):
        """Run all tests and collect results."""
        print("=" * 70)
        print("HONEST TEST RUNNER - THE REAL STATE OF TESTS")
        print("=" * 70)
        print()

        test_files = self.find_test_files()
        self.results["summary"]["total_files"] = len(test_files)

        print(f"Found {len(test_files)} test files")
        print()

        # Group by directory
        by_dir = {}
        for test_file in test_files:
            dir_name = test_file.parent.name
            if test_file.parent.parent.name == "tests":
                dir_name = f"{test_file.parent.parent.name}/{dir_name}"

            if dir_name not in by_dir:
                by_dir[dir_name] = []
            by_dir[dir_name].append(test_file)

        # Run tests by category
        for category, files in sorted(by_dir.items()):
            print(f"\n📁 {category} ({len(files)} files)")
            print("-" * 50)

            category_results = {
                "files": len(files),
                "with_tests": 0,
                "empty": 0,
                "errors": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            }

            for test_file in files:
                # Check if empty first
                is_empty, has_import_issues = self.check_if_empty(test_file)

                if is_empty:
                    print(f"  ⚪ {test_file.name:<40} EMPTY")
                    category_results["empty"] += 1
                    self.results["summary"]["files_empty"] += 1
                else:
                    # Run the test
                    status, passed, failed, skipped = self.run_test_file(test_file)

                    if status == "import_error":
                        print(f"  🔴 {test_file.name:<40} IMPORT ERROR")
                        category_results["errors"] += 1
                        self.results["summary"]["files_with_errors"] += 1
                    elif status == "error":
                        print(f"  🔴 {test_file.name:<40} ERROR")
                        category_results["errors"] += 1
                        self.results["summary"]["files_with_errors"] += 1
                    elif status == "timeout":
                        print(f"  ⏰ {test_file.name:<40} TIMEOUT")
                        category_results["errors"] += 1
                        self.results["summary"]["files_with_errors"] += 1
                    elif status == "no_tests":
                        print(f"  ⚪ {test_file.name:<40} NO TESTS")
                        category_results["empty"] += 1
                        self.results["summary"]["files_empty"] += 1
                    else:
                        # Has actual tests
                        category_results["with_tests"] += 1
                        category_results["passed"] += passed
                        category_results["failed"] += failed
                        category_results["skipped"] += skipped

                        self.results["summary"]["files_with_tests"] += 1
                        self.results["summary"]["total_passed"] += passed
                        self.results["summary"]["total_failed"] += failed
                        self.results["summary"]["total_skipped"] += skipped

                        if failed == 0 and passed > 0:
                            symbol = "✅"
                        elif failed > 0 and passed > 0:
                            symbol = "⚠️"
                        else:
                            symbol = "❌"

                        print(f"  {symbol} {test_file.name:<40} {passed} passed, {failed} failed")

            self.results["categories"][category] = category_results

        # Print summary
        self.print_summary()

        # Save results
        with open("honest_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

    def print_summary(self):
        """Print honest summary."""
        s = self.results["summary"]

        print("\n" + "=" * 70)
        print("BRUTAL HONESTY SUMMARY")
        print("=" * 70)

        print(f"\n📊 FILE STATISTICS:")
        print(f"  Total test files found:     {s['total_files']}")
        print(
            f"  Files with actual tests:    {s['files_with_tests']} ({s['files_with_tests']/s['total_files']*100:.1f}%)"
            if s["total_files"] > 0
            else ""
        )
        print(
            f"  Empty/no test files:        {s['files_empty']} ({s['files_empty']/s['total_files']*100:.1f}%)"
            if s["total_files"] > 0
            else ""
        )
        print(
            f"  Files with errors:          {s['files_with_errors']} ({s['files_with_errors']/s['total_files']*100:.1f}%)"
            if s["total_files"] > 0
            else ""
        )

        print(f"\n📈 TEST STATISTICS:")
        total_tests = s["total_passed"] + s["total_failed"]
        print(f"  Total tests run:            {total_tests}")
        print(
            f"  Tests passed:               {s['total_passed']} ({s['total_passed']/total_tests*100:.1f}%)"
            if total_tests > 0
            else "  No tests run"
        )
        print(
            f"  Tests failed:               {s['total_failed']} ({s['total_failed']/total_tests*100:.1f}%)"
            if total_tests > 0
            else ""
        )
        print(f"  Tests skipped:              {s['total_skipped']}")

        print(f"\n🎯 REALITY CHECK:")
        if s["files_with_tests"] < s["total_files"] * 0.5:
            print("  💀 MORE THAN HALF THE TEST FILES ARE EMPTY OR BROKEN")
        elif s["files_with_tests"] < s["total_files"] * 0.8:
            print("  ⚠️  SIGNIFICANT NUMBER OF TEST FILES ARE NOT FUNCTIONAL")
        else:
            print("  ✅ MOST TEST FILES CONTAIN ACTUAL TESTS")

        if total_tests > 0:
            pass_rate = s["total_passed"] / total_tests * 100
            if pass_rate < 50:
                print("  💀 LESS THAN HALF THE TESTS ARE PASSING")
            elif pass_rate < 80:
                print("  ⚠️  SIGNIFICANT NUMBER OF TESTS FAILING")
            else:
                print("  ✅ GOOD TEST PASS RATE")

        print("\n" + "=" * 70)
        print("Results saved to: honest_test_results.json")
        print("=" * 70)


if __name__ == "__main__":
    runner = HonestTestRunner()
    runner.run_all_tests()
