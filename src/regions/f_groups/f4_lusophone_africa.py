"""
F4 - Lusophone Africa regional processor.

Covers: Angola (AO), Mozambique (MZ), Cape Verde (CV),
Guinea-Bissau (GW), Sao Tome and Principe (ST).

Features: Portuguese particles (de, da, dos, das) per Rule 22-23,
multiple given names + maternal + paternal surname pattern,
Portuguese diacritics, Family-Given canonical order.
"""

import re
import unicodedata
from typing import Any, Dict, List

from ..base import RegionRuleError, RegionSpec


class F4LusophoneAfrica(RegionSpec):
    """
    Lusophone Africa region (F4).

    Handles Portuguese-speaking African naming conventions including:
    - Portuguese particles: de, da, do, dos, das (Rule 22-23)
    - Multiple given names (two or three is common)
    - Maternal surname + paternal surname ordering (Portuguese style)
    - Portuguese diacritics (accents, cedilla, tilde)
    - Family, Given canonical order
    """

    def __init__(self):
        super().__init__(
            code="F4",
            yaml_files=["f4_lusophone_africa.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["Portuguese"],
        )

        # Portuguese titles
        self.titles = {
            "Dr",
            "Dr.",
            "Doutor",
            "Doutora",
            "Prof",
            "Prof.",
            "Professor",
            "Professora",
            "Sr",
            "Sr.",
            "Senhor",
            "Sra",
            "Sra.",
            "Senhora",
            "Dom",
            "Dona",
            "Eng",
            "Eng.",
            "Engenheiro",
        }

        # Portuguese particles per Rule 22-23 (lowercase, ignored in sorting)
        self.particles = {"de", "da", "do", "dos", "das", "d'", "e"}

        # Portuguese diacritics
        self.portuguese_chars = set("àáâãçéêíóôõúüÀÁÂÃÇÉÊÍÓÔÕÚÜ")

        # Common Lusophone African surname indicators
        self.common_surnames = {
            "silva",
            "santos",
            "ferreira",
            "pereira",
            "oliveira",
            "costa",
            "rodrigues",
            "martins",
            "jesus",
            "sousa",
            "mendes",
            "gomes",
            "alves",
            "ribeiro",
            "fernandes",
            "neto",
            "lopes",
            "nascimento",
            "carvalho",
            "teixeira",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Lusophone African names in-place.

        - Remove Portuguese titles and honorifics
        - Normalize Portuguese diacritics (NFC)
        - Fix spacing around particles
        - Collapse whitespace
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Remove Portuguese titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Doutor|Doutora|Prof\.?|Professor|Professora|"
            r"Sr\.?|Senhor|Sra\.?|Senhora|Dom|Dona|Eng\.?|Engenheiro)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Remove suffixes
        suffixes_pattern = re.compile(
            r"\s+\b(Jr\.?|Filho|Neto|Sobrinho|II|III|IV)\b",
            re.IGNORECASE,
        )
        cleaned = suffixes_pattern.sub("", cleaned)

        # Normalize Unicode
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Normalize apostrophes for d' particle
        cleaned = cleaned.replace("\u2019", "'").replace("\u2018", "'")

        # Fix spacing around particles
        for particle in self.particles:
            pat = re.compile(rf"\s+\b{re.escape(particle)}\s+", re.IGNORECASE)
            cleaned = pat.sub(f" {particle} ", cleaned)

        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        entry["CanonicalLatin"] = cleaned

        # Clean observed variants
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    v = titles_pattern.sub("", variant["str"])
                    v = suffixes_pattern.sub("", v)
                    v = unicodedata.normalize("NFC", v)
                    v = re.sub(r"\s+", " ", v.strip())
                    variant["str"] = v

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with F4-specific data.

        - Extract family/given components
        - Detect maternal + paternal surname pattern
        - Detect Portuguese particles
        - Generate ASCII-lossy and particle-drop variants
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

        # Extract components
        family, given = self._split_canonical(canonical)
        extras["family_name"] = family
        extras["given_name"] = given

        # Detect particles (Rule 22-23)
        particles = self._extract_particles(family)
        if particles:
            extras["particles"] = particles

        # Parse Portuguese surname structure: [maternal] paternal
        surname_parts = self._parse_portuguese_surnames(family)
        if surname_parts.get("maternal"):
            extras["maternal_surname"] = surname_parts["maternal"]
        if surname_parts.get("paternal"):
            extras["paternal_surname"] = surname_parts["paternal"]

        # Detect language hints from diacritics
        if any(c in canonical for c in "ãõâêô"):
            extras["language_hint"] = "Portuguese"

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

        # Particle-drop variant for matching
        if particles:
            stripped = self._strip_particles(family)
            if stripped != family:
                variants.append(
                    {
                        "str": f"{stripped}, {given}" if given else stripped,
                        "type": "particle-drop",
                    }
                )

        # Paternal-only variant (common short form)
        if surname_parts.get("paternal") and surname_parts.get("maternal"):
            paternal_only = surname_parts["paternal"]
            variants.append(
                {
                    "str": f"{paternal_only}, {given}" if given else paternal_only,
                    "type": "paternal-surname-only",
                }
            )

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry per F4 rules.

        - CanonicalLatin must exist and be non-trivial
        - Characters must be Latin + Portuguese diacritics
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for F4 region")

        # Character validation
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        allowed.update(self.portuguese_chars)
        allowed.update(" ,-.'\u2019")

        invalid = set(canonical) - allowed
        if invalid:
            raise RegionRuleError(
                f"Invalid characters for F4 Lusophone: {', '.join(sorted(invalid))}"
            )

        if len(canonical) > 140:
            raise RegionRuleError("Name exceeds 140 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Sorts by paternal surname (ignoring particles per Rule 22-23),
        then given name.  Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family:
            canonical = entry.get("CanonicalLatin", "")
            family, given = self._split_canonical(canonical)

        # Use paternal surname for sorting if available
        paternal = extras.get("paternal_surname", "")
        sort_surname = paternal if paternal else family

        # Strip particles for sorting (Rule 22-23)
        sort_surname = self._strip_particles(sort_surname)
        sort_surname = self._remove_diacritics(sort_surname).upper()
        sort_given = self._remove_diacritics(given).upper()

        key = f"{sort_surname}, {sort_given}".strip(", ")
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
        """Extract Portuguese particles from the family name."""
        found: List[str] = []
        for word in family.split():
            normed = word.lower().rstrip(",")
            if normed in self.particles:
                found.append(word.rstrip(","))
        return found

    def _strip_particles(self, family: str) -> str:
        """Remove particles from the family name."""
        words = family.split()
        return " ".join(w for w in words if w.lower().rstrip(",") not in self.particles)

    def _parse_portuguese_surnames(self, family: str) -> Dict[str, str]:
        """
        Parse Portuguese-style dual surname: [maternal] paternal.

        In the Portuguese system the last surname is paternal (primary)
        and the preceding surname is maternal.
        """
        stripped = self._strip_particles(family)
        tokens = stripped.split()

        if len(tokens) >= 2:
            return {
                "maternal": " ".join(tokens[:-1]),
                "paternal": tokens[-1],
            }
        elif len(tokens) == 1:
            return {"paternal": tokens[0]}
        return {}

    def _remove_diacritics(self, text: str) -> str:
        """Strip diacritics, keeping base Latin letters."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
