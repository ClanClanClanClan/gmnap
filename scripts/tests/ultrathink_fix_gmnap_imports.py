#!/usr/bin/env python3
"""
ULTRATHINK: Fix all gmnap.* imports to src.*
"""

from pathlib import Path
import re


def fix_gmnap_imports():
    """Replace all gmnap.* imports with src.* imports."""

    print("=" * 80)
    print("🔧 FIXING GMNAP IMPORTS")
    print("=" * 80)

    test_dir = Path("tests")
    fixed_files = 0

    for test_file in test_dir.rglob("*.py"):
        try:
            content = test_file.read_text()
            original_content = content

            # Replace gmnap imports with src imports
            patterns = [
                (r"from gmnap\.core", "from src.core"),
                (r"from gmnap\.regions", "from src.regions"),
                (r"from gmnap\.pipeline", "from src.pipeline"),
                (r"from gmnap\.ops", "from src.ops"),
                (r"from gmnap\.", "from src."),
                (r"import gmnap\.", "import src."),
            ]

            for old_pattern, new_pattern in patterns:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)

            if content != original_content:
                test_file.write_text(content)
                print(f"  Fixed: {test_file.relative_to(test_dir)}")
                fixed_files += 1

        except Exception as e:
            print(f"  Error processing {test_file}: {e}")

    print(f"\n✅ Fixed {fixed_files} files")
    return fixed_files


def fix_other_import_issues():
    """Fix other common import issues in tests."""

    print("\n🔧 Fixing other import issues...")

    test_dir = Path("tests")
    fixes = 0

    # Common import replacements
    replacements = [
        ("from core.pipeline", "from src.core.pipeline"),
        ("from regions.", "from src.regions."),
        ("from pipeline.", "from src.pipeline."),
        ("from ops.", "from src.ops."),
        ("import core.", "import src.core."),
        ("import regions.", "import src.regions."),
        ("import pipeline.", "import src.pipeline."),
        ("import ops.", "import src.ops."),
    ]

    for test_file in test_dir.rglob("*.py"):
        try:
            content = test_file.read_text()
            original_content = content

            for old_import, new_import in replacements:
                content = content.replace(old_import, new_import)

            if content != original_content:
                test_file.write_text(content)
                print(f"  Fixed: {test_file.relative_to(test_dir)}")
                fixes += 1

        except Exception as e:
            print(f"  Error: {e}")

    print(f"  Fixed {fixes} files")
    return fixes


def main():
    """Main function."""

    print("=" * 80)
    print("🧠 ULTRATHINK: IMPORT PATH FIX")
    print("=" * 80)

    total_fixes = 0
    total_fixes += fix_gmnap_imports()
    total_fixes += fix_other_import_issues()

    print(f"\n✅ Total fixes: {total_fixes}")

    print("\n" + "=" * 80)
    print("✅ IMPORT FIX COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
