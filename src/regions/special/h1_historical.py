"""
H1 - Historical (pre-1850) regional processor.

Covers: Pre-modern mathematicians across all regions (Euler, Gauss,
Newton, Fibonacci, al-Khwarizmi, etc.).

Features: Latinised names (Leonhardus Eulerus -> Euler), epithets
(Leonardo of Pisa, al-Khwarizmi), approximate birth/death dates,
no standardised birth certificates, mononyms and place-epithets.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class H1Historical(RegionSpec):
    """
    Historical (pre-1850) region (H1).

    Handles pre-modern naming conventions including:
    - Latinised scholarly names (Eulerus -> Euler)
    - Place-based epithets (Leonardo of Pisa, Roger Bacon)
    - Mononyms (Euclid, Archimedes, Hypatia)
    - Arabic-style names (al-Khwarizmi, ibn Sina)
    - Approximate dates (circa, fl., d.)
    - Multiple name forms across historical periods
    """

    def __init__(self):
        super().__init__(
            code="H1",
            yaml_files=["h1_historical.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["Latin", "Historical"]
        )

        # Latin suffixes that indicate Latinised forms
        self.latin_suffixes = [
            "us", "ius", "eus", "aeus", "anus", "inus",
            "is", "es",
        ]

        # Common epithets / place indicators
        self.epithet_markers = {
            "of", "de", "von", "van", "di", "da",
            "al-", "el-", "ibn", "bin", "ben",
            "the",
        }

        # Historical titles to remove
        self.titles = {
            "Sir", "Lord", "Count", "Baron", "Duke",
            "Bishop", "Abbot", "Friar", "Brother",
            "Father", "Rev", "Rev.",
            "Prof", "Prof.", "Professor",
            "Dr", "Dr.",
        }

        # Date-annotation patterns (strip from names)
        self._date_pattern = re.compile(
            r"\s*\(?\s*(?:c\.?|ca\.?|circa|fl\.?|b\.?|d\.?|ob\.?)"
            r"\s*\d{2,4}\s*(?:-\s*(?:c\.?|ca\.?)?\s*\d{2,4})?\s*\)?\s*$",
            re.IGNORECASE,
        )

        # Known mononyms (no family name)
        self.known_mononyms = {
            "Euclid", "Archimedes", "Hypatia", "Pythagoras",
            "Ptolemy", "Thales", "Diophantus", "Eratosthenes",
            "Apollonius", "Aristarchus", "Brahmagupta",
            "Aryabhata", "Bhaskara",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean historical names in-place.

        - Strip date annotations (c.1707-1783)
        - Remove historical titles
        - Normalize Unicode (NFC)
        - Collapse whitespace
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Remove date annotations
        cleaned = self._date_pattern.sub("", canonical)

        # Remove titles
        titles_pattern = re.compile(
            r"\b(Sir|Lord|Count|Baron|Duke|Bishop|Abbot|Friar|Brother|"
            r"Father|Rev\.?|Prof\.?|Professor|Dr\.?)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", cleaned)

        # Normalize Unicode
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        entry["CanonicalLatin"] = cleaned

        # Clean observed variants
        if "Variants" in entry and "Observed" in entry["Variants"]:
            for variant in entry["Variants"]["Observed"]:
                if "str" in variant and variant["str"]:
                    v = self._date_pattern.sub("", variant["str"])
                    v = titles_pattern.sub("", v)
                    v = re.sub(r"\s+", " ", v.strip())
                    variant["str"] = v

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with H1-specific data.

        - Detect Latinised name forms and generate de-Latinised variants
        - Detect epithets / place names
        - Flag mononyms
        - Detect Arabic-style name components
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

        # Check for mononym
        is_mononym = self._is_mononym(canonical)
        extras["is_mononym"] = is_mononym

        if is_mononym:
            extras["given_name"] = canonical.strip()
            extras["family_name"] = ""
        else:
            family, given = self._split_canonical(canonical)
            extras["family_name"] = family
            extras["given_name"] = given

        # Detect Latinised form and generate de-Latinised variant
        latin_form = self._detect_latinised(canonical)
        if latin_form:
            extras["latinised_form"] = True
            de_latin = self._de_latinise(canonical)
            if de_latin and de_latin != canonical:
                variants.append({"str": de_latin, "type": "de-latinised"})

        # Detect epithet (e.g. "Leonardo of Pisa")
        epithet = self._detect_epithet(canonical)
        if epithet:
            extras["epithet"] = epithet["epithet"]
            extras["epithet_type"] = epithet["type"]
            # Generate variant without epithet
            if epithet.get("base_name"):
                variants.append({
                    "str": epithet["base_name"],
                    "type": "epithet-stripped",
                })

        # Detect Arabic-style components
        arabic = self._detect_arabic_components(canonical)
        if arabic:
            extras.update(arabic)

        # ASCII-lossy variant
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Order-swap variant (non-mononyms only)
        if not is_mononym:
            family = extras.get("family_name", "")
            given = extras.get("given_name", "")
            if family and given:
                variants.append({
                    "str": f"{given} {family}",
                    "type": "order-swap",
                })

        entry["RegionCode"] = self.code

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry per H1 rules.

        - CanonicalLatin must exist
        - Name must not be empty after cleaning
        - Accept broad character set (historical names vary widely)
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        if len(canonical.strip()) < 2:
            raise RegionRuleError("Name too short for H1 region")

        # Historical names can contain a wide range of characters.
        # Block only control characters and obviously invalid codepoints.
        for ch in canonical:
            if unicodedata.category(ch).startswith("C") and ch not in "\t\n":
                raise RegionRuleError(
                    f"Control character U+{ord(ch):04X} in H1 name"
                )

        if len(canonical) > 200:
            raise RegionRuleError("Name exceeds 200 character limit")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key.

        For mononyms: sort by the single name.
        For others: sort by family name, then given.
        Pure function.
        """
        extras = entry.get("RegionalExtras", {})

        if extras.get("is_mononym"):
            name = extras.get("given_name", "")
            return self._remove_diacritics(name).upper().strip()

        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if not family:
            canonical = entry.get("CanonicalLatin", "")
            family, given = self._split_canonical(canonical)

        sort_family = self._remove_diacritics(family).upper()
        sort_given = self._remove_diacritics(given).upper()

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

    def _is_mononym(self, name: str) -> bool:
        """Determine if a name is a mononym (single name, no family)."""
        clean = name.strip()
        # Explicit known mononyms
        if clean in self.known_mononyms:
            return True
        # Single word with no comma
        if " " not in clean and "," not in clean:
            return True
        return False

    def _detect_latinised(self, name: str) -> bool:
        """Detect if name appears to be a Latinised scholarly form."""
        tokens = name.replace(",", "").split()
        for token in tokens:
            lower = token.lower()
            for suffix in self.latin_suffixes:
                if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
                    return True
        return False

    def _de_latinise(self, name: str) -> Optional[str]:
        """
        Attempt to produce a de-Latinised form.

        Heuristic: strip common Latin suffixes (-us, -ius, etc.)
        from the last word.
        """
        if ", " in name:
            parts = name.split(", ", 1)
            family = parts[0].strip()
            given = parts[1].strip()
        else:
            tokens = name.split()
            if len(tokens) < 2:
                return None
            family = tokens[-1]
            given = " ".join(tokens[:-1])

        de_lat = self._strip_latin_suffix(family)
        if de_lat == family:
            return None

        given_de_lat = self._strip_latin_suffix(given) if given else given

        if ", " in name:
            return f"{de_lat}, {given_de_lat}"
        return f"{given_de_lat} {de_lat}"

    def _strip_latin_suffix(self, word: str) -> str:
        """Strip a Latin suffix from a single word."""
        lower = word.lower()
        # Try longer suffixes first
        for suffix in sorted(self.latin_suffixes, key=len, reverse=True):
            if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
                base = word[: len(word) - len(suffix)]
                # Preserve capitalisation
                return base
        return word

    def _detect_epithet(self, name: str) -> Optional[Dict[str, str]]:
        """
        Detect place-based or descriptive epithets.

        Examples: "Leonardo of Pisa", "Roger of Hereford",
        "William the Conqueror" (though we focus on mathematicians).
        """
        # Pattern: Name "of" Place
        match = re.search(
            r"^(.+?)\s+(of|de|von|van|di|da)\s+(.+)$", name, re.IGNORECASE
        )
        if match:
            return {
                "base_name": match.group(1).strip(),
                "epithet": f"{match.group(2)} {match.group(3).strip()}",
                "type": "place",
            }

        # Pattern: Name "the" Descriptor
        match = re.search(r"^(.+?)\s+the\s+(.+)$", name, re.IGNORECASE)
        if match:
            return {
                "base_name": match.group(1).strip(),
                "epithet": f"the {match.group(2).strip()}",
                "type": "descriptive",
            }

        return None

    def _detect_arabic_components(self, name: str) -> Optional[Dict[str, Any]]:
        """Detect Arabic-style name components (al-, ibn, bin, etc.)."""
        lower = name.lower()
        result: Dict[str, Any] = {}

        if "al-" in lower:
            result["has_arabic_article"] = True
        if re.search(r"\bibn\b|\bbin\b|\bben\b", lower):
            result["has_patronymic_marker"] = True
            result["patronymic_type"] = "Arabic"

        return result if result else None

    def _remove_diacritics(self, text: str) -> str:
        """Strip diacritics, keeping base Latin letters."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
