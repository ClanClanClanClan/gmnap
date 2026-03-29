#!/usr/bin/env python3
"""
QUICK TEST AUDIT
Fast assessment of test file status without running them.
"""

from pathlib import Path
import re


def audit_test_files():
    """Quick audit of test files."""

    print("=" * 70)
    print("QUICK TEST AUDIT - File Analysis Only")
    print("=" * 70)
    print()

    # Find all test files
    test_files = list(Path(".").glob("**/test_*.py"))
    test_files = [f for f in test_files if "venv" not in str(f) and "__pycache__" not in str(f)]

    stats = {
        "total": len(test_files),
        "has_tests": 0,
        "empty": 0,
        "import_errors": 0,
        "by_category": {},
    }

    for test_file in sorted(test_files):
        # Get category
        if "tests/" in str(test_file):
            parts = str(test_file).split("tests/")[1].split("/")
            category = parts[0] if len(parts) > 1 else "root"
        else:
            category = "other"

        if category not in stats["by_category"]:
            stats["by_category"][category] = {"total": 0, "has_tests": 0, "empty": 0}

        stats["by_category"][category]["total"] += 1

        # Check file content
        try:
            content = test_file.read_text()

            # Count test functions/methods
            test_count = len(re.findall(r"def test_\w+", content))

            # Check for common issues
            has_import_error = "from src.regions.manager import" in content  # Old import

            if test_count > 0:
                stats["has_tests"] += 1
                stats["by_category"][category]["has_tests"] += 1
                status = f"✅ {test_count} tests"
            else:
                stats["empty"] += 1
                stats["by_category"][category]["empty"] += 1
                status = "⚪ EMPTY"

            if has_import_error:
                stats["import_errors"] += 1
                status += " ⚠️"

            print(f"{test_file.name:<50} {status}")

        except Exception as e:
            print(f"{test_file.name:<50} 🔴 ERROR: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n📊 OVERALL:")
    print(f"  Total test files:        {stats['total']}")
    print(
        f"  Files with tests:        {stats['has_tests']} ({stats['has_tests']/stats['total']*100:.1f}%)"
    )
    print(f"  Empty files:             {stats['empty']} ({stats['empty']/stats['total']*100:.1f}%)")
    print(f"  Files with import issues: {stats['import_errors']}")

    print(f"\n📁 BY CATEGORY:")
    for category, cat_stats in sorted(stats["by_category"].items()):
        print(f"  {category:<15} {cat_stats['has_tests']}/{cat_stats['total']} files with tests")

    print("\n🎯 VERDICT:")
    if stats["has_tests"] < stats["total"] * 0.3:
        print("  💀 LESS THAN 30% OF TEST FILES HAVE ACTUAL TESTS!")
    elif stats["has_tests"] < stats["total"] * 0.5:
        print("  🔴 LESS THAN HALF THE TEST FILES HAVE TESTS")
    elif stats["has_tests"] < stats["total"] * 0.8:
        print("  ⚠️  MANY TEST FILES ARE EMPTY")
    else:
        print("  ✅ MOST TEST FILES HAVE ACTUAL TESTS")

    print("=" * 70)


if __name__ == "__main__":
    audit_test_files()
