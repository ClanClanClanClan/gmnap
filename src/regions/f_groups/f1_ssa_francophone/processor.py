"""
SSA - Francophone (F1) regional processor.

Implements Sub-Saharan Africa with French naming influence
"""

import logging
from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


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
        # Spec §2 F1 distinct_features: "Accented French particles" (R50 —
        # this processor was a stub, MASTERPLAN §5). Particles are
        # lowercase-normalised in clean() and excluded from the sort key so
        # "Le Grand" sorts under G and "de la Croix" under C, matching the
        # francophone convention. Includes the accented d'/l' forms.
        self.french_particles = {
            "de",
            "du",
            "des",
            "le",
            "la",
            "les",
            "l'",
            "d'",
            "de la",
            "de le",
            "van",
            "von",
        }

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

        # Accented-French-particle normalisation (spec §2 F1): particles
        # inside the name are lowercased ("Jean DE LA Croix" -> "Jean de la
        # Croix"); a leading family-name particle in "Family, Given" form is
        # preserved as written (it is part of the registered surname).
        for field in ("CanonicalLatin",):
            name = entry.get(field)
            if not isinstance(name, str) or " " not in name:
                continue
            tokens = name.split(" ")
            fixed = [tokens[0]] + [
                tok.lower() if tok.lower() in self.french_particles else tok
                for tok in tokens[1:]
            ]
            entry[field] = " ".join(fixed)

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

        # Particle-aware family sort (spec §2 F1): leading French
        # particles don't drive collation — "de la Croix" sorts under
        # "croix", "Le Grand" under "grand".
        if ", " in canonical:
            family = canonical.split(", ")[0]
        else:
            family = canonical
        words = family.split()
        while len(words) > 1 and words[0].lower().rstrip("'") in {
            w.rstrip("'") for w in self.french_particles
        }:
            words = words[1:]
        return " ".join(words).lower() if words else canonical.lower()

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
            fam_words = components["family_name"].split()
            particles = []
            while len(fam_words) > 1 and fam_words[0].lower() in self.french_particles:
                particles.append(fam_words.pop(0))
            if particles:
                components["family_particle"] = " ".join(particles)
                components["family_core"] = " ".join(fam_words)
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
