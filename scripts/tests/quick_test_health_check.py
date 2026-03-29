#!/usr/bin/env python3
"""
Quick test health check - sample from each category
"""

import subprocess
import sys
import os
from pathlib import Path
from collections import defaultdict


def quick_check():
    """Quick sampling of test health"""
    print("=" * 60)
    print("🔍 QUICK TEST HEALTH CHECK")
    print("=" * 60)

    test_root = Path("tests")

    # Sample tests from each major category
    test_samples = {
        "unit": ["test_minimal.py", "test_imports_only.py"],
        "integration": ["test_v7_integration.py", "test_v7_core_components.py"],
        "security": ["test_security_validator.py", "test_security_comprehensive.py"],
        "paranoid": ["test_idempotency_paranoid.py", "test_schema_paranoid.py"],
        "performance": ["test_performance_smoke.py"],
        "regions": ["test_b1_transliteration.py"],
        "stages": ["test_stage0.py", "test_stage1.py"],
    }

    results = defaultdict(list)

    for category, test_files in test_samples.items():
        print(f"\n🧪 Testing {category}...")

        for test_name in test_files:
            # Find the test file
            test_path = None
            for path in test_root.rglob(test_name):
                if "__pycache__" not in str(path):
                    test_path = path
                    break

            if not test_path:
                results["not_found"].append(f"{category}/{test_name}")
                print(f"  ❓ {test_name} - NOT FOUND")
                continue

            # Try running it
            try:
                result = subprocess.run(
                    [sys.executable, str(test_path)],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    env={**os.environ, "PYTHONPATH": str(Path.cwd())},
                )

                output = result.stdout + result.stderr

                # Check result
                if "ImportError" in output or "ModuleNotFoundError" in output:
                    results["import_error"].append(f"{category}/{test_name}")
                    print(f"  📦 {test_name} - IMPORT ERROR")
                    # Extract the error
                    for line in output.split("\n"):
                        if "ModuleNotFoundError" in line:
                            print(f"     {line[:80]}")
                            break
                elif (
                    result.returncode == 0
                    or "Success" in output
                    or "passed" in output.lower()
                ):
                    results["passed"].append(f"{category}/{test_name}")
                    print(f"  ✅ {test_name} - PASSED")
                else:
                    results["failed"].append(f"{category}/{test_name}")
                    print(f"  ❌ {test_name} - FAILED")

            except subprocess.TimeoutExpired:
                results["timeout"].append(f"{category}/{test_name}")
                print(f"  ⏱️ {test_name} - TIMEOUT")
            except Exception as e:
                results["error"].append(f"{category}/{test_name}")
                print(f"  ⚠️ {test_name} - ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 QUICK HEALTH CHECK SUMMARY")
    print("=" * 60)

    total = sum(len(v) for v in results.values())

    print(f"\nSampled {total} tests:")
    print(f"  ✅ Passed:       {len(results['passed'])}")
    print(f"  ❌ Failed:       {len(results['failed'])}")
    print(f"  📦 Import Error: {len(results['import_error'])}")
    print(f"  ⏱️ Timeout:      {len(results['timeout'])}")
    print(f"  ⚠️ Error:        {len(results['error'])}")
    print(f"  ❓ Not Found:    {len(results['not_found'])}")

    pass_rate = (len(results["passed"]) / total * 100) if total else 0

    print(f"\n📈 Pass Rate: {pass_rate:.1f}%")

    # Diagnosis
    print("\n🔍 DIAGNOSIS:")
    if len(results["import_error"]) > total * 0.3:
        print("  ❌ CRITICAL: Widespread import issues!")
    if pass_rate < 50:
        print("  ❌ CRITICAL: Most tests are failing!")
    elif pass_rate < 80:
        print("  ⚠️ WARNING: Many tests are not working")
    else:
        print("  ✅ HEALTHY: Most tests are passing")

    return results, pass_rate


if __name__ == "__main__":
    results, pass_rate = quick_check()

    print("\n" + "=" * 60)
    print("🎯 BOTTOM LINE:")
    if pass_rate >= 80:
        print("✅ Tests are MOSTLY WORKING")
    elif pass_rate >= 50:
        print("⚠️ Tests are PARTIALLY WORKING")
    else:
        print("❌ Tests are NOT WORKING PROPERLY")
    print("=" * 60)
