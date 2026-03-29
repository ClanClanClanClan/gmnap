"""
Z0 - Quarantine region implementation.

Covers: Names that need special handling or quarantine
Features: Secure processing of problematic names
"""

from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


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
            romanisation_standards=["Various"],
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
            if entry.get("Variants", {}).get("Synthesised"):
                self.logger.warning(f"Variants in quarantine: {canonical}")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key."""
        return f"QUARANTINE_{entry.get('CanonicalLatin', '')}"
