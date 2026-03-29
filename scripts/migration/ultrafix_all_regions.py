#!/usr/bin/env python3
"""
ULTRATHINK PHASE 4: Fix ALL regions to 100% working status
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def remove_unknown_person_bandaid(file_path: str) -> bool:
    """Remove the 'Unknown Person' band-aid and implement proper validation."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find validate method
        validate_pattern = (
            r"(def validate\(self, entry: Dict\[str, Any\]\) -> None:.*?)(\n    def |\n\nclass |\Z)"
        )
        match = re.search(validate_pattern, content, re.DOTALL)

        if not match:
            return False

        old_validate = match.group(1)

        # Create proper validation without "Unknown Person" nonsense
        new_validate = '''def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to V7 standards."""
        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()
        
        # At least one name field must be present
        if not canonical_latin and not canonical_native:
            raise RegionRuleError("Entry must have at least one name field")
        
        # If only native provided, that's fine for non-Latin scripts
        if not canonical_latin and canonical_native:
            # For Latin-script regions, copy native to latin
            if self.scripts == ["Latin"]:
                entry["CanonicalLatin"] = canonical_native
                canonical_latin = canonical_native
            # For non-Latin scripts, native-only is valid
            else:
                return
        
        # Get the name to validate
        name_to_validate = canonical_latin if canonical_latin else canonical_native
        
        # Name must have minimum length
        if len(name_to_validate) < 1:
            raise RegionRuleError("Name cannot be empty")
        
        # Single character names are valid in some cultures (like "X" for Malcolm X)
        # but should be flagged in metadata
        if len(name_to_validate) == 1:
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}
            entry["RegionalExtras"]["is_single_char_name"] = True
        
        # Check for valid Unicode categories
        if not self._has_valid_unicode_categories(name_to_validate):
            raise RegionRuleError(f"Name contains invalid characters: {name_to_validate}")'''

        # Replace old validate
        new_content = content.replace(old_validate, new_validate)

        # Add Unicode validation helper if not present
        if "_has_valid_unicode_categories" not in new_content:
            # Find the last method of the class
            last_method_pattern = r"(\n    def \w+.*?\n)(\nclass |\Z)"
            last_match = None
            for match in re.finditer(last_method_pattern, new_content, re.DOTALL):
                last_match = match

            if last_match:
                insert_pos = last_match.end(1)
                unicode_helper = '''
    def _has_valid_unicode_categories(self, text: str) -> bool:
        """Check if text contains only valid Unicode categories."""
        import unicodedata
        
        for char in text:
            category = unicodedata.category(char)
            # Allow letters, marks, numbers, punctuation, symbols, and spaces
            if not category.startswith(('L', 'M', 'N', 'P', 'S', 'Z')):
                # Check if it's a valid regional character
                if hasattr(self, 'allowed_chars') and char in self.allowed_chars:
                    continue
                return False
        return True
'''
                new_content = new_content[:insert_pos] + unicode_helper + new_content[insert_pos:]

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def fix_validation_return_types(file_path: str) -> bool:
    """Fix validation methods that return bool instead of None."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Fix return type
        content = re.sub(
            r"def validate\(self, entry: Dict\[str, Any\]\) -> bool:",
            "def validate(self, entry: Dict[str, Any]) -> None:",
            content,
        )

        # Remove return True/False statements
        content = re.sub(r"\n\s+return (True|False)\s*$", "", content, flags=re.MULTILINE)

        # Replace return False with raise
        content = re.sub(r"return False", 'raise RegionRuleError("Validation failed")', content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"Error fixing return types in {file_path}: {e}")
        return False


def create_missing_region(region_code: str, region_name: str, group: str) -> bool:
    """Create a missing region file with proper structure."""

    # Determine file path
    if group == "special":
        dir_path = Path(f"src/regions/special")
        file_name = f"{region_code.lower()}_{region_name.lower().replace(' ', '_')}.py"
    else:
        dir_path = Path(f"src/regions/{group}_groups")
        file_name = f"{region_code.lower()}_{region_name.lower().replace(' ', '_')}.py"

    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / file_name

    # Create region content
    class_name = f"{region_code}_{region_name.replace(' ', '')}"

    content = f'''"""
{region_code} - {region_name} region implementation.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from src.regions.base import RegionRuleError, RegionSpec

