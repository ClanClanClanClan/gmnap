"""
F1 - Sub-Saharan Africa Francophone regional processor.

Covers: Senegal, Mali, Cameroon, Ivory Coast, Guinea, Burkina Faso,
Benin, Togo, Chad, Central African Republic, Congo, Gabon, Djibouti,
Comoros, Seychelles, Madagascar, Burundi.

Features: French particles (de, du, des) per Rule 22-23, prefix
patterns (Ndi-, Ngo-, Ba-, Ma-), double given names (Jean-Pierre,
Marie-Claire), Family-Given canonical order.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class F1SSAFrancophone(RegionSpec):
    """
    Sub-Saharan Africa Francophone region (F1).

    Handles Francophone African naming conventions including:
    - French particles (de, du, des) per Rule 22-23
    - African prefix patterns (Ndi-, Ngo-, Ba-, Ma-, Mba-)
    - Compound/hyphenated French given names (Jean-Pierre, Marie-Claire)
    - Family, Given canonical order
    """

    def __init__(self):
        super().__init__(
            code="F1",
            yaml_files=["f1_ssa_francophone.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["French"]
        )

        # French titles to remove
        self.titles = {
            "Dr", "Dr.", "Docteur",
            "Prof", "Prof.", "Professeur",
            "M", "M.", "Monsieur",
            "Mme", "Mme.", "Madame",
            "Mlle", "Mlle.", "Mademoiselle",
            "Pr", "Pr.",
            "Mgr", "Mgr.",
        }

        # French particles per Rule 22-23 (kept lowercase, not used for sorting)
        self.particles = {"de", "du", "des", "d'", "le", "la", "les", "l'"}

        # African surname prefixes (must be kept attached)
        self.african_prefixes = [
            "Ndi", "Ngo", "Nga", "Ngu",
            "Ba", "Ma", "Mba", "Mbi",
            "Bi", "Di", "Fo", "Fa",
            "Nde", "Nke", "Nji", "Nta",
        ]

        # Compound French given name starters
        self.compound_starters = {
            "Jean", "Marie", "Pierre", "Anne",
            "Louis", "Charles", "Paul", "Claude",
        }

        # French diacritics
        self.french_chars = set("àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ")

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Francophone African names in-place.

        - Remove French titles and honorifics
        - Normalize French diacritics (NFC)
        - Normalize whitespace and punctuation
        - Preserve African prefix patterns and particles
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Remove French titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Docteur|Prof\.?|Professeur|M\.|Monsieur|"
            r"Mme\.?|Madame|Mlle\.?|Mademoiselle|Pr\.?|Mgr\.?)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Normalize Unicode (NFC for consistent diacritics)
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Normalize apostrophes for particles like d'
        cleaned = cleaned.replace("\u2019", "'").replace("\u2018", "'")

        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        entry["CanonicalLatin"] = cleaned

        # Also clean variant strings
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    v = titles_pattern.sub("", variant["str"])
                    v = unicodedata.normalize("NFC", v)
                    v = re.sub(r"\s+", " ", v.strip())
                    variant["str"] = v

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with F1-specific data.

        - Extract family/given name components
        - Detect African prefixes and French particles
        - Generate ASCII-lossy and hyphen-collapse variants
        - Flag compound given names
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Ensure structures exist
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

        # Detect African prefix in surname
        prefix = self._detect_african_prefix(family)
        if prefix:
            extras["african_prefix"] = prefix

        # Detect French particles (Rule 22-23)
        particles = self._extract_particles(family)
        if particles:
            extras["particles"] = particles

        # Detect compound given name (Jean-Pierre, Marie-Claire)
        if given and "-" in given:
            extras["compound_given"] = True
            # Generate collapsed variant (drop second part)
            first_part = given.split("-")[0]
            collapsed = f"{family}, {first_part}" if family else first_part
            if collapsed != canonical:
                variants.append({"str": collapsed, "type": "initial-collapse"})

        # ASCII-lossy variant (strip diacritics)
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Order-swap variant (Given Family)
        if family and given:
            variants.append({
                "str": f"{given} {family}",
                "type": "order-swap",
            })

        # Particle-drop variant for sorting aid
        if particles:
            no_particle = self._strip_particles(family)
            if no_particle != family:
                variants.append({
                    "str": f"{no_particle}, {given}" if given else no_particle,
                    "type": "particle-drop",
                })

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry per F1 rules.

        - CanonicalLatin must be present and non-trivial
        - Characters must be Latin + French diacritics
        - Name must have at least a family component
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for F1 region")

        # Character validation: Latin + French diacritics + punctuation
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        allowed.update(self.french_chars)
        allowed.update(" ,-.'\u2019")

        invalid = set(canonical) - allowed
        if invalid:
            raise RegionRuleError(
                f"Invalid characters for F1 Francophone: {', '.join(sorted(invalid))}"
            )

        # Length guard
        if len(canonical) > 120:
            raise RegionRuleError("Name exceeds 120 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Sorts by family name (ignoring particles per Rule 22-23),
        then by given name.  Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family:
            canonical = entry.get("CanonicalLatin", "")
            family, given = self._split_canonical(canonical)

        # Strip particles for sorting (Rule 22-23)
        sort_family = self._strip_particles(family)
        sort_family = self._remove_diacritics(sort_family).upper()
        sort_given = self._remove_diacritics(given).upper()

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

    def _detect_african_prefix(self, surname: str) -> Optional[str]:
        """Return the African prefix if the surname starts with one."""
        for prefix in self.african_prefixes:
            if surname.startswith(prefix) and len(surname) > len(prefix):
                return prefix
        return None

    def _extract_particles(self, family: str) -> List[str]:
        """Extract French particles from the family name."""
        found: List[str] = []
        for word in family.split():
            normed = word.lower().rstrip(",")
            if normed in self.particles or normed + "'" in self.particles:
                found.append(word.rstrip(","))
        return found

    def _strip_particles(self, family: str) -> str:
        """Remove particles from the family name string."""
        words = family.split()
        return " ".join(
            w for w in words
            if w.lower().rstrip(",") not in self.particles
               and w.lower().rstrip(",") + "'" not in self.particles
        )

    def _remove_diacritics(self, text: str) -> str:
        """Strip diacritics, keeping base Latin letters."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
