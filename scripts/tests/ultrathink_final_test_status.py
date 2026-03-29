#!/usr/bin/env python3
"""
ULTRATHINK: Final test status check - Run ALL tests
"""

import subprocess
import sys
import os
from pathlib import Path


def run_all_tests():
    """Run ALL tests and report status."""

    print("=" * 80)
    print("🧠 ULTRATHINK: FINAL TEST STATUS CHECK")
    print("=" * 80)

    # Set test environment
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(Path.cwd()),
            "GMNAP_TEST_MODE": "true",
            "GMNAP_OFFLINE": "1",
            "DISABLE_FASTTEXT": "1",
        }
    )

    # Run pytest on entire test directory
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-q",
        "--tb=no",
        "--timeout=10",
        "--co",  # Only collect tests first
    ]

    # First, collect all tests
    print("\n📊 Collecting all tests...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Count collected tests
    import re

    match = re.search(r"collected (\d+) items?", result.stdout)
    if match:
        total_collected = int(match.group(1))
        print(f"✅ Found {total_collected} tests")
    else:
        print("❌ Could not collect tests")
        print(result.stdout)
        print(result.stderr)
        return

    # Now run the actual tests
    print("\n🚀 Running all tests...")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-q",
        "--tb=no",
        "--timeout=10",
        "-x",  # Stop on first failure to see issues
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)

    output = result.stdout + result.stderr

    # Parse results
    passed = 0
    failed = 0
    errors = 0

    if "passed" in output:
        match = re.search(r"(\d+) passed", output)
        if match:
            passed = int(match.group(1))

    if "failed" in output:
        match = re.search(r"(\d+) failed", output)
        if match:
            failed = int(match.group(1))

    if "error" in output.lower():
        match = re.search(r"(\d+) error", output)
        if match:
            errors = int(match.group(1))

    # Show results
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️ Errors: {errors}")

    total_run = passed + failed + errors
    if total_run > 0:
        pass_rate = (passed / total_run) * 100
        print(f"\n📈 Pass Rate: {pass_rate:.1f}%")

        if pass_rate == 100:
            print("\n🎉 PERFECT! All tests passing!")
        elif pass_rate >= 90:
            print("\n✅ EXCELLENT: Almost there!")
        elif pass_rate >= 80:
            print("\n⚠️ GOOD: Getting close to 100%")
        else:
            print(f"\n❌ NEEDS WORK: Only {pass_rate:.1f}% passing")

    # Show which test files have issues
    if failed > 0 or errors > 0:
        print("\n📁 Tests with issues:")
        # Extract failed test info
        failed_tests = re.findall(r"FAILED (tests/[^:]+)::", output)
        unique_files = set(f.split("::")[0] for f in failed_tests)
        for test_file in sorted(unique_files):
            print(f"  - {test_file}")

    print("=" * 80)

    return pass_rate if total_run > 0 else 0


if __name__ == "__main__":
    pass_rate = run_all_tests()

    # Exit with appropriate code
    if pass_rate == 100:
        print("\n✅ SUCCESS: ALL TESTS PASSING!")
        sys.exit(0)
    else:
        print(f"\n❌ {100 - pass_rate:.1f}% of tests still need fixing")
        sys.exit(1)
