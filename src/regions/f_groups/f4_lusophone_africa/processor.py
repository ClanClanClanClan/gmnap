"""
F4 - Lusophone Africa region implementation.
Covers Portuguese colonial naming patterns in Angola, Mozambique, Cape Verde, Guinea-Bissau, São Tomé and Príncipe.
"""

import re
from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class F4_LusophoneAfrica(RegionSpec):
    """
    Lusophone Africa region (F4).
    Handles Portuguese naming patterns in African countries.
    """

    def __init__(self):
        super().__init__(
            code="F4",
            yaml_files=["f4_lusophone_africa.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[],
        )

        # Define allowed characters for this region
        self.allowed_chars = set()

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to F4 Lusophone Africa rules."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Basic cleaning
        canonical = canonical.strip()
        canonical = re.sub(r"\s+", " ", canonical)

        entry["CanonicalLatin"] = canonical

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with F4-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Initialize variants
        if "VariantsSynthesised" not in entry:
            entry["VariantsSynthesised"] = []

        # Add region code
        entry["RegionCode"] = "F4"

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

        # Single character names are valid in some cultures
        if len(name_to_validate) == 1:
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}
            entry["RegionalExtras"]["is_single_char_name"] = True

        # Basic character validation for F4
        if not self._is_valid_name(name_to_validate):
            raise RegionRuleError(
                f"Name contains invalid characters: {name_to_validate}"
            )

    def _is_valid_name(self, name: str) -> bool:
        """Check if name contains valid characters for this region."""
        import unicodedata

        for char in name:
            category = unicodedata.category(char)
            # Allow letters, marks, spaces, punctuation common in names
            if category.startswith(("L", "M", "Z")) or char in "-.',":
                continue
            # Allow numbers for special cases
            elif category.startswith("N") and len(name) > 1:
                continue
            else:
                return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for F4 Lusophone Africa names."""
        canonical = entry.get("CanonicalLatin", "")
        return canonical.upper()
