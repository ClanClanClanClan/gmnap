#!/usr/bin/env python3
"""Comprehensive audit of GMNAP system test results."""

import subprocess
import json
import sys
import os
from pathlib import Path


def run_test_file(test_file):
    """Run a single test file and return results."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap"

    cmd = [sys.executable, "-m", "pytest", str(test_file), "--tb=no", "-v"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        output = result.stdout + result.stderr

        # Look for test results in output
        passed = 0
        failed = 0
        errors = 0

        # Look for summary line
        for line in output.split("\n"):
            if " passed" in line or " failed" in line or " error" in line:
                # Extract counts from lines like "20 errors in 0.95s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed" and i > 0:
                        try:
                            passed += int(parts[i - 1])
                        except:
                            pass
                    elif part == "failed" and i > 0:
                        try:
                            failed += int(parts[i - 1])
                        except:
                            pass
                    elif part in ["error", "errors"] and i > 0:
                        try:
                            errors += int(parts[i - 1])
                        except:
                            pass

        return {
            "file": test_file.name,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "output": output if (failed > 0 or errors > 0) else None,
        }
    except Exception as e:
        return {
            "file": test_file.name,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "output": f"Exception: {str(e)}",
        }


def main():
    test_dir = Path("tests/hardcore")
    test_files = sorted(test_dir.glob("test_*.py"))

    print("=== GMNAP Test Suite Audit ===\n")

    results = []

    for test_file in test_files:
        print(f"Running {test_file.name}...", end="", flush=True)
        result = run_test_file(test_file)
        results.append(result)

        if result["errors"] > 0:
            print(f" {result['errors']} errors")
        elif result["failed"] > 0:
            print(f" {result['failed']} failed, {result['passed']} passed")
        elif result["passed"] > 0:
            print(f" {result['passed']} passed")
        else:
            print(" no tests found")

    # Summary
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_errors = sum(r["errors"] for r in results)

    print(f"\n=== Summary ===")
    print(f"Total test files: {len(test_files)}")
    print(f"Tests passed: {total_passed}")
    print(f"Tests failed: {total_failed}")
    print(f"Tests with errors: {total_errors}")

    if (total_passed + total_failed) > 0:
        pass_rate = total_passed / (total_passed + total_failed) * 100
        print(f"Pass rate: {pass_rate:.1f}%")

    # Show details of failures
    if total_failed > 0 or total_errors > 0:
        print("\n=== Failures and Errors ===")
        for result in results:
            if result["failed"] > 0 or result["errors"] > 0:
                print(f"\n{result['file']}:")
                if result["output"]:
                    # Show just the summary
                    lines = result["output"].split("\n")
                    for line in lines:
                        if "ERROR" in line or "FAILED" in line or "::" in line:
                            print(f"  {line}")


if __name__ == "__main__":
    main()
