"""
E4 - Korean region implementation (lightweight V7 stub).

This is a lightweight version that provides the basic RegionSpec interface
for V7 pipeline integration without loading the heavy Korean conversion modules.
"""

import re
from typing import Any, Dict

from ...base import RegionRuleError, RegionSpec


class E4KoreanProcessor(RegionSpec):
    """
    Korean region (E4) - Lightweight implementation.

    Provides basic Korean name handling for V7 pipeline without
    the full Korean conversion system to maintain performance.
    """

    def __init__(self):
        super().__init__(
            code="E4",
            yaml_files=["e4_korea.yaml"],
            scripts=["Hangul", "Hanja", "Latin"],
            mixed_scripts=True,
            canonical_order="Family Given",
            romanisation_standards=["Revised Romanization"],
        )

        # Common Korean surnames for pattern matching
        self.korean_surnames = {
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "kang",
            "cho",
            "yoon",
            "jang",
            "lim",
            "han",
            "oh",
            "seo",
            "shin",
            "kwon",
            "hwang",
            "ahn",
            "song",
            "yoo",
            "hong",
            "jeon",
            "go",
            "moon",
            "yang",
            "baek",
            "heo",
            "nam",
            "sim",
            "won",
            "kwak",
            "son",
            "myung",
            "noh",
            "koo",
            "ryu",
            "jin",
            "ma",
            "cha",
            "yu",
            "do",
            "bae",
            "seok",
            "woo",
            "min",
            "gang",
            "ko",
            "goo",
            "tae",
            "pyo",
            "ha",
            # Romanization variants
            "gim",
            "ri",
            "bak",
            "choe",
            "jeong",
            "gang",
            "jo",
            "yun",
            "jang",
            "im",
        }

        # Hangul character ranges for detection
        self.hangul_ranges = [
            (0xAC00, 0xD7AF),  # Hangul Syllables
            (0x1100, 0x11FF),  # Hangul Jamo
            (0x3130, 0x318F),  # Hangul Compatibility Jamo
        ]

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E4 rules."""
        # Basic cleaning for Korean names
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        if not name:
            return name

        # Normalize whitespace
        name = " ".join(name.split())

        # Handle common Korean romanization variations
        name = re.sub(r"\s*-\s*", "-", name)  # Normalize hyphen spacing
        name = re.sub(r"\s*,\s*", ", ", name)  # Normalize comma spacing

        return name.strip()

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E4-specific data."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return

        # Extract basic components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Basic Korean name patterns
        if self._is_korean_name(canonical):
            entry["RegionalExtras"]["korean_name"] = True

            # Generate hyphen/space variants for romanized names
            if not self._is_hangul_text(canonical):
                self._add_romanization_variants(entry, canonical)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract basic name components."""
        components = {}

        if "," in name:
            parts = name.split(",", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Korean names typically: Family Given (no comma)
            words = name.split()
            if len(words) >= 2:
                components["family_name"] = words[0]
                components["given_name"] = " ".join(words[1:])
            else:
                components["family_name"] = name
                components["given_name"] = ""

        return components

    def _is_korean_name(self, name: str) -> bool:
        """Check if name appears to be Korean."""
        # Check for Hangul characters
        if self._is_hangul_text(name):
            return True

        # Check for Korean surnames in romanization
        name_lower = name.lower()
        for surname in self.korean_surnames:
            if name_lower.startswith(surname + " ") or name_lower.startswith(surname + ","):
                return True

        return False

    def _is_hangul_text(self, text: str) -> bool:
        """Check if text contains Hangul characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.hangul_ranges):
                return True
        return False

    def _add_romanization_variants(self, entry: Dict[str, Any], canonical: str):
        """Add common romanization variants."""
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate hyphen/space variants
        if "-" in canonical:
            space_variant = canonical.replace("-", " ")
            if space_variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": space_variant, "type": "romanization-space"}
                )
        elif " " in canonical and "," not in canonical:
            # For given names with spaces, try hyphen
            parts = canonical.split()
            if len(parts) >= 3:  # Family + multi-part given name
                family = parts[0]
                given = "-".join(parts[1:])
                hyphen_variant = f"{family}, {given}"
                entry["Variants"]["Synthesised"].append(
                    {"str": hyphen_variant, "type": "romanization-hyphen"}
                )

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E4 rules."""
        canonical_latin = entry.get("CanonicalLatin", "")
        canonical_native = entry.get("CanonicalNative", "")

        if not canonical_latin and not canonical_native:
            raise RegionRuleError("Missing both CanonicalLatin and CanonicalNative")

        # Basic validation - ensure at least one word
        for canonical in [canonical_latin, canonical_native]:
            if canonical:
                words = canonical.split()
                if len(words) < 1:
                    raise RegionRuleError(f"Name should have at least 1 word: {canonical}")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Korean order: Family, Given
        if family and given:
            sort_key = f"{family}, {given}"
        elif family:
            sort_key = family
        else:
            # Fallback to canonical form
            canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
            sort_key = canonical

        # Rule 13: Korean Hyphen/Space - collapse in order_key
        # Both "Jong-sik" and "Jong sik" should produce same sort key
        sort_key = sort_key.upper().replace(",", "").replace("-", "").strip()
        # Normalize all whitespace to single spaces
        return " ".join(sort_key.split())
