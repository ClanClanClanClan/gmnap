#!/usr/bin/env python3
"""
Fix the import errors in generated region files.
Change from BaseRegionHandler to RegionSpec.
"""

import re
from pathlib import Path


def fix_region_file(file_path: Path):
    """Fix imports and inheritance in a region file."""

    with open(file_path, "r") as f:
        content = f.read()

    # Fix the import statement
    content = re.sub(
        r"from src\.regions\.base import BaseRegionHandler, RegionRuleError",
        "from ..base import RegionSpec, RegionRuleError",
        content,
    )

    # Fix the class inheritance
    content = re.sub(r"class (\w+)\(BaseRegionHandler\):", r"class \1(RegionSpec):", content)

    # Fix territories parameter (not used in RegionSpec)
    content = re.sub(r",\s*territories=\[.*?\]", "", content, flags=re.DOTALL)

    # Write back
    with open(file_path, "w") as f:
        f.write(content)

    print(f"✅ Fixed: {file_path}")


def main():
    """Fix all generated region files."""

    regions_dir = Path(__file__).parent.parent / "src" / "regions"

    # List of generated files to fix
    files_to_fix = [
        "c_groups/c5_arabic_maghreb.py",
        "c_groups/c6_hebrew_diaspora.py",
        "c_groups/c7_turkic_peoples.py",
        "c_groups/c8_caucasus_muslim.py",
        "c_groups/c9_central_asian_muslim.py",
        "d_groups/d2_dravidian_south.py",
        "d_groups/d3_dravidian_diaspora.py",
        "d_groups/d4_bengali_region.py",
        "d_groups/d5_indic_periphery.py",
        "e_groups/e5_vietnam.py",
        "e_groups/e6_mainland_sea.py",
        "e_groups/e7_maritime_sea.py",
        "f_groups/f1_polynesia.py",
        "f_groups/f2_melanesia.py",
        "f_groups/f3_micronesia.py",
        "f_groups/f4_aboriginal_australia.py",
        "special/h1_historical.py",
        "special/r0_residual_latin_ascii.py",
        "special/z0_quarantine.py",
    ]

    for file_path in files_to_fix:
        full_path = regions_dir / file_path
        if full_path.exists():
            fix_region_file(full_path)
        else:
            print(f"⚠️  Not found: {full_path}")


if __name__ == "__main__":
    main()
