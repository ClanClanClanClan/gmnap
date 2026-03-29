#!/usr/bin/env python3
"""Fix indentation issues in test files caused by test_repair_tool."""

import re
from pathlib import Path


def fix_test_file(filepath):
    """Fix indentation issues in a single test file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Fix pattern: @pytest.mark.timeout(15) followed by empty lines and badly indented def
    # Pattern 1: Class method decorators with wrong indentation
    pattern1 = re.compile(
        r'^(\s*)"""[^"]*"""\s*\n(@pytest\.mark\.timeout\(\d+\))\s*\n\s*\n\s*def\s', re.MULTILINE
    )

    # Pattern 2: Decorator at wrong indentation level for class methods
    pattern2 = re.compile(
        r"^(@pytest\.mark\.timeout\(\d+\))\s*\n\s*\n(\s+)def\s+test_", re.MULTILINE
    )

    # Pattern 3: Fix class-level decorators
    content = re.sub(
        r'^(\s*)"""[^"]*"""\s*\n@pytest\.mark\.timeout\(\d+\)\s*\n\s*\n\s+def\s+test_',
        r'\1"""\n\n\1@pytest.mark.timeout(15)\n\1def test_',
        content,
        flags=re.MULTILINE,
    )

    # Pattern 4: Fix method-level decorators in classes
    content = re.sub(
        r"^@pytest\.mark\.timeout\(\d+\)\s*\n\s*\n(\s+)def\s+test_",
        r"\n\1@pytest.mark.timeout(15)\n\1def test_",
        content,
        flags=re.MULTILINE,
    )

    # Pattern 5: Remove duplicate empty lines before decorators
    content = re.sub(r"\n\n\n+(\s+@pytest\.mark\.timeout)", r"\n\n\1", content)

    # Write back
    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def main():
    """Fix all test files."""
    test_dir = Path("tests")
    fixed_files = []

    for test_file in test_dir.rglob("test_*.py"):
        try:
            fix_test_file(test_file)
            fixed_files.append(test_file)
        except Exception as e:
            print(f"Error fixing {test_file}: {e}")

    print(f"Fixed {len(fixed_files)} test files")

    # List first 10 fixed files
    for f in fixed_files[:10]:
        print(f"  - {f}")

    if len(fixed_files) > 10:
        print(f"  ... and {len(fixed_files) - 10} more")


if __name__ == "__main__":
    main()
