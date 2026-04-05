"""
Baltic (C9) regional processor.

Implements Lithuanian and Latvian naming patterns.
Features: Latin script with diacritics (ą,č,ę,ė,į,š,ų,ū,ž for Lithuanian;
ā,č,ē,ģ,ī,ķ,ļ,ņ,š,ū,ž for Latvian), gendered surname suffixes,
and patronymic/matronymic traditions.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class C9_Baltic(RegionSpec):
    """Handler for C9 - Baltic (Lithuanian, Latvian)."""

    def __init__(self):
        super().__init__(
            code="C9",
            yaml_files=["c9_baltic.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["ISO 9"],
        )

        # Lithuanian diacritical characters
        self.lithuanian_chars = {
            "ą",
            "č",
            "ę",
            "ė",
            "į",
            "š",
            "ų",
            "ū",
            "ž",
            "Ą",
            "Č",
            "Ę",
            "Ė",
            "Į",
            "Š",
            "Ų",
            "Ū",
            "Ž",
        }

        # Latvian diacritical characters
        self.latvian_chars = {
            "ā",
            "č",
            "ē",
            "ģ",
            "ī",
            "ķ",
            "ļ",
            "ņ",
            "š",
            "ū",
            "ž",
            "Ā",
            "Č",
            "Ē",
            "Ģ",
            "Ī",
            "Ķ",
            "Ļ",
            "Ņ",
            "Š",
            "Ū",
            "Ž",
        }

        # Lithuanian masculine surname suffixes and their feminine counterparts
        self.lt_surname_gender_map = {
            # Masculine → feminine mappings
            "auskas": ("auskienė", "auskaitė"),  # married, unmarried
            "aitis": ("aitienė", "aitytė"),
            "ūnas": ("ūnienė", "ūnaitė"),
            "ėnas": ("ėnienė", "ėnaitė"),
            "onis": ("onienė", "onytė"),
            "utis": ("utienė", "utytė"),
            "us": ("ienė", "ūtė"),
            "is": ("ienė", "ytė"),
            "as": ("ienė", "aitė"),
            "ys": ("ienė", "ytė"),
        }

        # Latvian surname suffixes
        self.lv_surname_suffixes = {
            "iņš",
            "iņa",  # masculine, feminine
            "āns",
            "āne",
            "bergs",
            "berga",
            "sons",
            "sone",
        }

        # Academic titles
        self.titles = {
            "prof",
            "prof.",
            "profesorius",
            "profesore",
            "dr",
            "dr.",
            "daktaras",
            "daktarė",
            "doc",
            "doc.",
            "docentas",
            "docentė",
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        super().clean(entry)

        # Security validation
        self.apply_security_and_validation_checks(entry)

        # Security: check for dangerous characters
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                value = entry[field]
                for char in value:
                    char_code = ord(char)
                    if char_code < 32:
                        if char_code == 9:
                            value = value.replace("\t", " ")
                            entry[field] = value
                            continue
                        elif char_code == 10:
                            value = value.replace("\n", " ")
                            entry[field] = value
                            continue
                        elif char_code == 13:
                            raise RegionRuleError(f"Carriage return in {field}")
                        else:
                            raise RegionRuleError(
                                f"Control character in {field}: U+{char_code:04X}"
                            )
                    if char_code == 127:
                        raise RegionRuleError(f"DELETE character in {field}")
                    if char_code in [0x200B, 0x200C, 0x200D, 0xFEFF]:
                        raise RegionRuleError(
                            f"Zero-width character in {field}: U+{char_code:04X}"
                        )

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
        if not name:
            return name
        name = self._remove_titles(name)
        name = re.sub(r"\s*,\s*", ", ", name)
        name = re.sub(r"\s*-\s*", "-", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip()

    def _remove_titles(self, text: str) -> str:
        if not text:
            return text
        words = text.split()
        cleaned = [w for w in words if w.lower().rstrip(".,") not in self.titles]
        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        super().augment(entry)

        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        components = self._extract_components(canonical)

        # Detect Baltic language
        lang = self._detect_baltic_language(entry)
        if lang:
            components["baltic_language"] = lang

        # Detect gender from surname suffix
        gender = self._detect_gender(canonical)
        if gender:
            components["gender"] = gender

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # ASCII variants
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical:
            entry["Variants"]["Synthesised"].append(
                {"str": ascii_variant, "type": "baltic-to-ascii"}
            )

    def _detect_baltic_language(self, entry: Dict[str, Any]) -> Optional[str]:
        text = entry.get("CanonicalLatin", "") + entry.get("CanonicalNative", "")
        if any(c in text for c in self.lithuanian_chars - self.latvian_chars):
            return "Lithuanian"
        if any(c in text for c in self.latvian_chars - self.lithuanian_chars):
            return "Latvian"
        # Check suffixes
        name_lower = text.lower()
        if any(name_lower.endswith(s) for s in ["auskas", "aitis", "ūnas", "ėnas"]):
            return "Lithuanian"
        if any(name_lower.endswith(s) for s in ["iņš", "iņa", "āns", "āne"]):
            return "Latvian"
        return None

    def _detect_gender(self, name: str) -> Optional[str]:
        name_lower = name.lower()
        family = self._extract_family_name(name)
        if not family:
            return None
        family_lower = family.lower()

        # Lithuanian feminine markers
        if any(
            family_lower.endswith(s)
            for s in [
                "ienė",
                "aitė",
                "ytė",
                "ūtė",
                "utė",
                "auskienė",
                "auskaitė",
                "aitienė",
                "aitytė",
            ]
        ):
            return "female"

        # Lithuanian masculine markers
        if any(
            family_lower.endswith(s)
            for s in [
                "auskas",
                "aitis",
                "ūnas",
                "ėnas",
                "onis",
                "utis",
            ]
        ):
            return "male"

        # Latvian feminine
        if any(family_lower.endswith(s) for s in ["iņa", "āne", "berga", "sone"]):
            return "female"

        # Latvian masculine
        if any(family_lower.endswith(s) for s in ["iņš", "āns", "bergs", "sons"]):
            return "male"

        return None

    def _generate_ascii_variant(self, name: str) -> str:
        translit = {
            "ą": "a",
            "č": "c",
            "ę": "e",
            "ė": "e",
            "į": "i",
            "š": "s",
            "ų": "u",
            "ū": "u",
            "ž": "z",
            "Ą": "A",
            "Č": "C",
            "Ę": "E",
            "Ė": "E",
            "Į": "I",
            "Š": "S",
            "Ų": "U",
            "Ū": "U",
            "Ž": "Z",
            "ā": "a",
            "ē": "e",
            "ģ": "g",
            "ī": "i",
            "ķ": "k",
            "ļ": "l",
            "ņ": "n",
            "Ā": "A",
            "Ē": "E",
            "Ģ": "G",
            "Ī": "I",
            "Ķ": "K",
            "Ļ": "L",
            "Ņ": "N",
        }
        result = name
        for src, dst in translit.items():
            result = result.replace(src, dst)
        return result

    def validate(self, entry: Dict[str, Any]) -> None:
        canonical = self.get_canonical_name(entry)
        if not canonical:
            if not self.has_sufficient_name_data(entry):
                raise RegionRuleError("Entry must have at least one name field")
            return

        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()

        if not canonical_latin and canonical_native:
            entry["CanonicalLatin"] = canonical_native
            canonical_latin = canonical_native

        name_to_validate = canonical_latin or canonical_native
        if len(name_to_validate) < 1:
            raise RegionRuleError("Name cannot be empty")

        if not self._has_valid_unicode_categories(name_to_validate):
            raise RegionRuleError(
                f"Name contains invalid characters: {name_to_validate}"
            )

    def _has_valid_unicode_categories(self, text: str) -> bool:
        valid_categories = {
            "Lu",
            "Ll",
            "Lt",
            "Lm",
            "Lo",
            "Nd",
            "Nl",
            "No",
            "Zs",
            "Zl",
            "Zp",
            "Pc",
            "Pd",
            "Pe",
            "Pf",
            "Pi",
            "Po",
            "Ps",
            "Mn",
            "Mc",
            "Me",
        }
        return all(unicodedata.category(char) in valid_categories for char in text)

    def order_key(self, entry: Dict[str, Any]) -> str:
        canonical = entry.get("CanonicalLatin", "")
        family = self._extract_family_name(canonical) or canonical
        family_normalized = unicodedata.normalize("NFD", family.lower())
        family_clean = "".join(
            char for char in family_normalized if unicodedata.category(char) != "Mn"
        )
        return family_clean

    def _extract_family_name(self, name: str) -> Optional[str]:
        if ", " in name:
            return name.split(", ")[0]
        parts = name.split()
        if parts:
            return parts[-1]
        return None

    def _extract_components(self, name: str) -> Dict[str, Any]:
        components = {}
        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = name.split()
            if len(parts) >= 2:
                components["family_name"] = parts[-1]
                components["given_name"] = " ".join(parts[:-1])
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""
        return components
