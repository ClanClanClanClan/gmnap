"""
B2 - South-Slavic & Central Europe region implementation.

Covers: Bulgaria, Serbia, Montenegro, Croatia, Slovenia, Bosnia and Herzegovina,
North Macedonia, Poland, Czech Republic, Slovakia, Hungary, Romania, Albania, Kosovo.

Features: Mixed Latin & Cyrillic scripts, Gaj's Latin alphabet,
Hungarian name-order flip, diverse naming conventions across Central Europe.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class B2_SouthSlavicCentral(RegionSpec):
    """
    South-Slavic & Central Europe region (B2).

    Handles diverse naming conventions across Central and Southeastern Europe:
    - Mixed scripts: Latin (Polish, Czech, Slovak, Croatian, Slovene) and Cyrillic (Serbian, Bulgarian, Macedonian)
    - Gaj's Latin alphabet for South Slavic languages (č, ć, đ, š, ž)
    - Hungarian name order (Family Given instead of Given Family)
    - Polish special characters (ą, ć, ę, ł, ń, ó, ś, ź, ż)
    - Czech/Slovak characters (á, č, ď, é, ě, í, ň, ó, ř, š, ť, ú, ů, ý, ž)
    - Romanian characters (ă, â, î, ș, ț)
    """

    def __init__(self):
        super().__init__(
            code="B2",
            yaml_files=["b2_south_slavic_central.yaml"],
            scripts=["Latin", "Cyrillic"],
            mixed_scripts=True,
            canonical_order="Family, Given",  # Except Hungary
            romanisation_standards=["Gaj's Latin", "ISO 9", "GOST 7.79"],
        )

        # Country-specific character sets
        self.polish_chars = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
        self.czech_slovak_chars = set("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ")
        self.south_slavic_latin = set("čćđšžČĆĐŠŽ")  # Gaj's alphabet
        self.romanian_chars = set("ăâîșțĂÂÎȘȚ")
        self.cyrillic_chars = set(
            "абвгдежзијклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        )

        # Combined Latin character set for the region
        self.latin_extended = (
            self.polish_chars
            | self.czech_slovak_chars
            | self.south_slavic_latin
            | self.romanian_chars
        )

        # Country mapping with specific features
        self.country_features = {
            "PL": {
                "chars": self.polish_chars,
                "suffixes": ["ski", "ska", "cki", "cka", "icz", "owicz", "ewicz"],
            },
            "CZ": {"chars": self.czech_slovak_chars, "suffixes": ["ová", "ý", "á", "ek", "ík"]},
            "SK": {
                "chars": self.czech_slovak_chars,
                "suffixes": ["ová", "ý", "á", "ek", "ík", "iak"],
            },
            "HU": {"chars": set("áéíóöőúüűÁÉÍÓÖŐÚÜŰ"), "name_order": "Family Given"},
            "RO": {"chars": self.romanian_chars, "suffixes": ["escu", "eanu", "aru", "an"]},
            "HR": {"chars": self.south_slavic_latin, "suffixes": ["ić", "ović", "ević"]},
            "SI": {"chars": self.south_slavic_latin, "suffixes": ["ič", "nik", "ar"]},
            "RS": {
                "scripts": ["Cyrillic", "Latin"],
                "suffixes": ["ић", "овић", "евић", "ić", "ović", "ević"],
            },
            "BG": {"scripts": ["Cyrillic"], "suffixes": ["ов", "ова", "ев", "ева", "ски", "ска"]},
            "MK": {"scripts": ["Cyrillic"], "suffixes": ["ски", "ска", "ов", "ова", "ев", "ева"]},
            "BA": {"scripts": ["Latin", "Cyrillic"], "suffixes": ["ić", "ović", "begović"]},
            "ME": {"scripts": ["Latin", "Cyrillic"], "suffixes": ["ić", "ović", "ević"]},
            "AL": {"chars": set("ëçËÇ"), "suffixes": ["i", "u", "aj", "llari"]},
            "XK": {
                "scripts": ["Latin"],
                "suffixes": ["i", "u", "aj", "ić"],
            },  # Albanian/Serbian mix
        }

        # Hungarian name order detection patterns
        self.hungarian_patterns = {
            "family_suffixes": ["fi", "fy", "i", "y", "né"],  # Common Hungarian family name endings
            "common_families": [
                "Nagy",
                "Kovács",
                "Tóth",
                "Szabó",
                "Horváth",
                "Varga",
                "Kiss",
                "Molnár",
                "Németh",
                "Farkas",
            ],
        }

        # Gender suffix patterns for Slavic languages
        self.gender_suffixes = {
            "female": {
                "czech_slovak": "ová",
                "polish": "ska",
                "bulgarian": ["ова", "ева", "ска"],
                "serbian": ["ић", "овић", "евић"],  # Same as male in Serbian
            }
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Central European names according to regional conventions.

        - Remove titles and academic degrees
        - Handle mixed scripts appropriately
        - Normalize spacing and punctuation
        - Preserve gender-specific suffixes
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")

        # Remove common Central European titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Doc\.?|Doz\.?|Prof\.?|Ing\.?|Mgr\.?|Bc\.?|JUDr\.?|PhDr\.?|MUDr\.?|RNDr\.?|ThDr\.?|PaedDr\.?|CSc\.?|DrSc\.?|PhD\.?)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Remove nobility titles (still sometimes seen)
        nobility_pattern = re.compile(r"\b(von|de|gróf|báró|herceg|князь|граф)\s+", re.IGNORECASE)
        cleaned = nobility_pattern.sub("", cleaned)

        # Normalize Unicode
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Clean up spacing
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        # Handle Hungarian name order if detected
        if self._is_hungarian_name(cleaned):
            # Already in Family Given order, ensure comma separation
            if " " in cleaned and "," not in cleaned:
                parts = cleaned.split(" ", 1)
                cleaned = f"{parts[0]}, {parts[1]}"

        entry["CanonicalLatin"] = cleaned

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment Central European names with regional variants and metadata.

        - Generate script variants (Latin/Cyrillic conversions where applicable)
        - Handle gender-specific surname variants
        - Create ASCII variants
        - Add country-specific metadata
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Initialize variants
        if "VariantsSynthesised" not in entry:
            entry["VariantsSynthesised"] = []

        variants = entry["VariantsSynthesised"]

        # Generate ASCII variant
        ascii_variant = self._to_ascii(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Detect script and country
        script = self._detect_script(canonical)
        estimated_country = self._estimate_country(canonical, script)

        # Generate script variants for countries with mixed scripts
        if estimated_country in ["RS", "BA", "ME"]:  # Serbian/Bosnian/Montenegrin
            if script == "Latin":
                cyrillic_variant = self._latin_to_cyrillic_serbian(canonical)
                if cyrillic_variant and cyrillic_variant != canonical:
                    variants.append({"str": cyrillic_variant, "type": "romanisation-alt"})
            elif script == "Cyrillic":
                latin_variant = self._cyrillic_to_latin_serbian(canonical)
                if latin_variant and latin_variant != canonical:
                    variants.append({"str": latin_variant, "type": "romanisation-alt"})

        # Handle gender variants for Czech/Slovak
        if estimated_country in ["CZ", "SK"]:
            gender_variants = self._generate_gender_variants(canonical)
            for variant in gender_variants:
                variants.append(variant)

        # Rule 10: Hungarian Name Order - generate both native and Western orders
        if self._is_hungarian_name(canonical):
            hungarian_variants = self._generate_hungarian_order_variants(canonical)
            for variant in hungarian_variants:
                variants.append(variant)

            # Store Hungarian name order information in RegionalExtras
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}
            entry["RegionalExtras"]["is_hungarian_name"] = True
            entry["RegionalExtras"]["native_order_generated"] = True

        # Generate order swap variants for non-Hungarian names
        elif ", " in canonical:
            family, given = canonical.split(", ", 1)
            swapped = f"{given} {family}"
            variants.append({"str": swapped, "type": "order-swap"})

        # Add regional metadata
        entry["RegionCode"] = "B2"
        entry["RegionFeatures"] = {
            "script": script,
            "estimated_country": estimated_country,
            "has_diacritics": self._has_diacritics(canonical),
            "is_hungarian_order": self._is_hungarian_name(canonical),
            "has_gender_suffix": self._has_gender_suffix(canonical, estimated_country),
        }

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate Central European names according to regional rules.

        - Check for valid character sets (Latin extended or Cyrillic)
        - Validate name structure
        - Ensure script consistency
        - Check for reasonable length
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")

        # Check for invalid whitespace characters first
        if any(c in canonical for c in "\n\r\t\xa0"):
            raise RegionRuleError(f"Invalid whitespace characters in name: {canonical}")

        # Detect script
        script = self._detect_script(canonical)

        # Validate character set based on script
        if script == "Latin":
            valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
            valid_chars.update(self.latin_extended)
            valid_chars.update(" ,-'.")
        elif script == "Cyrillic":
            valid_chars = self.cyrillic_chars.copy()
            valid_chars.update(" ,-'.")
        else:
            raise RegionRuleError(f"Mixed or unknown script in name: {canonical}")

        invalid_chars = set(canonical) - valid_chars
        if invalid_chars:
            raise RegionRuleError(
                f"Invalid characters for {script} script: {', '.join(invalid_chars)}"
            )

        # Check basic structure
        if not (", " in canonical or " " in canonical):
            raise RegionRuleError("Invalid name format: must contain family and given names")

        # Check length
        if len(canonical) > 80:
            raise RegionRuleError("Name too long (>80 characters)")

        # Warn about potential issues
        if script == "Mixed":
            self.logger.warning(f"Mixed scripts detected in name: {canonical}")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate sort key for Central European names.

        - Handle different alphabetical orders (Czech/Slovak vs Polish vs others)
        - Sort by family name
        - Handle special characters appropriately
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return ""

        # Extract family and given names
        if ", " in canonical:
            family, given = canonical.split(", ", 1)
        else:
            # Might be Hungarian (Family Given) or other format
            parts = canonical.split()
            if self._is_hungarian_name(canonical) and len(parts) >= 2:
                family = parts[0]
                given = " ".join(parts[1:])
            else:
                # Assume last word is family
                family = parts[-1] if parts else ""
                given = " ".join(parts[:-1]) if len(parts) > 1 else ""

        # Create sort key - use transliteration for Cyrillic
        script = self._detect_script(family)
        if script == "Cyrillic":
            family_sort = self._cyrillic_sort_key(family)
        else:
            family_sort = self._latin_sort_key(family)

        given_sort = self._to_ascii(given).upper()

        return f"{family_sort}, {given_sort}"

    def _detect_script(self, text: str) -> str:
        """Detect whether text is Latin, Cyrillic, or Mixed."""
        has_latin = bool(re.search(r"[a-zA-Z]", text))
        has_cyrillic = any(c in self.cyrillic_chars for c in text)

        if has_latin and has_cyrillic:
            return "Mixed"
        elif has_cyrillic:
            return "Cyrillic"
        else:
            return "Latin"

    def _to_ascii(self, text: str) -> str:
        """Convert text to ASCII, handling special characters."""
        # First normalize
        text = unicodedata.normalize("NFD", text)

        # Special replacements for common characters
        replacements = {
            "ł": "l",
            "Ł": "L",
            "ø": "o",
            "Ø": "O",
            "đ": "dj",
            "Đ": "Dj",
            "ß": "ss",
            "æ": "ae",
            "Æ": "AE",
            "œ": "oe",
            "Œ": "OE",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        # Remove combining marks
        ascii_text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        return ascii_text

    def _has_diacritics(self, text: str) -> bool:
        """Check if text contains diacritical marks."""
        return any(c in self.latin_extended for c in text)

    def _is_hungarian_name(self, name: str) -> bool:
        """Detect if name follows Hungarian conventions."""
        name.lower()

        # Check for Hungarian characters
        if any(c in name for c in "őűŐŰ"):
            return True

        # Check for common Hungarian family names
        first_word = name.split()[0] if name.split() else ""
        if first_word in self.hungarian_patterns["common_families"]:
            return True

        # Check for typical Hungarian endings
        if any(
            first_word.endswith(suffix) for suffix in self.hungarian_patterns["family_suffixes"]
        ):
            return True

        return False

    def _estimate_country(self, name: str, script: str) -> Optional[str]:
        """Estimate country based on name characteristics."""
        name.lower()

        # Script-based initial filtering
        if script == "Cyrillic":
            # Check Bulgarian patterns
            if any(name.endswith(suffix) for suffix in ["ов", "ова", "ев", "ева"]):
                return "BG"
            # Serbian uses ић extensively
            if name.endswith("ић"):
                return "RS"
            # Default Cyrillic to Bulgarian
            return "BG"

        # Latin script analysis
        # Polish
        if any(c in name for c in "łńśźżŁŃŚŹŻ"):
            return "PL"

        # Czech/Slovak (harder to distinguish)
        if any(c in name for c in "řěůŘĚŮ"):
            return "CZ"
        if any(name.endswith(suffix) for suffix in ["ová", "ý", "ský"]):
            return "CZ" if "ř" in name else "SK"

        # Hungarian
        if self._is_hungarian_name(name):
            return "HU"

        # Romanian
        if any(c in name for c in "ăîșțĂÎȘȚ") or any(
            name.endswith(suffix) for suffix in ["escu", "eanu"]
        ):
            return "RO"

        # Croatian/Serbian Latin
        if any(name.endswith(suffix) for suffix in ["ić", "ović", "ević"]):
            if "ć" in name or "č" in name:
                return "HR"
            return "RS"  # Serbian Latin

        # Albanian
        if any(c in name for c in "ëË") or any(name.endswith(suffix) for suffix in ["aj", "llari"]):
            return "AL"

        return None

    def _has_gender_suffix(self, name: str, country: Optional[str]) -> bool:
        """Check if name has gender-specific suffix."""
        if country in ["CZ", "SK"] and name.endswith("ová"):
            return True
        if country == "PL" and name.endswith("ska"):
            return True
        if country == "BG" and any(name.endswith(suffix) for suffix in ["ова", "ева", "ска"]):
            return True
        return False

    def _generate_gender_variants(self, name: str) -> List[Dict[str, str]]:
        """Generate gender variants for Czech/Slovak names."""
        variants = []

        if ", " in name:
            family, given = name.split(", ", 1)

            # Female to male variant
            if family.endswith("ová"):
                male_family = family[:-3]  # Remove ová
                if male_family.endswith("sk"):
                    male_family += "ý"
                elif not male_family.endswith(("ý", "í")):
                    male_family += "ý"

                variants.append({"str": f"{male_family}, {given}", "type": "gender-variant"})

        return variants

    def _generate_hungarian_order_variants(self, name: str) -> List[Dict[str, str]]:
        """
        Rule 10: Hungarian Name Order - generate both native and Western orders.

        Hungarian names traditionally follow Family Given order (native), but
        Western publications often use Given Family order. This method generates
        both variants for comprehensive matching.

        Examples:
        - "Nagy József" (native) → "József Nagy" (Western)
        - "Kovács, Anna" (canonical) → "Anna Kovács" (Western)
        """
        variants = []

        if ", " in name:
            # Already in "Family, Given" canonical format
            family, given = name.split(", ", 1)

            # Generate native order (Family Given without comma)
            native_order = f"{family} {given}"
            variants.append({"str": native_order, "type": "hungarian-native-order"})

            # Generate Western order (Given Family)
            western_order = f"{given} {family}"
            variants.append({"str": western_order, "type": "hungarian-western-order"})
        else:
            # Name might be in Family Given format (native) without comma
            parts = name.split(" ", 1)
            if len(parts) == 2:
                family, given = parts[0], parts[1]

                # Generate canonical format (Family, Given)
                canonical_format = f"{family}, {given}"
                variants.append({"str": canonical_format, "type": "hungarian-canonical"})

                # Generate Western order (Given Family)
                western_order = f"{given} {family}"
                variants.append({"str": western_order, "type": "hungarian-western-order"})

        return variants

    def _latin_to_cyrillic_serbian(self, text: str) -> Optional[str]:
        """Convert Serbian Latin to Cyrillic."""
        # Basic Serbian Latin to Cyrillic mapping
        mapping = {
            "a": "а",
            "b": "б",
            "c": "ц",
            "č": "ч",
            "ć": "ћ",
            "d": "д",
            "đ": "ђ",
            "e": "е",
            "f": "ф",
            "g": "г",
            "h": "х",
            "i": "и",
            "j": "ј",
            "k": "к",
            "l": "л",
            "lj": "љ",
            "m": "м",
            "n": "н",
            "nj": "њ",
            "o": "о",
            "p": "п",
            "r": "р",
            "s": "с",
            "š": "ш",
            "t": "т",
            "u": "у",
            "v": "в",
            "z": "з",
            "ž": "ж",
            "A": "А",
            "B": "Б",
            "C": "Ц",
            "Č": "Ч",
            "Ć": "Ћ",
            "D": "Д",
            "Đ": "Ђ",
            "E": "Е",
            "F": "Ф",
            "G": "Г",
            "H": "Х",
            "I": "И",
            "J": "Ј",
            "K": "К",
            "L": "Л",
            "Lj": "Љ",
            "M": "М",
            "N": "Н",
            "Nj": "Њ",
            "O": "О",
            "P": "П",
            "R": "Р",
            "S": "С",
            "Š": "Ш",
            "T": "Т",
            "U": "У",
            "V": "В",
            "Z": "З",
            "Ž": "Ж",
        }

        result = text
        # Handle digraphs first
        result = result.replace("lj", "љ").replace("Lj", "Љ").replace("LJ", "Љ")
        result = result.replace("nj", "њ").replace("Nj", "Њ").replace("NJ", "Њ")
        result = result.replace("dž", "џ").replace("Dž", "Џ").replace("DŽ", "Џ")

        # Then single characters
        for latin, cyrillic in mapping.items():
            if len(latin) == 1:  # Skip digraphs already handled
                result = result.replace(latin, cyrillic)

        return result if result != text else None

    def _cyrillic_to_latin_serbian(self, text: str) -> Optional[str]:
        """Convert Serbian Cyrillic to Latin."""
        # Reverse mapping
        mapping = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "ђ": "đ",
            "е": "e",
            "ж": "ž",
            "з": "z",
            "и": "i",
            "ј": "j",
            "к": "k",
            "л": "l",
            "љ": "lj",
            "м": "m",
            "н": "n",
            "њ": "nj",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "ћ": "ć",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "c",
            "ч": "č",
            "џ": "dž",
            "ш": "š",
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Ђ": "Đ",
            "Е": "E",
            "Ж": "Ž",
            "З": "Z",
            "И": "I",
            "Ј": "J",
            "К": "K",
            "Л": "L",
            "Љ": "Lj",
            "М": "M",
            "Н": "N",
            "Њ": "Nj",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "Ћ": "Ć",
            "У": "U",
            "Ф": "F",
            "Х": "H",
            "Ц": "C",
            "Ч": "Č",
            "Џ": "Dž",
            "Ш": "Š",
        }

        result = text
        for cyrillic, latin in mapping.items():
            result = result.replace(cyrillic, latin)

        return result if result != text else None

    def _cyrillic_sort_key(self, text: str) -> str:
        """Generate sort key for Cyrillic text."""
        # Transliterate to Latin for consistent sorting
        latin = self._cyrillic_to_latin_serbian(text)
        if latin:
            return self._latin_sort_key(latin)
        # Fallback
        return text.upper()

    def _latin_sort_key(self, text: str) -> str:
        """Generate sort key for Latin text with special character handling."""
        # Language-specific sorting would ideally use locale.strxfrm
        # For now, use ASCII approximation
        return self._to_ascii(text).upper()
