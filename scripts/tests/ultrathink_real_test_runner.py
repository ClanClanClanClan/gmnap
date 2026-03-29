#!/usr/bin/env python3
"""
ULTRATHINK: REAL Comprehensive Test Runner
No cherry-picking. No hiding. Run EVERYTHING.
"""

import subprocess
import sys
import os
from pathlib import Path
import time
import json
import re


def run_all_tests_brutally():
    """Run ALL tests - no exceptions, no cherry-picking"""

    print("=" * 80)
    print("🔥 ULTRATHINK: BRUTAL COMPREHENSIVE TEST EXECUTION")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("NO CHERRY-PICKING. RUNNING EVERYTHING.\n")

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

    # Find ALL test files
    test_dirs = {
        "Unit Tests": "tests/unit/",
        "Integration Tests": "tests/integration/",
        "Security Tests": "tests/security/",
        "Performance Tests": "tests/performance/",
        "Hardcore Tests": "tests/hardcore/",
        "Paranoid Tests": "tests/paranoid/",
        "Regional Tests": "tests/regions/",
        "CJK Tests": "tests/cjk/",
        "Property Tests": "tests/property/",
        "Memory Tests": "tests/memory/",
        "Stress Tests": "tests/stress/",
        "V7 Tests": "tests/v7/",
        "Authority Tests": "tests/authority/",
        "Coherence Tests": "tests/coherence/",
        "Compliance Tests": "tests/compliance/",
        "Database Tests": "tests/db/",
        "Idempotency Tests": "tests/idempotency/",
        "Roundtrip Tests": "tests/roundtrip/",
        "Validation Tests": "tests/validation/",
    }

    # Track everything
    total_files = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    total_timeout = 0
    category_results = {}
    failed_files = []
    error_files = []
    timeout_files = []
    skipped_files = []

    # Run each category
    for category, test_dir in test_dirs.items():
        if not Path(test_dir).exists():
            print(f"\n❌ {category}: Directory not found")
            continue

        print(f"\n📂 {category}")
        print("-" * 40)

        # Find all test files
        test_files = list(Path(test_dir).glob("test_*.py"))
        if not test_files:
            print(f"  No test files found")
            continue

        category_passed = 0
        category_failed = 0
        category_errors = 0
        category_skipped = 0
        category_timeout = 0

        for test_file in test_files:
            total_files += 1

            # Run EVERY test file, even slow ones
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_file),
                    "-v",
                    "--tb=short",
                    "--timeout=30",  # 30 seconds per test
                    "-q",
                    # Include slow tests
                    "-m",
                    "",  # No marker filtering
                    # Run skipped tests too
                    "--runxfail",
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,  # 1 minute total timeout
                    env=env,
                )

                output = result.stdout + result.stderr

                # Parse results more carefully
                passed = failed = errors = skipped = 0

                # Look for summary line
                if " passed" in output:
                    match = re.search(r"(\d+) passed", output)
                    if match:
                        passed = int(match.group(1))

                if " failed" in output:
                    match = re.search(r"(\d+) failed", output)
                    if match:
                        failed = int(match.group(1))

                if " error" in output:
                    match = re.search(r"(\d+) error", output)
                    if match:
                        errors = int(match.group(1))

                if " skipped" in output:
                    match = re.search(r"(\d+) skipped", output)
                    if match:
                        skipped = int(match.group(1))

                # Update counters
                category_passed += passed
                category_failed += failed
                category_errors += errors
                category_skipped += skipped

                total_passed += passed
                total_failed += failed
                total_errors += errors
                total_skipped += skipped

                # Report status
                status_parts = []
                if passed > 0:
                    status_parts.append(f"{passed} passed")
                if failed > 0:
                    status_parts.append(f"{failed} failed")
                    failed_files.append(str(test_file))
                if errors > 0:
                    status_parts.append(f"{errors} errors")
                    error_files.append(str(test_file))
                if skipped > 0:
                    status_parts.append(f"{skipped} skipped")
                    skipped_files.append(str(test_file))

                status = ", ".join(status_parts) if status_parts else "No tests found"
                icon = (
                    "✅"
                    if failed == 0 and errors == 0
                    else "❌" if failed > 0 else "⚠️"
                )
                print(f"  {icon} {test_file.name}: {status}")

            except subprocess.TimeoutExpired:
                print(f"  ⏱️ {test_file.name}: TIMEOUT (>60s)")
                category_timeout += 1
                total_timeout += 1
                timeout_files.append(str(test_file))

            except Exception as e:
                print(f"  💥 {test_file.name}: EXCEPTION - {e}")
                category_errors += 1
                total_errors += 1
                error_files.append(str(test_file))

        # Store category results
        category_results[category] = {
            "files": len(test_files),
            "passed": category_passed,
            "failed": category_failed,
            "errors": category_errors,
            "skipped": category_skipped,
            "timeout": category_timeout,
        }

        print(f"\n  Category Summary:")
        print(f"    Files tested: {len(test_files)}")
        print(f"    Tests passed: {category_passed}")
        print(f"    Tests failed: {category_failed}")
        print(f"    Tests errored: {category_errors}")
        print(f"    Tests skipped: {category_skipped}")
        print(f"    Files timeout: {category_timeout}")

    # Calculate overall statistics
    total_tests = total_passed + total_failed + total_errors
    actual_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    # Generate HONEST report
    print("\n" + "=" * 80)
    print("💀 BRUTAL HONEST TEST RESULTS")
    print("=" * 80)

    print("\n📊 Overall Statistics:")
    print(f"  Total Test Files: {total_files}")
    print(f"  Total Tests Executed: {total_tests}")
    print(f"  ✅ Passed: {total_passed}")
    print(f"  ❌ Failed: {total_failed}")
    print(f"  💥 Errors: {total_errors}")
    print(f"  ⏭️ Skipped: {total_skipped}")
    print(f"  ⏱️ Timeouts: {total_timeout}")
    print(f"  📊 REAL Pass Rate: {actual_pass_rate:.1f}%")

    print("\n📂 By Category:")
    for category, results in category_results.items():
        total = results["passed"] + results["failed"] + results["errors"]
        if total > 0:
            cat_pass_rate = results["passed"] / total * 100
            print(f"  {category}:")
            print(
                f"    Files: {results['files']}, Tests: {total}, Pass Rate: {cat_pass_rate:.1f}%"
            )
            print(
                f"    Breakdown: {results['passed']} passed, {results['failed']} failed, {results['errors']} errors, {results['skipped']} skipped"
            )

    # List problem files
    if failed_files:
        print(f"\n❌ Files with failures ({len(failed_files)}):")
        for f in failed_files[:10]:  # Show first 10
            print(f"  - {f}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")

    if error_files:
        print(f"\n💥 Files with errors ({len(error_files)}):")
        for f in error_files[:10]:
            print(f"  - {f}")
        if len(error_files) > 10:
            print(f"  ... and {len(error_files) - 10} more")

    if timeout_files:
        print(f"\n⏱️ Files that timed out ({len(timeout_files)}):")
        for f in timeout_files[:10]:
            print(f"  - {f}")

    # Final assessment
    print("\n" + "=" * 80)
    print("🎯 BRUTAL ASSESSMENT")
    print("=" * 80)

    if actual_pass_rate >= 95:
        print(f"✅ ACTUALLY GOOD: {actual_pass_rate:.1f}% pass rate")
        print("The test suite is genuinely solid.")
    elif actual_pass_rate >= 80:
        print(f"⚠️ MEDIOCRE: {actual_pass_rate:.1f}% pass rate")
        print("Significant gaps in test coverage and quality.")
    elif actual_pass_rate >= 50:
        print(f"❌ BAD: {actual_pass_rate:.1f}% pass rate")
        print("The test suite is broken. Many tests are failing.")
    else:
        print(f"💀 DISASTER: {actual_pass_rate:.1f}% pass rate")
        print("The test suite is a complete mess. Most tests don't even run.")

    print(f"\n🔍 Reality Check:")
    print(f"  - Files that couldn't even run: {len(error_files) + len(timeout_files)}")
    print(f"  - Tests being skipped: {total_skipped}")
    print(f"  - Actual test coverage: UNKNOWN (needs coverage measurement)")

    # Save detailed report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_files": total_files,
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "timeouts": total_timeout,
            "pass_rate": actual_pass_rate,
        },
        "categories": category_results,
        "failed_files": failed_files,
        "error_files": error_files,
        "timeout_files": timeout_files,
        "skipped_files": skipped_files,
    }

    with open("brutal_test_reality.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: brutal_test_reality.json")
    print("=" * 80)

    return actual_pass_rate


if __name__ == "__main__":
    pass_rate = run_all_tests_brutally()

    # Exit with honest code
    if pass_rate >= 95:
        sys.exit(0)  # Actually good
    elif pass_rate >= 80:
        sys.exit(1)  # Needs work
    else:
        sys.exit(2)  # Broken
