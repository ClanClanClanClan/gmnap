"""
B1 - East-Slavic region implementation.

Covers: Russia, Ukraine, Belarus
Features: Cyrillic script, patronymic names, flexible order
"""

import re
from typing import Any, Dict, Optional

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class B1_EastSlavic(RegionSpec):
    """
    East-Slavic region (B1).

    Handles Russian, Ukrainian, and Belarusian names:
    - Cyrillic script support
    - Patronymic handling (Иванович, Петровна)
    - Flexible name order
    - Romanization support
    """

    def __init__(self):
        super().__init__(
            code="B1",
            yaml_files=["b1_east_slavic.yaml"],
            scripts=["Cyrillic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["BGN/PCGN", "GOST", "Scientific"],
        )

        # Common patronymic patterns
        self.patronymic_patterns = {
            # Russian/Ukrainian male patronymics
            r".*ович$": "masculine",
            r".*евич$": "masculine",
            r".*ич$": "masculine",
            # Russian/Ukrainian female patronymics
            r".*овна$": "feminine",
            r".*евна$": "feminine",
            r".*ична$": "feminine",
            # Belarusian variations
            r".*авіч$": "masculine",
            r".*оўна$": "feminine",
        }

        # Common titles to remove
        self.titles = {
            # Russian
            "академик",
            "профессор",
            "доктор",
            "кандидат",
            "господин",
            "госпожа",
            "товарищ",
            # Ukrainian
            "академік",
            "професор",
            "доктор",
            "кандидат",
            "пан",
            "пані",
            # Belarusian
            "акадэмік",
            "прафесар",
            "доктар",
            # English equivalents
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
        }

        # Cyrillic character ranges
        self.cyrillic_ranges = [
            (0x0400, 0x04FF),  # Cyrillic
            (0x0500, 0x052F),  # Cyrillic Supplement
            (0x2DE0, 0x2DFF),  # Cyrillic Extended-A
            (0xA640, 0xA69F),  # Cyrillic Extended-B
        ]

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to B1 rules."""
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
        """Clean a single name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize whitespace using base class method (handles tabs/newlines)
        name = self.normalize_whitespace_characters(name)

        # Normalize punctuation
        name = self._normalize_punctuation(name)

        return name

    def _remove_titles(self, text: str) -> str:
        """Remove titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            if clean_word.lower() not in [t.lower() for t in self.titles]:
                cleaned.append(word)

        return " ".join(cleaned)

    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # Normalize whitespace (including tabs/newlines) using base class method
        name = self.normalize_whitespace_characters(name)

        # Normalize dashes
        name = re.sub(r"[-—–]", "-", name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]$", "", name)

        return name.strip()

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with B1-specific data."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Check if already processed for idempotency
        entry_id = entry.get("GlobalID", "")
        process_key = f"{self.code}:{entry_id}:{canonical}"
        if process_key in self._processed_entries:
            return  # Already processed, skip to avoid duplicates

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Rule 24: Russian Transliteration – GOST 7.79-2000 (A) & BGN-PCGN 1947 variants
        if self._is_cyrillic(canonical):
            # Generate GOST 7.79-2000 (A) variant
            gost_romanized = self._romanize_gost(canonical)
            if gost_romanized != canonical:
                # Update CanonicalLatin to be GOST romanized
                entry["CanonicalLatin"] = gost_romanized
                # Use add_variant for idempotency
                if hasattr(self, "add_variant"):
                    self.add_variant(
                        entry, {"str": gost_romanized, "type": "gost-romanization"}
                    )
                else:
                    entry["Variants"]["Synthesised"].append(
                        {"str": gost_romanized, "type": "gost-romanization"}
                    )

            # Generate BGN-PCGN 1947 variant
            bgn_romanized = self._romanize_bgn_pcgn(canonical)
            if bgn_romanized != canonical and bgn_romanized != gost_romanized:
                # Use add_variant for idempotency
                if hasattr(self, "add_variant"):
                    self.add_variant(
                        entry, {"str": bgn_romanized, "type": "bgn-pcgn-romanization"}
                    )
                else:
                    entry["Variants"]["Synthesised"].append(
                        {"str": bgn_romanized, "type": "bgn-pcgn-romanization"}
                    )

        # Rule 9: East-Slavic Patronymic – strip middle token; gender inference
        if components.get("patronymic"):
            # Generate variant without patronymic (stripped middle token)
            without_patronymic = self._generate_no_patronymic_variant(
                canonical, components
            )
            if without_patronymic and without_patronymic != canonical:
                # Use add_variant for idempotency
                if hasattr(self, "add_variant"):
                    self.add_variant(
                        entry, {"str": without_patronymic, "type": "no-patronymic"}
                    )
                else:
                    entry["Variants"]["Synthesised"].append(
                        {"str": without_patronymic, "type": "no-patronymic"}
                    )

            # Store gender at top level for V7 compliance
            if components.get("gender"):
                entry["Gender"] = components["gender"]
                # Also store whether gender was inferred from patronymic
                entry["GenderProvided"] = False  # Since it's inferred, not provided

                # Rule 26: Apply gender heuristic guard for safety
                self.apply_gender_heuristic_guard(entry)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        # Split into words
        words = name.split()

        # Try to identify patronymic
        patronymic_idx = None
        for i, word in enumerate(words):
            if self._is_patronymic(word):
                patronymic_idx = i
                components["patronymic"] = word
                break

        # Extract given and family names
        if patronymic_idx is not None:
            # Pattern: Given Patronymic Family
            if patronymic_idx == 1 and len(words) >= 3:
                components["given_name"] = words[0]
                components["family_name"] = " ".join(words[2:])
            elif patronymic_idx == 2 and len(words) >= 3:
                components["given_name"] = " ".join(words[:2])
                components["family_name"] = " ".join(words[3:])
            else:
                # Fallback - assume last word is family name
                components["given_name"] = " ".join(words[:patronymic_idx])
                components["family_name"] = " ".join(words[patronymic_idx + 1 :])
        else:
            # No patronymic found - assume Given Family format
            if len(words) >= 2:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
            else:
                components["family_name"] = name

        # Rule 9: Gender inference from patronymic
        if components.get("patronymic"):
            for pattern, gender in self.patronymic_patterns.items():
                if re.match(pattern, components["patronymic"]):
                    components["gender"] = gender
                    components["gender_source"] = "patronymic-inference"
                    break

        return components

    def _is_patronymic(self, word: str) -> bool:
        """Check if word is a patronymic."""
        for pattern in self.patronymic_patterns.keys():
            if re.match(pattern, word):
                return True
        return False

    def _is_cyrillic(self, text: str) -> bool:
        """Check if text is primarily Cyrillic characters."""
        cyrillic_count = 0
        letter_count = 0

        for char in text:
            if char.isalpha():
                letter_count += 1
                for start, end in self.cyrillic_ranges:
                    if start <= ord(char) <= end:
                        cyrillic_count += 1
                        break

        if letter_count == 0:
            return False

        # Consider it Cyrillic if more than 70% of letters are Cyrillic
        return cyrillic_count / letter_count > 0.7

    def _has_cyrillic(self, text: str) -> bool:
        """Check if text contains any Cyrillic characters."""
        for char in text:
            for start, end in self.cyrillic_ranges:
                if start <= ord(char) <= end:
                    return True
        return False

    def _romanize_name(self, name: str) -> str:
        """Romanize Cyrillic name using BGN/PCGN standard."""
        # Simple romanization mapping (BGN/PCGN for Russian)
        romanization_map = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "kh",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "shch",
            "ъ": "",
            "ы": "y",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            # Uppercase
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "Zh",
            "З": "Z",
            "И": "I",
            "Й": "Y",
            "К": "K",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ф": "F",
            "Х": "Kh",
            "Ц": "Ts",
            "Ч": "Ch",
            "Ш": "Sh",
            "Щ": "Shch",
            "Ъ": "",
            "Ы": "Y",
            "Ь": "",
            "Э": "E",
            "Ю": "Yu",
            "Я": "Ya",
            # Ukrainian specific
            "і": "i",
            "ї": "yi",
            "є": "ye",
            "ґ": "g",
            "І": "I",
            "Ї": "Yi",
            "Є": "Ye",
            "Ґ": "G",
            # Belarusian specific
            "ў": "u",
            "Ў": "U",
        }

        result = []
        for char in name:
            if char in romanization_map:
                result.append(romanization_map[char])
            else:
                result.append(char)

        return "".join(result)

    def _romanize_gost(self, name: str) -> str:
        """
        Rule 24: Romanize Cyrillic name using GOST 7.79-2000 (A) standard.

        GOST 7.79-2000 System A is the official Russian transliteration standard
        for bibliographic purposes and scientific literature.
        """
        # GOST 7.79-2000 System A mapping
        gost_map = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "j",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "x",
            "ц": "c",
            "ч": "ch",
            "ш": "sh",
            "щ": "shh",
            "ъ": "``",
            "ы": "y`",
            "ь": "`",
            "э": "e`",
            "ю": "yu",
            "я": "ya",
            # Uppercase
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "Zh",
            "З": "Z",
            "И": "I",
            "Й": "J",
            "К": "K",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ф": "F",
            "Х": "X",
            "Ц": "C",
            "Ч": "Ch",
            "Ш": "Sh",
            "Щ": "Shh",
            "Ъ": "``",
            "Ы": "Y`",
            "Ь": "`",
            "Э": "E`",
            "Ю": "Yu",
            "Я": "Ya",
            # Ukrainian specific
            "і": "i",
            "ї": "yi",
            "є": "ye",
            "ґ": "g`",
            "І": "I",
            "Ї": "Yi",
            "Є": "Ye",
            "Ґ": "G`",
            # Belarusian specific
            "ў": "w",
            "Ў": "W",
        }

        result = []
        for char in name:
            if char in gost_map:
                result.append(gost_map[char])
            else:
                result.append(char)

        return "".join(result)

    def _romanize_bgn_pcgn(self, name: str) -> str:
        """
        Rule 24: Romanize Cyrillic name using BGN-PCGN 1947 standard.

        BGN-PCGN (Board on Geographic Names/Permanent Committee on Geographical Names)
        is the standard used by US and UK geographic agencies.
        """
        # BGN-PCGN 1947 mapping (more readable than GOST)
        bgn_map = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "kh",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "shch",
            "ъ": "",
            "ы": "y",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            # Uppercase
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "Zh",
            "З": "Z",
            "И": "I",
            "Й": "Y",
            "К": "K",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ф": "F",
            "Х": "Kh",
            "Ц": "Ts",
            "Ч": "Ch",
            "Ш": "Sh",
            "Щ": "Shch",
            "Ъ": "",
            "Ы": "Y",
            "Ь": "",
            "Э": "E",
            "Ю": "Yu",
            "Я": "Ya",
            # Ukrainian specific
            "і": "i",
            "ї": "yi",
            "є": "ye",
            "ґ": "g",
            "І": "I",
            "Ї": "Yi",
            "Є": "Ye",
            "Ґ": "G",
            # Belarusian specific
            "ў": "u",
            "Ў": "U",
        }

        result = []
        for char in name:
            if char in bgn_map:
                result.append(bgn_map[char])
            else:
                result.append(char)

        return "".join(result)

    def _generate_no_patronymic_variant(
        self, name: str, components: Dict[str, Any]
    ) -> Optional[str]:
        """
        Rule 9: Generate variant without patronymic (strip middle token).

        East-Slavic names typically follow: Given + Patronymic + Family
        This method removes the patronymic to create: Given + Family
        """
        given = components.get("given_name", "")
        family = components.get("family_name", "")

        if given and family:
            # For romanized forms, ensure proper spacing
            if self._is_cyrillic(name):
                return f"{given} {family}"
            else:
                # For romanized, capitalize appropriately
                return f"{given} {family}".title()

        return None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to B1 rules with graceful degradation."""
        # Use graceful degradation for missing canonical fields
        canonical = self.get_canonical_name(entry)
        if not canonical:
            if not self.has_sufficient_name_data(entry):
                raise RegionRuleError("Missing CanonicalLatin or CanonicalNative")
            else:
                # Has sufficient data but no processable name - skip strict validation
                return

        # Apply comprehensive security and validation checks from base class
        # This properly normalizes whitespace BEFORE checking for control chars
        self.apply_security_and_validation_checks(entry)

        # B1-specific validation: Cyrillic script checking
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        # If CanonicalNative exists, prefer it to be Cyrillic (but be very lenient)
        if canonical_native and len(canonical_native.strip()) > 0:
            if not self._is_cyrillic(canonical_native) and not self._has_cyrillic(
                canonical_native
            ):
                # Only warn for non-Cyrillic native names in B1 region
                # Don't fail completely - allow processing to continue
                self.logger.warning(
                    f"CanonicalNative in B1 region is not Cyrillic: {canonical_native}"
                )

        # If CanonicalLatin exists, it should be mostly romanized (allow some Cyrillic in mixed names)
        if canonical_latin and len(canonical_latin.strip()) > 0:
            if self._is_cyrillic(canonical_latin):
                raise RegionRuleError(
                    f"CanonicalLatin should be romanized: {canonical_latin}"
                )

    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters (permissive for international names)."""
        import unicodedata

        for char in name:
            category = unicodedata.category(char)
            # Allow all letters (L*), marks (M*), and spaces (Z*)
            if category.startswith(("L", "M", "Z")):
                continue
            # Allow common punctuation: spaces, hyphens, apostrophes, periods, commas
            if char in " -'.,":
                continue
            # Allow numbers in some contexts
            if category == "Nd":
                continue
            # Check if it's valid Cyrillic (for backward compatibility)
            if any(start <= ord(char) <= end for start, end in self.cyrillic_ranges):
                continue
            # Reject control characters and unusual categories
            return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Rule 9: Use only given and family names (patronymic stripped) for sorting
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # If we have the components, use them directly (patronymic already excluded)
        if family and given:
            # Romanize if Cyrillic
            if self._is_cyrillic(family):
                family = self._romanize_name(family)
            if self._is_cyrillic(given):
                given = self._romanize_name(given)
        else:
            # Fallback to canonical form
            canonical = entry.get("CanonicalLatin", "") or entry.get(
                "CanonicalNative", ""
            )

            # If we have Cyrillic, romanize for sorting
            if self._is_cyrillic(canonical):
                canonical = self._romanize_name(canonical)

            # Try to extract from canonical (without patronymic)
            no_patronymic = self._generate_no_patronymic_variant(canonical, components)
            if no_patronymic:
                parts = no_patronymic.split()
                if len(parts) >= 2:
                    given = " ".join(parts[:-1])
                    family = parts[-1]

        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        # Generate key
        key = f"{sort_family} {sort_given}"

        # Ensure determinism
        key = " ".join(key.split())

        return key

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        if not name:
            return False
        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False
