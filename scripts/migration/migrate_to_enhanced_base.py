#!/usr/bin/env python3
"""
Migration script to update all regional processors to use enhanced base class.
This achieves A+ compliance by fixing all issues found in psychotic testing.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple


def backup_file(filepath: Path) -> None:
    """Create a backup of the file before modification."""
    backup_path = filepath.with_suffix(filepath.suffix + ".backup")
    if not backup_path.exists():
        shutil.copy2(filepath, backup_path)
        print(f"  Backed up: {filepath.name}")


def update_base_class(content: str) -> Tuple[str, bool]:
    """Update base class imports and inheritance."""
    modified = False
    original = content

    # Update import statement
    if "from ...base import RegionSpec" in content:
        content = content.replace(
            "from ...base import RegionSpec",
            "from ...base_enhanced import EnhancedRegionSpec as RegionSpec",
        )
        modified = True
    elif "from src.regions.base import RegionSpec" in content:
        content = content.replace(
            "from src.regions.base import RegionSpec",
            "from src.regions.base_enhanced import EnhancedRegionSpec as RegionSpec",
        )
        modified = True

    # Update RegionRuleError import if needed
    if "from ...base import RegionRuleError" in content:
        content = content.replace(
            "from ...base import RegionRuleError", "from ...base_enhanced import RegionRuleError"
        )
        modified = True
    elif "from src.regions.base import RegionRuleError" in content:
        content = content.replace(
            "from src.regions.base import RegionRuleError",
            "from src.regions.base_enhanced import RegionRuleError",
        )
        modified = True

    # Update combined imports
    if "from ...base import RegionRuleError, RegionSpec" in content:
        content = content.replace(
            "from ...base import RegionRuleError, RegionSpec",
            "from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec",
        )
        modified = True

    return content, modified


def enhance_clean_method(content: str, region_code: str) -> Tuple[str, bool]:
    """Enhance the clean method to use new security features."""
    modified = False

    # Find the clean method
    clean_pattern = r"(    def clean\(self, entry: Dict\[str, Any\]\) -> None:.*?)(?=\n    def \w+|\n\nclass |\Z)"
    clean_match = re.search(clean_pattern, content, re.DOTALL)

    if clean_match:
        clean_method = clean_match.group(1)
        original_clean = clean_method

        # Check if it already calls super().clean()
        if "super().clean(entry)" not in clean_method:
            # Add super().clean() at the beginning of the method
            lines = clean_method.split("\n")

            # Find the first non-comment, non-docstring line after the def
            insert_index = 1
            in_docstring = False
            for i, line in enumerate(lines[1:], 1):
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = not in_docstring
                elif not in_docstring and not stripped.startswith("#") and stripped:
                    insert_index = i
                    break

            # Insert super().clean() call
            indentation = "        "  # 8 spaces for method body
            lines.insert(
                insert_index, f"{indentation}# Apply enhanced base security and normalization"
            )
            lines.insert(insert_index + 1, f"{indentation}super().clean(entry)")
            lines.insert(insert_index + 2, "")

            clean_method = "\n".join(lines)
            content = content.replace(original_clean, clean_method)
            modified = True

        # Update to use comprehensive_unicode_filter for better security
        if "comprehensive_unicode_filter" not in clean_method:
            # Replace basic security checks with comprehensive filtering
            patterns_to_replace = [
                (
                    r"if self\.has_security_risks_lenient\([^)]+\):",
                    "if False:  # Now handled by super().clean()",
                ),
                (
                    r"if self\._has_security_risks\([^)]+\):",
                    "if False:  # Now handled by super().clean()",
                ),
                (
                    r"if any\(ord\(c\) in \[0xFEFF[^\]]+\][^:]+:",
                    "if False:  # Now handled by super().clean()",
                ),
            ]

            for pattern, replacement in patterns_to_replace:
                if re.search(pattern, clean_method):
                    clean_method = re.sub(pattern, replacement, clean_method)
                    content = content.replace(original_clean, clean_method)
                    modified = True
                    original_clean = clean_method

    return content, modified


def enhance_augment_method(content: str, region_code: str) -> Tuple[str, bool]:
    """Enhance the augment method to prevent variant duplication."""
    modified = False

    # Find the augment method
    augment_pattern = r"(    def augment\(self, entry: Dict\[str, Any\]\) -> None:.*?)(?=\n    def \w+|\n\nclass |\Z)"
    augment_match = re.search(augment_pattern, content, re.DOTALL)

    if augment_match:
        augment_method = augment_match.group(1)
        original_augment = augment_method

        # Check if it already has idempotency check
        if "_augmented" not in augment_method and "super().augment(entry)" not in augment_method:
            # Add idempotency check at the beginning
            lines = augment_method.split("\n")

            # Find insertion point
            insert_index = 1
            in_docstring = False
            for i, line in enumerate(lines[1:], 1):
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = not in_docstring
                elif not in_docstring and not stripped.startswith("#") and stripped:
                    insert_index = i
                    break

            # Insert idempotency check
            indentation = "        "
            lines.insert(insert_index, f"{indentation}# Ensure idempotency")
            lines.insert(insert_index + 1, f"{indentation}super().augment(entry)")
            lines.insert(insert_index + 2, "")

            augment_method = "\n".join(lines)
            content = content.replace(original_augment, augment_method)
            modified = True

    return content, modified


def process_region_file(filepath: Path) -> bool:
    """Process a single region processor file."""
    print(f"\nProcessing: {filepath}")

    # Read the file
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Skip if already using enhanced base
    if "base_enhanced" in content:
        print("  Already using enhanced base - skipping")
        return False

    # Backup the file
    backup_file(filepath)

    # Extract region code from path
    region_code = filepath.parent.name.split("_")[-1].upper()
    if region_code.startswith("E"):
        region_code = "E" + filepath.parent.name.split("_")[-1][0]
    elif len(region_code) > 2:
        # Handle cases like a1_anglo_sphere -> A1
        parts = filepath.parent.name.split("_")
        if parts[0][0].isalpha() and parts[0][1:].isdigit():
            region_code = parts[0].upper()

    # Apply updates
    content, base_updated = update_base_class(content)
    content, clean_updated = enhance_clean_method(content, region_code)
    content, augment_updated = enhance_augment_method(content, region_code)

    if base_updated or clean_updated or augment_updated:
        # Write the updated content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(
            f"  ✅ Updated: base={base_updated}, clean={clean_updated}, augment={augment_updated}"
        )
        return True
    else:
        print("  No changes needed")
        return False


def find_all_region_processors() -> List[Path]:
    """Find all regional processor files."""
    base_path = Path("./src/regions")
    processors = []

    # Pattern for processor files
    for group_dir in base_path.glob("*_groups"):
        for region_dir in group_dir.glob("*"):
            processor_file = region_dir / "processor.py"
            if processor_file.exists():
                processors.append(processor_file)

    return sorted(processors)


def main():
    """Main migration function."""
    print("=" * 60)
    print("MIGRATING TO ENHANCED BASE CLASS FOR A+ COMPLIANCE")
    print("=" * 60)

    # Find all regional processors
    processors = find_all_region_processors()
    print(f"\nFound {len(processors)} regional processors")

    # Process each file
    updated_count = 0
    for processor_path in processors:
        if process_region_file(processor_path):
            updated_count += 1

    print("\n" + "=" * 60)
    print(f"MIGRATION COMPLETE: {updated_count}/{len(processors)} files updated")
    print("=" * 60)

    if updated_count > 0:
        print("\n⚠️  IMPORTANT: Please run the psychotic test suite to verify A+ compliance:")
        print("  PYTHONPATH=. python3 tests/integration/test_psychotic_paranoid_ultimate.py")
        print("\n📝 Backups created with .backup extension")
        print("  To restore: rename .backup files back to .py")


if __name__ == "__main__":
    main()
