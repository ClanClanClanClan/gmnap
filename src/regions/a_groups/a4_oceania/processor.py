"""
A4 - Oceania Island States region implementation.

Covers: FJ, PG, SB, VU, WS, TO, KI, TV, NR, CK, NU, PF, NC
(Fiji, Papua New Guinea, Solomon Islands, Vanuatu, Samoa, Tonga,
Kiribati, Tuvalu, Nauru, Cook Islands, Niue, French Polynesia, New Caledonia)

Features: Polynesian macron restoration, island-specific patterns,
          Māori/Samoan/Tongan forms, colonial vs indigenous naming.
"""

import re
from typing import Any, Dict

from ...base import RegionRuleError, RegionSpec


class A4OceaniaProcessor(RegionSpec):
    """
    Oceania Island States region (A4).

    Handles Oceanic naming conventions:
    - Polynesian macron restoration (ā, ē, ī, ō, ū)
    - Island-specific name patterns
    - Māori, Samoan, Tongan, Fijian forms
    - Colonial (English/French) vs indigenous naming
    - Polynesian name particles (O, Ki, Ka, Te, etc.)
    - Multi-part Polynesian names without family/given distinction
    """

    def __init__(self):
        super().__init__(
            code="A4",
            yaml_files=["a4_oceania.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",  # Colonial format; many use mononyms
            romanisation_standards=[],
        )

        # Polynesian characters with macrons
        self.macron_chars = {
            "ā",
            "Ā",
            "ē",
            "Ē",
            "ī",
            "Ī",
            "ō",
            "Ō",
            "ū",
            "Ū",
            "ă",
            "Ă",
            "ĕ",
            "Ĕ",
            "ŏ",
            "Ŏ",  # Some regions use breve
        }

        # Other special characters used in the region
        self.special_chars = {
            "'",
            "'",
            "ʻ",  # ʻokina (glottal stop)
            "ç",
            "Ç",  # French influence (New Caledonia)
            "ñ",
            "Ñ",  # Some Spanish influence
        }

        self.allowed_chars = self.macron_chars | self.special_chars

        # Polynesian name particles (often part of the name, not titles)
        self.polynesian_particles = {
            # Māori
            "Te",
            "Ngā",
            "Ngāi",
            "Ngāti",
            "Ka",
            "Tū",
            # Samoan
            "O",
            "Le",
            "Sa",
            "Fa'a",
            "Faa",
            # Tongan
            "Tu'i",
            "Tui",
            "'Aho",
            "Aho",
            "Faka",
            # Fijian
            "Ro",
            "Adi",
            "Ratu",
            "Tui",
            # Hawaiian/Cook Islands
            "Ke",
            "Ka",
            "Na",
            "Kaha",
            # General
            "Ki",
            "Vai",
            "Mata",
            "Motu",
        }

        # Common Polynesian name elements
        self.common_elements = {
            # Nature elements (common in Polynesian names)
            "moana",
            "vai",
            "mata",
            "rangi",
            "lani",
            "marama",
            "tane",
            "wahine",
            "keiki",
            "tamariki",
            # Directional/locational
            "hema",
            "tonga",
            "tokelau",
            "hiva",
            # Status/nobility markers
            "ariki",
            "ali'i",
            "alii",
            "matai",
            "tulafale",
        }

        # Colonial-origin surnames (English/French)
        self.colonial_surnames = {
            # English
            "Smith",
            "Williams",
            "Brown",
            "Wilson",
            "Taylor",
            "Johnson",
            "White",
            "Martin",
            "Thompson",
            "Harris",
            # French
            "Martin",
            "Bernard",
            "Dubois",
            "Thomas",
            "Robert",
            "Petit",
            "Durand",
            "Leroy",
            "Moreau",
            "Simon",
        }

        # Common Polynesian first names
        self.polynesian_first_names = {
            # Māori
            "Aroha",
            "Hine",
            "Mere",
            "Pania",
            "Tane",
            "Wiremu",
            # Samoan
            "Tala",
            "Sina",
            "Malia",
            "Pua",
            "Tui",
            "Sione",
            # Tongan
            "Salote",
            "Finau",
            "Viliami",
            "Siaosi",
            "Mele",
            # Fijian
            "Mere",
            "Salote",
            "Litia",
            "Vasiti",
            "Jone",
            "Peni",
        }

        # Titles (should be removed)
        self.titles = {
            # English
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Rev",
            "Rev.",
            "Fr",
            "Fr.",
            # French
            "M",
            "M.",
            "Mme",
            "Mlle",
            "Dr",
            "Pr",
            # Traditional (these might be part of names, need careful handling)
            "Tui",
            "Tu'i",
            "Ratu",
            "Adi",
            "Ro",  # Often integral to names
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to A4 rules."""
        # Clean canonical forms
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        # Clean variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        # Input validation - ensure it's a string
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")

        if not name:
            return name

        # Security: filter out dangerous control characters (except safe whitespace)
        if any(ord(c) < 32 and c not in "\t\n\r " for c in name):
            raise RegionRuleError("Name contains dangerous control characters")

        # Handle ʻokina normalization (various apostrophe-like characters → ʻ)
        name = self._normalize_okina(name)

        # Remove titles (but be careful with traditional titles that might be names)
        name = self._remove_titles(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        return name.strip()

    def _normalize_okina(self, text: str) -> str:
        """Normalize various apostrophe-like characters to ʻokina."""
        # Common apostrophe-like characters that represent ʻokina
        okina_variants = ["'", "'", "'", "`", "´", "ʼ"]

        for variant in okina_variants:
            # Only replace if it's between letters (not possessive)
            text = re.sub(rf"([a-zA-Z]){variant}([a-zA-Z])", r"\1ʻ\2", text)

        return text

    def _remove_titles(self, text: str) -> str:
        """Remove titles from beginning of name."""
        if not text:
            return text

        words = text.split()

        # Check first word for common titles
        while words and words[0] in self.titles:
            # Special handling for traditional titles that might be part of names
            if words[0] in ["Tui", "Tu'i", "Ratu", "Adi", "Ro"] and len(words) > 1:
                # Check if it's likely a title vs part of name
                # If followed by a known first name or colonial surname, likely a title
                if len(words) > 1 and (
                    words[1] in self.polynesian_first_names or words[1] in self.colonial_surnames
                ):
                    words.pop(0)
                else:
                    # Likely part of the name, keep it
                    break
            else:
                words.pop(0)

        return " ".join(words)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with A4-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate synthesized variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Add macron-restored variant (Rule #31)
        macron_variant = self._restore_macrons(canonical)
        if macron_variant != canonical:
            entry["Variants"]["Synthesised"].append(
                {"str": macron_variant, "type": "macron-restored"}
            )

        # Add no-macron variant
        no_macron = self._remove_macrons(canonical)
        if no_macron != canonical:
            entry["Variants"]["Synthesised"].append({"str": no_macron, "type": "no-macron"})

        # Add ASCII variant
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical and ascii_variant != no_macron:
            entry["Variants"]["Synthesised"].append({"str": ascii_variant, "type": "ascii-lossy"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Oceanic-specific handling."""
        components = {}

        # Check if it's a mononym (common in Pacific islands)
        if "," not in name and len(name.split()) == 1:
            components["name_type"] = "mononym"
            components["full_name"] = name
            return components

        # Detect name pattern (colonial vs indigenous)
        is_colonial = self._detect_colonial_pattern(name)
        components["name_pattern"] = "colonial" if is_colonial else "indigenous"

        if "," in name:
            # Western format: Family, Given
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""

            components["family_name"] = family
            components["given_name"] = given
        else:
            # Check for Polynesian multi-part names
            words = name.split()

            # Check if it starts with a particle
            if words and words[0] in self.polynesian_particles:
                components["has_particle"] = True
                components["particle"] = words[0]

                # In Polynesian names, particles are often integral
                # Don't separate them for sorting
                components["full_name"] = name
                components["name_type"] = "polynesian"
            elif is_colonial and len(words) >= 2:
                # Assume Western order for colonial names
                given = " ".join(words[:-1])
                family = words[-1]
                components["family_name"] = family
                components["given_name"] = given
            else:
                # Indigenous name without clear family/given split
                components["full_name"] = name
                components["name_type"] = "indigenous"

        # Check for traditional elements
        name_lower = name.lower()
        traditional_elements = []
        for element in self.common_elements:
            if element in name_lower:
                traditional_elements.append(element)

        if traditional_elements:
            components["traditional_elements"] = traditional_elements

        return components

    def _detect_colonial_pattern(self, name: str) -> bool:
        """Detect if name follows colonial (European) pattern."""
        words = name.split()

        # Check for colonial surnames
        for word in words:
            if word in self.colonial_surnames:
                return True

        # Check for Western given names with Polynesian surnames (hybrid)
        # This is actually common, so not necessarily "colonial"

        # If has comma, likely colonial format
        if "," in name:
            return True

        # If all words are non-Polynesian, likely colonial
        has_polynesian = False
        for word in words:
            if (
                any(char in word for char in self.macron_chars)
                or "ʻ" in word
                or word in self.polynesian_particles
                or word.lower() in self.common_elements
            ):
                has_polynesian = True
                break

        return not has_polynesian

    def _restore_macrons(self, name: str) -> str:
        """Restore macrons to common Polynesian words (Rule #31)."""
        # Common words that should have macrons
        # This is a simplified set - full implementation would need comprehensive dictionary
        macron_map = {
            # Māori common words
            "maori": "māori",
            "Maori": "Māori",
            "pakeha": "pākehā",
            "Pakeha": "Pākehā",
            "whanau": "whānau",
            "Whanau": "Whānau",
            "hapu": "hapū",
            "Hapu": "Hapū",
            # Māori name elements
            "Tamati": "Tāmati",
            "tamati": "tāmati",
            "Rangi": "Rāngi",
            "rangi": "rāngi",
            "Hone": "Hōne",
            "hone": "hōne",
            "Mere": "Mēre",
            "mere": "mēre",
            "Tane": "Tāne",
            "tane": "tāne",
            "Ngata": "Ngāta",
            "ngata": "ngāta",
            "Ratana": "Rātana",
            "ratana": "rātana",
            "Mahuta": "Māhuta",
            "mahuta": "māhuta",
            "Pomare": "Pōmare",
            "pomare": "pōmare",
            "Turei": "Tūrei",
            "turei": "tūrei",
            "Parata": "Pārata",
            "parata": "pārata",
            "Tamihere": "Tāmihere",
            "tamihere": "tāmihere",
            "Mahara": "Māhara",
            "mahara": "māhara",
            "Kahui": "Kāhui",
            "kahui": "kāhui",
            "Rapata": "Rāpata",
            "rapata": "rāpata",
            # Samoan name elements
            "Tui": "Tu'i",
            "Malietoa": "Mālietoa",
            "Tupua": "Tupuā",
            "Tamasese": "Tāmasese",
            "Matautia": "Mataʻutia",
            "Tuilaepa": "Tuila'epa",
            "Tuimalealiifano": "Tuimalealiʻifano",
            "Fiame": "Fiamē",
            "Naomi": "Naomi",  # no macron
            # Tongan name elements
            "Tupou": "Tūpou",
            "tupou": "tūpou",
            "Taufa": "Taufaʻāhau",
            "Lavaka": "Lāvaka",
            "lavaka": "lāvaka",
            "Fonua": "Fonuā",
            "Vaha'i": "Vahaʻi",
            # Hawaiian
            "ohana": "ʻohana",
            "Ohana": "ʻOhana",
            "kane": "kāne",
            "Kane": "Kāne",
            "Kamehameha": "Kamehameha",  # no macron
            "Liliuokalani": "Liliʻuokalani",
            # General Polynesian
            "malo": "mālō",
            "Malo": "Mālō",
        }

        result = name
        for word, macron_word in macron_map.items():
            # Use word boundaries to avoid partial matches
            result = re.sub(rf"\b{word}\b", macron_word, result)

        return result

    def _remove_macrons(self, name: str) -> str:
        """Remove macrons from name."""
        replacements = {
            "ā": "a",
            "Ā": "A",
            "ē": "e",
            "Ē": "E",
            "ī": "i",
            "Ī": "I",
            "ō": "o",
            "Ō": "O",
            "ū": "u",
            "Ū": "U",
            "ă": "a",
            "Ă": "A",
            "ĕ": "e",
            "Ĕ": "E",
            "ŏ": "o",
            "Ŏ": "O",
        }

        result = name
        for macron, plain in replacements.items():
            result = result.replace(macron, plain)

        return result

    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII variant of name."""
        # First remove macrons
        result = self._remove_macrons(name)

        # Handle ʻokina
        result = result.replace("ʻ", "'")

        # Handle other special characters
        replacements = {"ç": "c", "Ç": "C", "ñ": "n", "Ñ": "N", """: "'", """: "'", "ʼ": "'"}

        for char, ascii_char in replacements.items():
            result = result.replace(char, ascii_char)

        # Final normalization
        import unicodedata

        result = unicodedata.normalize("NFKD", result)
        result = result.encode("ascii", "ignore").decode("ascii")

        return result

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to A4 rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        # Check for valid characters
        if not self._is_valid_oceanic_name(canonical):
            invalid_chars = (
                set(canonical)
                - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ,.-")
                - self.allowed_chars
            )
            if invalid_chars:
                raise RegionRuleError(f"Invalid characters in name: {invalid_chars}")

        # Validate structure based on name type
        components = entry.get("RegionalExtras", {})
        name_type = components.get("name_type", "unknown")

        if name_type == "mononym":
            # Mononyms should not have commas
            if "," in canonical:
                raise RegionRuleError("Mononym should not contain comma")

        elif name_type == "colonial" or "family_name" in components:
            # Western format validation
            if "," in canonical:
                parts = canonical.split(",")
                if len(parts) != 2:
                    raise RegionRuleError(f"Invalid comma usage in name: {canonical}")
                if not parts[0].strip() or not parts[1].strip():
                    raise RegionRuleError(f"Empty name component: {canonical}")

    def _is_valid_oceanic_name(self, name: str) -> bool:
        """Check if name contains valid Oceanic characters."""
        # Allow basic Latin, Polynesian special characters, and common punctuation
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-")
        allowed.update(self.allowed_chars)

        return all(c in allowed for c in name)

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        name_type = components.get("name_type", "unknown")

        if name_type in ["mononym", "indigenous", "polynesian"]:
            # For mononyms and indigenous names, sort by full name
            full_name = components.get("full_name", "")
            if full_name:
                sort_key = full_name
            else:
                # Fallback to canonical
                sort_key = entry.get("CanonicalLatin", "")
        else:
            # Western format sorting
            family = components.get("family_name", "")
            given = components.get("given_name", "")

            if family:
                sort_key = f"{family}, {given}".strip(", ")
            else:
                # Fallback
                sort_key = entry.get("CanonicalLatin", "")

        # Normalize for sorting (remove macrons for consistent ordering)
        sort_key = self._remove_macrons(sort_key)
        sort_key = sort_key.replace("ʻ", "")  # Remove ʻokina for sorting

        # Uppercase and normalize whitespace
        sort_key = " ".join(sort_key.split()).upper()

        return sort_key
