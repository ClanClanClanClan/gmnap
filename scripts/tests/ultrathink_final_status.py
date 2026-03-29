#!/usr/bin/env python3
"""
ULTRATHINK: Final comprehensive status check
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test_categories():
    """Run tests by category and report results."""

    print("=" * 80)
    print("🧠 ULTRATHINK: FINAL STATUS CHECK")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    env = {
        "PYTHONPATH": str(Path.cwd()),
        "GMNAP_TEST_MODE": "true",
        "GMNAP_OFFLINE": "1",
        "DISABLE_FASTTEXT": "1",
    }

    # Test categories in priority order
    test_categories = [
        (
            "Core Tests",
            [
                "tests/unit/test_minimal.py",
                "tests/unit/test_imports_only.py",
            ],
        ),
        (
            "Security Tests",
            [
                "tests/security/test_security_validator.py",
                "tests/security/test_dos_protection.py",
            ],
        ),
        (
            "Performance Tests",
            [
                "tests/performance/test_performance_smoke.py",
                "tests/performance/test_performance_benchmarks.py",
            ],
        ),
        (
            "Paranoid Tests",
            [
                "tests/paranoid/test_schema_paranoid.py",
                "tests/paranoid/test_idempotency_paranoid.py",
            ],
        ),
        (
            "Integration Tests (Quick)",
            [
                "tests/integration/test_pipeline_stages.py",
                "tests/integration/test_v7_core_components.py",
            ],
        ),
    ]

    overall_results = {"total_passed": 0, "total_failed": 0, "total_errors": 0, "categories": {}}

    for category_name, test_files in test_categories:
        print(f"\n📂 {category_name}")
        print("-" * 40)

        category_passed = 0
        category_failed = 0
        category_errors = 0

        for test_file in test_files:
            if not Path(test_file).exists():
                print(f"  ⏭️ {Path(test_file).name}: NOT FOUND")
                continue

            # Run test with timeout
            cmd = [sys.executable, "-m", "pytest", test_file, "-q", "--tb=no", "--timeout=5"]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)

                output = result.stdout + result.stderr

                # Parse results
                import re

                if "passed" in output:
                    match = re.search(r"(\d+) passed", output)
                    if match:
                        passed = int(match.group(1))
                        category_passed += passed
                        overall_results["total_passed"] += passed

                if "failed" in output:
                    match = re.search(r"(\d+) failed", output)
                    if match:
                        failed = int(match.group(1))
                        category_failed += failed
                        overall_results["total_failed"] += failed

                if "error" in output.lower() and "ERROR" in output:
                    match = re.search(r"(\d+) error", output)
                    if match:
                        errors = int(match.group(1))
                        category_errors += errors
                        overall_results["total_errors"] += errors

                # Show result
                total = passed if "passed" in locals() else 0
                total += failed if "failed" in locals() else 0

                if total > 0:
                    status = f"{passed if 'passed' in locals() else 0}/{total}"
                    if "failed" in locals() and failed == 0:
                        print(f"  ✅ {Path(test_file).name}: {status}")
                    else:
                        print(f"  ❌ {Path(test_file).name}: {status}")
                else:
                    print(f"  ⚠️ {Path(test_file).name}: NO TESTS")

            except subprocess.TimeoutExpired:
                print(f"  ⏱️ {Path(test_file).name}: TIMEOUT")
                category_errors += 1
                overall_results["total_errors"] += 1
            except Exception as e:
                print(f"  ❌ {Path(test_file).name}: ERROR - {e}")
                category_errors += 1
                overall_results["total_errors"] += 1

        # Category summary
        overall_results["categories"][category_name] = {
            "passed": category_passed,
            "failed": category_failed,
            "errors": category_errors,
        }

        total_cat = category_passed + category_failed + category_errors
        if total_cat > 0:
            pass_rate = (category_passed / total_cat) * 100
            print(f"  Summary: {category_passed}/{total_cat} ({pass_rate:.1f}%)")

    # Overall summary
    print("\n" + "=" * 80)
    print("📊 OVERALL RESULTS")
    print("=" * 80)

    total_tests = (
        overall_results["total_passed"]
        + overall_results["total_failed"]
        + overall_results["total_errors"]
    )

    print(f"\n✅ Passed: {overall_results['total_passed']}")
    print(f"❌ Failed: {overall_results['total_failed']}")
    print(f"⚠️ Errors: {overall_results['total_errors']}")
    print(f"📊 Total: {total_tests}")

    if total_tests > 0:
        overall_pass_rate = (overall_results["total_passed"] / total_tests) * 100
        print(f"\n🎯 Pass Rate: {overall_pass_rate:.1f}%")

        if overall_pass_rate == 100:
            print("\n🎉 PERFECT! ALL TESTS PASSING!")
            print("✨ ULTRATHINK MISSION ACCOMPLISHED! ✨")
        elif overall_pass_rate >= 90:
            print("\n✅ EXCELLENT! Almost at 100%")
        elif overall_pass_rate >= 80:
            print("\n⚠️ GOOD! Getting close...")
        else:
            print(f"\n❌ {100 - overall_pass_rate:.1f}% still need fixing")

    # By category breakdown
    print("\n📈 By Category:")
    for category, results in overall_results["categories"].items():
        total = results["passed"] + results["failed"] + results["errors"]
        if total > 0:
            rate = (results["passed"] / total) * 100
            print(f"  {category}: {results['passed']}/{total} ({rate:.1f}%)")

    print("\n" + "=" * 80)

    return overall_pass_rate if total_tests > 0 else 0


def main():
    """Main function."""

    pass_rate = run_test_categories()

    if pass_rate == 100:
        print("\n✅ ✅ ✅ SUCCESS: 100% TESTS PASSING! ✅ ✅ ✅")
        sys.exit(0)
    else:
        remaining = 100 - pass_rate
        print(f"\n⚠️ {remaining:.1f}% of tests still need fixing")
        print("\nNext steps:")
        print("1. Fix remaining SecurityValidator tests")
        print("2. Fix any timeout/error tests")
        print("3. Run comprehensive test suite")
        sys.exit(1)


if __name__ == "__main__":
    main()
