#!/usr/bin/env python3
"""
Fix generated regions to add RegionCode to their augment() methods.
"""

import re
from pathlib import Path

# List of generated region files to fix
REGIONS_TO_FIX = [
    "src/regions/c_groups/c5_arabic_maghreb.py",
    "src/regions/c_groups/c6_hebrew_diaspora.py",
    "src/regions/c_groups/c7_armenian.py",
    "src/regions/c_groups/c8_georgian.py",
    "src/regions/c_groups/c9_caucasus_turkic.py",
    "src/regions/d_groups/d2_south_asia_dravidian.py",
    "src/regions/d_groups/d3_south_asia_bengali.py",
    "src/regions/d_groups/d4_pakistan_urdu.py",
    "src/regions/d_groups/d5_sinhala.py",
    "src/regions/e_groups/e5_vietnam.py",
    "src/regions/e_groups/e6_mainland_sea.py",
    "src/regions/e_groups/e7_maritime_sea.py",
    "src/regions/f_groups/f1_ssa_francophone.py",
    "src/regions/f_groups/f2_ssa_anglophone.py",
    "src/regions/f_groups/f3_horn_of_africa.py",
    "src/regions/f_groups/f4_lusophone_africa.py",
    "src/regions/special/h1_historical.py",
    "src/regions/special/r0_residual_latin_ascii.py",
    "src/regions/special/z0_quarantine.py",
]


def fix_augment_method(file_path: Path) -> bool:
    """Fix the augment method to add RegionCode."""

    with open(file_path, "r") as f:
        content = f.read()

    # Check if RegionCode is already set
    if "entry['RegionCode']" in content:
        print(f"✓ {file_path.name} already has RegionCode")
        return False

    # Find the augment method and add RegionCode
    # Pattern to match the start of augment method
    pattern = r'(def augment\(self, entry: Dict\[str, Any\]\) -> None:\s*\n\s*"""[^"]*"""\s*\n)'

    # Replacement adds RegionCode as first line after docstring
    replacement = r'\1        # Add region code\n        entry["RegionCode"] = self.code\n        \n'

    new_content = re.sub(pattern, replacement, content)

    if new_content != content:
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"✅ Fixed {file_path.name}")
        return True
    else:
        print(f"⚠️  Could not fix {file_path.name} - pattern not found")
        return False


def main():
    """Fix all generated region files."""

    base_dir = Path(__file__).parent.parent
    fixed_count = 0

    for relative_path in REGIONS_TO_FIX:
        file_path = base_dir / relative_path
        if file_path.exists():
            if fix_augment_method(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
