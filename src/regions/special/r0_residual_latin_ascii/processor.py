"""
R0 - Residual Latin ASCII region implementation.

Covers: Basic Latin ASCII names that don't fit other regions
Features: ASCII-only Latin script
"""

from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


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
            romanisation_standards=["ASCII"],
        )

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean ASCII Latin names."""
        super().clean(entry)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment ASCII Latin names."""
        super().augment(entry)

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate residual-bucket names."""
        canonical = self.get_canonical_name(entry)
        if canonical and len(canonical) > 150:
            raise RegionRuleError("Name too long")
        # R56.4 (real-data pilot finding): NO isascii() hard-reject here.
        # R0 is the ABSTENTION bucket — names land in it precisely because
        # detection could not classify them, and accented Latin names
        # ("Possamaï", "Réveillac", "Kršek") are its most common residents.
        # The old check stamped `_processing_error: Non-ASCII characters in
        # ASCII region` on exactly the inputs whose diacritics caused the
        # abstention — punishing the name for our own uncertainty. The
        # "ASCII" in this region's title is historical naming, not an input
        # contract; garbage/control characters are already rejected by the
        # security layer upstream.

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key."""
        return entry.get("CanonicalLatin", "").upper()