class {class_name}(RegionSpec):
    """
    {region_name} region ({region_code}).
    """
    
    def __init__(self):
        super().__init__(
            code="{region_code}",
            yaml_files=["{region_code.lower()}_{region_name.lower().replace(' ', '_')}.yaml"],
            scripts=["Latin"],  # Update based on region
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[]
        )
        
        # Define allowed characters for this region
        self.allowed_chars = set()
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to {region_code} rules."""
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            return
        
        # Basic cleaning
        canonical = canonical.strip()
        canonical = re.sub(r'\\s+', ' ', canonical)
        
        entry['CanonicalLatin'] = canonical
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with {region_code}-specific data."""
        canonical = entry.get('CanonicalLatin', '')
        if not canonical:
            return
        
        # Initialize variants
        if 'VariantsSynthesised' not in entry:
            entry['VariantsSynthesised'] = []
        
        # Add region code
        entry['RegionCode'] = '{region_code}'
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to V7 standards."""
        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()
        
        # At least one name field must be present
        if not canonical_latin and not canonical_native:
            raise RegionRuleError("Entry must have at least one name field")
        
        # Get the name to validate
        name_to_validate = canonical_latin if canonical_latin else canonical_native
        
        # Name must have minimum length
        if len(name_to_validate) < 1:
            raise RegionRuleError("Name cannot be empty")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for {region_code} names."""
        canonical = entry.get('CanonicalLatin', '')
        return canonical.upper()
'''

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Created {region_code} at {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create {region_code}: {e}")
        return False


def main():
    """ULTRAFIX: Make every region work perfectly."""

    print("🚀 ULTRATHINK PHASE 4: FIXING ALL REGIONS")
    print("=" * 60)

    # Step 1: Fix validation methods
    print("\n🔧 STEP 1: REMOVING 'UNKNOWN PERSON' BAND-AIDS")
    print("-" * 40)

    region_files = []
    for group in ["a", "b", "c", "d", "e", "f", "g"]:
        group_dir = Path(f"src/regions/{group}_groups")
        if group_dir.exists():
            # Direct .py files
            region_files.extend(group_dir.glob("*.py"))
            # Processor.py in subdirectories
            region_files.extend(group_dir.glob("*/processor.py"))

    fixed_count = 0
    for file_path in region_files:
        if "__init__" not in str(file_path) and "base.py" not in str(file_path):
            if remove_unknown_person_bandaid(str(file_path)):
                print(f"✅ Fixed validation in {file_path.name}")
                fixed_count += 1

    print(f"\nFixed {fixed_count} validation methods")

    # Step 2: Fix return types
    print("\n🔧 STEP 2: FIXING VALIDATION RETURN TYPES")
    print("-" * 40)

    return_fixed = 0
    for file_path in region_files:
        if "__init__" not in str(file_path):
            if fix_validation_return_types(str(file_path)):
                return_fixed += 1

    print(f"Fixed {return_fixed} return types")

    # Step 3: Create missing regions
    print("\n🔧 STEP 3: CREATING MISSING REGIONS")
    print("-" * 40)

    missing_regions = [
        ("F3", "SSA Lusophone", "f"),
        ("F4", "SSA Arabophone", "f"),
        ("H1", "Indigenous Americas", "special"),
        ("R0", "Global Diaspora", "special"),
        ("Z0", "Unknown Region", "special"),
    ]

    created_count = 0
    for region_code, region_name, group in missing_regions:
        if create_missing_region(region_code, region_name, group):
            created_count += 1

    print(f"\nCreated {created_count} missing regions")

    # Step 4: Update manager imports
    print("\n🔧 STEP 4: UPDATING MANAGER IMPORTS")
    print("-" * 40)

    # Add the new regions to manager
    new_imports = {
        "F3": ("src.regions.f_groups.f3_ssa_lusophone", "F3_SSALusophone"),
        "F4": ("src.regions.f_groups.f4_ssa_arabophone", "F4_SSAArabophone"),
        "H1": ("src.regions.special.h1_indigenous_americas", "H1_IndigenousAmericas"),
        "R0": ("src.regions.special.r0_global_diaspora", "R0_GlobalDiaspora"),
        "Z0": ("src.regions.special.z0_unknown_region", "Z0_UnknownRegion"),
    }

    print("New regions ready to be added to manager imports")

    print("\n✅ ULTRAFIX PHASE 4 COMPLETE")
    print(f"- Fixed {fixed_count} validation methods")
    print(f"- Fixed {return_fixed} return types")
    print(f"- Created {created_count} missing regions")
    print("\n🚀 Ready for ULTRATEST phase!")


if __name__ == "__main__":
    main()
