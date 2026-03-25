"""
C1 - Greater-Turkic region implementation.

Covers: TR, AZ, UZ, TM, KG, KZ (Turkey, Azerbaijan, Uzbekistan, Turkmenistan, Kyrgyzstan, Kazakhstan)
Features: Multi-script handling (Latin/Cyrillic/Arabic), script reform schedules,
          Turkic patronymic patterns, hyphenated names, country-specific variants.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from ...base import RegionRuleError, RegionSpec


class C1TurkicProcessor(RegionSpec):
    """
    Greater-Turkic region (C1).

    Handles Turkic naming conventions across multiple countries and scripts:
    - Turkey (TR): Latin script, Ottoman legacy names
    - Azerbaijan (AZ): Latin script (post-1991), Cyrillic legacy
    - Uzbekistan (UZ): Latin script reform (2023→), Cyrillic legacy
    - Turkmenistan (TM): Latin script reform (2019→), Cyrillic legacy
    - Kyrgyzstan (KG): Cyrillic script primary, Latin variants
    - Kazakhstan (KZ): Cyrillic primary, Latin reform (2023→2031)

    Features:
    - Script reform schedule tracking
    - Cross-script name variants
    - Turkic patronymic patterns (-oğlu, -qızı, -uulu, etc.)
    - Country-specific orthographic conventions
    """

    def __init__(self):
        super().__init__(
            code="C1",
            yaml_files=["c1_turkic.yaml"],
            scripts=["Latin", "Cyrillic", "Arabic"],
            mixed_scripts=True,  # Names can appear in multiple scripts
            canonical_order="Given Family",  # Most Turkic cultures use this order
            romanisation_standards=["BGN/PCGN", "ISO 9", "ALA-LC"],
        )

        # Script reform schedules (key feature of C1) — hardcoded defaults
        self.script_reforms = {
            "UZ": {"start": 2023, "status": "active", "from": "Cyrillic", "to": "Latin"},
            "TM": {"start": 2019, "status": "active", "from": "Cyrillic", "to": "Latin"},
            "KZ": {
                "start": 2023,
                "end": 2031,
                "status": "transitional",
                "from": "Cyrillic",
                "to": "Latin",
            },
            "AZ": {"start": 1991, "status": "completed", "from": "Cyrillic", "to": "Latin"},
            "TR": {"start": 1928, "status": "completed", "from": "Arabic", "to": "Latin"},
        }

        # Override from config/script_switch.yaml if available (v7 spec Rule 5)
        self._load_script_switch_config()

        # Latin characters used in Turkic languages
        self.turkic_latin_chars = {
            # Turkish
            "ç",
            "Ç",
            "ğ",
            "Ğ",
            "ı",
            "I",
            "İ",
            "i",
            "ö",
            "Ö",
            "ş",
            "Ş",
            "ü",
            "Ü",
            # Azerbaijani
            "ə",
            "Ə",
            # Uzbek
            "oʻ",
            "gʻ",
            "Oʻ",
            "Gʻ",
            """, """,  # Apostrophe variants
            # Turkmen
            "ä",
            "Ä",
            "ň",
            "Ň",
            "ý",
            "Ý",
            "ž",
            "Ž",
            # Kazakh/Kyrgyz Latin variants
            "ä",
            "ö",
            "ü",
            "ğ",
            "ń",
            "ß",
        }

        # Cyrillic characters used in Turkic languages
        self.turkic_cyrillic_chars = {
            # Standard Cyrillic
            "а",
            "б",
            "в",
            "г",
            "д",
            "е",
            "ё",
            "ж",
            "з",
            "и",
            "й",
            "к",
            "л",
            "м",
            "н",
            "о",
            "п",
            "р",
            "с",
            "т",
            "у",
            "ф",
            "х",
            "ц",
            "ч",
            "ш",
            "щ",
            "ъ",
            "ы",
            "ь",
            "э",
            "ю",
            "я",
            "А",
            "Б",
            "В",
            "Г",
            "Д",
            "Е",
            "Ё",
            "Ж",
            "З",
            "И",
            "Й",
            "К",
            "Л",
            "М",
            "Н",
            "О",
            "П",
            "Р",
            "С",
            "Т",
            "У",
            "Ф",
            "Х",
            "Ц",
            "Ч",
            "Ш",
            "Щ",
            "Ъ",
            "Ы",
            "Ь",
            "Э",
            "Ю",
            "Я",
            # Turkic-specific Cyrillic
            "ә",
            "Ә",
            "ғ",
            "Ғ",
            "қ",
            "Қ",
            "ң",
            "Ң",
            "ө",
            "Ө",
            "ұ",
            "Ұ",
            "ү",
            "Ү",
            "һ",
            "Һ",  # Kazakh
            "ө",
            "Ө",
            "ү",
            "Ү",
            "ң",
            "Ң",  # Kyrgyz
            "ҳ",
            "Ҳ",
            "ў",
            "Ў",
            "қ",
            "Қ",
            "ғ",
            "Ғ",
            "ҳ",
            "Ҳ",  # Uzbek
            "ә",
            "Ә",
            "җ",
            "Җ",
            "ң",
            "Ң",
            "ө",
            "Ө",
            "ү",
            "Ү",
            "һ",
            "Һ",
            "ы",
            "Ы",  # Turkmen
        }

        # Arabic characters (for historical/legacy names)
        self.turkic_arabic_chars = {
            "ا",
            "ب",
            "ت",
            "ث",
            "ج",
            "ح",
            "خ",
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
            "ع",
            "غ",
            "ف",
            "ق",
            "ك",
            "ل",
            "م",
            "ن",
            "ه",
            "و",
            "ي",
            "آ",
            "أ",
            "ؤ",
            "إ",
            "ئ",
            "ة",
            "ى",
        }

        self.allowed_chars = (
            self.turkic_latin_chars | self.turkic_cyrillic_chars | self.turkic_arabic_chars
        )

        # Turkic patronymic suffixes by country/language
        self.patronymic_suffixes = {
            # Turkish
            "oğlu": "son of",
            "kızı": "daughter of",
            # Azerbaijani
            "oğlu": "son of",
            "qızı": "daughter of",
            # Uzbek
            "o'g'li": "son of",
            "qizi": "daughter of",
            # Turkmen
            "ogly": "son of",
            "gyzy": "daughter of",
            # Kyrgyz
            "uulu": "son of",
            "kyzy": "daughter of",
            # Kazakh
            "ұлы": "son of",
            "қызы": "daughter of",
        }

        # Common Turkic given names (for pattern recognition)
        self.common_turkic_names = {
            # Turkish
            "Mehmet",
            "Ahmet",
            "Mustafa",
            "Ali",
            "Hasan",
            "Hüseyin",
            "İbrahim",
            "Osman",
            "Ayşe",
            "Fatma",
            "Emine",
            "Hatice",
            "Zeynep",
            "Şerife",
            "Meryem",
            # Azerbaijani
            "Əli",
            "Həsən",
            "Hüseyn",
            "Məhəmməd",
            "Rəşid",
            "Elçin",
            "Günel",
            "Leyla",
            "Sevil",
            "Aynur",
            "Nigar",
            # Central Asian
            "Bakyt",
            "Bolot",
            "Ermek",
            "Nursultan",
            "Aida",
            "Ainur",
            "Gulnara",
        }

        # Country-specific orthographic patterns
        self.country_patterns = {
            "TR": {"script": "Latin", "apostrophe": False, "case_sensitive": True},
            "AZ": {"script": "Latin", "apostrophe": False, "case_sensitive": True},
            "UZ": {"script": "Latin", "apostrophe": True, "case_sensitive": False},  # Uses oʻ, gʻ
            "TM": {"script": "Latin", "apostrophe": False, "case_sensitive": True},
            "KG": {"script": "Cyrillic", "apostrophe": False, "case_sensitive": True},
            "KZ": {"script": "Cyrillic", "apostrophe": False, "case_sensitive": True},
        }

        # Common titles (multilingual)
        self.titles = {
            # Turkish
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Doç",
            "Doç.",
            "Bay",
            "Bayan",
            "Sayın",
            # Azerbaijani
            "Cənab",
            "Xanım",
            # Central Asian
            "Господин",
            "Госпожа",  # Russian influence
        }

    def _load_script_switch_config(self):
        """Load script switch schedule from config/script_switch.yaml (v7 spec Rule 5)."""
        import pathlib

        config_path = pathlib.Path(__file__).resolve().parents[3] / "config" / "script_switch.yaml"
        if not config_path.exists():
            return
        try:
            import yaml

            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            # Map YAML entries to script_reforms format
            for _key, entry in data.items():
                if not isinstance(entry, dict):
                    continue
                cc = entry.get("country_code")
                if not cc:
                    continue
                reform = {}
                if "migration_start" in entry:
                    reform["start"] = entry["migration_start"]
                if "migration_complete" in entry:
                    reform["end"] = entry["migration_complete"]
                if "current_script" in entry:
                    reform["to"] = entry.get("target_script", entry["current_script"])
                    reform["from"] = entry.get("historical_script", entry.get("legacy_script", ""))
                # Determine status
                if reform.get("end") and reform["end"] <= 2025:
                    reform["status"] = "completed"
                elif reform.get("start") and reform.get("end"):
                    reform["status"] = "transitional"
                elif reform.get("start"):
                    reform["status"] = "active"
                if reform:
                    self.script_reforms[cc] = reform
        except Exception:
            pass  # Fall back to hardcoded defaults

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C1 rules."""
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

        # Remove titles
        name = self._remove_titles(name)

        # Normalize different apostrophe types (important for Uzbek)
        name = self._normalize_apostrophes(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove titles from beginning of name."""
        if not text:
            return text

        words = text.split()
        while words and words[0] in self.titles:
            words.pop(0)

        return " ".join(words)

    def _normalize_apostrophes(self, name: str) -> str:
        """Normalize apostrophe variants (critical for Uzbek names)."""
        # Uzbek uses specific apostrophe forms: oʻ, gʻ
        apostrophe_variants = {"'", "'", "'", "`", "ʼ"}

        # Replace all variants with the standard Unicode apostrophe
        for variant in apostrophe_variants:
            name = name.replace(variant, "'")

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C1-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Handle patronymic naming
        if components.get("is_patronymic"):
            entry["FamilyNameType"] = "patronymic"

        # Generate script variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Rule 5: Kazakh Script Switch – handle Cyrillic→Latin transition (2023-2031)
        if components.get("likely_country") == "KZ" or self._is_kazakh_name(canonical):
            kazakh_script_variants = self._generate_kazakh_script_transition_variants(
                canonical, components
            )
            for variant in kazakh_script_variants:
                if variant["str"] != canonical:
                    entry["Variants"]["Synthesised"].append(variant)

        # Add transliteration variants for different scripts
        transliterations = self._generate_script_variants(canonical, components)
        for variant in transliterations:
            entry["Variants"]["Synthesised"].append(variant)

        # Rule 6: Turkish İ/i ambiguity – generate proper capitalization variants
        if components.get("likely_country") == "TR" or self._has_turkish_chars(canonical):
            turkish_variants = self._generate_turkish_case_variants(canonical)
            for variant in turkish_variants:
                if variant["str"] != canonical:
                    entry["Variants"]["Synthesised"].append(variant)

        # Rule 20: Turkic -oğlu/-ogly – patronymic suffix handling
        if components.get("is_patronymic"):
            # Store detailed patronymic information for V7 compliance
            patronymic_info = self._extract_turkic_patronymic_details(canonical, components)
            if patronymic_info:
                entry["RegionalExtras"].update(patronymic_info)

            # Generate patronymic variants
            patronymic_variants = self._generate_patronymic_variants(canonical, components)
            for variant in patronymic_variants:
                entry["Variants"]["Synthesised"].append(variant)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Turkic-specific handling."""
        components = {}

        # Detect script
        script = self._detect_script(name)
        components["script"] = script

        # Parse name structure
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Most Turkic names use "Given Family" order
            words = name.split()
            if len(words) >= 2:
                given = " ".join(words[:-1])
                family = words[-1]
            else:
                given = ""
                family = name

        components["family_name"] = family
        components["given_name"] = given

        # Check for patronymic patterns
        if self._is_patronymic(family):
            components["is_patronymic"] = True
            # Extract root name and type
            for suffix, meaning in self.patronymic_suffixes.items():
                if family.endswith(suffix):
                    components["patronymic_root"] = family[: -len(suffix)]
                    components["patronymic_type"] = meaning
                    break

        # Detect country/language based on orthographic patterns
        country = self._detect_country(name, script)
        if country:
            components["likely_country"] = country
            components["script_reform_status"] = self.script_reforms.get(country, {}).get(
                "status", "stable"
            )

        return components

    def _detect_script(self, name: str) -> str:
        """Detect the primary script used in the name."""
        latin_count = sum(
            1
            for c in name
            if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            or c in self.turkic_latin_chars
        )
        cyrillic_count = sum(1 for c in name if c in self.turkic_cyrillic_chars)
        arabic_count = sum(1 for c in name if c in self.turkic_arabic_chars)

        if arabic_count > 0:
            return "Arabic"
        elif cyrillic_count > latin_count:
            return "Cyrillic"
        else:
            return "Latin"

    def _detect_country(self, name: str, script: str) -> Optional[str]:
        """Detect likely country based on orthographic patterns."""
        # Turkish-specific characters
        if any(c in name for c in "çğışöüÇĞIŞÖÜ"):
            return "TR"

        # Azerbaijani-specific
        if "ə" in name or "Ə" in name:
            return "AZ"

        # Uzbek apostrophes
        if "oʻ" in name or "gʻ" in name or "''" in name:
            return "UZ"

        # Turkmen-specific
        if any(c in name for c in "äňýžÄŇÝŽ"):
            return "TM"

        # Kazakh/Kyrgyz Cyrillic
        if script == "Cyrillic" and any(c in name for c in "әғқңөұүһ"):
            return "KZ"  # Could also be KG, but KZ is more common

        return None

    def _is_patronymic(self, name: str) -> bool:
        """Check if name follows patronymic pattern."""
        name_lower = name.lower()
        return any(name_lower.endswith(suffix) for suffix in self.patronymic_suffixes.keys())

    def _generate_script_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate transliteration variants between scripts."""
        variants = []
        current_script = components.get("script", "Latin")

        # For now, generate ASCII variant (most common need)
        if current_script in ["Cyrillic", "Arabic"]:
            ascii_name = self._transliterate_to_ascii(name, current_script)
            if ascii_name != name:
                variants.append({"str": ascii_name, "type": f"{current_script.lower()}-to-latin"})

        return variants

    def _transliterate_to_ascii(self, name: str, from_script: str) -> str:
        """Basic transliteration to ASCII/Latin."""
        if from_script == "Cyrillic":
            # BGN/PCGN Cyrillic transliteration (simplified)
            cyrillic_to_latin = {
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
                # Turkic-specific
                "ә": "a",
                "ғ": "gh",
                "қ": "q",
                "ң": "ng",
                "ө": "o",
                "ұ": "u",
                "ү": "u",
                "һ": "h",
            }

            result = ""
            for char in name:
                if char.lower() in cyrillic_to_latin:
                    transliterated = cyrillic_to_latin[char.lower()]
                    result += transliterated.capitalize() if char.isupper() else transliterated
                else:
                    result += char
            return result

        # For Arabic, use basic Unicode normalization
        return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")

    def _has_turkish_chars(self, name: str) -> bool:
        """Check if name contains Turkish-specific characters."""
        # Turkish-specific characters that indicate Turkish language
        turkish_chars = {"ç", "ğ", "ı", "İ", "ö", "ş", "ü", "Ç", "Ğ", "I", "Ö", "Ş", "Ü"}
        return any(c in turkish_chars for c in name)

    def _generate_turkish_case_variants(self, name: str) -> List[Dict[str, str]]:
        """
        Rule 6: Turkish İ/i ambiguity – generate proper Turkish capitalization variants.

        Turkish has unique capitalization rules:
        - i (dotted lowercase) ↔ İ (dotted uppercase)
        - ı (dotless lowercase) ↔ I (dotless uppercase)

        This is different from most languages where i → I.

        Examples:
        - "istanbul" → "İSTANBUL" (not "ISTANBUL")
        - "ılık" → "ILIK"
        - "İbrahim" → "ibrahim" or "IBRAHIM"

        This rule generates variants with proper Turkish capitalization to handle
        international systems that might not understand Turkish case rules.
        """
        variants = []

        # Generate uppercase variant with proper Turkish capitalization
        turkish_upper = self._turkish_upper(name)
        if turkish_upper != name:
            variants.append({"str": turkish_upper, "type": "turkish-uppercase"})

        # Generate lowercase variant with proper Turkish capitalization
        turkish_lower = self._turkish_lower(name)
        if turkish_lower != name:
            variants.append({"str": turkish_lower, "type": "turkish-lowercase"})

        # Generate "international" variants where Turkish i/İ/ı/I are normalized
        # This helps with systems that don't understand Turkish capitalization
        international_variant = self._normalize_turkish_case_for_international(name)
        if international_variant != name:
            variants.append({"str": international_variant, "type": "international-compatible"})

        return variants

    def _turkish_upper(self, name: str) -> str:
        """Convert to uppercase using Turkish capitalization rules."""
        # Turkish-specific uppercase conversions
        turkish_upper_map = {
            "i": "İ",  # dotted i → dotted I
            "ı": "I",  # dotless i → dotless I
            "ç": "Ç",
            "ğ": "Ğ",
            "ö": "Ö",
            "ş": "Ş",
            "ü": "Ü",
        }

        result = []
        for char in name:
            if char in turkish_upper_map:
                result.append(turkish_upper_map[char])
            else:
                result.append(char.upper())

        return "".join(result)

    def _turkish_lower(self, name: str) -> str:
        """Convert to lowercase using Turkish capitalization rules."""
        # Turkish-specific lowercase conversions
        turkish_lower_map = {
            "İ": "i",  # dotted I → dotted i
            "I": "ı",  # dotless I → dotless i
            "Ç": "ç",
            "Ğ": "ğ",
            "Ö": "ö",
            "Ş": "ş",
            "Ü": "ü",
        }

        result = []
        for char in name:
            if char in turkish_lower_map:
                result.append(turkish_lower_map[char])
            else:
                result.append(char.lower())

        return "".join(result)

    def _normalize_turkish_case_for_international(self, name: str) -> str:
        """
        Normalize Turkish i/İ/ı/I for international systems that don't understand Turkish rules.

        This creates variants that work better with ASCII-only systems:
        - İ/i → I/i (normalize to standard Latin)
        - I/ı → I/i (normalize dotless to dotted)
        """
        # Map Turkish characters to international equivalents
        international_map = {
            "İ": "I",  # Turkish dotted I → standard I
            "ı": "i",  # Turkish dotless i → standard i
            "I": "I",  # Turkish dotless I → standard I (no change)
            "i": "i",  # Turkish dotted i → standard i (no change)
        }

        result = []
        for char in name:
            result.append(international_map.get(char, char))

        return "".join(result)

    def _is_kazakh_name(self, name: str) -> bool:
        """Check if name contains Kazakh-specific characters or patterns."""
        # Kazakh-specific Cyrillic characters
        kazakh_cyrillic_chars = {
            "ә",
            "ғ",
            "қ",
            "ң",
            "ө",
            "ұ",
            "ү",
            "һ",
            "Ә",
            "Ғ",
            "Қ",
            "Ң",
            "Ө",
            "Ұ",
            "Ү",
            "Һ",
        }

        # Check for Kazakh-specific characters
        if any(c in kazakh_cyrillic_chars for c in name):
            return True

        # Check for Kazakh patronymic patterns
        if name.lower().endswith(("ұлы", "қызы")):
            return True

        # Check for common Kazakh name patterns
        kazakh_name_patterns = [
            "нұр",  # Nur- prefix common in Kazakh names
            "сұл",  # Sul- prefix
            "бақ",  # Baq- prefix
        ]

        name_lower = name.lower()
        return any(pattern in name_lower for pattern in kazakh_name_patterns)

    def _generate_kazakh_script_transition_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Rule 5: Kazakh Script Switch – generate variants for Cyrillic↔Latin transition.

        Kazakhstan is transitioning from Cyrillic to Latin script (2023-2031).
        During this transition period, names may appear in either script.

        This rule generates cross-script variants to handle:
        - Legacy Cyrillic names → new Latin equivalents
        - New Latin names → legacy Cyrillic equivalents
        - Transition period compatibility

        Official Kazakh Latin alphabet (2023):
        A a, Ä ä, B b, D d, E e, F f, G g, Ğ ğ, H h, I i, İ ı, J j, K k, L l, M m, N n, Ñ ñ, O o, Ö ö, P p, Q q, R r, S s, Ş ş, T t, U u, Ü ü, V v, W w, X x, Y y, Z z
        """
        variants = []
        current_script = components.get("script", "Latin")

        # Kazakh Cyrillic to Latin mapping (official 2023 standard)
        kazakh_cyrillic_to_latin = {
            # Standard Cyrillic → Latin
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "yo",
            "ж": "j",
            "з": "z",
            "и": "i",
            "й": "i",
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
            "х": "h",
            "ц": "ts",
            "ч": "ş",
            "ш": "ş",
            "щ": "şş",
            "ъ": "",
            "ы": "ı",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            # Kazakh-specific Cyrillic → Latin
            "ә": "ä",
            "ғ": "ğ",
            "қ": "q",
            "ң": "ñ",
            "ө": "ö",
            "ұ": "u",
            "ү": "ü",
            "һ": "h",
            # Uppercase
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "Yo",
            "Ж": "J",
            "З": "Z",
            "И": "I",
            "Й": "I",
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
            "Х": "H",
            "Ц": "Ts",
            "Ч": "Ş",
            "Ш": "Ş",
            "Щ": "Şş",
            "Ъ": "",
            "Ы": "I",
            "Ь": "",
            "Э": "E",
            "Ю": "Yu",
            "Я": "Ya",
            "Ә": "Ä",
            "Ғ": "Ğ",
            "Қ": "Q",
            "Ң": "Ñ",
            "Ө": "Ö",
            "Ұ": "U",
            "Ү": "Ü",
            "Һ": "H",
        }

        # Reverse mapping for Latin → Cyrillic
        kazakh_latin_to_cyrillic = {v: k for k, v in kazakh_cyrillic_to_latin.items() if v}

        # Additional Latin → Cyrillic mappings for ambiguous cases
        kazakh_latin_to_cyrillic.update(
            {
                "ä": "ә",
                "ğ": "ғ",
                "q": "қ",
                "ñ": "ң",
                "ö": "ө",
                "ü": "ү",
                "Ä": "Ә",
                "Ğ": "Ғ",
                "Q": "Қ",
                "Ñ": "Ң",
                "Ö": "Ө",
                "Ü": "Ү",
                "ı": "ы",
                "I": "Ы",  # Dotless i maps to Kazakh ы
            }
        )

        if current_script == "Cyrillic":
            # Generate Latin variant
            latin_variant = self._transliterate_kazakh_cyrillic_to_latin(
                name, kazakh_cyrillic_to_latin
            )
            if latin_variant != name:
                variants.append(
                    {
                        "str": latin_variant,
                        "type": "kazakh-script-transition-latin",
                        "transition_info": {
                            "from_script": "Cyrillic",
                            "to_script": "Latin",
                            "transition_period": "2023-2031",
                            "status": "official",
                        },
                    }
                )

        elif current_script == "Latin":
            # Generate Cyrillic variant (for backward compatibility)
            cyrillic_variant = self._transliterate_kazakh_latin_to_cyrillic(
                name, kazakh_latin_to_cyrillic
            )
            if cyrillic_variant != name:
                variants.append(
                    {
                        "str": cyrillic_variant,
                        "type": "kazakh-script-transition-cyrillic",
                        "transition_info": {
                            "from_script": "Latin",
                            "to_script": "Cyrillic",
                            "transition_period": "2023-2031",
                            "status": "legacy",
                        },
                    }
                )

        return variants

    def _transliterate_kazakh_cyrillic_to_latin(self, name: str, mapping: Dict[str, str]) -> str:
        """Transliterate Kazakh name from Cyrillic to Latin script."""
        result = []
        for char in name:
            if char in mapping:
                result.append(mapping[char])
            else:
                result.append(char)

        # Clean up double characters and normalize
        transliterated = "".join(result)
        transliterated = re.sub(r"şş", "ş", transliterated)  # Normalize double ş
        transliterated = re.sub(
            r"([A-ZÄÖÜĞÑŞİI])([a-zäöüğñşıi])", r"\1\2", transliterated
        )  # Fix case

        return transliterated

    def _transliterate_kazakh_latin_to_cyrillic(self, name: str, mapping: Dict[str, str]) -> str:
        """Transliterate Kazakh name from Latin to Cyrillic script."""
        result = []
        i = 0

        while i < len(name):
            # Check for multi-character sequences first
            if i < len(name) - 1:
                two_char = name[i : i + 2]
                if two_char.lower() in ["ts", "yu", "ya", "yo"]:
                    if two_char.lower() == "ts":
                        result.append("ц" if name[i].islower() else "Ц")
                    elif two_char.lower() == "yu":
                        result.append("ю" if name[i].islower() else "Ю")
                    elif two_char.lower() == "ya":
                        result.append("я" if name[i].islower() else "Я")
                    elif two_char.lower() == "yo":
                        result.append("ё" if name[i].islower() else "Ё")
                    i += 2
                    continue

            # Single character mapping
            char = name[i]
            if char in mapping:
                result.append(mapping[char])
            else:
                result.append(char)
            i += 1

        return "".join(result)

    def _extract_turkic_patronymic_details(
        self, name: str, components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rule 20: Turkic -oğlu/-ogly – extract detailed patronymic information.

        Turkic patronymic suffixes indicate lineage and should be:
        - Identified by country/language variant
        - Root name extracted and stored
        - Gender information inferred where possible
        - Alternative spellings tracked

        Common Turkic patronymic patterns:
        - Turkish: -oğlu (son of), -kızı (daughter of)
        - Azerbaijani: -oğlu (son of), -qızı (daughter of)
        - Uzbek: -o'g'li (son of), -qizi (daughter of)
        - Turkmen: -ogly (son of), -gyzy (daughter of)
        - Kyrgyz: -uulu (son of), -kyzy (daughter of)
        - Kazakh: -ұлы (son of), -қызы (daughter of)
        """
        patronymic_details = {}

        family_name = components.get("family_name", "")
        if not family_name:
            return patronymic_details

        # Enhanced patronymic suffix detection with regional variants
        turkic_patronymic_map = {
            # Turkish
            "oğlu": {
                "meaning": "son of",
                "gender": "masculine",
                "language": "Turkish",
                "country": "TR",
            },
            "kızı": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Turkish",
                "country": "TR",
            },
            # Azerbaijani (similar to Turkish but distinct)
            "qızı": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Azerbaijani",
                "country": "AZ",
            },
            # Uzbek (with apostrophes)
            "o'g'li": {
                "meaning": "son of",
                "gender": "masculine",
                "language": "Uzbek",
                "country": "UZ",
            },
            "qizi": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Uzbek",
                "country": "UZ",
            },
            # Turkmen
            "ogly": {
                "meaning": "son of",
                "gender": "masculine",
                "language": "Turkmen",
                "country": "TM",
            },
            "gyzy": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Turkmen",
                "country": "TM",
            },
            # Kyrgyz
            "uulu": {
                "meaning": "son of",
                "gender": "masculine",
                "language": "Kyrgyz",
                "country": "KG",
            },
            "kyzy": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Kyrgyz",
                "country": "KG",
            },
            # Kazakh (Cyrillic)
            "ұлы": {
                "meaning": "son of",
                "gender": "masculine",
                "language": "Kazakh",
                "country": "KZ",
            },
            "қызы": {
                "meaning": "daughter of",
                "gender": "feminine",
                "language": "Kazakh",
                "country": "KZ",
            },
        }

        # Find matching patronymic suffix
        suffix_info = None
        matched_suffix = None

        for suffix, info in turkic_patronymic_map.items():
            if family_name.lower().endswith(suffix.lower()):
                suffix_info = info
                matched_suffix = suffix
                break

        if suffix_info and matched_suffix:
            # Extract the root name (father's name)
            root_name = family_name[: -len(matched_suffix)].strip()
            if root_name:
                patronymic_details.update(
                    {
                        "turkic_patronymic_suffix": matched_suffix,
                        "turkic_patronymic_meaning": suffix_info["meaning"],
                        "turkic_patronymic_root": root_name,
                        "turkic_patronymic_gender": suffix_info["gender"],
                        "turkic_patronymic_language": suffix_info["language"],
                        "turkic_patronymic_country": suffix_info["country"],
                        "patronymic_type": "turkic",
                    }
                )

                # Generate alternative spellings/variants of the suffix
                alternatives = self._get_patronymic_alternatives(matched_suffix, suffix_info)
                if alternatives:
                    patronymic_details["turkic_patronymic_alternatives"] = alternatives

        return patronymic_details

    def _get_patronymic_alternatives(self, suffix: str, suffix_info: Dict[str, str]) -> List[str]:
        """Get alternative spellings of Turkic patronymic suffixes."""
        alternatives = []

        # Turkish oğlu alternatives
        if suffix == "oğlu":
            alternatives = ["oglu", "oghlu"]  # Common romanization variants

        # Uzbek alternatives (apostrophe variations)
        elif suffix == "o'g'li":
            alternatives = ["ogʻli", "og'li", "ogli"]  # Different apostrophe styles

        # Turkmen alternatives
        elif suffix == "ogly":
            alternatives = ["oğly"]  # With Turkish ğ

        # Add case variations
        if alternatives:
            case_variants = []
            for alt in alternatives:
                case_variants.extend([alt.lower(), alt.upper(), alt.capitalize()])
            alternatives.extend(case_variants)

        return list(set(alternatives))  # Remove duplicates

    def _generate_patronymic_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate patronymic variants (e.g., with/without suffix)."""
        variants = []

        if components.get("is_patronymic"):
            root = components.get("patronymic_root", "")
            given = components.get("given_name", "")

            if root and given:
                # Variant without patronymic suffix
                simple_form = f"{given} {root}"
                variants.append({"str": simple_form, "type": "patronymic-root"})

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to C1 rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        # Check for valid characters
        if not self._is_valid_turkic_name(canonical):
            invalid_chars = (
                set(canonical)
                - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-'")
                - self.allowed_chars
            )
            if invalid_chars:
                raise RegionRuleError(f"Invalid characters in name: {invalid_chars}")

        # Validate script consistency
        components = entry.get("RegionalExtras", {})
        script = components.get("script")

        if script == "Arabic" and not any(c in self.turkic_arabic_chars for c in canonical):
            raise RegionRuleError("Name marked as Arabic script but contains no Arabic characters")

        # Validate patronymic consistency
        if components.get("is_patronymic"):
            family = components.get("family_name", "")
            if not self._is_patronymic(family):
                raise RegionRuleError(f"Marked as patronymic but doesn't match pattern: {family}")

    def _is_valid_turkic_name(self, name: str) -> bool:
        """Check if name contains valid Turkic characters."""
        # Allow basic Latin, Turkic special characters, numbers, and common punctuation
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-'")
        allowed.update(self.allowed_chars)

        return all(c in allowed for c in name)

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Get family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Rule 20: For Turkic patronymics, sort by given name first (common in Central Asia)
        if components.get("is_patronymic"):
            # For patronymic names, prioritize given name for sorting
            # Remove patronymic suffix from family name for cleaner sorting
            if components.get("turkic_patronymic_root"):
                # Use the root name (father's name) without suffix for secondary sort
                patronymic_root = components["turkic_patronymic_root"]
                sort_key = f"{given} {patronymic_root}"
            else:
                sort_key = f"{given} {family}"
        else:
            # Standard family, given sorting
            sort_key = f"{family}, {given}"

        # Normalize for sorting (handle Turkic characters)
        sort_key = self._normalize_for_sorting(sort_key)

        # Ensure determinism
        return " ".join(sort_key.split()).upper()

    def _normalize_for_sorting(self, text: str) -> str:
        """Normalize text for sorting with Turkic rules."""
        # Turkish-specific sorting: ç, ğ, ı, İ, ö, ş, ü have special positions
        replacements = {
            "ç": "czz",
            "Ç": "CZZ",
            "ğ": "gzz",
            "Ğ": "GZZ",
            "ı": "izz",
            "I": "Izz",  # Turkish dotless i
            "İ": "I",
            "i": "i",  # Turkish dotted i
            "ö": "ozz",
            "Ö": "OZZ",
            "ş": "szz",
            "Ş": "SZZ",
            "ü": "uzz",
            "Ü": "UZZ",
            "ə": "azz",
            "Ə": "AZZ",  # Azerbaijani
        }

        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        # Remove punctuation for sorting
        result = re.sub(r"[^\w\s]", "", result)

        return result
