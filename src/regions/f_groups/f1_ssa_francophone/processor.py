"""
SSA - Francophone (F1) regional processor.

Implements Sub-Saharan Africa with French naming influence
"""

import logging
from typing import Any, Dict
from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class F1_SSAFrancophone(RegionSpec):
    """Handler for F1 - SSA - Francophone."""

    def __init__(self):
        super().__init__(
            code="F1",
            yaml_files=["f1_ssa_francophone.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[],
        )
        # Initialize logger for F1 region
        self.logger = logging.getLogger(f"gmnap.regions.{self.code}")

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Apply V7 security validation and graceful edge case handling."""
        # Use comprehensive V7 security validation from base class
        # This includes all 7 required security checks:
        # 1. Dangerous characters, 2. DoS protection (length limits)
        # 3. SQL injection patterns, 4. XSS patterns
        # 5. Command injection patterns, 6. Path traversal patterns
        # 7. Native field validation
        self.apply_security_and_validation_checks(entry)

        # Handle legitimate edge cases gracefully
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with F1-specific data."""
        # Add region code
        entry["RegionCode"] = self.code

        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        # Normalize tabs and newlines BEFORE security check (V7 edge case)
        if canonical:
            canonical = canonical.replace("\t", " ").replace("\n", " ")

        if self._has_security_risks(canonical):
            raise RegionRuleError(
                f"Name contains dangerous characters: {canonical[:50]}..."
            )

        # Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(
                f"Name too long: {len(canonical)} characters (max 150)"
            )

        # THEN handle legitimate edge cases
        if len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for F1 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Simple sort by family name
        if ", " in canonical:
            family = canonical.split(", ")[0]
            return family.lower()

        return canonical.lower()

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated
            parts = name.split(None, 1)
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""

        return components
