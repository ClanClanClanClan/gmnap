#!/usr/bin/env python3
"""
Fix common syntax errors in test files
"""

import os
import re
from pathlib import Path


def fix_misplaced_imports(filepath):
    """Fix misplaced import statements in the middle of code"""
    try:
        with open(filepath, "r") as f:
            content = f.read()

        # Pattern to find misplaced imports after except blocks
        pattern = r"(except.*?:\n.*?print.*?\n)(import sys\nfrom pathlib import Path\nproject_root.*?\nsys\.path.*?\n\n)(.*?traceback\.print_exc)"

        if re.search(pattern, content, re.DOTALL):
            # Remove the misplaced imports
            content = re.sub(pattern, r"\1\3", content, flags=re.DOTALL)

            with open(filepath, "w") as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False


def fix_comment_pass_issue(filepath):
    """Fix lines with both comment and pass statement"""
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        fixed = False
        new_lines = []
        for line in lines:
            # Fix lines with comment and pass on same line
            if (
                "# MOVED:" in line
                and "pass" in line
                and not line.strip().startswith("#")
            ):
                # Split comment and pass
                comment_part = line[: line.rfind("pass")].rstrip()
                new_lines.append(comment_part + "\n")
                new_lines.append("    pass\n")
                fixed = True
            else:
                new_lines.append(line)

        if fixed:
            with open(filepath, "w") as f:
                f.writelines(new_lines)

        return fixed
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False


def fix_indentation_after_except(filepath):
    """Fix indentation issues after except blocks"""
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        fixed = False
        new_lines = []
        in_except = False

        for i, line in enumerate(lines):
            if line.strip().startswith("except "):
                in_except = True
            elif in_except and line.strip() and not line[0].isspace():
                # Line after except should be indented
                if not line.startswith("    "):
                    line = "        " + line
                    fixed = True
                in_except = False
            elif in_except and not line.strip():
                # Empty line, keep checking
                pass
            else:
                in_except = False

            new_lines.append(line)

        if fixed:
            with open(filepath, "w") as f:
                f.writelines(new_lines)

        return fixed
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False


def fix_unexpected_indent(filepath):
    """Fix unexpected indentation errors"""
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()

        fixed = False
        new_lines = []

        for i, line in enumerate(lines):
            # Check for lines that shouldn't be indented
            if i > 0:
                prev_line = lines[i - 1].strip()
                curr_line_stripped = line.strip()

                # If previous line is empty or a regular statement, current shouldn't have extra indent
                if (
                    prev_line
                    and not prev_line.endswith(":")
                    and not prev_line.endswith("\\")
                    and line.startswith("        ")
                    and curr_line_stripped
                    and curr_line_stripped[0].isalpha()
                ):

                    # Reduce indentation
                    line = "    " + line.lstrip()
                    fixed = True

            new_lines.append(line)

        if fixed:
            with open(filepath, "w") as f:
                f.writelines(new_lines)

        return fixed
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False


def main():
    """Main function to fix syntax errors"""
    print("🔧 FIXING TEST SYNTAX ERRORS")
    print("=" * 60)

    # Files identified with syntax errors
    problem_files = [
        "tests/integration/test_rule_3_arabic_patronymic.py",
        "tests/integration/test_v7_pipeline_stages.py",
        "tests/integration/test_rule_13_korean_hyphen_space.py",
        "tests/integration/test_all_regions_comprehensive.py",
        "tests/integration/test_perfect_coverage_v7.py",
        "tests/integration/test_rule_9_east_slavic_patronymic.py",
        "tests/integration/test_v7_pipeline_integration.py",
        "tests/integration/test_v7_integration_complete.py",
    ]

    fixes_applied = 0

    for filepath in problem_files:
        if os.path.exists(filepath):
            print(f"\n📝 Fixing {os.path.basename(filepath)}...")

            if fix_misplaced_imports(filepath):
                print("  ✅ Fixed misplaced imports")
                fixes_applied += 1

            if fix_comment_pass_issue(filepath):
                print("  ✅ Fixed comment/pass issue")
                fixes_applied += 1

            if fix_indentation_after_except(filepath):
                print("  ✅ Fixed except indentation")
                fixes_applied += 1

            if fix_unexpected_indent(filepath):
                print("  ✅ Fixed unexpected indentation")
                fixes_applied += 1

    print("\n" + "=" * 60)
    print(f"✅ Applied {fixes_applied} fixes")

    # Test if syntax errors are resolved
    print("\n🧪 Testing syntax fixes...")
    for filepath in problem_files[:3]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    compile(f.read(), filepath, "exec")
                print(f"  ✅ {os.path.basename(filepath)} - syntax OK")
            except SyntaxError as e:
                print(f"  ❌ {os.path.basename(filepath)} - still has errors: {e}")


if __name__ == "__main__":
    main()
