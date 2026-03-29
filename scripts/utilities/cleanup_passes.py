#!/usr/bin/env python3
"""
Clean up unnecessary pass statements added by fix script.
"""

import re
from pathlib import Path


def cleanup_passes(file_path: str) -> bool:
    """Remove unnecessary pass statements."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Remove patterns like:
        # if condition:
        #
        #     pass
        #     actual_code
        pattern = r"(\n\s*pass\n)(\s*[^\s])"
        content = re.sub(pattern, r"\n\2", content)

        # Remove duplicate passes
        content = re.sub(r"(\n\s*pass\n\s*pass\n)", r"\n    pass\n", content)

        # Remove pass before actual code on same indentation
        pattern2 = r"(\n)([ ]*)(pass\n)(\2)([^\s])"
        content = re.sub(pattern2, r"\1\2\5", content)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False


def main():
    """Clean up all region files."""
    print("🧹 CLEANING UP UNNECESSARY PASSES")
    print("=" * 60)

    # Find all region files
    region_files = []
    for group in ["a", "b", "c", "d", "e", "f", "g"]:
        group_dir = Path(f"src/regions/{group}_groups")
        if group_dir.exists():
            region_files.extend(group_dir.glob("*.py"))
            region_files.extend(group_dir.glob("*/processor.py"))

    # Add special regions
    special_dir = Path("src/regions/special")
    if special_dir.exists():
        region_files.extend(special_dir.glob("*.py"))

    cleaned_count = 0
    for file_path in region_files:
        if "__init__" not in str(file_path) and "base.py" not in str(file_path):
            if cleanup_passes(str(file_path)):
                print(f"✅ Cleaned {file_path.name}")
                cleaned_count += 1

    print(f"\nCleaned {cleaned_count} files")


if __name__ == "__main__":
    main()
