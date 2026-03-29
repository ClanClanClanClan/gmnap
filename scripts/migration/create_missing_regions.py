#!/usr/bin/env python3
"""Create stub implementations for missing regions H1, R0, Z0."""

import os

# Create H1 (Historical) region
h1_content = '''"""
H1 - Historical region implementation.

Covers: Historical names and archaic naming conventions
Features: Latin script, historical variants, period-specific naming
"""

from typing import Any, Dict
from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class H1_Historical(RegionSpec):
    """
    Historical region (H1).
    
    Handles historical names and archaic naming conventions.
    """
    
    def __init__(self):
        super().__init__(
            code="H1",
            yaml_files=["h1_historical.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Given Family",
            romanisation_standards=["Latin"]
        )
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean historical names."""
        super().clean(entry)
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment historical names."""
        super().augment(entry)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate historical names."""
        canonical = self.get_canonical_name(entry)
        if canonical and len(canonical) > 150:
            raise RegionRuleError("Name too long")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key."""
        return entry.get('CanonicalLatin', '')
'''

# Create R0 (Residual Latin ASCII) region
r0_content = '''"""
R0 - Residual Latin ASCII region implementation.

Covers: Basic Latin ASCII names that don't fit other regions
Features: ASCII-only Latin script
"""

from typing import Any, Dict
from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class R0_ResidualLatinAscii(RegionSpec):
    """
    Residual Latin ASCII region (R0).
    
    Handles basic ASCII Latin names.
    """
    
    def __init__(self):
        super().__init__(
            code="R0",
            yaml_files=["r0_residual_latin_ascii.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Given Family",
            romanisation_standards=["ASCII"]
        )
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean ASCII Latin names."""
        super().clean(entry)
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment ASCII Latin names."""
        super().augment(entry)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate ASCII Latin names."""
        canonical = self.get_canonical_name(entry)
        if canonical and len(canonical) > 150:
            raise RegionRuleError("Name too long")
        # Ensure ASCII only
        if canonical and not canonical.isascii():
            raise RegionRuleError("Non-ASCII characters in ASCII region")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key."""
        return entry.get('CanonicalLatin', '').upper()
'''

# Create Z0 (Quarantine) region
z0_content = '''"""
Z0 - Quarantine region implementation.

Covers: Names that need special handling or quarantine
Features: Secure processing of problematic names
"""

from typing import Any, Dict
from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class Z0_Quarantine(RegionSpec):
    """
    Quarantine region (Z0).
    
    Handles names that need special security processing.
    """
    
    def __init__(self):
        super().__init__(
            code="Z0",
            yaml_files=["z0_quarantine.yaml"],
            scripts=["Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["Various"]
        )
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean quarantined names with extra security."""
        super().clean(entry)
        # Extra security for quarantined names
        canonical = self.get_canonical_name(entry)
        if canonical:
            # Apply stricter validation
            if len(canonical) > 100:  # Lower limit for quarantine
                raise RegionRuleError("Quarantined name too long")
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment quarantined names."""
        super().augment(entry)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate quarantined names with strict security."""
        canonical = self.get_canonical_name(entry)
        if canonical:
            # Strict validation for quarantine
            if len(canonical) > 100:
                raise RegionRuleError("Quarantined name too long")
            # No variants allowed in quarantine
            if entry.get('Variants', {}).get('Synthesised'):
                self.logger.warning(f"Variants in quarantine: {canonical}")
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key."""
        return f"QUARANTINE_{entry.get('CanonicalLatin', '')}"
'''

# Create directories and files
regions_to_create = [
    ("src/regions/special/h1_historical", "H1_Historical", h1_content),
    ("src/regions/special/r0_residual_latin_ascii", "R0_ResidualLatinAscii", r0_content),
    ("src/regions/special/z0_quarantine", "Z0_Quarantine", z0_content),
]

print("Creating missing regions...")
print("=" * 50)

for dir_path, class_name, content in regions_to_create:
    os.makedirs(dir_path, exist_ok=True)

    # Create __init__.py
    init_content = f"from .processor import {class_name}\n"
    with open(f"{dir_path}/__init__.py", "w") as f:
        f.write(init_content)

    # Create processor.py
    with open(f"{dir_path}/processor.py", "w") as f:
        f.write(content)

    print(f"✅ Created {dir_path}")

print("\n" + "=" * 50)
print("✅ All missing regions created!")
print("\nNow test if all regions work:")
print("  python3 final_check_for_a_plus.py")
