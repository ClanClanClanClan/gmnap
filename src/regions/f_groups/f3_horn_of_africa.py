"""
F3 - Horn of Africa regional processor.

Covers: Ethiopia (ET), Eritrea (ER).

Features: Ge'ez/Ethiopic script (U+1200-U+137F), patronymic chains
(no family names), three-generation naming (given + father + grandfather),
Mononym canonical order for single-generation entries.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


# Ge'ez / Ethiopic Unicode range
_GEEZ_START = 0x1200
_GEEZ_END = 0x137F
_GEEZ_SUPPLEMENT_START = 0x1380
_GEEZ_SUPPLEMENT_END = 0x139F


def _is_geez(ch: str) -> bool:
    """Return True if character is in the Ge'ez/Ethiopic block."""
    cp = ord(ch)
    return _GEEZ_START <= cp <= _GEEZ_END or _GEEZ_SUPPLEMENT_START <= cp <= _GEEZ_SUPPLEMENT_END


def _has_geez(text: str) -> bool:
    """Return True if text contains any Ge'ez characters."""
    return any(_is_geez(c) for c in text)


class F3HornOfAfrica(RegionSpec):
    """
    Horn of Africa region (F3).

    Handles Ethiopian/Eritrean naming conventions including:
    - Patronymic chains: no hereditary surnames
    - Three-generation naming: Given + Father + Grandfather
    - Ge'ez (Ethiopic) script support alongside Latin romanisation
    - Common romanisation variants (Amharic, Tigrinya)
    """

    def __init__(self):
        super().__init__(
            code="F3",
            yaml_files=["f3_horn_of_africa.yaml"],
            scripts=["Ge'ez", "Latin"],
            mixed_scripts=True,
            canonical_order="Patronymic",
            romanisation_standards=["Amharic-Latin", "Tigrinya-Latin"],
        )

        # Titles / honorifics in Amharic romanisation
        self.titles = {
            "Dr",
            "Dr.",
            "Doctor",
            "Prof",
            "Prof.",
            "Professor",
            "Ato",
            "Woizero",
            "Woizerit",
            "Dejazmach",
            "Ras",
            "Negus",
            "Fitawrari",
            "Grazmach",
            "Blatta",
            "Rev",
            "Rev.",
        }

        # Common Amharic romanisation alternates (for variant generation)
        self.romanisation_alternates = {
            "ou": "u",
            "oo": "u",
            "ee": "i",
            "ei": "e",
            "sh": "ch",
            "tch": "ch",
            "dj": "j",
            "gn": "ny",
            "w": "ou",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Horn of Africa names in-place.

        - Remove Amharic/English titles
        - Normalize Ge'ez and Latin text (NFC)
        - Normalize whitespace
        """
        # Clean CanonicalLatin
        canonical = entry.get("CanonicalLatin", "")
        if canonical:
            entry["CanonicalLatin"] = self._clean_text(canonical)

        # Clean CanonicalNative (Ge'ez script)
        native = entry.get("CanonicalNative", "")
        if native:
            entry["CanonicalNative"] = self._clean_native(native)

        # Clean observed variants
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    variant["str"] = self._clean_text(variant["str"])

    def _clean_text(self, text: str) -> str:
        """Clean a Latin-script name string."""
        # Remove titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Doctor|Prof\.?|Professor|Ato|Woizero|Woizerit|"
            r"Dejazmach|Ras|Negus|Fitawrari|Grazmach|Blatta|Rev\.?)\s+",
            re.IGNORECASE,
        )
        text = titles_pattern.sub("", text)
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"\s+", " ", text.strip())
        return text

    def _clean_native(self, text: str) -> str:
        """Clean a Ge'ez script string."""
        text = unicodedata.normalize("NFC", text)
        # Remove stray Latin punctuation that may have been mixed in
        text = re.sub(r"[.,;:!?]", "", text)
        text = re.sub(r"\s+", " ", text.strip())
        return text

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with F3-specific data.

        - Parse patronymic chain (given, father, grandfather)
        - Flag as patronymic system (no hereditary surname)
        - Generate romanisation variants
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

        # Parse patronymic chain
        chain = self._parse_patronymic_chain(canonical)
        extras["given_name"] = chain["given"]
        extras["father_name"] = chain.get("father", "")
        extras["grandfather_name"] = chain.get("grandfather", "")
        extras["has_patronymic"] = True
        extras["is_mononym"] = not chain.get("father")
        extras["patronymic_depth"] = len(
            [v for v in [chain["given"], chain.get("father"), chain.get("grandfather")] if v]
        )

        # Detect Ge'ez script in native field
        native = entry.get("CanonicalNative", "")
        if native and _has_geez(native):
            extras["script"] = "Ge'ez"

        # Generate romanisation alternate variants
        rom_variants = self._generate_romanisation_variants(canonical)
        for rv in rom_variants:
            variants.append({"str": rv, "type": "romanisation-variant"})

        # Given-name-only variant (common short form)
        if chain.get("father"):
            variants.append(
                {
                    "str": chain["given"],
                    "type": "given-only",
                }
            )

        # Two-generation variant (given + father)
        if chain.get("grandfather"):
            two_gen = f"{chain['given']} {chain['father']}"
            variants.append({"str": two_gen, "type": "two-generation"})

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry per F3 rules.

        - CanonicalLatin must exist
        - If CanonicalNative present, must be Ge'ez or Latin
        - Patronymic chain: at least a given name
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for F3 region")

        # Validate native script if present
        native = entry.get("CanonicalNative", "")
        if native:
            has_g = _has_geez(native)
            has_latin = any("A" <= c <= "z" for c in native if c.isalpha())
            if not has_g and not has_latin:
                raise RegionRuleError("CanonicalNative must be Ge'ez or Latin script")

        # Validate patronymic chain has at least a given name
        chain = self._parse_patronymic_chain(canonical)
        if not chain["given"]:
            raise RegionRuleError("Patronymic chain must have a given name")

        if len(canonical) > 120:
            raise RegionRuleError("Name exceeds 120 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        Sorts by given name (primary), then father, then grandfather.
        This matches the patronymic convention where given name is the
        primary identifier.  Pure function.
        """
        extras = entry.get("RegionalExtras", {})
        given = extras.get("given_name", "")
        father = extras.get("father_name", "")
        grandfather = extras.get("grandfather_name", "")

        if not given:
            canonical = entry.get("CanonicalLatin", "")
            chain = self._parse_patronymic_chain(canonical)
            given = chain["given"]
            father = chain.get("father", "")
            grandfather = chain.get("grandfather", "")

        # ASCII-fold for deterministic sorting
        parts = [self._ascii_fold(given)]
        if father:
            parts.append(self._ascii_fold(father))
        if grandfather:
            parts.append(self._ascii_fold(grandfather))

        return " ".join(parts).upper()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_patronymic_chain(self, name: str) -> Dict[str, str]:
        """
        Parse a patronymic chain.

        Ethiopian/Eritrean names: Given Father [Grandfather]
        No comma-separated format expected, but handle it if present.
        """
        if ", " in name:
            # Unusual for F3 but handle gracefully: treat as Father, Given
            parts = name.split(", ", 1)
            rest = parts[1].strip().split()
            return {
                "given": parts[1].strip().split()[0] if rest else parts[1].strip(),
                "father": parts[0].strip(),
                "grandfather": " ".join(rest[1:]) if len(rest) > 1 else "",
            }

        tokens = name.strip().split()
        result: Dict[str, str] = {"given": ""}
        if len(tokens) >= 1:
            result["given"] = tokens[0]
        if len(tokens) >= 2:
            result["father"] = tokens[1]
        if len(tokens) >= 3:
            result["grandfather"] = " ".join(tokens[2:])
        return result

    def _generate_romanisation_variants(self, name: str) -> List[str]:
        """Generate common romanisation alternates for Amharic names."""
        generated: List[str] = []
        lower = name.lower()

        for original, alternate in self.romanisation_alternates.items():
            if original in lower:
                variant = name
                # Case-preserving replacement (first occurrence)
                idx = lower.find(original)
                variant = variant[:idx] + alternate + variant[idx + len(original) :]
                if variant != name and variant not in generated:
                    generated.append(variant)

        return generated[:3]  # Limit to avoid combinatorial explosion

    def _ascii_fold(self, text: str) -> str:
        """Fold to ASCII for sorting."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
