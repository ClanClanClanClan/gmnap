"""
Caucasus-Turkic (C9) regional processor.

Implements Azerbaijani and other Caucasus Turkic minority naming patterns.
Features: Azerbaijani Latin/Cyrillic scripts, patronymics (-oğlu/-qızı),
Soviet-era Russian influences, and Turkic naming elements.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional
from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class C9_CaucasusTurkic(RegionSpec):
    """Handler for C9 - Caucasus-Turkic (Azerbaijan and minorities)."""

    def __init__(self):
        super().__init__(
            code="C9",
            yaml_files=["c9_caucasus_turkic.yaml"],
            scripts=["Latin", "Cyrillic", "Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 9", "BGN/PCGN"],
        )

        # Azerbaijani Latin special characters
        self.azeri_latin_chars = {
            "ə",
            "ğ",
            "ı",
            "ö",
            "ş",
            "ü",
            "ç",  # lowercase
            "Ə",
            "Ğ",
            "İ",
            "Ö",
            "Ş",
            "Ü",
            "Ç",  # uppercase
        }

        # Cyrillic range (for Soviet-era names)
        self.cyrillic_range = (0x0400, 0x04FF)

        # Common Azerbaijani surnames
        self.azerbaijani_surnames = {
            # -ov/-ova endings (Soviet influence)
            "aliyev",
            "aliyeva",
            "hasanov",
            "hasanova",
            "mammadov",
            "mammadova",
            "huseynov",
            "huseynova",
            "ahmadov",
            "ahmadova",
            "ismayilov",
            "ismayilova",
            "babayev",
            "babayeva",
            "guliyev",
            "guliyeva",
            "hajiyev",
            "hajiyeva",
            "karimov",
            "karimova",
            "mustafayev",
            "mustafayeva",
            "suleymanov",
            "suleymanova",
            # -li/-lu endings (place-based)
            "bakili",
            "ganjali",
            "nakhchivanli",
            "shamakhili",
            "lankarli",
            "qubali",
            "shekili",
            "agdamli",
            "fuzuli",
            "jabrailili",
            # -zadə endings (Persian influence)
            "mehdizadə",
            "rzazadə",
            "əlizadə",
            "həsənzadə",
            "hüseynzadə",
            "məmmədzadə",
            "əhmədəzadə",
            "quluzadə",
            "mirzəzadə",
            "şahzadə",
            # Pure Turkic surnames
            "oğuz",
            "türk",
            "qarabağ",
            "şirvan",
            "xəzər",
            "talış",
            "arslan",
            "aslan",
            "qartal",
            "şahin",
            "turan",
            "altay",
        }

        # Patronymic patterns
        self.patronymic_suffixes = {
            "oğlu": {"meaning": "son of", "gender": "male"},
            "qızı": {"meaning": "daughter of", "gender": "female"},
        }

        # Common Azerbaijani given names
        self.azerbaijani_given_names = {
            # Male names
            "murad",
            "eldar",
            "farid",
            "fuad",
            "tofiq",
            "rafiq",
            "arif",
            "əli",
            "həsən",
            "hüseyn",
            "məmməd",
            "əhməd",
            "rəşid",
            "kamil",
            "ilham",
            "heydər",
            "vahid",
            "namiq",
            "elçin",
            "anar",
            "ramiz",
            "rovshan",
            "ruslan",
            "zaur",
            "elnur",
            "vüsal",
            "tural",
            "nicat",
            # Female names
            "leyla",
            "aynur",
            "günel",
            "nigar",
            "səadət",
            "fəridə",
            "kəmalə",
            "zəhra",
            "fatimə",
            "aysel",
            "aygün",
            "günay",
            "sevil",
            "lamiyə",
            "nərgiz",
            "gülnar",
            "səbinə",
            "aytən",
            "ülviyyə",
            "könül",
            "arzu",
        }

        # Soviet-era Russian given names (common in older generation)
        self.russian_names = {
            "vladimir",
            "nikolay",
            "sergey",
            "aleksandr",
            "mikhail",
            "ivan",
            "natalya",
            "yelena",
            "olga",
            "tatyana",
            "irina",
            "marina",
        }

        # Academic titles
        self.titles = {
            # Azerbaijani
            "prof",
            "prof.",
            "professor",
            "dos",
            "dos.",
            "dosent",
            "dr",
            "dr.",
            "doktor",
            "müəllim",
            "akademik",
            # Russian/Soviet
            "академик",
            "профессор",
            "доцент",
            "доктор",
            # Standard
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "miss",
            "ms",
            "ms.",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to C9 rules."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check for dangerous characters BEFORE normalization
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                value = entry[field]
                for char in value:
                    char_code = ord(char)
                    # Block ALL control characters including tab, LF, CR
                    if char_code < 32:
                        if char_code == 9:
                            # Normalize tab to space (V7 edge case)
                            value = value.replace("\t", " ")
                            entry[field] = value
                            continue  # Skip to next char
                        elif char_code == 10:
                            # Normalize newline to space (V7 edge case)
                            value = value.replace("\n", " ")
                            entry[field] = value
                            continue  # Skip to next char
                        elif char_code == 13:
                            raise RegionRuleError(f"Carriage return in {field}")
                        else:
                            raise RegionRuleError(
                                f"Control character in {field}: U+{char_code:04X}"
                            )
                    if char_code == 127:  # DEL
                        raise RegionRuleError(f"DELETE character in {field}")
                    if char_code in [0x200B, 0x200C, 0x200D, 0xFEFF]:  # Zero-width
                        raise RegionRuleError(f"Zero-width character in {field}: U+{char_code:04X}")

        # Security validation first

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
        """Clean a single Azerbaijani name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize Azerbaijani characters
        name = self._normalize_azeri_chars(name)

        # Handle patronymics
        name = self._normalize_patronymics(name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)
        name = re.sub(r"\s*-\s*", "-", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Azerbaijani academic titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            word_lower = word.lower().rstrip(".,")
            if word_lower not in self.titles and word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def _normalize_azeri_chars(self, name: str) -> str:
        """Normalize Azerbaijani special characters."""
        # Common substitutions when Azeri chars unavailable
        substitutions = {
            "ə": "e",
            "Ə": "E",
            "ğ": "g",
            "Ğ": "G",
            "ı": "i",
            "İ": "I",
            "ö": "o",
            "Ö": "O",
            "ş": "s",
            "Ş": "S",
            "ü": "u",
            "Ü": "U",
            "ç": "c",
            "Ç": "C",
        }

        # Only normalize if no Azeri chars present (suggesting ASCII-only context)
        if not any(c in name for c in self.azeri_latin_chars):
            # Check if there are substitute patterns
            for azeri_char, latin_char in substitutions.items():
                if latin_char in name:
                    # Don't substitute - name might already be in plain Latin
                    pass

        return name

    def _normalize_patronymics(self, name: str) -> str:
        """Normalize patronymic patterns."""
        # oğlu/qızı should be lowercase and attached with space
        name = re.sub(r"\b([A-ZƏĞİÖŞÜÇa-zəğıöşüç]+)\s*[Oo]ğlu\b", r"\1 oğlu", name)
        name = re.sub(r"\b([A-ZƏĞİÖŞÜÇa-zəğıöşüç]+)\s*[Qq]ızı\b", r"\1 qızı", name)

        # Also handle transliterated versions
        name = re.sub(r"\b([A-Za-z]+)\s*[Oo]glu\b", r"\1 oglu", name)
        name = re.sub(r"\b([A-Za-z]+)\s*[Gg]izi\b", r"\1 gizi", name)
        name = re.sub(r"\b([A-Za-z]+)\s*[Kq]izi\b", r"\1 qizi", name)

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with C9-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect scripts
        script_info = self._detect_scripts(entry)
        if script_info:
            components.update(script_info)

        # Detect Azerbaijani elements
        azeri_features = self._detect_azerbaijani_features(canonical)
        if azeri_features:
            components.update(azeri_features)

        # Detect Soviet/Russian influence
        if self._has_soviet_influence(canonical):
            components["soviet_influence"] = True

        # Detect minority patterns
        minority = self._detect_minority_group(canonical)
        if minority:
            components["caucasus_minority"] = minority

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate patronymic variants
        patronymic_variants = self._generate_patronymic_variants(canonical, components)
        for variant in patronymic_variants:
            if variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": variant, "type": "patronymic-variant"}
                )

        # Generate transliteration variants
        if components.get("has_azeri_chars"):
            latin_variant = self._generate_ascii_variant(canonical)
            if latin_variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": latin_variant, "type": "azeri-to-ascii"}
                )

    def _detect_scripts(self, entry: Dict[str, Any]) -> Dict[str, bool]:
        """Detect which scripts are used in the entry."""
        script_info = {}

        # Check CanonicalNative for Cyrillic/Arabic
        native = entry.get("CanonicalNative", "")
        if native:
            has_cyrillic = any(
                ord(c) in range(self.cyrillic_range[0], self.cyrillic_range[1] + 1) for c in native
            )
            has_arabic = any("\u0600" <= c <= "\u06FF" for c in native)

            if has_cyrillic:
                script_info["cyrillic_script_detected"] = True
            if has_arabic:
                script_info["arabic_script_detected"] = True

        # Check for Azerbaijani Latin chars
        canonical = entry.get("CanonicalLatin", "")
        if any(c in canonical for c in self.azeri_latin_chars):
            script_info["has_azeri_chars"] = True

        return script_info

    def _detect_azerbaijani_features(self, name: str) -> Dict[str, Any]:
        """Detect Azerbaijani-specific features."""
        features = {}
        name_lower = name.lower()

        # Check for patronymics
        if " oğlu" in name_lower or " oglu" in name_lower:
            features["has_patronymic"] = True
            features["patronymic_type"] = "oğlu"
            features["gender"] = "male"
        elif " qızı" in name_lower or " qizi" in name_lower or " gizi" in name_lower:
            features["has_patronymic"] = True
            features["patronymic_type"] = "qızı"
            features["gender"] = "female"

        # Check for place-based surnames
        if any(name_lower.endswith(suffix) for suffix in ["li", "lu", "lı", "lü"]):
            features["place_based_surname"] = True

        # Check for Persian-influenced -zadə ending
        if (
            name_lower.endswith("zadə")
            or name_lower.endswith("zade")
            or name_lower.endswith("zadeh")
        ):
            features["persian_influence"] = True

        # Check surname patterns
        family_name = self._extract_family_name(name)
        if family_name:
            family_lower = family_name.lower()

            # Soviet-style endings
            if family_lower.endswith("ov") or family_lower.endswith("ova"):
                features["soviet_style_surname"] = True
                if family_lower.endswith("ova"):
                    features["gender"] = "female"
            elif family_lower.endswith("yev") or family_lower.endswith("yeva"):
                features["soviet_style_surname"] = True
                if family_lower.endswith("yeva"):
                    features["gender"] = "female"

        return features

    def _has_soviet_influence(self, name: str) -> bool:
        """Check for Soviet/Russian influence in naming."""
        name_lower = name.lower()

        # Soviet-style surnames
        if any(
            name_lower.endswith(suffix) for suffix in ["ov", "ova", "yev", "yeva", "ski", "skaya"]
        ):
            return True

        # Russian given names
        given_parts = name_lower.split()[:-1] if name_lower else []
        for part in given_parts:
            if part in self.russian_names:
                return True

        return False

    def _detect_minority_group(self, name: str) -> Optional[str]:
        """Detect if name belongs to a specific Caucasus minority."""
        name_lower = name.lower()

        # Talysh indicators
        if any(indicator in name_lower for indicator in ["talış", "talysh", "tolış"]):
            return "talysh"

        # Lezgin indicators
        if any(indicator in name_lower for indicator in ["lezgi", "lezgin", "ləzgi"]):
            return "lezgin"

        # Kurdish indicators
        if any(indicator in name_lower for indicator in ["kürd", "kurd"]):
            return "kurdish"

        # Tat indicators
        if name_lower.endswith("tatlı") or " tat " in name_lower:
            return "tat"

        return None

    def _generate_patronymic_variants(self, name: str, components: Dict[str, Any]) -> List[str]:
        """Generate patronymic spelling variants."""
        variants = []

        if not components.get("has_patronymic"):
            return variants

        # oğlu variants
        if " oğlu" in name:
            variants.append(name.replace(" oğlu", " oglu"))
            variants.append(name.replace(" oğlu", "-oğlu"))
            variants.append(name.replace(" oğlu", " Oğlu"))
        elif " oglu" in name:
            variants.append(name.replace(" oglu", " oğlu"))
            variants.append(name.replace(" oglu", "-oglu"))

        # qızı variants
        if " qızı" in name:
            variants.append(name.replace(" qızı", " qizi"))
            variants.append(name.replace(" qızı", " gizi"))
            variants.append(name.replace(" qızı", "-qızı"))
            variants.append(name.replace(" qızı", " Qızı"))
        elif " qizi" in name:
            variants.append(name.replace(" qizi", " qızı"))
            variants.append(name.replace(" qizi", " gizi"))
        elif " gizi" in name:
            variants.append(name.replace(" gizi", " qızı"))
            variants.append(name.replace(" gizi", " qizi"))

        return list(set(variants))  # Remove duplicates

    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII-only variant of Azerbaijani name."""
        # Transliteration mapping
        translit_map = {
            "ə": "e",
            "Ə": "E",
            "ğ": "g",
            "Ğ": "G",
            "ı": "i",
            "İ": "I",
            "ö": "o",
            "Ö": "O",
            "ş": "s",
            "Ş": "S",
            "ü": "u",
            "Ü": "U",
            "ç": "c",
            "Ç": "C",
        }

        result = name
        for azeri_char, ascii_char in translit_map.items():
            result = result.replace(azeri_char, ascii_char)

        return result

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to V7 standards."""
        # Use graceful degradation for missing canonical fields
        canonical = self.get_canonical_name(entry)
        if not canonical:
            if not self.has_sufficient_name_data(entry):
                raise RegionRuleError("Entry must have at least one name field")
            else:
                # Has sufficient data but no processable name - skip strict validation
                return

        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()

        # If only native provided, that's fine for non-Latin scripts
        if not canonical_latin and canonical_native:
            # For Latin-script regions, copy native to latin
            if self.scripts == ["Latin"]:
                entry["CanonicalLatin"] = canonical_native
                canonical_latin = canonical_native
            # For non-Latin scripts, native-only is valid
            else:
                return

        # Get the name to validate
        name_to_validate = canonical_latin if canonical_latin else canonical_native

        # Name must have minimum length
        if len(name_to_validate) < 1:
            raise RegionRuleError("Name cannot be empty")

        # Single character names are valid in some cultures (like "X" for Malcolm X)
        # but should be flagged in metadata
        if len(name_to_validate) == 1:
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}
            entry["RegionalExtras"]["is_single_char_name"] = True

        # Check for valid Unicode categories
        if not self._has_valid_unicode_categories(name_to_validate):
            raise RegionRuleError(f"Name contains invalid characters: {name_to_validate}")

    def _has_valid_unicode_categories(self, text: str) -> bool:
        """Check if text contains only valid Unicode categories."""
        valid_categories = {
            "Lu",
            "Ll",
            "Lt",
            "Lm",
            "Lo",  # Letters
            "Nd",
            "Nl",
            "No",  # Numbers
            "Zs",
            "Zl",
            "Zp",  # Separators
            "Pc",
            "Pd",
            "Pe",
            "Pf",
            "Pi",
            "Po",
            "Ps",  # Punctuation
            "Mn",
            "Mc",
            "Me",  # Marks
        }

        return all(unicodedata.category(char) in valid_categories for char in text)

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for C9 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Extract family name for sorting
        family = self._extract_family_name(canonical)

        if not family:
            # If no clear family name, use whole name
            family = canonical

        # Normalize for sorting
        family_normalized = unicodedata.normalize("NFD", family.lower())

        # Handle Azerbaijani special chars for sorting
        sort_map = {
            "ə": "e~",  # Sort after regular e
            "ğ": "g~",
            "ı": "i~",
            "ö": "o~",
            "ş": "s~",
            "ü": "u~",
            "ç": "c~",
        }

        for azeri_char, sort_char in sort_map.items():
            family_normalized = family_normalized.replace(azeri_char, sort_char)

        # Remove diacritics from other chars
        family_clean = "".join(
            char for char in family_normalized if unicodedata.category(char) != "Mn" or char == "~"
        )

        return family_clean

    def _extract_family_name(self, name: str) -> Optional[str]:
        """Extract family name from full name."""
        if ", " in name:
            return name.split(", ")[0]

        parts = name.split()

        # Skip patronymics when finding family name
        cleaned_parts = []
        skip_next = False

        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue

            part_lower = part.lower()
            if part_lower in ["oğlu", "oglu", "qızı", "qizi", "gizi"]:
                # Skip the patronymic and the preceding name
                if cleaned_parts:
                    cleaned_parts.pop()
                continue

            cleaned_parts.append(part)

        if cleaned_parts:
            return cleaned_parts[-1]

        return None

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Azerbaijani names."""
        components = {}

        if ", " in name:
            # Comma format: "Family, Given"
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated, considering patronymics
            parts = name.split()

            # Find patronymic if present
            patronymic_idx = -1
            for i, part in enumerate(parts):
                if part.lower() in ["oğlu", "oglu", "qızı", "qizi", "gizi"]:
                    patronymic_idx = i
                    break

            if patronymic_idx > 0:
                # Name has patronymic
                components["given_name"] = parts[0]
                if patronymic_idx > 1:
                    components["father_name"] = " ".join(parts[1:patronymic_idx])
                components["patronymic"] = parts[patronymic_idx]
                if patronymic_idx < len(parts) - 1:
                    components["family_name"] = " ".join(parts[patronymic_idx + 1 :])
            else:
                # Standard given + family
                if len(parts) >= 2:
                    components["family_name"] = parts[-1]
                    components["given_name"] = " ".join(parts[:-1])
                else:
                    components["family_name"] = name.strip()
                    components["given_name"] = ""

        return components
