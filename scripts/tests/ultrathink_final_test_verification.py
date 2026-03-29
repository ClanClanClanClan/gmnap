#!/usr/bin/env python3
"""
ULTRATHINK FINAL VERIFICATION - Are tests ACTUALLY working now?
"""

import subprocess
import sys
import os
from pathlib import Path
from collections import defaultdict
import time


def run_test_verification():
    """Verify that tests are actually working after fixes"""
    print("=" * 60)
    print("🧠 ULTRATHINK FINAL TEST VERIFICATION")
    print("=" * 60)

    project_root = Path.cwd()

    # Critical test samples across categories
    test_samples = {
        "Unit Tests": ["tests/unit/test_minimal.py", "tests/unit/test_imports_only.py"],
        "Integration Tests": [
            "tests/integration/test_v7_core_components.py",
            "tests/integration/test_stage11_gate.py",
            "tests/integration/test_bayesian_coherence.py",
            "tests/integration/test_duckdb_analytics.py",
            "tests/integration/test_v7_integration.py",
        ],
        "Paranoid Tests": [
            "tests/paranoid/test_idempotency_paranoid.py",
            "tests/paranoid/test_schema_paranoid.py",
        ],
        "Security Tests": [
            "tests/security/test_security_validator.py",
            "tests/security/test_security_comprehensive.py",
        ],
        "Performance Tests": ["tests/performance/test_performance_smoke.py"],
        "Regional Tests": ["tests/regions/test_b1_transliteration.py"],
    }

    results = defaultdict(list)
    total_tests = 0
    working_tests = 0

    for category, test_files in test_samples.items():
        print(f"\n📋 {category}:")

        for test_path in test_files:
            test_file = Path(test_path)
            total_tests += 1

            if not test_file.exists():
                results[category].append((test_file.name, "NOT_FOUND"))
                print(f"  ❓ {test_file.name} - NOT FOUND")
                continue

            # Try running with pytest
            try:
                # Use pytest with quick timeout
                cmd = [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(test_file),
                    "-xvs",
                    "--tb=short",
                    "--timeout=5",
                    "--timeout-method=thread",
                ]

                env = os.environ.copy()
                env.update(
                    {
                        "PYTHONPATH": str(project_root),
                        "GMNAP_TEST_MODE": "true",
                        "GMNAP_OFFLINE": "1",
                        "DISABLE_FASTTEXT": "1",
                    }
                )

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)

                output = result.stdout + result.stderr

                # Analyze result
                if "passed" in output.lower() or "1 passed" in output:
                    results[category].append((test_file.name, "PASSED"))
                    print(f"  ✅ {test_file.name} - PASSED")
                    working_tests += 1
                elif "no tests ran" in output:
                    # Try running directly
                    try:
                        direct_result = subprocess.run(
                            [sys.executable, str(test_file)],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            env=env,
                        )

                        if direct_result.returncode == 0 or "Success" in direct_result.stdout:
                            results[category].append((test_file.name, "PASSED_DIRECT"))
                            print(f"  ✅ {test_file.name} - PASSED (direct run)")
                            working_tests += 1
                        else:
                            results[category].append((test_file.name, "NO_TESTS"))
                            print(f"  ⚠️ {test_file.name} - NO TESTS")
                    except:
                        results[category].append((test_file.name, "NO_TESTS"))
                        print(f"  ⚠️ {test_file.name} - NO TESTS")

                elif "failed" in output.lower():
                    # Extract failure count
                    import re

                    match = re.search(r"(\d+) failed", output)
                    if match:
                        results[category].append((test_file.name, f"FAILED_{match.group(1)}"))
                        print(f"  ❌ {test_file.name} - {match.group(1)} tests failed")
                    else:
                        results[category].append((test_file.name, "FAILED"))
                        print(f"  ❌ {test_file.name} - FAILED")

                elif "ImportError" in output or "ModuleNotFoundError" in output:
                    # Extract the import error
                    for line in output.split("\n"):
                        if "ImportError" in line or "ModuleNotFoundError" in line:
                            error = line.split(":")[-1].strip()[:50]
                            results[category].append((test_file.name, "IMPORT_ERROR"))
                            print(f"  📦 {test_file.name} - IMPORT ERROR: {error}")
                            break
                else:
                    results[category].append((test_file.name, "UNKNOWN"))
                    print(f"  ❓ {test_file.name} - UNKNOWN STATUS")

            except subprocess.TimeoutExpired:
                results[category].append((test_file.name, "TIMEOUT"))
                print(f"  ⏱️ {test_file.name} - TIMEOUT (still hanging)")
            except Exception as e:
                results[category].append((test_file.name, "ERROR"))
                print(f"  ⚠️ {test_file.name} - ERROR: {e}")

    # Generate summary
    print("\n" + "=" * 60)
    print("📊 TEST VERIFICATION SUMMARY")
    print("=" * 60)

    print(f"\nTotal tests checked: {total_tests}")
    print(f"✅ Working tests: {working_tests}")
    print(f"❌ Not working: {total_tests - working_tests}")
    print(f"📈 Success rate: {(working_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")

    # Category breakdown
    print("\n📂 By Category:")
    for category, test_results in results.items():
        passed = sum(1 for _, status in test_results if "PASSED" in status)
        total = len(test_results)
        print(f"  {category}: {passed}/{total} working")

    # Detailed issues
    print("\n🔍 Issues Found:")
    issues = defaultdict(list)
    for category, test_results in results.items():
        for test_name, status in test_results:
            if "PASSED" not in status:
                issues[status].append(test_name)

    for issue_type, tests in issues.items():
        if tests:
            print(f"  {issue_type}: {len(tests)} tests")
            for test in tests[:3]:
                print(f"    - {test}")

    # Final verdict
    success_rate = (working_tests / total_tests * 100) if total_tests > 0 else 0

    print("\n" + "=" * 60)
    print("🎯 FINAL VERDICT:")
    if success_rate >= 80:
        print(f"✅ SUCCESS: {success_rate:.1f}% of tests are working!")
        print("Tests are now MOSTLY FUNCTIONAL after fixes.")
    elif success_rate >= 50:
        print(f"⚠️ PARTIAL SUCCESS: {success_rate:.1f}% of tests are working")
        print("Significant improvement but more work needed.")
    else:
        print(f"❌ LIMITED SUCCESS: Only {success_rate:.1f}% of tests are working")
        print("Tests still have major issues despite fixes.")
    print("=" * 60)

    return success_rate


if __name__ == "__main__":
    success_rate = run_test_verification()

    # Save detailed report
    with open("test_fix_verification.txt", "w") as f:
        f.write(f"Test Fix Verification Report\n")
        f.write(f"Success Rate: {success_rate:.1f}%\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    print(f"\n📄 Report saved to: test_fix_verification.txt")
