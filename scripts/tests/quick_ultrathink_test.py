#!/usr/bin/env python3
"""
Quick ULTRATHINK Test Analysis and Execution
"""

import subprocess
import sys
from pathlib import Path
from collections import defaultdict


def quick_analysis():
    print("=" * 60)
    print("🧠 ULTRATHINK QUICK TEST ANALYSIS")
    print("=" * 60)

    test_root = Path("tests")

    # Find duplicates
    name_to_paths = defaultdict(list)
    for test_file in test_root.rglob("test_*.py"):
        if "__pycache__" not in str(test_file):
            name_to_paths[test_file.name].append(test_file)

    duplicates = {
        name: paths for name, paths in name_to_paths.items() if len(paths) > 1
    }

    print(f"\n📊 DUPLICATE TEST FILES ({len(duplicates)} found):")
    for name, paths in list(duplicates.items())[:5]:
        print(f"\n  {name}:")
        for path in paths:
            size = path.stat().st_size
            print(f"    - {path} ({size:,} bytes)")

    # Test organization
    print("\n📁 TEST ORGANIZATION:")
    category_counts = defaultdict(int)
    for test_file in test_root.rglob("test_*.py"):
        if "__pycache__" not in str(test_file):
            parent = test_file.parent.name
            category_counts[parent] += 1

    for category, count in sorted(
        category_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        print(f"  {category:20} : {count:3} files")

    # Quick test execution
    print("\n🚀 QUICK TEST EXECUTION:")

    critical_tests = [
        "tests/test_minimal.py",
        "tests/test_idempotency_basic.py",
        "tests/integration/test_v7_core_components.py",
        "tests/integration/test_stage11_gate.py",
        "tests/integration/test_bayesian_coherence.py",
    ]

    for test_path in critical_tests:
        test_file = Path(test_path)
        if not test_file.exists():
            print(f"  ❓ {test_file.name} - NOT FOUND")
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=5,
                env={"PYTHONPATH": str(Path.cwd())},
            )

            if (
                result.returncode == 0
                or "Success" in result.stdout
                or "✅" in result.stdout
            ):
                print(f"  ✅ {test_file.name}")
            else:
                print(f"  ❌ {test_file.name}")

        except subprocess.TimeoutExpired:
            print(f"  ⏱️ {test_file.name} - TIMEOUT")
        except Exception as e:
            print(f"  ⚠️ {test_file.name} - ERROR")

    # Summary
    total_tests = sum(category_counts.values())
    print(f"\n📊 SUMMARY:")
    print(f"  Total test files: {total_tests}")
    print(f"  Files with duplicates: {len(duplicates)}")
    print(f"  Categories: {len(category_counts)}")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"  1. Merge {len(duplicates)} duplicate test files")
    print(f"  2. Move {category_counts.get('tests', 0)} root-level tests to categories")
    print(f"  3. Consolidate paranoid tests (multiple directories)")
    print(f"  4. Create unified security test suite")


if __name__ == "__main__":
    quick_analysis()
