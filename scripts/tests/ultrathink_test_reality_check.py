#!/usr/bin/env python3
"""
ULTRATHINK REALITY CHECK - Are tests ACTUALLY working?
Let's find out the brutal truth about our test suite.
"""

import subprocess
import sys
import os
from pathlib import Path
from collections import defaultdict
import json
import time


class TestRealityChecker:
    def __init__(self):
        self.project_root = Path.cwd()
        self.test_root = self.project_root / "tests"
        self.results = {
            "passed": [],
            "failed": [],
            "error": [],
            "timeout": [],
            "not_found": [],
            "import_error": [],
        }

    def run_single_test(self, test_file, timeout=10):
        """Run a single test file and categorize result"""
        if not test_file.exists():
            return "not_found", "File does not exist"

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": str(self.project_root)},
            )

            output = result.stdout + result.stderr

            # Check for import errors first
            if "ImportError" in output or "ModuleNotFoundError" in output:
                return "import_error", output[:500]

            # Check for actual test results
            if "passed" in output.lower() and "failed" not in output.lower():
                return "passed", "Tests passed"
            elif "failed" in output.lower() or "FAILED" in output:
                # Extract failure count
                import re

                match = re.search(r"(\d+) failed", output)
                if match:
                    return "failed", f"{match.group(1)} tests failed"
                return "failed", "Tests failed"
            elif "error" in output.lower():
                return "error", "Test execution error"
            elif result.returncode == 0:
                return "passed", "No tests or all passed"
            else:
                return "error", f"Unknown error (exit code: {result.returncode})"

        except subprocess.TimeoutExpired:
            return "timeout", f"Timeout after {timeout}s"
        except Exception as e:
            return "error", str(e)

    def check_all_tests(self):
        """Check ALL test files systematically"""
        print("=" * 60)
        print("🔍 ULTRATHINK TEST REALITY CHECK")
        print("=" * 60)
        print("\nScanning all test files...")

        # Collect all test files
        all_tests = []
        for test_file in self.test_root.rglob("test_*.py"):
            if "__pycache__" not in str(test_file):
                all_tests.append(test_file)

        print(f"Found {len(all_tests)} test files to check\n")

        # Test by category
        categories = defaultdict(list)
        for test_file in all_tests:
            parent = test_file.parent.name
            if parent == "tests":
                parent = "root"
            categories[parent].append(test_file)

        # Run tests category by category
        for category, tests in sorted(categories.items()):
            print(f"\n🔬 Testing {category} ({len(tests)} files)...")

            category_results = defaultdict(int)

            for i, test_file in enumerate(tests):
                # Quick timeout for efficiency
                timeout = 5 if i < 10 else 2  # First 10 get more time

                status, message = self.run_single_test(test_file, timeout)
                self.results[status].append(
                    {"file": str(test_file.relative_to(self.project_root)), "message": message}
                )
                category_results[status] += 1

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"  Tested {i + 1}/{len(tests)}...", end="\r")

            # Category summary
            print(f"  Results: ", end="")
            if category_results["passed"]:
                print(f"✅ {category_results['passed']} passed", end=" ")
            if category_results["failed"]:
                print(f"❌ {category_results['failed']} failed", end=" ")
            if category_results["error"]:
                print(f"⚠️ {category_results['error']} errors", end=" ")
            if category_results["import_error"]:
                print(f"📦 {category_results['import_error']} import errors", end=" ")
            if category_results["timeout"]:
                print(f"⏱️ {category_results['timeout']} timeouts", end=" ")
            print()

        return self.results

    def analyze_results(self):
        """Analyze and report test results"""
        print("\n" + "=" * 60)
        print("📊 TEST REALITY ANALYSIS")
        print("=" * 60)

        total = sum(len(v) for v in self.results.values())

        print(f"\n📈 Overall Statistics ({total} tests):")
        print(
            f"  ✅ Passed:       {len(self.results['passed']):3} ({len(self.results['passed'])*100//total if total else 0}%)"
        )
        print(
            f"  ❌ Failed:       {len(self.results['failed']):3} ({len(self.results['failed'])*100//total if total else 0}%)"
        )
        print(
            f"  📦 Import Error: {len(self.results['import_error']):3} ({len(self.results['import_error'])*100//total if total else 0}%)"
        )
        print(
            f"  ⚠️  Error:        {len(self.results['error']):3} ({len(self.results['error'])*100//total if total else 0}%)"
        )
        print(
            f"  ⏱️  Timeout:      {len(self.results['timeout']):3} ({len(self.results['timeout'])*100//total if total else 0}%)"
        )

        # Show sample failures
        if self.results["failed"]:
            print(f"\n❌ Sample Failed Tests:")
            for test in self.results["failed"][:5]:
                print(f"  - {Path(test['file']).name}: {test['message']}")

        if self.results["import_error"]:
            print(f"\n📦 Sample Import Errors:")
            for test in self.results["import_error"][:5]:
                print(f"  - {Path(test['file']).name}")
                # Extract actual error
                if "ModuleNotFoundError" in test["message"]:
                    import re

                    match = re.search(r"ModuleNotFoundError: (.+)", test["message"])
                    if match:
                        print(f"    {match.group(1)[:80]}")

        # Save detailed results
        with open("test_reality_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed results saved to: test_reality_results.json")

        # Verdict
        pass_rate = (len(self.results["passed"]) / total * 100) if total else 0

        print("\n" + "=" * 60)
        print("🎯 VERDICT:")
        if pass_rate >= 80:
            print(f"✅ GOOD: {pass_rate:.1f}% tests passing")
        elif pass_rate >= 50:
            print(f"⚠️ CONCERNING: Only {pass_rate:.1f}% tests passing")
        else:
            print(f"❌ CRITICAL: Only {pass_rate:.1f}% tests passing!")

        print(f"\n🔧 Main Issues:")
        if len(self.results["import_error"]) > 10:
            print(f"  - Widespread import errors ({len(self.results['import_error'])} files)")
        if len(self.results["failed"]) > 20:
            print(f"  - Many test failures ({len(self.results['failed'])} files)")
        if len(self.results["timeout"]) > 10:
            print(f"  - Performance issues ({len(self.results['timeout'])} timeouts)")

        return pass_rate


def main():
    print("🧠 ULTRATHINK - TEST REALITY CHECK")
    print("Finding out if tests are ACTUALLY working...")
    print()

    checker = TestRealityChecker()

    # Run all tests
    results = checker.check_all_tests()

    # Analyze results
    pass_rate = checker.analyze_results()

    print("\n" + "=" * 60)
    if pass_rate >= 80:
        print("✅ TEST SUITE IS HEALTHY!")
    elif pass_rate >= 50:
        print("⚠️ TEST SUITE NEEDS ATTENTION")
    else:
        print("❌ TEST SUITE IS NOT WORKING PROPERLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
