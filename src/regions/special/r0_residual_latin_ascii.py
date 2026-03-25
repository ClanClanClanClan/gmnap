"""
R0 - Residual Latin-ASCII regional processor.

Catch-all for Latin-script names that do not match any specific
region (A1-G1).  Applies minimal processing: basic cleaning,
component extraction, and low-confidence flagging.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class R0ResidualLatinASCII(RegionSpec):
    """
    Residual Latin-ASCII catch-all region (R0).

    Handles Latin-script names that could not be assigned to a more
    specific regional processor.  Processing is intentionally minimal
    to avoid making incorrect cultural assumptions:

    - Basic whitespace and punctuation normalisation
    - Simple family / given name extraction
    - Low confidence flag for downstream review
    - ASCII-lossy variant generation
    """

    def __init__(self):
        super().__init__(
            code="R0",
            yaml_files=["r0_residual_latin_ascii.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[],
        )

        # Minimal title set (only universally recognised ones)
        self.titles = {
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Professor",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Miss",
        }

        # Universal particles (only the very common ones)
        self.particles = {"de", "van", "von", "di", "da", "del", "la", "le"}

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Minimal cleaning of residual Latin-ASCII names in-place.

        - Remove universally recognised titles
        - Normalize Unicode to NFC
        - Collapse whitespace
        - Normalize basic punctuation
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Remove common titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Normalize Unicode
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Normalize apostrophes
        cleaned = cleaned.replace("\u2019", "'").replace("\u2018", "'")

        # Normalize dashes
        cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")

        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        entry["CanonicalLatin"] = cleaned

        # Clean observed variants
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    v = titles_pattern.sub("", variant["str"])
                    v = unicodedata.normalize("NFC", v)
                    v = re.sub(r"\s+", " ", v.strip())
                    variant["str"] = v

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Minimal augmentation for residual names.

        - Extract family / given components
        - Flag as low confidence
        - Generate ASCII-lossy variant
        - Generate order-swap variant
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        extras = entry["RegionalExtras"]
        variants = entry["Variants"]["Synthesised"]

        # Extract name components
        family, given = self._split_canonical(canonical)
        extras["family_name"] = family
        extras["given_name"] = given

        # Flag as residual / low confidence
        extras["residual"] = True
        extras["confidence"] = "low"
        extras["region_assignment_reason"] = "no-specific-region-match"

        # Detect particles if any
        particles = self._extract_particles(family)
        if particles:
            extras["particles"] = particles

        # Detect if name is likely a mononym
        if not given and family:
            extras["is_mononym"] = True

        # ASCII-lossy variant
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Order-swap variant
        if family and given:
            variants.append(
                {
                    "str": f"{given} {family}",
                    "type": "order-swap",
                }
            )

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Minimal validation for residual names.

        R0 is deliberately permissive since we have low confidence
        in how to validate these names.  We only check:
        - CanonicalLatin exists
        - Name is not trivially short
        - Script is broadly Latin-compatible
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for R0 region")

        # Check that the name is broadly Latin-script.
        # Allow Latin, Latin Extended, and common punctuation.
        for ch in canonical:
            cp = ord(ch)
            if cp > 0x024F and ch not in " ,-.'\u2019\u2013\u2014":
                # Allow Latin Extended Additional and a few more blocks
                if not (0x1E00 <= cp <= 0x1EFF):
                    raise RegionRuleError(
                        f"Non-Latin character U+{cp:04X} in R0 entry; "
                        "consider assigning to a specific region"
                    )

        if len(canonical) > 150:
            raise RegionRuleError("Name exceeds 150 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Simple family-then-given sort, ASCII-folded.
        Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family:
            canonical = entry.get("CanonicalLatin", "")
            family, given = self._split_canonical(canonical)

        # Strip particles for sorting
        sort_family = self._strip_particles(family)
        sort_family = self._remove_diacritics(sort_family).upper()
        sort_given = self._remove_diacritics(given).upper()

        # Remove punctuation for consistent sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family}, {sort_given}".strip(", ")
        return " ".join(key.split())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_canonical(self, name: str) -> tuple:
        """Split canonical into (family, given)."""
        if ", " in name:
            parts = name.split(", ", 1)
            return parts[0].strip(), parts[1].strip()
        tokens = name.split()
        if len(tokens) >= 2:
            return tokens[-1], " ".join(tokens[:-1])
        return name.strip(), ""

    def _extract_particles(self, family: str) -> List[str]:
        """Extract common particles from family name."""
        found: List[str] = []
        for word in family.split():
            if word.lower().rstrip(",") in self.particles:
                found.append(word.rstrip(","))
        return found

    def _strip_particles(self, family: str) -> str:
        """Remove particles from family name."""
        words = family.split()
        return " ".join(w for w in words if w.lower().rstrip(",") not in self.particles)

    def _remove_diacritics(self, text: str) -> str:
        """Strip diacritics, keeping base Latin letters."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
