"""
C3 - Arabic Levant-Nile region implementation.

Covers: Iraq, Jordan, Lebanon, Syria, Palestine, Egypt, Sudan, South Sudan
Features: Arabic script, patronymic (ibn/bint), flexible order
"""

import re
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C3_ArabicLevantNile(RegionSpec):
    """
    Arabic Levant-Nile region (C3).

    Handles Arabic names from Levant and Nile regions:
    - Arabic script support
    - Patronymic handling (ibn, bint, abu, um)
    - Flexible name order
    - Romanization support
    """

    def __init__(self):
        super().__init__(
            code="C3",
            yaml_files=["c3_arabic_levant_nile.yaml"],
            scripts=["Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "DIN", "ISO"],
        )

        # Common patronymic/matrionymic patterns
        self.patronymic_patterns = {
            # Arabic patronymics
            "ibn": "son of",
            "ابن": "son of",
            "bin": "son of",
            "بن": "son of",
            "bint": "daughter of",
            "بنت": "daughter of",
            "abu": "father of",
            "أبو": "father of",
            "um": "mother of",
            "أم": "mother of",
            "umm": "mother of",
            # Regional variations
            "ould": "son of",  # Mauritanian
            "mint": "daughter of",  # Mauritanian
        }

        # Common titles to remove
        self.titles = {
            # Arabic titles
            "دكتور",
            "أستاذ",
            "بروفيسور",
            "مهندس",
            "محامي",
            "طبيب",
            "الشيخ",
            "الأستاذ",
            "الدكتور",
            "المهندس",
            "القاضي",
            "سيد",
            "سيدة",
            "آنسة",
            "حضرة",
            "معالي",
            "سعادة",
            # English equivalents
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Professor",
            "Engineer",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Sheikh",
            "His Excellency",
            "Her Excellency",
        }

        # Arabic character ranges
        self.arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]

        # Common Arabic name elements
        self.common_elements = {
            "عبد": "Abd",  # Servant of (Allah)
            "محمد": "Muhammad",
            "أحمد": "Ahmad",
            "علي": "Ali",
            "حسن": "Hassan",
            "حسين": "Hussein",
            "عمر": "Omar",
            "خالد": "Khalid",
            "يوسف": "Yusuf",
            "إبراهيم": "Ibrahim",
            "صالح": "Saleh",
            "عثمان": "Othman",
            "طارق": "Tariq",
            "نبيل": "Nabil",
            "وليد": "Walid",
        }

        # Rule 2: Arabic al- Article – sun letters for assimilation
        # Sun letters: These letters cause assimilation of the 'l' in 'al-'
        self.sun_letters = {
            "ت",
            "ث",
            "د",
            "ذ",
            "ر",
            "ز",
            "س",
            "ش",
            "ص",
            "ض",
            "ط",
            "ظ",
            "ل",
            "ن",
        }

        # Moon letters: These letters do not cause assimilation
        self.moon_letters = {
            "ا",
            "ب",
            "ج",
            "ح",
            "خ",
            "ع",
            "غ",
            "ف",
            "ق",
            "ك",
            "م",
            "ه",
            "و",
            "ي",
        }

        # Definite article patterns
        self.definite_articles = {
            "ال": "al",  # Standard Arabic
            "الـ": "al",  # With tatweel
            "اَلْ": "al",  # With diacritics
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C3 rules."""
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

        # Normalize whitespace
        name = " ".join(name.split())

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
            if clean_word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # Remove extra spaces
        name = re.sub(r"\s+", " ", name)

        # Handle Arabic punctuation
        name = name.replace("،", ", ")
        name = name.replace("؛", "; ")
        name = name.replace("؟", "?")
        name = name.replace("؍", "/")

        # Normalize dashes
        name = re.sub(r"[-—–]", "-", name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]$", "", name)

        return name.strip()

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C3-specific data."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

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

        # Add romanized variant if original is Arabic
        if self._is_arabic(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
                # Update CanonicalLatin to be romanized
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append(
                    {"str": romanized, "type": "romanization"}
                )

        # Add variant without patronymic
        if components.get("patronymic"):
            without_patronymic = self._generate_no_patronymic_variant(
                canonical, components
            )
            if without_patronymic and without_patronymic != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": without_patronymic, "type": "no-patronymic"}
                )

        # Rule 2: Arabic al- Article normalization
        article_info = self._analyze_definite_article(canonical)
        if article_info:
            components["has_definite_article"] = True
            components["article_type"] = article_info["type"]
            components["root_form"] = article_info["root"]

            # Add variant with article removed
            without_article = article_info["root"]
            if without_article != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": without_article, "type": "no-article"}
                )

            # Add variant with proper sun letter assimilation if needed
            if (
                article_info.get("assimilated_form")
                and article_info["assimilated_form"] != canonical
            ):
                entry["Variants"]["Synthesised"].append(
                    {
                        "str": article_info["assimilated_form"],
                        "type": "sun-letter-assimilation",
                    }
                )

        # Rule 32: Ibn/Abu/Um Prefixes – dropped when next token length ≥ 3
        prefix_variants = self._generate_prefix_drop_variants(canonical)
        for variant in prefix_variants:
            if variant["str"] != canonical:
                entry["Variants"]["Synthesised"].append(variant)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        # Split into words
        words = name.split()

        # Look for patronymic indicators
        patronymic_info = self._find_patronymic(words)
        if patronymic_info:
            components.update(patronymic_info)
            # Store the is_bin_bint flag for Rule 3
            if patronymic_info.get("is_bin_bint"):
                components["is_bin_bint"] = True

        # Look for definite article (al-, el-, etc.)
        if self._has_definite_article(name):
            components["has_definite_article"] = True

        # Extract given and family names
        if patronymic_info and "patronymic_index" in patronymic_info:
            idx = patronymic_info["patronymic_index"]
            # Pattern: Given [Patronymic] Family
            if idx > 0:
                components["given_name"] = " ".join(words[:idx])
            if idx + 2 < len(words):
                components["family_name"] = " ".join(words[idx + 2 :])
        else:
            # No patronymic found - assume Given Family format
            if len(words) >= 2:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
            else:
                components["given_name"] = name

        return components

    def _find_patronymic(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """
        Rule 3: Find Arabic bin/bint patronymic indicators.

        These patronymics indicate lineage and should be:
        - Identified and stored in RegionalExtras
        - Removed from order_key for sorting
        """
        for i, word in enumerate(words):
            word_lower = word.lower()
            if (
                word_lower in self.patronymic_patterns
                or word in self.patronymic_patterns
            ):
                # Check if this is specifically bin/bint (Rule 3)
                is_bin_bint = word_lower in ["bin", "ibn", "bint", "بن", "ابن", "بنت"]

                return {
                    "patronymic": word,
                    "patronymic_index": i,
                    "patronymic_type": self.patronymic_patterns.get(
                        word_lower, self.patronymic_patterns.get(word, "unknown")
                    ),
                    "is_bin_bint": is_bin_bint,  # Flag for Rule 3
                }
        return None

    def _has_definite_article(self, name: str) -> bool:
        """Check if name contains definite article."""
        # Arabic definite article patterns
        articles = ["ال", "al-", "el-", "Al-", "El-"]
        for article in articles:
            if article in name:
                return True
        return False

    def _analyze_definite_article(self, name: str) -> Optional[Dict[str, str]]:
        """
        Rule 2: Analyze Arabic al- article with sun letter assimilation.

        Returns dict with:
        - type: 'sun' or 'moon' based on following letter
        - root: name with article removed
        - assimilated_form: proper form with sun letter assimilation
        """
        # Check for Arabic script first
        if self._is_arabic(name):
            # Look for Arabic definite article
            for article in self.definite_articles:
                if article in name:
                    article_idx = name.find(article)
                    if article_idx >= 0 and article_idx + len(article) < len(name):
                        following_letter = name[article_idx + len(article)]

                        # Determine if sun or moon letter
                        letter_type = (
                            "sun" if following_letter in self.sun_letters else "moon"
                        )

                        # Extract root (without article)
                        root = name[:article_idx] + name[article_idx + len(article) :]
                        root = " ".join(root.split())

                        # Generate assimilated form for sun letters
                        assimilated = name
                        if letter_type == "sun":
                            # In sun letter assimilation, the 'l' sound becomes the sun letter
                            # e.g., al-shams → ash-shams
                            pass  # Already handled in the original

                        return {
                            "type": letter_type,
                            "root": root,
                            "assimilated_form": assimilated,
                        }

        # Check for romanized forms
        romanized_patterns = [
            (r"\b[Aa]l-([A-Za-z])", r"\1"),  # al-Name → Name
            (r"\b[Ee]l-([A-Za-z])", r"\1"),  # el-Name → Name
            (r"\b[Aa]sh-([sStT])", r"\1"),  # ash-Shams → Shams (sun letter)
            (r"\b[Aa][tdrzsnl]-([tdrzsnlTDRZSNL])", r"\1"),  # sun letter assimilation
        ]

        for pattern, replacement in romanized_patterns:
            match = re.search(pattern, name)
            if match:
                # Extract root
                root = re.sub(pattern, replacement, name)
                root = " ".join(root.split())

                # Determine type based on pattern
                letter_type = (
                    "sun" if "sh-" in pattern or "[tdrzsnl]-" in pattern else "moon"
                )

                return {"type": letter_type, "root": root, "assimilated_form": name}

        return None

    def _generate_prefix_drop_variants(self, name: str) -> List[Dict[str, str]]:
        """
        Rule 32: Ibn/Abu/Um Prefixes – dropped when next token length ≥ 3.

        Arabic names often contain patronymic prefixes like Ibn, Abu, Um.
        These should be dropped from variants when the following name token
        is substantial (≥ 3 characters), as they're primarily genealogical markers.

        Examples:
        - "Ibn Rushd" → keep (next token < 3 chars)
        - "Ibn Muhammad" → drop "Ibn" (Muhammad ≥ 3 chars)
        - "Abu Bakr" → drop "Abu" (Bakr ≥ 3 chars)
        - "Um Kulthum" → drop "Um" (Kulthum ≥ 3 chars)
        """
        variants = []

        # Arabic and romanized prefixes to check
        prefixes_to_drop = {
            # Arabic script
            "ابن": "ibn",  # Ibn (son of)
            "أبو": "abu",  # Abu (father of)
            "أم": "um",  # Um (mother of)
            "بن": "bin",  # Bin (son of, short form)
            "بنت": "bint",  # Bint (daughter of)
            # Romanized forms
            "ibn": "ibn",
            "abu": "abu",
            "um": "um",
            "bin": "bin",
            "bint": "bint",
            # Case variations
            "Ibn": "ibn",
            "Abu": "abu",
            "Um": "um",
            "Bin": "bin",
            "Bint": "bint",
        }

        words = name.split()

        for i, word in enumerate(words):
            word_clean = word.rstrip(".,")

            if word_clean in prefixes_to_drop:
                # Check if there's a following token with length ≥ 3
                if i + 1 < len(words):
                    next_token = words[i + 1].rstrip(".,")
                    if len(next_token) >= 3:
                        # Generate variant without this prefix
                        variant_words = words[:i] + words[i + 1 :]
                        if variant_words:  # Ensure we don't create empty names
                            variant_name = " ".join(variant_words)
                            variants.append(
                                {"str": variant_name, "type": "prefix-drop"}
                            )

        return variants

    def _remove_definite_article(self, name: str) -> str:
        """Remove definite article from name (legacy method)."""
        article_info = self._analyze_definite_article(name)
        if article_info:
            return article_info["root"]
        return name

    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                return True
        return False

    def _romanize_name(self, name: str) -> str:
        """Romanize Arabic name using ALA-LC standard with common name mappings."""
        # First check for common full names
        common_names = {
            "محمد": "Muhammad",
            "أحمد": "Ahmad",
            "علي": "Ali",
            "حسن": "Hassan",
            "حسين": "Hussein",
            "عمر": "Omar",
            "خالد": "Khalid",
            "يوسف": "Yusuf",
            "إبراهيم": "Ibrahim",
            "صالح": "Saleh",
            "عثمان": "Othman",
            "طارق": "Tariq",
            "نبيل": "Nabil",
            "وليد": "Walid",
            "عبد": "Abd",
            "فاطمة": "Fatima",
            "عائشة": "Aisha",
            "زينب": "Zainab",
            "مريم": "Maryam",
            "خديجة": "Khadija",
        }

        # Split name into parts and check each against common names
        parts = name.split()
        romanized_parts = []

        for part in parts:
            if part in common_names:
                romanized_parts.append(common_names[part])
            else:
                # Fallback to character-by-character romanization
                romanization_map = {
                    "ا": "a",
                    "ب": "b",
                    "ت": "t",
                    "ث": "th",
                    "ج": "j",
                    "ح": "h",
                    "خ": "kh",
                    "د": "d",
                    "ذ": "dh",
                    "ر": "r",
                    "ز": "z",
                    "س": "s",
                    "ش": "sh",
                    "ص": "s",
                    "ض": "d",
                    "ط": "t",
                    "ظ": "z",
                    "ع": "'",
                    "غ": "gh",
                    "ف": "f",
                    "ق": "q",
                    "ك": "k",
                    "ل": "l",
                    "م": "m",
                    "ن": "n",
                    "ه": "h",
                    "و": "w",
                    "ي": "y",
                    "ى": "a",
                    "ة": "ah",
                    "ء": "'",
                    "أ": "a",
                    "إ": "i",
                    "آ": "aa",
                    "ؤ": "u",
                    "ئ": "i",
                    # Vowel marks
                    "َ": "a",
                    "ُ": "u",
                    "ِ": "i",
                    "ً": "an",
                    "ٌ": "un",
                    "ٍ": "in",
                    "ْ": "",
                    "ّ": "",
                    "ٰ": "a",
                    # Numbers
                    "٠": "0",
                    "١": "1",
                    "٢": "2",
                    "٣": "3",
                    "٤": "4",
                    "٥": "5",
                    "٦": "6",
                    "٧": "7",
                    "٨": "8",
                    "٩": "9",
                }

                result = []
                for i, char in enumerate(part):
                    if char in romanization_map:
                        mapped = romanization_map[char]
                        # Add vowels for better readability
                        if (
                            i > 0
                            and mapped
                            and result
                            and result[-1] in "bcdfghjklmnpqrstvwxyz"
                        ):
                            # Check if we need to add a vowel between consonants
                            if char in "محد" and i < len(part) - 1:
                                if part[i + 1] not in "اويىَُِ":
                                    # Add appropriate vowel based on position
                                    if char == "م":
                                        result.append("u")  # محمد -> Muhammad
                                    elif char == "ح":
                                        result.append("a")  # أحمد -> Ahmad
                                    elif char == "د" and i == len(part) - 1:
                                        pass  # No vowel at end
                                    else:
                                        result.append("a")  # Default vowel
                        result.append(mapped)
                    else:
                        result.append(char)

                romanized_part = "".join(result)
                # Clean up double consonants and format
                romanized_part = romanized_part.replace("mm", "m").replace("ll", "l")
                romanized_parts.append(romanized_part.capitalize())

        romanized = " ".join(romanized_parts)

        # Clean up multiple spaces
        romanized = " ".join(romanized.split())
        return romanized

    def _generate_no_patronymic_variant(
        self, name: str, components: Dict[str, Any]
    ) -> Optional[str]:
        """Generate variant without patronymic."""
        given = components.get("given_name", "")
        family = components.get("family_name", "")

        if given and family:
            return f"{given} {family}"
        elif given:
            return given

        return None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to C3 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")

        # If CanonicalNative exists, it should be Arabic
        if canonical_native:
            if not self._is_arabic(canonical_native):
                raise RegionRuleError(
                    f"CanonicalNative should be Arabic: {canonical_native}"
                )

        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_arabic(canonical_latin):
                raise RegionRuleError(
                    f"CanonicalLatin should be romanized: {canonical_latin}"
                )

        # Check name structure
        for canonical in [canonical_native, canonical_latin]:
            if canonical:
                words = canonical.split()
                if len(words) < 2:
                    raise RegionRuleError(
                        f"Name should have at least 2 words: {canonical}"
                    )

                # Check for invalid characters
                if not self._has_valid_characters(canonical):
                    raise RegionRuleError(f"Invalid characters in name: {canonical}")

    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters."""
        for char in name:
            # Allow Latin, Arabic, spaces, hyphens, apostrophes, commas
            if char.isalpha() or char in " -',":
                continue
            # Check if it's valid Arabic
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                continue
            # Invalid character found
            return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Rule 2: Use root form (without article) for sorting
        if components.get("root_form"):
            # Use the root form without the definite article
            canonical = components["root_form"]
        else:
            # Fallback to canonical form
            canonical = entry.get("CanonicalLatin", "") or entry.get(
                "CanonicalNative", ""
            )

        # Extract family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Rule 3: Remove bin/bint patronymic from order_key
        if components.get("patronymic") and components.get("is_bin_bint"):
            # Reconstruct name without the patronymic
            patronymic = components["patronymic"]

            # Remove patronymic from given or family name
            if given and patronymic in given:
                given = given.replace(patronymic, "").strip()
                # Also remove the following word (father's name)
                words = given.split()
                if len(words) > 0:
                    given = " ".join(words[1:]) if len(words) > 1 else ""

            # Clean up the canonical form too
            if canonical and patronymic in canonical:
                # Remove patronymic and following word
                words = canonical.split()
                new_words = []
                skip_next = False
                for word in words:
                    if skip_next:
                        skip_next = False
                        continue
                    if word == patronymic:
                        skip_next = True
                        continue
                    new_words.append(word)
                canonical = " ".join(new_words)

        # If we have Arabic, romanize for sorting
        if self._is_arabic(canonical):
            canonical = self._romanize_name(canonical)
            if family and self._is_arabic(family):
                family = self._romanize_name(family)
            if given and self._is_arabic(given):
                given = self._romanize_name(given)

        # Rule 2: Remove definite articles from family name for sorting
        if family:
            article_info = self._analyze_definite_article(family)
            if article_info:
                family = article_info["root"]

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
