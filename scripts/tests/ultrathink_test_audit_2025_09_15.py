#!/usr/bin/env python3
"""
ULTRATHINK Test Suite Audit
Analyzes test health and identifies specific issues
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class TestAuditor:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "timeout": 0,
                "import_error": 0,
                "syntax_error": 0,
                "not_found": 0,
                "unknown": 0,
                "error": 0,
            },
            "categories": defaultdict(
                lambda: {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "timeout": 0,
                    "import_error": 0,
                    "syntax_error": 0,
                    "not_found": 0,
                    "unknown": 0,
                    "error": 0,
                }
            ),
            "details": [],
        }

    def audit_test_file(self, test_path):
        """Audit a single test file."""
        result = {
            "file": str(test_path),
            "category": test_path.parent.name,
            "status": "unknown",
            "error": None,
            "duration": 0,
        }

        if not test_path.exists():
            result["status"] = "not_found"
            return result

        # Try to run the test with timeout
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--no-header",
            "-x",
        ]

        start_time = time.time()
        try:
            # Run with 5 second timeout
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OFFLINE": "1"},
            )

            duration = time.time() - start_time
            result["duration"] = duration

            output = proc.stdout + proc.stderr

            # Check for import errors
            if "ModuleNotFoundError" in output or "ImportError" in output:
                result["status"] = "import_error"
                # Extract the error message
                for line in output.split("\n"):
                    if "ModuleNotFoundError" in line or "ImportError" in line:
                        result["error"] = line.strip()
                        break
            elif "FAILED" in output or proc.returncode != 0:
                result["status"] = "failed"
                # Extract failure reason
                for line in output.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        result["error"] = line.strip()
                        break
            elif "passed" in output.lower():
                result["status"] = "passed"
            else:
                result["status"] = "unknown"
                result["error"] = "Could not determine test status"

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = "Test execution timeout (5s)"
            result["duration"] = 5.0
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def audit_sample_tests(self, sample_size=30):
        """Audit a sample of test files."""
        test_dir = Path("tests")

        if not test_dir.exists():
            print("Tests directory not found!")
            return

        # Find all test files
        test_files = sorted(test_dir.rglob("test_*.py"))

        # Sample evenly across categories
        categories = defaultdict(list)
        for tf in test_files:
            categories[tf.parent.name].append(tf)

        # Select sample
        sample = []
        for cat, files in categories.items():
            # Take up to 3 from each category
            sample.extend(files[: min(3, len(files))])

        sample = sample[:sample_size]

        print(f"Found {len(test_files)} test files")
        print(f"Auditing sample of {len(sample)} tests...")
        print("=" * 60)

        for i, test_file in enumerate(sample, 1):
            print(f"[{i}/{len(sample)}] {test_file.relative_to(test_dir)}", end="... ")

            result = self.audit_test_file(test_file)

            self.results["summary"]["total"] += 1
            self.results["summary"][result["status"]] += 1

            category = result["category"]
            self.results["categories"][category]["total"] += 1
            self.results["categories"][category][result["status"]] += 1

            self.results["details"].append(result)

            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "timeout": "⏱️",
                "import_error": "📦",
                "syntax_error": "🔴",
                "not_found": "❓",
                "error": "💥",
                "unknown": "❓",
            }
            print(f"{status_emoji.get(result['status'], '❓')} {result['status']}")

            if result["status"] != "passed" and result.get("error"):
                print(f"  └─ {result['error'][:100]}")

    def generate_report(self):
        """Generate report."""
        print("\n" + "=" * 80)
        print("TEST AUDIT REPORT")
        print("=" * 80)

        summary = self.results["summary"]
        total = summary["total"]

        if total == 0:
            print("No tests audited!")
            return

        def pct(val):
            return f"{val}/{total} ({100*val/total:.1f}%)"

        print("\nOVERALL (Sample):")
        print(f"  ✅ Passed:       {pct(summary['passed'])}")
        print(f"  ❌ Failed:       {pct(summary['failed'])}")
        print(f"  ⏱️ Timeout:      {pct(summary['timeout'])}")
        print(f"  📦 Import Error: {pct(summary['import_error'])}")

        # Save results
        output_file = (
            f"ultrathink_test_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results: {output_file}")


def main():
    auditor = TestAuditor()
    auditor.audit_sample_tests(30)
    auditor.generate_report()


if __name__ == "__main__":
    main()
