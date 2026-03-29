#!/usr/bin/env python3
"""
ULTRATHINK: Fix all sys.exit() calls in test files
These cause pytest collection errors
"""

import os
import re
from pathlib import Path


def fix_sys_exits():
    """Remove or wrap sys.exit calls that break pytest"""

    print("=" * 60)
    print("🧠 ULTRATHINK: FIXING SYS.EXIT CALLS IN TESTS")
    print("=" * 60)

    test_dir = Path("tests")
    fixed_count = 0

    # Find all Python test files
    for test_file in test_dir.rglob("*.py"):
        if "__pycache__" in str(test_file):
            continue

        with open(test_file, "r") as f:
            content = f.read()

        original = content

        # Fix patterns that cause collection errors

        # 1. Wrap sys.exit at module level (not in main block)
        if "sys.exit" in content and "if __name__" not in content:
            # Check if it's at module level by looking for indentation
            lines = content.split("\n")
            new_lines = []
            for i, line in enumerate(lines):
                if (
                    "sys.exit" in line
                    and not line.startswith("    ")
                    and not line.startswith("\t")
                ):
                    # This is module-level sys.exit - wrap it
                    new_lines.append(
                        "# " + line + "  # DISABLED: Breaks pytest collection"
                    )
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)

        # 2. For test_ultrafix_validation.py specifically - it has module-level sys.exit
        if test_file.name == "test_ultrafix_validation.py":
            # Find the offending line at module level
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if "sys.exit(0 if overall_percentage" in line and not line.startswith(
                    " "
                ):
                    new_lines.append(
                        "# " + line + "  # DISABLED: Breaks pytest collection"
                    )
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)

        # 3. Ensure sys.exit in main blocks are properly wrapped
        if "if __name__ == '__main__':" in content:
            # sys.exit should be OK here, but let's make sure it's indented
            pass  # These are fine for pytest

        # 4. Comment out module-level execution that might exit
        # Look for patterns like direct function calls at module level that might exit
        lines = content.split("\n")
        new_lines = []
        in_main = False
        in_function = False
        indent_level = 0

        for line in lines:
            # Track if we're in a function or main block
            if line.strip().startswith("def "):
                in_function = True
                indent_level = len(line) - len(line.lstrip())
            elif line.strip().startswith("class "):
                in_function = True
                indent_level = len(line) - len(line.lstrip())
            elif line.strip() == "if __name__ == '__main__':":
                in_main = True
                indent_level = len(line) - len(line.lstrip())
            elif line.strip() and not line.strip().startswith("#"):
                # Check if we've left the function/main block
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and (in_function or in_main):
                    in_function = False
                    in_main = False

            # If we find sys.exit at module level (not in function or main), comment it
            if (
                "sys.exit" in line
                and not in_function
                and not in_main
                and not line.strip().startswith("#")
            ):
                new_lines.append(
                    "    # " + line.strip() + "  # MOVED: Was at module level"
                )
                fixed_count += 1
                print(f"  Fixed: {test_file.relative_to(test_dir)}")
            else:
                new_lines.append(line)

        content = "\n".join(new_lines)

        if content != original:
            with open(test_file, "w") as f:
                f.write(content)

    print(f"\n✅ Fixed {fixed_count} sys.exit issues")

    # Now fix import errors and other issues
    print("\n🔧 FIXING IMPORT ERRORS")
    print("=" * 40)

    # Fix specific known issues
    problem_files = [
        "tests/integration/test_ultrafix_validation.py",
        "tests/idempotency/test_v7_idempotency_compliance.py",
        "tests/unit/generate_test_report.py",
        "tests/unit/ultrathink_comprehensive_testing.py",
        "tests/unit/ultrathink_full_verification.py",
        "tests/unit/ultracheck_maniacal_hell_testing.py",
    ]

    for filepath in problem_files:
        path = Path(filepath)
        if not path.exists():
            continue

        print(f"  Checking: {filepath}")

        with open(path, "r") as f:
            content = f.read()

        original = content

        # Add proper imports at the top if missing
        if "sys.path" not in content and "from src" in content:
            lines = content.split("\n")
            import_added = False
            new_lines = []

            for line in lines:
                if not import_added and (
                    line.startswith("from src") or line.startswith("import src")
                ):
                    # Add path setup before first src import
                    new_lines.append("import sys")
                    new_lines.append("from pathlib import Path")
                    new_lines.append(
                        "sys.path.insert(0, str(Path(__file__).parent.parent.parent))"
                    )
                    new_lines.append("")
                    import_added = True
                new_lines.append(line)

            content = "\n".join(new_lines)

        # Fix any module-level code that runs tests immediately
        if "if __name__" not in content:
            # Check if there's test execution at module level
            test_patterns = [
                r"^test_\w+\(\)",
                r"^main\(\)",
                r"^run_tests\(\)",
                r"^success = ",
            ]

            lines = content.split("\n")
            new_lines = []

            for line in lines:
                skip = False
                for pattern in test_patterns:
                    if re.match(pattern, line.strip()):
                        new_lines.append(
                            "# " + line + "  # DISABLED: Module-level execution"
                        )
                        skip = True
                        break

                if not skip:
                    new_lines.append(line)

            content = "\n".join(new_lines)

        if content != original:
            with open(path, "w") as f:
                f.write(content)
            print(f"    ✅ Fixed: {filepath}")

    print("\n" + "=" * 60)
    print("✅ FIXES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    fix_sys_exits()
