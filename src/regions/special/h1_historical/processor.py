"""
H1 - Historical region implementation.

Covers: Historical names and archaic naming conventions
Features: Latin script, historical variants, period-specific naming
"""

from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


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
            romanisation_standards=["Latin"],
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
        return entry.get("CanonicalLatin", "")
