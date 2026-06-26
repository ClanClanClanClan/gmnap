#!/usr/bin/env python3
"""
Clean and fix the test suite by removing broken references and fixing imports
"""

import ast
import os
import sys
from pathlib import Path


def analyze_test_file(filepath):
    """Analyze a test file for issues"""
    issues = []
    try:
        with open(filepath, "r") as f:
            content = f.read()
            tree = ast.parse(content)

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if not check_module_exists(module_name):
                        issues.append(f"Missing module: {module_name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if not check_module_exists(node.module):
                        issues.append(f"Missing module: {node.module}")

    except SyntaxError as e:
        issues.append(f"Syntax error: {e}")
    except Exception as e:
        issues.append(f"Parse error: {e}")

    return issues


def check_module_exists(module_name):
    """Check if a module exists in the project"""
    if not module_name:
        return True

    # Skip external modules
    if not module_name.startswith("src."):
        return True

    # Convert module to path
    module_path = module_name.replace(".", "/")

    # Check if it exists as a file or directory
    if os.path.exists(f"{module_path}.py"):
        return True
    if os.path.exists(module_path) and os.path.isdir(module_path):
        return True

    return False


def fix_test_imports(filepath):
    """Fix common import issues in test files"""
    fixes_made = []

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        new_lines = []
        for i, line in enumerate(lines):
            # Fix common issues
            if "from src.v7_compat" in line:
                new_lines.append(line.replace("src.v7_compat", "src.core.pipeline_v7"))
                fixes_made.append(f"Line {i+1}: Fixed v7_compat import")
            elif "from src.core.models" in line:
                new_lines.append(line.replace("src.core.models", "src.core.pipeline"))
                fixes_made.append(f"Line {i+1}: Fixed core.models import")
            else:
                new_lines.append(line)

        if fixes_made:
            with open(filepath, "w") as f:
                f.writelines(new_lines)

    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return fixes_made


def main():
    """Main cleaning function"""
    print("🧹 CLEANING TEST SUITE")
    print("=" * 60)

    test_dirs = ["tests/unit", "tests/integration", "tests/regional"]

    total_files = 0
    files_with_issues = 0
    fixes_applied = 0

    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue

        print(f"\n📁 Checking {test_dir}...")

        for root, dirs, files in os.walk(test_dir):
            # Skip obsolete directories
            if "obsolete" in root:
                continue

            for file in files:
                if file.endswith(".py") and file.startswith("test_"):
                    filepath = os.path.join(root, file)
                    total_files += 1

                    # Analyze the file
                    issues = analyze_test_file(filepath)

                    if issues:
                        files_with_issues += 1
                        print(f"\n  ⚠️  {file}:")
                        for issue in issues[:3]:  # Show first 3 issues
                            print(f"      - {issue}")

                        # Try to fix import issues
                        fixes = fix_test_imports(filepath)
                        if fixes:
                            fixes_applied += len(fixes)
                            print(f"      ✅ Applied {len(fixes)} fixes")

    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"  - Total test files: {total_files}")
    print(f"  - Files with issues: {files_with_issues}")
    print(f"  - Fixes applied: {fixes_applied}")

    # Now check which tests actually pass
    print("\n🧪 RUNNING QUICK TEST CHECK...")
    os.system("python3 -m pytest tests/unit -q --tb=no --timeout=2 2>&1 | tail -5")


if __name__ == "__main__":
    main()
