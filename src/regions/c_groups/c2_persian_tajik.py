"""
C2 - Persian-Tajik region implementation.

Covers: Iran, Afghanistan, Tajikistan
Features: Persian/Dari/Tajik scripts, patronymic patterns, flexible order
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C2_PersianTajik(RegionSpec):
    """
    Persian-Tajik region (C2).

    Handles Persian, Dari, and Tajik names:
    - Persian script support (Arabic-derived)
    - Cyrillic script for Tajik
    - Patronymic patterns
    - Flexible name order
    """

    def __init__(self):
        super().__init__(
            code="C2",
            yaml_files=["c2_persian_tajik.yaml"],
            scripts=["Persian", "Cyrillic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "Scientific"],
        )

        # Common Persian/Tajik patronymic patterns
        self.patronymic_patterns = {
            # Persian/Dari
            "پسر": "son of",
            "دختر": "daughter of",
            "بن": "son of",
            "بنت": "daughter of",
            # Tajik (Cyrillic)
            "писар": "son of",
            "духтар": "daughter of",
        }

        # Common titles to remove
        self.titles = {
            # Persian/Dari titles
            "دکتر",
            "پروفسور",
            "استاد",
            "مهندس",
            "آقای",
            "خانم",
            "حاج",
            "حاجی",
            "میرزا",
            "خان",
            "بیگم",
            # Tajik titles
            "доктор",
            "профессор",
            "устод",
            "мухандис",
            "ҷаноб",
            "хонум",
            "хоҷа",
            "хон",
            "бегум",
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
        }

        # Persian character ranges
        self.persian_ranges = [
            (0x0600, 0x06FF),  # Arabic (used for Persian)
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]

        # Cyrillic character ranges (for Tajik)
        self.cyrillic_ranges = [
            (0x0400, 0x04FF),  # Cyrillic
            (0x0500, 0x052F),  # Cyrillic Supplement
        ]

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C2 rules."""
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

        # Handle Persian punctuation
        name = name.replace("،", ", ")
        name = name.replace("؛", "; ")
        name = name.replace("؟", "?")

        # Normalize dashes
        name = re.sub(r"[-—–]", "-", name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]$", "", name)

        return name.strip()

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C2-specific data."""
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

        # Add romanized variant if original is Persian/Tajik
        if self._is_persian_or_tajik(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
                entry["Variants"]["Synthesised"].append({"str": romanized, "type": "romanization"})

        # Rule 7: Persian Ezafe – identify and generate variants
        ezafe_info = self._analyze_persian_ezafe(canonical)
        if ezafe_info:
            components.update(ezafe_info)

            # Generate variants with different ezafe representations
            ezafe_variants = self._generate_ezafe_variants(canonical, ezafe_info)
            for variant in ezafe_variants:
                if variant["str"] != canonical:
                    entry["Variants"]["Synthesised"].append(variant)

        # Rule 21: -zadeh Suffix – Persian patronymic/descendant suffix
        zadeh_info = self._analyze_zadeh_suffix(canonical)
        if zadeh_info:
            components.update(zadeh_info)

            # Generate variants with different -zadeh representations
            zadeh_variants = self._generate_zadeh_variants(canonical, zadeh_info)
            for variant in zadeh_variants:
                if variant["str"] != canonical:
                    entry["Variants"]["Synthesised"].append(variant)

        # Add variant without patronymic
        if components.get("patronymic"):
            without_patronymic = self._generate_no_patronymic_variant(canonical, components)
            if without_patronymic and without_patronymic != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": without_patronymic, "type": "no-patronymic"}
                )

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        # Split into words
        words = name.split()

        # Look for patronymic indicators
        patronymic_idx = None
        for i, word in enumerate(words):
            if word in self.patronymic_patterns:
                patronymic_idx = i
                components["patronymic"] = word
                components["patronymic_type"] = self.patronymic_patterns[word]
                break

        # Extract given and family names
        if patronymic_idx is not None:
            # Pattern: Given [Patronymic] Family
            if patronymic_idx > 0:
                components["given_name"] = " ".join(words[:patronymic_idx])
            if patronymic_idx + 1 < len(words):
                components["family_name"] = " ".join(words[patronymic_idx + 1 :])
        else:
            # No patronymic found - assume Given Family format
            if len(words) >= 2:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
            else:
                components["given_name"] = name

        # Detect script
        if self._is_persian(name):
            components["script"] = "Persian"
        elif self._is_cyrillic(name):
            components["script"] = "Cyrillic"
        else:
            components["script"] = "Latin"

        return components

    def _is_persian_or_tajik(self, text: str) -> bool:
        """Check if text contains Persian or Tajik characters."""
        return self._is_persian(text) or self._is_cyrillic(text)

    def _is_persian(self, text: str) -> bool:
        """Check if text contains Persian characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.persian_ranges):
                return True
        return False

    def _is_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.cyrillic_ranges):
                return True
        return False

    def _romanize_name(self, name: str) -> str:
        """Romanize Persian/Tajik name."""
        if self._is_persian(name):
            return self._romanize_persian(name)
        elif self._is_cyrillic(name):
            return self._romanize_cyrillic(name)
        else:
            return name

    def _romanize_persian(self, name: str) -> str:
        """Romanize Persian text using ALA-LC standard."""
        # Simple Persian romanization mapping
        persian_map = {
            "ا": "a",
            "ب": "b",
            "پ": "p",
            "ت": "t",
            "ث": "th",
            "ج": "j",
            "چ": "ch",
            "ح": "h",
            "خ": "kh",
            "د": "d",
            "ذ": "dh",
            "ر": "r",
            "ز": "z",
            "ژ": "zh",
            "س": "s",
            "ش": "sh",
            "ص": "s",
            "ض": "z",
            "ط": "t",
            "ظ": "z",
            "ع": "",
            "غ": "gh",
            "ف": "f",
            "ق": "q",
            "ک": "k",
            "گ": "g",
            "ل": "l",
            "م": "m",
            "ن": "n",
            "و": "v",
            "ه": "h",
            "ی": "y",
            "ء": "",
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
        }

        result = []
        for char in name:
            if char in persian_map:
                result.append(persian_map[char])
            else:
                result.append(char)

        romanized = "".join(result)
        romanized = " ".join(romanized.split())
        return romanized.title()

    def _romanize_cyrillic(self, name: str) -> str:
        """Romanize Tajik Cyrillic text."""
        # Simple Tajik romanization mapping
        tajik_map = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "ғ": "gh",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "ӣ": "i",
            "й": "y",
            "к": "k",
            "қ": "q",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ӯ": "u",
            "ф": "f",
            "х": "kh",
            "ҳ": "h",
            "ч": "ch",
            "ҷ": "j",
            "ш": "sh",
            "ъ": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            # Uppercase
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Ғ": "Gh",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "Zh",
            "З": "Z",
            "И": "I",
            "Ӣ": "I",
            "Й": "Y",
            "К": "K",
            "Қ": "Q",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ӯ": "U",
            "Ф": "F",
            "Х": "Kh",
            "Ҳ": "H",
            "Ч": "Ch",
            "Ҷ": "J",
            "Ш": "Sh",
            "Ъ": "",
            "Э": "E",
            "Ю": "Yu",
            "Я": "Ya",
        }

        result = []
        for char in name:
            if char in tajik_map:
                result.append(tajik_map[char])
            else:
                result.append(char)

        return "".join(result)

    def _analyze_persian_ezafe(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Rule 7: Persian Ezafe – identify and analyze ezafe constructions.

        Persian ezafe (اضافه) is a grammatical linker used in compound names:
        - Possessive relationships: "Ali-ye Shirazi" (Ali of Shiraz)
        - Descriptive relationships: "Mohammad-e Kabir" (Mohammad the Great)
        - Location-based: "Hassan-e Isfahani" (Hassan of Isfahan)

        Ezafe can be represented as:
        - ِ (kasre/short i diacritic) - typically invisible in modern texts
        - -e (romanized form)
        - -ye (after vowels)
        - No marking (implicit)

        This method identifies ezafe patterns and extracts components.
        """
        if not name:
            return None

        ezafe_info = {}

        # Ezafe patterns to detect
        ezafe_patterns = [
            # Romanized forms
            (r"\b(\w+)-ye\s+(\w+)", "romanized_ye"),  # "Ali-ye Shirazi"
            (r"\b(\w+)-e\s+(\w+)", "romanized_e"),  # "Hassan-e Isfahani"
            (r"\b(\w+)ye\s+(\w+)", "compact_ye"),  # "Aliye Shirazi"
            (r"\b(\w+)e\s+(\w+)", "compact_e"),  # "Hassane Isfahani"
            # Persian script forms (with kasre mark)
            (r"(\w+)ِ\s+(\w+)", "kasre_marked"),  # With visible kasre
            (r"(\w+)\u0650\s+(\w+)", "kasre_unicode"),  # Unicode kasre (U+0650)
            # Common Persian ezafe constructions (implicit)
            (r"\b(\w+)\s+(شیرازی|اصفهانی|تهرانی|کاشانی|یزدی|کرمانی|فارسی)", "geographic_implicit"),
            (r"\b(\w+)\s+(کبیر|صغیر|اکبر|اصغر|بزرگ|کوچک)", "descriptive_implicit"),
        ]

        # Check for ezafe patterns
        for pattern, ezafe_type in ezafe_patterns:
            matches = re.finditer(pattern, name, re.IGNORECASE)
            for match in matches:
                ezafe_info.update(
                    {
                        "has_ezafe": True,
                        "ezafe_type": ezafe_type,
                        "ezafe_base": match.group(1),
                        "ezafe_complement": match.group(2),
                        "ezafe_full_match": match.group(0),
                        "ezafe_position": match.span(),
                    }
                )

                # Determine the relationship type
                if ezafe_type in ["geographic_implicit"]:
                    ezafe_info["ezafe_relationship"] = "geographic"
                elif ezafe_type in ["descriptive_implicit"]:
                    ezafe_info["ezafe_relationship"] = "descriptive"
                else:
                    ezafe_info["ezafe_relationship"] = "possessive"

                # Return first match (most names have one ezafe construction)
                return ezafe_info

        # Check for implicit ezafe (two-part names that might have ezafe)
        words = name.split()
        if len(words) == 2:
            first, second = words

            # Common patterns that suggest implicit ezafe
            geographic_endings = ["ی", "ي", "انی", "i", "ani"]  # Persian/Arabic geographic suffixes
            descriptive_words = [
                "کبیر",
                "صغیر",
                "اکبر",
                "اصغر",
                "بزرگ",
                "kabir",
                "saghir",
                "akbar",
                "asghar",
                "bozorg",
            ]

            is_geographic = any(second.endswith(ending) for ending in geographic_endings)
            is_descriptive = second.lower() in [word.lower() for word in descriptive_words]

            if is_geographic or is_descriptive:
                ezafe_info.update(
                    {
                        "has_ezafe": True,
                        "ezafe_type": "implicit",
                        "ezafe_base": first,
                        "ezafe_complement": second,
                        "ezafe_full_match": name,
                        "ezafe_relationship": "geographic" if is_geographic else "descriptive",
                    }
                )
                return ezafe_info

        return None

    def _generate_ezafe_variants(
        self, name: str, ezafe_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Rule 7: Generate variants with different ezafe representations.

        Creates multiple representations of the same ezafe construction:
        - With explicit ezafe marking (-e, -ye)
        - Without ezafe marking (bare juxtaposition)
        - With kasre diacritic (Persian script)
        - Normalized forms for international systems
        """
        variants = []

        base = ezafe_info.get("ezafe_base", "")
        complement = ezafe_info.get("ezafe_complement", "")
        ezafe_type = ezafe_info.get("ezafe_type", "")

        if not (base and complement):
            return variants

        # Generate different ezafe representations

        # 1. Explicit -e form (most common romanization)
        if ezafe_type != "romanized_e":
            e_form = f"{base}-e {complement}"
            variants.append({"str": e_form, "type": "ezafe-explicit-e"})

        # 2. Explicit -ye form (after vowels)
        if ezafe_type != "romanized_ye" and base[-1].lower() in "aeiou":
            ye_form = f"{base}-ye {complement}"
            variants.append({"str": ye_form, "type": "ezafe-explicit-ye"})

        # 3. No ezafe marking (bare juxtaposition)
        if ezafe_type not in ["implicit"]:
            bare_form = f"{base} {complement}"
            variants.append({"str": bare_form, "type": "ezafe-bare"})

        # 4. Compact forms (no hyphen)
        if "-" in name:
            if ezafe_type == "romanized_e":
                compact_form = f"{base}e {complement}"
                variants.append({"str": compact_form, "type": "ezafe-compact-e"})
            elif ezafe_type == "romanized_ye":
                compact_form = f"{base}ye {complement}"
                variants.append({"str": compact_form, "type": "ezafe-compact-ye"})

        # 5. Persian script form with kasre (if original is romanized)
        if not self._is_persian(name) and ezafe_type.startswith("romanized"):
            # Add kasre mark to the base word
            kasre_form = f"{base}\u0650 {complement}"  # U+0650 is Arabic kasre
            variants.append({"str": kasre_form, "type": "ezafe-kasre-marked"})

        # 6. International normalized form (ASCII-compatible)
        international_form = f"{base} {complement}"
        if international_form != name:
            variants.append({"str": international_form, "type": "ezafe-international"})

        return variants

    def _analyze_zadeh_suffix(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Rule 21: -zadeh Suffix – identify Persian patronymic/descendant suffix.

        The Persian suffix -zadeh (زاده) means "born of" or "descendant of" and is
        commonly used in Persian family names to indicate lineage:

        - "Mohammadzadeh" = descendant of Mohammad
        - "Alizada" = descendant of Ali (Azerbaijani spelling)
        - "Hassanzadeh" = descendant of Hassan
        - "Rezazadeh" = descendant of Reza

        Variations include:
        - -zadeh (Persian romanization)
        - -zade (Turkish/Azerbaijani spelling)
        - -zadah (alternative romanization)
        - زاده (Persian script)
        - زاد (shortened form)
        """
        if not name:
            return None

        zadeh_info = {}

        # -zadeh suffix patterns to detect
        zadeh_patterns = [
            # Full suffix forms
            (r"(\w+)zadeh\b", "full_zadeh"),  # "Mohammadzadeh"
            (r"(\w+)zade\b", "short_zade"),  # "Alizada" (Azerbaijani)
            (r"(\w+)zadah\b", "alt_zadah"),  # "Mohammadzadah"
            # Persian script forms
            (r"(\w+)زاده\b", "persian_full"),  # Persian script full form
            (r"(\w+)زاد\b", "persian_short"),  # Persian script short form
            # Space-separated forms (sometimes written separately)
            (r"(\w+)\s+زاده\b", "persian_separate"),  # "محمد زاده"
            (r"(\w+)\s+zadeh\b", "roman_separate"),  # "Mohammad zadeh"
        ]

        # Check for -zadeh patterns
        for pattern, zadeh_type in zadeh_patterns:
            matches = re.finditer(pattern, name, re.IGNORECASE)
            for match in matches:
                root_name = match.group(1).strip()

                # Skip very short roots (likely false positives)
                if len(root_name) < 2:
                    continue

                zadeh_info.update(
                    {
                        "has_zadeh_suffix": True,
                        "zadeh_type": zadeh_type,
                        "zadeh_root": root_name,
                        "zadeh_full_match": match.group(0),
                        "zadeh_position": match.span(),
                        "zadeh_meaning": f"descendant of {root_name}",
                    }
                )

                # Determine the suffix variant used
                if zadeh_type in ["full_zadeh", "roman_separate"]:
                    zadeh_info["zadeh_suffix"] = "zadeh"
                elif zadeh_type == "short_zade":
                    zadeh_info["zadeh_suffix"] = "zade"
                elif zadeh_type == "alt_zadah":
                    zadeh_info["zadeh_suffix"] = "zadah"
                elif zadeh_type in ["persian_full", "persian_separate"]:
                    zadeh_info["zadeh_suffix"] = "زاده"
                elif zadeh_type == "persian_short":
                    zadeh_info["zadeh_suffix"] = "زاد"

                # Check if the root name is a known Persian name
                persian_names = [
                    "mohammad",
                    "mohammed",
                    "muhammad",
                    "ali",
                    "hassan",
                    "hussain",
                    "ahmad",
                    "ahmed",
                    "reza",
                    "abbas",
                    "hossein",
                    "javad",
                    "mehdi",
                    "masoud",
                    "mahmoud",
                    "kazem",
                    "morteza",
                    "mostafa",
                    "ebrahim",
                    "ibrahim",
                    "hamid",
                    "majid",
                    "said",
                    "saeed",
                ]

                if root_name.lower() in persian_names:
                    zadeh_info["zadeh_confidence"] = "high"
                else:
                    zadeh_info["zadeh_confidence"] = "medium"

                # Return first match (most names have one -zadeh suffix)
                return zadeh_info

        return None

    def _generate_zadeh_variants(
        self, name: str, zadeh_info: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Rule 21: Generate variants with different -zadeh suffix representations.

        Creates multiple representations of the same -zadeh construction:
        - Different suffix spellings (-zadeh, -zade, -zadah)
        - With and without the suffix (root name only)
        - Persian script and romanized variants
        - Space-separated and compound forms
        """
        variants = []

        root = zadeh_info.get("zadeh_root", "")
        zadeh_type = zadeh_info.get("zadeh_type", "")
        current_suffix = zadeh_info.get("zadeh_suffix", "")

        if not root:
            return variants

        # Generate different suffix spellings
        suffix_variants = {
            "zadeh": f"{root}zadeh",  # Standard Persian romanization
            "zade": f"{root}zade",  # Turkish/Azerbaijani spelling
            "zadah": f"{root}zadah",  # Alternative romanization
        }

        # Add variants for different suffix spellings
        for suffix_type, variant_name in suffix_variants.items():
            if suffix_type != current_suffix.replace("زاده", "zadeh").replace("زاد", "zade"):
                variants.append({"str": variant_name, "type": f"zadeh-suffix-{suffix_type}"})

        # Generate root name variant (without suffix)
        if len(root) >= 3:  # Only for substantial root names
            variants.append({"str": root, "type": "zadeh-root-only"})

        # Generate space-separated variants
        if " " not in name:  # If original is compound form
            space_separated = f"{root} zadeh"
            variants.append({"str": space_separated, "type": "zadeh-space-separated"})

        # Generate Persian script variants (if original is romanized)
        if not self._is_persian(name):
            persian_full = f"{root}زاده"
            persian_short = f"{root}زاد"

            variants.extend(
                [
                    {"str": persian_full, "type": "zadeh-persian-full"},
                    {"str": persian_short, "type": "zadeh-persian-short"},
                ]
            )

        # Generate romanized variants (if original is Persian script)
        elif self._is_persian(name):
            romanized_full = f"{root}zadeh"
            romanized_short = f"{root}zade"

            variants.extend(
                [
                    {"str": romanized_full, "type": "zadeh-romanized-full"},
                    {"str": romanized_short, "type": "zadeh-romanized-short"},
                ]
            )

        # Generate capitalized variants for proper names
        for variant in variants[:]:  # Copy list to avoid modification during iteration
            if variant["str"].islower():
                capitalized = variant["str"].title()
                if capitalized != variant["str"]:
                    variants.append({"str": capitalized, "type": variant["type"] + "-capitalized"})

        return variants

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
        """Validate entry according to C2 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")

        # If CanonicalNative exists, it should be Persian or Cyrillic
        if canonical_native:
            if not self._is_persian_or_tajik(canonical_native):
                raise RegionRuleError(
                    f"CanonicalNative should be Persian or Tajik: {canonical_native}"
                )

        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_persian_or_tajik(canonical_latin):
                raise RegionRuleError(f"CanonicalLatin should be romanized: {canonical_latin}")

        # Check name structure
        for canonical in [canonical_native, canonical_latin]:
            if canonical:
                words = canonical.split()
                if len(words) < 2:
                    raise RegionRuleError(f"Name should have at least 2 words: {canonical}")

                # Check for invalid characters
                if not self._has_valid_characters(canonical):
                    raise RegionRuleError(f"Invalid characters in name: {canonical}")

    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters."""
        for char in name:
            # Allow Latin, Persian, Cyrillic, spaces, hyphens, apostrophes
            if char.isalpha() or char in " -'":
                continue
            # Check if it's valid Persian
            if any(start <= ord(char) <= end for start, end in self.persian_ranges):
                continue
            # Check if it's valid Cyrillic
            if any(start <= ord(char) <= end for start, end in self.cyrillic_ranges):
                continue
            # Invalid character found
            return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Use romanized form for sorting if available
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")

        # If we have Persian/Tajik, romanize for sorting
        if self._is_persian_or_tajik(canonical):
            canonical = self._romanize_name(canonical)

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
