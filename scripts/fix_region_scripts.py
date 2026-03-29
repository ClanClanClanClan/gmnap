#!/usr/bin/env python3
"""
Fix missing scripts parameter in generated region files.
"""

# Map regions to their script types
REGION_SCRIPTS = {
    "C5": ["Arabic", "Latin"],  # Arabic Maghreb (Arabic with French influence)
    "C6": ["Hebrew", "Latin"],  # Hebrew & Diaspora
    "C7": ["Armenian", "Latin"],  # Armenian
    "C8": ["Georgian", "Latin"],  # Georgian
    "C9": ["Latin", "Cyrillic", "Arabic"],  # Caucasus-Turkic (mixed)
    "D2": ["Tamil", "Latin"],  # South Asia - Dravidian
    "D3": ["Bengali", "Latin"],  # South Asia - Bengali
    "D4": ["Arabic", "Latin"],  # Pakistan & Urdu
    "D5": ["Sinhala", "Latin"],  # Sinhala
    "E5": ["Latin"],  # Vietnam (uses Latin script)
    "E6": ["Thai", "Latin"],  # Mainland SEA
    "E7": ["Latin"],  # Maritime SEA (mostly Latin)
    "F1": ["Latin"],  # SSA - Francophone
    "F2": ["Latin"],  # SSA - Anglophone
    "F3": ["Ge'ez", "Latin"],  # Horn of Africa
    "F4": ["Latin"],  # Lusophone Africa
    "H1": ["Latin"],  # Historical (pre-1850)
    "R0": ["Latin"],  # Residual Latin-ASCII
    "Z0": ["Latin"],  # Quarantine
}

# File paths to fix
FILES_TO_FIX = {
    "C5": "src/regions/c_groups/c5_arabic_maghreb.py",
    "C6": "src/regions/c_groups/c6_hebrew_diaspora.py",
    "C7": "src/regions/c_groups/c7_armenian.py",
    "C8": "src/regions/c_groups/c8_georgian.py",
    "C9": "src/regions/c_groups/c9_caucasus_turkic.py",
    "D2": "src/regions/d_groups/d2_south_asia_dravidian.py",
    "D3": "src/regions/d_groups/d3_south_asia_bengali.py",
    "D4": "src/regions/d_groups/d4_pakistan_urdu.py",
    "D5": "src/regions/d_groups/d5_sinhala.py",
    "E5": "src/regions/e_groups/e5_vietnam.py",
    "E6": "src/regions/e_groups/e6_mainland_sea.py",
    "E7": "src/regions/e_groups/e7_maritime_sea.py",
    "F1": "src/regions/f_groups/f1_ssa_francophone.py",
    "F2": "src/regions/f_groups/f2_ssa_anglophone.py",
    "F3": "src/regions/f_groups/f3_horn_of_africa.py",
    "F4": "src/regions/f_groups/f4_lusophone_africa.py",
    "H1": "src/regions/special/h1_historical.py",
    "R0": "src/regions/special/r0_residual_latin_ascii.py",
    "Z0": "src/regions/special/z0_quarantine.py",
}

import re
from pathlib import Path


def fix_region_file(region_code: str, file_path: Path, scripts: list):
    """Fix a single region file to add scripts parameter."""

    with open(file_path, "r") as f:
        content = f.read()

    # Find the super().__init__ call and add scripts parameter
    pattern = r'(super\(\).__init__\(\s*code="{}".*?yaml_files=\[\].*?)(\s*\))'.format(
        region_code
    )

    scripts_str = repr(scripts)
    replacement = r"\1,\n            scripts={}\2".format(scripts_str)

    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"✅ Fixed {region_code}: {file_path} with scripts={scripts}")


def main():
    """Fix all generated region files."""

    base_dir = Path(__file__).parent.parent

    for region_code, relative_path in FILES_TO_FIX.items():
        file_path = base_dir / relative_path
        if file_path.exists():
            scripts = REGION_SCRIPTS.get(region_code, ["Latin"])
            fix_region_file(region_code, file_path, scripts)
        else:
            print(f"⚠️  File not found: {file_path}")


if __name__ == "__main__":
    main()
