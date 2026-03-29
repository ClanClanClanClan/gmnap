#!/usr/bin/env python3
"""
ULTRAFIX TEST AUDIT
Brutally honest assessment of what actually works
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class BrutalTestAuditor:
    """Audit tests with brutal honesty"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "categories": {},
            "details": [],
            "critical_findings": [],
        }

    def run_test_file(self, test_path: Path) -> Dict:
        """Run a single test file and return results"""
        result = {
            "file": str(test_path),
            "status": "unknown",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "warnings": 0,
            "output": "",
            "import_error": False,
        }

        # Set environment
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        env["GMNAP_TEST_MODE"] = "true"
        env["GMNAP_OFFLINE"] = "1"

        try:
            # Try to run the test
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_path),
                "-xvs",
                "--tb=no",
                "--json-report",
                "--json-report-file=/tmp/test_report.json",
                "--timeout=30",
            ]

            process = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, env=env
            )

            # Parse output
            output = process.stdout + process.stderr
            result["output"] = output[:1000]  # First 1000 chars

            # Check for import errors
            if "ImportError" in output or "ModuleNotFoundError" in output:
                result["import_error"] = True
                result["status"] = "import_error"

            # Parse test counts
            if "passed" in output:
                # Extract test counts from output
                import re

                match = re.search(r"(\d+) passed", output)
                if match:
                    result["passed"] = int(match.group(1))

                match = re.search(r"(\d+) failed", output)
                if match:
                    result["failed"] = int(match.group(1))

                match = re.search(r"(\d+) error", output)
                if match:
                    result["errors"] = int(match.group(1))

                match = re.search(r"(\d+) skipped", output)
                if match:
                    result["skipped"] = int(match.group(1))

                match = re.search(r"(\d+) warning", output)
                if match:
                    result["warnings"] = int(match.group(1))

            # Determine overall status
            if result["import_error"]:
                result["status"] = "import_error"
            elif result["errors"] > 0:
                result["status"] = "error"
            elif result["failed"] > 0:
                result["status"] = "failed"
            elif result["passed"] > 0:
                result["status"] = "passed"
            else:
                result["status"] = "unknown"

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        except Exception as e:
            result["status"] = "crash"
            result["output"] = str(e)

        return result

    def audit_category(self, category: str, test_dir: Path) -> Dict:
        """Audit all tests in a category"""
        category_results = {
            "total_files": 0,
            "passed_files": 0,
            "failed_files": 0,
            "error_files": 0,
            "import_error_files": 0,
            "timeout_files": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "files": [],
        }

        # Find all test files in category
        test_files = list(test_dir.glob("test_*.py"))
        category_results["total_files"] = len(test_files)

        for test_file in test_files:
            print(f"  Testing {test_file.name}...", end="")
            result = self.run_test_file(test_file)

            # Update counts
            if result["status"] == "passed":
                category_results["passed_files"] += 1
                print(" ✅")
            elif result["status"] == "failed":
                category_results["failed_files"] += 1
                print(" ❌")
            elif result["status"] == "import_error":
                category_results["import_error_files"] += 1
                print(" 🚫 (import error)")
            elif result["status"] == "timeout":
                category_results["timeout_files"] += 1
                print(" ⏰ (timeout)")
            else:
                category_results["error_files"] += 1
                print(" 💥 (error)")

            category_results["passed_tests"] += result["passed"]
            category_results["failed_tests"] += result["failed"]
            category_results["total_tests"] += result["passed"] + result["failed"]

            category_results["files"].append(result)
            self.results["details"].append(result)

        return category_results

    def run_comprehensive_audit(self):
        """Run complete test audit"""
        print("=" * 60)
        print("ULTRAFIX BRUTAL TEST AUDIT")
        print("=" * 60)

        # Define test categories
        test_categories = {
            "unit": Path("tests/unit"),
            "integration": Path("tests/integration"),
            "security": Path("tests/security"),
            "paranoid": Path("tests/paranoid"),
            "paranoid_security": Path("tests/paranoid/security"),
            "performance": Path("tests/performance"),
            "cjk": Path("tests/cjk"),
            "validation": Path("tests/validation"),
            "idempotency": Path("tests/idempotency"),
            "coherence": Path("tests/coherence"),
            "compliance": Path("tests/compliance"),
            "v7": Path("tests/v7"),
        }

        # Audit each category
        for category, path in test_categories.items():
            if path.exists():
                print(f"\n📁 Auditing {category} tests...")
                self.results["categories"][category] = self.audit_category(
                    category, path
                )
            else:
                print(f"\n⚠️  Category {category} not found at {path}")

        # Calculate totals
        total_files = 0
        total_passed_files = 0
        total_failed_files = 0
        total_error_files = 0
        total_import_errors = 0
        total_tests = 0
        total_passed_tests = 0
        total_failed_tests = 0

        for category, data in self.results["categories"].items():
            total_files += data["total_files"]
            total_passed_files += data["passed_files"]
            total_failed_files += data["failed_files"]
            total_error_files += data["error_files"]
            total_import_errors += data["import_error_files"]
            total_tests += data["total_tests"]
            total_passed_tests += data["passed_tests"]
            total_failed_tests += data["failed_tests"]

        self.results["summary"] = {
            "total_files": total_files,
            "passed_files": total_passed_files,
            "failed_files": total_failed_files,
            "error_files": total_error_files,
            "import_error_files": total_import_errors,
            "total_tests": total_tests,
            "passed_tests": total_passed_tests,
            "failed_tests": total_failed_tests,
            "file_success_rate": (
                (total_passed_files / total_files * 100) if total_files > 0 else 0
            ),
            "test_success_rate": (
                (total_passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
        }

        # Identify critical findings
        self.identify_critical_issues()

        # Print summary
        self.print_summary()

        # Save results
        with open("ULTRAFIX_TEST_AUDIT_RESULTS.json", "w") as f:
            json.dump(self.results, f, indent=2)

        return self.results

    def identify_critical_issues(self):
        """Identify the most critical issues"""

        # Find files with import errors
        import_errors = [d for d in self.results["details"] if d["import_error"]]

        if import_errors:
            self.results["critical_findings"].append(
                {
                    "issue": "Import Errors",
                    "severity": "CRITICAL",
                    "count": len(import_errors),
                    "files": [e["file"] for e in import_errors[:5]],  # First 5
                }
            )

        # Find consistently failing categories
        for category, data in self.results["categories"].items():
            if data["total_files"] > 0:
                failure_rate = (data["failed_files"] + data["error_files"]) / data[
                    "total_files"
                ]
                if failure_rate > 0.5:
                    self.results["critical_findings"].append(
                        {
                            "issue": f"{category} tests mostly broken",
                            "severity": "HIGH",
                            "failure_rate": f"{failure_rate*100:.1f}%",
                            "failed_files": data["failed_files"],
                            "error_files": data["error_files"],
                        }
                    )

        # Check for missing security tests
        if "security" in self.results["categories"]:
            sec_data = self.results["categories"]["security"]
            if sec_data["passed_tests"] < 10:
                self.results["critical_findings"].append(
                    {
                        "issue": "Insufficient security test coverage",
                        "severity": "CRITICAL",
                        "passed_tests": sec_data["passed_tests"],
                        "recommendation": "Security testing is dangerously weak",
                    }
                )

    def print_summary(self):
        """Print brutal summary"""
        s = self.results["summary"]

        print("\n" + "=" * 60)
        print("BRUTAL TRUTH SUMMARY")
        print("=" * 60)

        print(f"\n📊 FILE-LEVEL STATISTICS:")
        print(f"  Total test files: {s['total_files']}")
        print(
            f"  ✅ Passed files: {s['passed_files']} ({s['passed_files']/s['total_files']*100:.1f}%)"
            if s["total_files"] > 0
            else "  No files"
        )
        print(f"  ❌ Failed files: {s['failed_files']}")
        print(f"  💥 Error files: {s['error_files']}")
        print(f"  🚫 Import errors: {s['import_error_files']}")

        print(f"\n📈 TEST-LEVEL STATISTICS:")
        print(f"  Total tests: {s['total_tests']}")
        print(
            f"  ✅ Passed tests: {s['passed_tests']} ({s['test_success_rate']:.1f}%)"
            if s["total_tests"] > 0
            else "  No tests"
        )
        print(f"  ❌ Failed tests: {s['failed_tests']}")

        print(f"\n🎯 SUCCESS RATES:")
        print(f"  File success rate: {s['file_success_rate']:.1f}%")
        print(f"  Test success rate: {s['test_success_rate']:.1f}%")

        if self.results["critical_findings"]:
            print(f"\n⚠️  CRITICAL FINDINGS:")
            for finding in self.results["critical_findings"]:
                print(f"  [{finding['severity']}] {finding['issue']}")
                if "count" in finding:
                    print(f"    Count: {finding['count']}")
                if "failure_rate" in finding:
                    print(f"    Failure rate: {finding['failure_rate']}")

        print("\n" + "=" * 60)
        print("BOTTOM LINE:")
        if s["file_success_rate"] < 50:
            print("💀 MORE THAN HALF THE TEST FILES ARE BROKEN")
        elif s["file_success_rate"] < 80:
            print("⚠️  SIGNIFICANT TEST INFRASTRUCTURE PROBLEMS")
        else:
            print("✅ TEST INFRASTRUCTURE MOSTLY FUNCTIONAL")

        print("\n📄 Full results saved to: ULTRAFIX_TEST_AUDIT_RESULTS.json")
        print("=" * 60)


if __name__ == "__main__":
    auditor = BrutalTestAuditor()
    results = auditor.run_comprehensive_audit()

    # Return exit code based on success
    if results["summary"]["file_success_rate"] < 50:
        sys.exit(1)  # Failure
    else:
        sys.exit(0)  # Success
