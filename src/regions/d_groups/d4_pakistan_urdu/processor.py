"""
D4 - Pakistan & Urdu region implementation for GMNAP v7.

Covers: Pakistan, Urdu-speaking communities in India, and global Pakistani diaspora
Features: Urdu (Arabic-Nastaliq) script, Islamic naming patterns, tribal/clan names,
          British colonial influences, regional language variations

Key capabilities:
- Urdu script detection and romanization (ALA-LC standard)
- Islamic patronymic patterns (bin/ibn, bint/binte)
- Pakistani tribal and clan name recognition
- Regional variations (Punjabi, Sindhi, Pashto, Balochi influences)
- British colonial administrative name patterns
- Academic and professional title handling
- Gender-sensitive processing with Islamic cultural awareness
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class D4_PakistanUrdu(RegionSpec):
    """
    Pakistan & Urdu region (D4) processor.

    Handles mathematician names from Pakistani and Urdu-speaking communities:
    - Urdu script (Arabic-Nastaliq) and romanized forms
    - Islamic naming conventions and patronymics
    - Pakistani tribal, clan, and occupational surnames
    - Regional language influences (Punjabi, Sindhi, Pashto, Balochi)
    - British colonial naming legacy
    - Modern academic and professional titles
    - Culturally sensitive gender inference
    """

    def __init__(self):
        super().__init__(
            code="D4",
            yaml_files=["d4_pakistan_urdu.yaml"],
            scripts=["Arabic-Nastaliq", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "UN"],
        )

        # Islamic naming patterns
        self.islamic_names = {
            # Theophoric names (Abdul + attribute)
            "abdul_names": {
                "عبدالله",
                "Abdullah",
                "عبدالرحمن",
                "Abdul Rahman",
                "عبدالرحیم",
                "Abdul Rahim",
                "عبدالکریم",
                "Abdul Kareem",
                "عبدالحی",
                "Abdul Hai",
                "عبدالعلیم",
                "Abdul Aleem",
                "عبدالقادر",
                "Abdul Qadir",
                "عبدالمجید",
                "Abdul Majid",
                "عبدالغفور",
                "Abdul Ghafoor",
                "عبدالستار",
                "Abdul Sattar",
                "عبدالجبار",
                "Abdul Jabbar",
                "عبدالرؤوف",
                "Abdul Rauf",
            },
            # Prophet Muhammad variations
            "muhammad_variants": {
                "محمد",
                "Muhammad",
                "Mohammed",
                "Mohammad",
                "Ahmed",
                "Ahmad",
                "احمد",
                "Muhammed",
                "Mohamed",
                "Mahmood",
                "Mahmud",
                "محمود",
                "Hamid",
                "حامد",
            },
            # Common Islamic first names
            "common_islamic": {
                "علی",
                "Ali",
                "حسن",
                "Hassan",
                "حسین",
                "Hussain",
                "عثمان",
                "Usman",
                "Othman",
                "عمر",
                "Omar",
                "Umar",
                "ابراہیم",
                "Ibrahim",
                "اسماعیل",
                "Ismail",
                "یوسف",
                "Yusuf",
                "موسٰی",
                "Musa",
                "عیسٰی",
                "Isa",
                "یحییٰ",
                "Yahya",
                "زکریا",
                "Zakaria",
                "فاطمہ",
                "Fatima",
                "عائشہ",
                "Ayesha",
                "Aisha",
                "خدیجہ",
                "Khadija",
                "زینب",
                "Zainab",
                "رقیہ",
                "Ruqayyah",
                "ام کلثوم",
                "Umm Kulthum",
            },
        }

        # Patronymic indicators
        self.patronymic_patterns = {
            # Arabic-style patronymics
            "bin",
            "ibn",
            "بن",  # son of
            "bint",
            "binte",
            "بنت",  # daughter of
            # Urdu/subcontinental variations
            "s/o",
            "son of",
            "بیٹا",  # son of
            "d/o",
            "daughter of",
            "بیٹی",
            "w/o",
            "wife of",  # daughter/wife of
        }

        # Pakistani tribal and clan names
        self.tribal_clan_names = {
            # Major Punjabi clans
            "punjabi_clans": {
                "Jat",
                "جٹ",
                "Rajput",
                "راجپوت",
                "Arain",
                "اعوان",
                "Gujjar",
                "گجر",
                "Sheikh",
                "شیخ",
                "Malik",
                "ملک",
                "Chaudhry",
                "چودھری",
                "Mian",
                "میاں",
                "Rao",
                "راؤ",
                "Butt",
                "بٹ",
                "Dar",
                "ڈار",
                "Lone",
                "لون",
            },
            # Pathan/Pashtun tribes
            "pathan_tribes": {
                "Khan",
                "خان",
                "Afridi",
                "آفریدی",
                "Khattak",
                "خٹک",
                "Yusufzai",
                "یوسفزئی",
                "Bangash",
                "بنگش",
                "Orakzai",
                "اورکزئی",
                "Wazir",
                "وزیر",
                "Mahsud",
                "محسود",
                "Mohmand",
                "مومند",
                "Shinwari",
                "شینواری",
                "Durrani",
                "درانی",
                "Ghilzai",
                "غلجئی",
            },
            # Baloch tribes
            "baloch_tribes": {
                "Baloch",
                "بلوچ",
                "Rind",
                "رند",
                "Lashari",
                "لاشاری",
                "Marri",
                "مری",
                "Bugti",
                "بگٹی",
                "Mengal",
                "مینگل",
                "Bizenjo",
                "بزنجو",
                "Jamali",
                "جمالی",
                "Zehri",
                "زہری",
                "Raisani",
                "ریسانی",
                "Lehri",
                "لہری",
            },
            # Sindhi tribes/clans
            "sindhi_clans": {
                "Sindhi",
                "سندھی",
                "Soomro",
                "سومرو",
                "Talpur",
                "ٹالپور",
                "Jatoi",
                "جٹوئی",
                "Bhutto",
                "بھٹو",
                "Chandio",
                "چاندیو",
                "Khuhro",
                "کھوہرو",
                "Mahar",
                "مہار",
                "Mangi",
                "منگی",
                "Palijo",
                "پالیجو",
                "Qureshi",
                "قریشی",
            },
        }

        # Occupational and status surnames
        self.occupational_surnames = {
            # Religious/scholarly
            "Maulana",
            "مولانا",
            "Maulvi",
            "مولوی",
            "Hafiz",
            "حافظ",
            "Qari",
            "قاری",
            "Imam",
            "امام",
            "Pir",
            "پیر",
            "Shah",
            "شاہ",
            "Syed",
            "سید",
            "Sharif",
            "شریف",
            # Administrative/military (British colonial legacy)
            "Khan",
            "خان",
            "Malik",
            "ملک",
            "Chaudhry",
            "چودھری",
            "Sardar",
            "سردار",
            "Mir",
            "میر",
            "Nawab",
            "نواب",
            "Baig",
            "بیگ",
            "Mirza",
            "مرزا",
            # Professional/occupational
            "Sheikh",
            "شیخ",
            "Mian",
            "میاں",
            "Rao",
            "راؤ",
            "Roy",
            "رائے",
            "Bahadur",
            "بہادر",
            "Qazi",
            "قاضی",
            "Munshi",
            "منشی",
            "Vakil",
            "وکیل",
        }

        # Academic and professional titles
        self.academic_titles = {
            # Modern academic
            "Professor",
            "Prof",
            "پروفیسر",
            "Doctor",
            "Dr",
            "ڈاکٹر",
            "Engineer",
            "Engr",
            "انجینئر",
            "Advocate",
            "Adv",
            "وکیل",
            # Islamic traditional
            "Allama",
            "علامہ",
            "Mufti",
            "مفتی",
            "Maulana",
            "مولانا",
            "Hafiz",
            "حافظ",
            "Qari",
            "قاری",
            # Military/governmental
            "Colonel",
            "کرنل",
            "Brigadier",
            "بریگیڈیئر",
            "General",
            "جنرل",
            "Justice",
            "جسٹس",
            "Honourable",
            "محترم",
        }

        # Regional language influences
        self.regional_patterns = {
            "punjabi": {
                "common_surnames": [
                    "Singh",
                    "سنگھ",
                    "Kaur",
                    "کور",
                    "Gill",
                    "گل",
                    "Sandhu",
                    "سندھو",
                ],
                "patterns": [r"\b\w+deep\b", r"\b\w+jit\b", r"\b\w+pal\b", r"\b\w+want\b"],
            },
            "sindhi": {
                "common_surnames": ["Lal", "لال", "Das", "داس", "Ani", "انی", "Wani", "وانی"],
                "patterns": [r"\b\w+ani\b", r"\b\w+wani\b", r"\b\w+chandani\b"],
            },
            "balochi": {
                "suffixes": ["-zai", "زئی", "-ani", "انی", "-zada", "زادہ", "-shah", "شاہ"],
                "patterns": [r"\b\w+zai\b", r"\b\w+ani\b", r"\b\w+zada\b"],
            },
            "pashto": {
                "suffixes": ["-zai", "زئی", "-khel", "خیل", "-khan", "خان"],
                "patterns": [r"\b\w+zai\b", r"\b\w+khel\b", r"\b\w+ullah\b"],
            },
        }

        # Urdu script character ranges
        self.urdu_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
            (0x08A0, 0x08FF),  # Arabic Extended-A
        ]

        # Common Urdu name words for validation
        self.urdu_name_vocabulary = {
            "نام",
            "نوم",
            "لقب",
            "کنیت",  # name, surname, title terms
            "خان",
            "ملک",
            "شیخ",
            "میاں",  # common surnames
            "بن",
            "بنت",
            "ابن",  # patronymic
            "محمد",
            "احمد",
            "علی",
            "حسن",  # common first names
            "بیگم",
            "صاحب",
            "صاحبہ",  # respectful suffixes
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to D4 Pakistan Urdu rules."""
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

        # Apply security validation first

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
        """Clean a single name string according to Pakistani conventions."""
        if not name:
            return name

        # Apply Unicode fold exceptions (Rule 16)
        name = self.apply_unicode_fold_exceptions(name)

        # Remove academic and professional titles
        name = self._remove_titles(name)

        # Normalize Urdu punctuation
        name = self._normalize_urdu_punctuation(name)

        # Standardize patronymic indicators
        name = self._standardize_patronymics(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Handle common spelling variations
        name = self._normalize_spelling_variations(name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove academic, professional, and honorific titles."""
        if not text:
            return text

        # Create pattern for all titles
        all_titles = set()
        all_titles.update(self.academic_titles)

        # Sort by length (longest first) to avoid partial matches
        sorted_titles = sorted(all_titles, key=len, reverse=True)

        for title in sorted_titles:
            # Remove title at beginning with optional period and space
            pattern = rf"^\s*{re.escape(title)}\.?\s+"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

            # Remove title at end with optional period
            pattern = rf"\s+{re.escape(title)}\.?\s*$"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Handle common title patterns
        text = re.sub(r"^\s*(Dr\.?|Prof\.?|Engr\.?)\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+(Sahib|Saheb|Saab)\s*$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+(صاحب|صاحبہ)\s*$", "", text)

        return text.strip()

    def _normalize_urdu_punctuation(self, name: str) -> str:
        """Normalize Urdu and Arabic punctuation marks."""
        # Arabic-Urdu punctuation normalization
        name = name.replace("؍", "/")  # Arabic date separator
        name = name.replace("؎", "*")  # Arabic footnote marker
        name = name.replace("؏", "*")  # Arabic sign safha
        name = name.replace("؞", '"')  # Arabic triple dot punctuation
        name = name.replace("؟", "?")  # Arabic question mark
        name = name.replace("٪", "%")  # Arabic percent sign
        name = name.replace("٫", ",")  # Arabic decimal separator
        name = name.replace("٬", ",")  # Arabic thousands separator

        # Remove Arabic diacritical marks (but preserve letters)
        diacritics = [
            "\u064b",
            "\u064c",
            "\u064d",
            "\u064e",
            "\u064f",  # Short vowels
            "\u0650",
            "\u0651",
            "\u0652",
            "\u0653",
            "\u0654",  # More diacritics
            "\u0655",
            "\u0656",
            "\u0657",
            "\u0658",
            "\u0659",
            "\u065a",
            "\u065b",
            "\u065c",
            "\u065d",
            "\u065e",
            "\u065f",
            "\u0670",  # Additional diacritics
        ]

        for diacritic in diacritics:
            name = name.replace(diacritic, "")

        return name

    def _standardize_patronymics(self, name: str) -> str:
        """Standardize patronymic indicators."""
        # Standardize to common forms
        name = re.sub(r"\bs/o\b", "bin", name, flags=re.IGNORECASE)
        name = re.sub(r"\bson of\b", "bin", name, flags=re.IGNORECASE)
        name = re.sub(r"\bd/o\b", "bint", name, flags=re.IGNORECASE)
        name = re.sub(r"\bdaughter of\b", "bint", name, flags=re.IGNORECASE)
        name = re.sub(r"\bw/o\b", "wife of", name, flags=re.IGNORECASE)

        # Handle Urdu equivalents
        name = name.replace("بیٹا", "bin")
        name = name.replace("بیٹی", "bint")

        return name

    def _normalize_spelling_variations(self, name: str) -> str:
        """Normalize common spelling variations in Pakistani names."""
        # Muhammad variations
        variations = [
            (r"\bMohammad\b", "Muhammad"),
            (r"\bMohammed\b", "Muhammad"),
            (r"\bMuhammed\b", "Muhammad"),
            (r"\bMohamed\b", "Muhammad"),
            # Ahmed variations
            (r"\bAhmad\b", "Ahmed"),
            (r"\bAhmed\b", "Ahmed"),
            # Common consonant variations
            (r"\bKh([aeiou])", r"Kh\1"),  # Ensure Kh is capitalized
            (r"\bGh([aeiou])", r"Gh\1"),  # Ensure Gh is capitalized
            # Standardize common endings
            (r"ullah$", "ullah"),
            (r"uddin$", "uddin"),
            (r"uddin$", "uddin"),
        ]

        for pattern, replacement in variations:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with D4-specific data."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Initialize RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)
        entry["RegionalExtras"]["script"] = self._detect_script(canonical)
        entry["RegionalExtras"]["likely_country"] = "PK"  # Pakistan

        # Add region code
        entry["RegionCode"] = self.code

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Add romanized variant if original is Urdu script
        if self._is_urdu_script(canonical):
            romanized = self._romanize_urdu(canonical)
            if romanized != canonical:
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append(
                    {"str": romanized, "type": "romanization", "standard": "ALA-LC"}
                )

        # Add name variants
        variants = self._generate_name_variants(canonical, components)
        for variant in variants:
            if variant["str"] != canonical:
                entry["Variants"]["Synthesised"].append(variant)

        # Apply gender heuristic guard (Rule 26)
        self.apply_gender_heuristic_guard(entry)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract Pakistani name components."""
        components = {}
        words = name.split()

        if not words:
            return components

        # Detect patronymic patterns
        patronymic_info = self._detect_patronymic_pattern(words)
        if patronymic_info:
            components.update(patronymic_info)

        # Detect Islamic naming patterns
        islamic_info = self._detect_islamic_patterns(words)
        if islamic_info:
            components.update(islamic_info)

        # Detect tribal/clan affiliations
        tribal_info = self._detect_tribal_patterns(words)
        if tribal_info:
            components.update(tribal_info)

        # Basic name component extraction
        if len(words) == 1:
            # Single name (often religious figures or mononyms)
            components["given_name"] = words[0]
            components["is_mononym"] = True

        elif len(words) == 2:
            # Simple: Given Family
            components["given_name"] = words[0]
            components["family_name"] = words[1]

        elif len(words) == 3:
            # Common Pakistani pattern: Given Father/Middle Family
            components["given_name"] = words[0]

            # Check if middle word is a patronymic indicator
            if words[1].lower() in {"bin", "ibn", "bint", "s/o", "d/o"}:
                components["patronymic_indicator"] = words[1]
                components["father_name"] = words[2]
            else:
                components["middle_name"] = words[1]
                components["family_name"] = words[2]

        elif len(words) >= 4:
            # Complex pattern: Given [Middle/Patronymic] [Father] Family
            components["given_name"] = words[0]
            components["family_name"] = words[-1]

            # Middle parts analysis
            middle_parts = words[1:-1]
            if len(middle_parts) == 1:
                components["middle_name"] = middle_parts[0]
            else:
                # Look for patronymic patterns
                patronymic_found = False
                for i, part in enumerate(middle_parts):
                    if part.lower() in self.patronymic_patterns:
                        components["patronymic_indicator"] = part
                        if i + 1 < len(middle_parts):
                            components["father_name"] = " ".join(middle_parts[i + 1 :])
                        patronymic_found = True
                        break

                if not patronymic_found:
                    components["middle_name"] = " ".join(middle_parts)

        return components

    def _detect_patronymic_pattern(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """Detect Islamic patronymic patterns."""
        result = {}

        for i, word in enumerate(words):
            if word.lower() in self.patronymic_patterns:
                result["has_patronymic"] = True
                result["patronymic_type"] = "islamic"
                result["patronymic_indicator"] = word

                # Try to identify father's name
                if i + 1 < len(words):
                    result["father_name"] = words[i + 1]

                return result

        # Check for implicit patronymic (Islamic naming without explicit bin/ibn)
        if len(words) >= 3:
            # Pattern: Muhammad Ali Khan (likely Muhammad bin Ali Khan)
            if words[0] in self.islamic_names["muhammad_variants"]:
                result["has_implicit_patronymic"] = True
                result["patronymic_type"] = "implicit_islamic"
                result["likely_father_name"] = words[1]
                return result

        return None

    def _detect_islamic_patterns(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """Detect Islamic naming patterns."""
        result = {}

        # Check for Abdul + attribute combinations
        for word in words:
            if word.lower().startswith("abdul"):
                result["has_theophoric"] = True
                result["theophoric_type"] = "abdul"
                break

        # Check for Muhammad variants
        muhammad_variants = {name.lower() for name in self.islamic_names["muhammad_variants"]}
        for word in words:
            if word.lower() in muhammad_variants:
                result["has_muhammad_name"] = True
                result["muhammad_variant"] = word
                break

        # Check for common Islamic names
        islamic_names = {name.lower() for names in self.islamic_names.values() for name in names}
        islamic_count = sum(1 for word in words if word.lower() in islamic_names)

        if islamic_count > 0:
            result["islamic_name_count"] = islamic_count
            result["islamic_name_ratio"] = islamic_count / len(words)

        return result if result else None

    def _detect_tribal_patterns(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """Detect tribal and clan affiliations."""
        result = {}

        # Check all tribal categories
        for category, tribes in self.tribal_clan_names.items():
            for word in words:
                if word in tribes:
                    if "tribal_affiliations" not in result:
                        result["tribal_affiliations"] = []
                    result["tribal_affiliations"].append({"category": category, "name": word})

        # Check occupational surnames
        for word in words:
            if word in self.occupational_surnames:
                if "occupational_surnames" not in result:
                    result["occupational_surnames"] = []
                result["occupational_surnames"].append(word)

        return result if result else None

    def _detect_script(self, text: str) -> str:
        """Detect the primary script used in the text."""
        if not text:
            return "unknown"

        urdu_chars = 0
        latin_chars = 0
        total_chars = 0

        for char in text:
            if char.isalpha():
                total_chars += 1
                if any(start <= ord(char) <= end for start, end in self.urdu_ranges):
                    urdu_chars += 1
                elif ord(char) < 256:  # Basic Latin
                    latin_chars += 1

        if total_chars == 0:
            return "unknown"

        urdu_ratio = urdu_chars / total_chars
        latin_ratio = latin_chars / total_chars

        if urdu_ratio > 0.7:
            return "Urdu"
        elif latin_ratio > 0.7:
            return "Latin"
        elif urdu_chars > 0 and latin_chars > 0:
            return "Mixed"
        else:
            return "other"

    def _is_urdu_script(self, text: str) -> bool:
        """Check if text contains Urdu/Arabic script characters."""
        for char in text:
            pass

    def _romanize_urdu(self, text: str) -> str:
        """Romanize Urdu text using ALA-LC standard."""
        # Basic Urdu to Latin romanization mapping (ALA-LC)
        romanization_map = {
            # Letters
            "ا": "a",
            "ب": "b",
            "پ": "p",
            "ت": "t",
            "ٹ": "ṭ",
            "ث": "s̤",
            "ج": "j",
            "چ": "ch",
            "ح": "ḥ",
            "خ": "kh",
            "د": "d",
            "ڈ": "ḍ",
            "ذ": "z̤",
            "ر": "r",
            "ڑ": "ṛ",
            "ز": "z",
            "ژ": "zh",
            "س": "s",
            "ش": "sh",
            "ص": "ṣ",
            "ض": "ḍ",
            "ط": "ṭ",
            "ظ": "ẓ",
            "ع": "ʻ",
            "غ": "gh",
            "ف": "f",
            "ق": "q",
            "ک": "k",
            "گ": "g",
            "ل": "l",
            "م": "m",
            "ن": "n",
            "ں": "ṅ",
            "و": "v",
            "ہ": "h",
            "ھ": "h",
            "ی": "y",
            "ے": "e",
            # Vowel marks
            "َ": "a",
            "ِ": "i",
            "ُ": "u",
            "ٰ": "ā",
            "ً": "an",
            "ٌ": "un",
            "ٍ": "in",
            # Special combinations for common names
            "خان": "Khan",
            "شیخ": "Sheikh",
            "محمد": "Muhammad",
            "احمد": "Ahmed",
            "علی": "Ali",
            "حسن": "Hassan",
            "حسین": "Hussain",
        }

        # Apply romanization
        result = text
        for urdu, roman in romanization_map.items():
            result = result.replace(urdu, roman)

        # Clean up and format
        result = re.sub(r"[ʻ]", "", result)  # Remove ayn marks for simplicity
        result = " ".join(result.split())

        return result.title()

    def _generate_name_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate name variants for Pakistani names."""
        variants = []

        given = components.get("given_name", "")
        family = components.get("family_name", "")
        middle = components.get("middle_name", "")
        father = components.get("father_name", "")

        # Initials variant
        if given and family:
            if middle:
                initials = f"{given[0]}. {middle[0]}. {family}"
            else:
                initials = f"{given[0]}. {family}"
            variants.append({"str": initials, "type": "initials"})

        # Short form (without middle name)
        if given and family and (middle or father):
            short_form = f"{given} {family}"
            variants.append({"str": short_form, "type": "short-form"})

        # Full patronymic form
        if components.get("has_patronymic") and father:
            patronymic_form = f"{given} bin {father}"
            if family:
                patronymic_form += f" {family}"
            variants.append({"str": patronymic_form, "type": "patronymic"})

        # Islamic traditional format
        if components.get("has_muhammad_name") and given != "Muhammad":
            traditional = f"Muhammad {name}"
            variants.append({"str": traditional, "type": "islamic-traditional"})

        return variants

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

        # SECURITY: Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")

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

    def _has_valid_urdu_structure(self, text: str) -> bool:
        """Check if Urdu text has valid structure."""
        if not text:
            return False

        # Check for valid Urdu characters
        urdu_char_count = 0
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.urdu_ranges):
                urdu_char_count += 1

        if urdu_char_count == 0:
            return False

        # Check for common Urdu name vocabulary
        has_name_vocab = any(word in text for word in self.urdu_name_vocabulary)

        # Check for valid word boundaries (spaces between words)
        words = text.split()
        if len(words) == 0:
            return False

        return True

    def _has_valid_name_structure(self, name: str) -> bool:
        """Check if name has valid Pakistani name structure."""
        words = name.split()

        if len(words) == 0:
            return False

        # Single word names should be Islamic names or known surnames
        if len(words) == 1:
            word_lower = words[0].lower()
            # Check against known Islamic names and common surnames
            all_islamic = {n.lower() for names in self.islamic_names.values() for n in names}
            all_surnames = {
                s.lower() for surnames in self.tribal_clan_names.values() for s in surnames
            }
            all_surnames.update({s.lower() for s in self.occupational_surnames})

            return word_lower in all_islamic or word_lower in all_surnames

        # Multi-word names should follow Pakistani patterns
        return True  # Most multi-word combinations are valid

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for Pakistani names."""
        components = entry.get("RegionalExtras", {})

        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        middle = components.get("middle_name", "") or components.get("father_name", "")

        # Use romanized form for sorting
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")

        # If we have Urdu script, romanize for sorting
        if self._is_urdu_script(canonical):
            canonical = self._romanize_urdu(canonical)

        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""
        sort_middle = middle.upper() if middle else ""

        # Special handling for common Pakistani patterns
        if not sort_family and canonical:
            words = canonical.upper().split()
            if len(words) > 1:
                # Last word is likely family name
                sort_family = words[-1]
                sort_given = " ".join(words[:-1])

        # Remove diacritics and punctuation for consistent sorting
        import unicodedata

        def normalize_for_sort(text):
            # Remove diacritics
            normalized = unicodedata.normalize("NFD", text)
            ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
            # Remove punctuation except spaces
            cleaned = re.sub(r"[^\w\s]", "", ascii_text)
            return " ".join(cleaned.split())

        sort_family = normalize_for_sort(sort_family) if sort_family else ""
        sort_given = normalize_for_sort(sort_given) if sort_given else ""
        sort_middle = normalize_for_sort(sort_middle) if sort_middle else ""

        # Generate key: Family, Given Middle
        key_parts = []
        if sort_family:
            key_parts.append(sort_family)
        if sort_given:
            key_parts.append(sort_given)
        if sort_middle:
            key_parts.append(sort_middle)

        key = " ".join(key_parts) if key_parts else normalize_for_sort(canonical.upper())

        # Ensure determinism and clean formatting
        key = " ".join(key.split())

        return key
