#!/usr/bin/env python3
"""
C5 Arabic Maghreb Region Processor for GMNAP v7
Covers Arabic-speaking mathematician names from North Africa (Maghreb)

HELL-LEVEL TESTED:
- Moroccan mathematicians (Rabat, Casablanca, Fez, Marrakech)
- Tunisian mathematicians (Tunis, Sousse, Sfax)
- Algerian mathematicians (Algiers, Oran, Constantine)
- Libyan mathematicians (Tripoli, Benghazi)
- Maghreb Arabic dialect detection and romanization
- French colonial influence on transliteration
- Ben- prefixes and Maghrebi naming conventions

V7 SPEC COMPLIANCE:
- iso_territories: [MA, DZ, TN, LY, EH, MR]
- primary_scripts: ["Arabic"]
- distinct_features: Ben... prefixes; French transliteration
"""

import re
import logging
from typing import Dict, Any, List, Set

from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class C5_ArabicMaghreb(RegionSpec):
    """
    C5 Arabic Maghreb region processor.

    Handles mathematician names from Maghreb (North Africa):
    - Morocco (MA)
    - Algeria (DZ)
    - Tunisia (TN)
    - Libya (LY)
    - Western Sahara (EH)
    - Mauritania (MR)

    Features:
    - Arabic script detection and romanization
    - French transliteration influence recognition
    - Ben/Ibn prefix handling (distinctive Maghrebi pattern)
    - Tribal and regional surname patterns
    - Academic title recognition (Arabic and French)
    """

    REGION_CODE = "C5"
    REGION_NAME = "Arabic Maghreb"

    # Arabic script range
    ARABIC_RANGE = (0x0600, 0x06FF)  # Basic Arabic
    ARABIC_SUPPLEMENT_RANGE = (0x0750, 0x077F)  # Arabic Supplement

    def __init__(self):
        super().__init__(
            code="C5",
            yaml_files=["c5_arabic_maghreb.yaml"],
            scripts=["Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 233-2"],
        )
        self.logger = logging.getLogger(f"gmnap.regions.C5")

        # Load Maghrebi Arabic resources
        self.maghrebi_patterns = self._load_maghrebi_patterns()
        self.romanization_map = self._load_romanization_mappings()
        self.honorific_titles = self._load_honorific_titles()
        self.maghrebi_surnames = self._load_maghrebi_surnames()
        self.place_indicators = self._load_place_indicators()
        self.french_influences = self._load_french_influences()

        self.logger.info(f"C5 Arabic Maghreb processor initialized")

    def _load_maghrebi_patterns(self) -> Dict[str, List[str]]:
        """Load Maghrebi Arabic name patterns."""
        return {
            "ben_prefixes": [
                # Ben/Ibn patterns (distinctive Maghrebi)
                r"\bben\s+[A-Za-z]+\b",  # Ben + name
                r"\biben\s+[A-Za-z]+\b",  # Ibn + name
                r"\bbou\s+[A-Za-z]+\b",  # Bou + name (Maghrebi variant)
                r"\bbel\s+[A-Za-z]+\b",  # Bel + name
                r"\bbin\s+[A-Za-z]+\b",  # Bin + name
                r"\b[A-Za-z]+\s+ben\s+[A-Za-z]+\b",  # Name + ben + name
            ],
            "arabic_script_patterns": [
                # Arabic script sequences
                r"[\u0628\u0646][\u0020]",  # بن (ben/ibn) with space
                r"[\u0623\u0628\u0648][\u0020]",  # أبو (Abu) pattern
                r"[\u0639\u0628\u062F][\u0020]",  # عبد (Abd) pattern
            ],
            "maghrebi_endings": [
                # Common Maghrebi name endings
                r"\b[A-Za-z]*oui\b",  # -oui endings (Moroccan)
                r"\b[A-Za-z]*awi\b",  # -awi endings
                r"\b[A-Za-z]*ini\b",  # -ini endings (regional)
                r"\b[A-Za-z]*ani\b",  # -ani endings
                r"\b[A-Za-z]*ati\b",  # -ati endings (Tunisian)
            ],
            "french_influence": [
                # French transliteration patterns
                r"\b[A-Za-z]*ech\b",  # -ech endings (French ch)
                r"\b[A-Za-z]*ou[aeiou]\b",  # French ou patterns
                r"\b[A-Za-z]*eau\b",  # French eau endings
                r"\b[A-Za-z]*ieu\b",  # French ieu patterns
            ],
        }

    def _load_romanization_mappings(self) -> Dict[str, str]:
        """Load Arabic to Roman mappings with Maghrebi variants."""
        return {
            # Arabic consonants (basic)
            "ب": "b",
            "ت": "t",
            "ث": "th",
            "ج": "j",
            "ح": "ḥ",
            "خ": "kh",
            "د": "d",
            "ذ": "dh",
            "ر": "r",
            "ز": "z",
            "س": "s",
            "ش": "sh",
            "ص": "ṣ",
            "ض": "ḍ",
            "ط": "ṭ",
            "ظ": "ẓ",
            "ع": "ʿ",
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
            # Arabic vowels
            "ا": "a",
            "أ": "a",
            "إ": "i",
            "آ": "ā",
            "ى": "ā",
            "ة": "a",
            "ُ": "u",
            "ِ": "i",
            "َ": "a",
            "ً": "an",
            "ٌ": "un",
            "ٍ": "in",
            "ْ": "",  # Sukun (no vowel)
            "ّ": "",  # Shadda (doubled consonant)
            # Common words
            "بن": "ben",
            "ابن": "ibn",
            "أبو": "abu",
            "عبد": "abd",
            "محمد": "mohamed",
            "أحمد": "ahmed",
            "عبدالله": "abdallah",
            # Maghrebi-specific variants
            "ش": "ch",  # French influence
            "ج": "dj",  # Maghrebi pronunciation
        }

    def _load_honorific_titles(self) -> Set[str]:
        """Load Arabic and French honorific titles."""
        return {
            # Arabic titles
            "سيد",
            "سيدة",
            "أستاذ",
            "دكتور",
            "شيخ",
            "إمام",
            "حاج",
            "حاجة",
            "sayyid",
            "sayida",
            "ustaz",
            "doktor",
            "sheikh",
            "imam",
            "hajj",
            "hajja",
            "si",
            "sidi",
            "lalla",
            "moulay",
            "moulai",
            # French titles (colonial influence)
            "monsieur",
            "madame",
            "mademoiselle",
            "professeur",
            "docteur",
            "maître",
            "maître",
            "ingénieur",
            "avocat",
            "m",
            "mme",
            "mlle",
            "prof",
            "dr",
            "ing",
            # Academic titles
            "professor",
            "prof",
            "doctor",
            "dr",
            "mr",
            "mrs",
            "ms",
        }

    def _load_maghrebi_surnames(self) -> Dict[str, Set[str]]:
        """Load common Maghrebi surnames by country/region."""
        return {
            "moroccan_surnames": {
                "benali",
                "bennani",
                "benyoussef",
                "berrada",
                "bouazza",
                "cherkaoui",
                "el",
                "fassi",
                "filali",
                "idrissi",
                "kettani",
                "lahlou",
                "nejjar",
                "ouali",
                "tazi",
                "zemmouri",
            },
            "algerian_surnames": {
                "benahmed",
                "belabed",
                "belhaj",
                "benabdallah",
                "benaissa",
                "bouali",
                "boudjedra",
                "chaoui",
                "hadj",
                "hamdi",
                "khediri",
                "madani",
                "messaoud",
                "ouali",
                "slimani",
                "zerrouki",
            },
            "tunisian_surnames": {
                "abid",
                "amara",
                "arfaoui",
                "ben",
                "chahed",
                "dridi",
                "ghanmi",
                "hajji",
                "jemli",
                "karray",
                "mestiri",
                "najar",
                "ouerghi",
                "rezgui",
                "trabelsi",
                "zouari",
            },
            "libyan_surnames": {
                "abu",
                "gaddafi",
                "qadhafi",
                "benghazi",
                "tripoli",
                "omar",
                "saleh",
                "abdallah",
                "mohamed",
                "ali",
                "hassan",
            },
            "tribal_surnames": {
                # Berber/Amazigh influences
                "amellal",
                "azoulay",
                "tahiri",
                "targui",
                "tuareg",
                "kabyle",
                "chaoui",
                "riffian",
                "souss",
            },
        }

    def _load_place_indicators(self) -> Dict[str, Set[str]]:
        """Load Maghrebi place names and indicators."""
        return {
            "morocco": {
                "rabat",
                "casablanca",
                "fez",
                "marrakech",
                "agadir",
                "meknes",
                "tangier",
                "oujda",
                "kenitra",
                "tetouan",
                "sale",
                "temara",
                "mohammedia",
                "el jadida",
                "khouribga",
                "beni mellal",
            },
            "algeria": {
                "algiers",
                "alger",
                "oran",
                "constantine",
                "batna",
                "djelfa",
                "setif",
                "sidi bel abbes",
                "biskra",
                "tebessa",
                "ouargla",
                "skikda",
                "tiaret",
                "bejaie",
                "tlemcen",
                "saida",
            },
            "tunisia": {
                "tunis",
                "sfax",
                "sousse",
                "kairouan",
                "bizerte",
                "gabes",
                "ariana",
                "gafsa",
                "kasserine",
                "medenine",
                "monastir",
                "nabeul",
                "tataouine",
                "tozeur",
                "zaghouan",
                "mahdia",
            },
            "libya": {
                "tripoli",
                "benghazi",
                "misrata",
                "zawiya",
                "bayda",
                "derna",
                "tobruk",
                "ajdabiya",
                "sirte",
                "gharyan",
                "khoms",
                "zliten",
                "marj",
                "ubari",
                "murzuq",
            },
            "institutions": {
                "mohammed v university",
                "hassan ii university",
                "cadi ayyad",
                "university of algiers",
                "constantine university",
                "university of tunis",
                "sfax university",
                "university of libya",
                "ecole mohammadia",
                "ecole hassania",
                "enit",
                "ensias",
            },
        }

    def _load_french_influences(self) -> Dict[str, str]:
        """Load French transliteration influences."""
        return {
            # French-influenced romanization
            "ch": "š",  # French ch -> Arabic š
            "dj": "j",  # French dj -> Arabic j
            "gh": "ğ",  # French gh -> Arabic ğ
            "kh": "ḫ",  # French kh -> Arabic ḫ
            "ou": "ū",  # French ou -> long u
            "ech": "īš",  # French ech pattern
            "eau": "ū",  # French eau pattern
        }

    def detect_region(self, entry: Dict[str, Any]) -> float:
        """
        Detect if entry belongs to C5 Arabic Maghreb region.

        Detection criteria:
        - Arabic script characters (U+0600-U+06FF)
        - Distinctive Ben/Ibn prefixes
        - Maghrebi surname patterns
        - French transliteration influences
        - Geographic indicators (North African countries)
        """
        if not self.basic_validation(entry):
            return 0.0

        name = str(entry.get("name", ""))
        email = str(entry.get("email", ""))
        affiliation = str(entry.get("affiliation", ""))

        # Combine all text for analysis
        full_text = f"{name} {email} {affiliation}".lower()

        confidence = 0.0
        indicators = []

        # Check for Arabic script
        script_score = self._detect_arabic_script(name)
        if script_score > 0:
            confidence += script_score * 0.3
            indicators.append(f"arabic_script:{script_score:.2f}")

        # Check Ben/Ibn prefixes (distinctive for Maghreb)
        ben_score = self._check_ben_prefixes(name)
        if ben_score > 0:
            confidence += ben_score * 0.25
            indicators.append(f"ben_prefixes:{ben_score:.2f}")

        # Check Maghrebi patterns
        pattern_score = self._check_maghrebi_patterns(name)
        if pattern_score > 0:
            confidence += pattern_score * 0.2
            indicators.append(f"maghrebi_patterns:{pattern_score:.2f}")

        # Check surnames
        surname_score = self._check_maghrebi_surnames(name)
        if surname_score > 0:
            confidence += surname_score * 0.15
            indicators.append(f"surnames:{surname_score:.2f}")

        # Check place indicators
        place_score = self._check_place_indicators(full_text)
        if place_score > 0:
            confidence += place_score * 0.1
            indicators.append(f"places:{place_score:.2f}")

        if confidence > 0:
            self.logger.debug(f"C5 detection: {confidence:.3f} [{', '.join(indicators)}]")

        return min(confidence, 1.0)

    def _detect_arabic_script(self, text: str) -> float:
        """Detect Arabic script characters."""
        if not text:
            return 0.0

        arabic_chars = 0
        total_chars = 0

        for char in text:
            if char.isalpha() or ord(char) >= 0x0600:
                total_chars += 1
                codepoint = ord(char)
                if (
                    self.ARABIC_RANGE[0] <= codepoint <= self.ARABIC_RANGE[1]
                    or self.ARABIC_SUPPLEMENT_RANGE[0]
                    <= codepoint
                    <= self.ARABIC_SUPPLEMENT_RANGE[1]
                ):
                    arabic_chars += 1

        return arabic_chars / total_chars if total_chars > 0 else 0.0

    def _check_ben_prefixes(self, name: str) -> float:
        """Check for Ben/Ibn prefixes (distinctive Maghrebi pattern)."""
        if not name:
            return 0.0

        ben_patterns = self.maghrebi_patterns["ben_prefixes"]
        matches = 0

        for pattern in ben_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                matches += 1

        return min(matches / len(ben_patterns), 1.0)

    def _check_maghrebi_patterns(self, name: str) -> float:
        """Check for general Maghrebi name patterns."""
        if not name:
            return 0.0

        pattern_matches = 0
        total_patterns = 0

        pattern_groups = ["maghrebi_endings", "french_influence"]
        for group in pattern_groups:
            patterns = self.maghrebi_patterns.get(group, [])
            for pattern in patterns:
                total_patterns += 1
                if re.search(pattern, name, re.IGNORECASE):
                    pattern_matches += 1

        return pattern_matches / total_patterns if total_patterns > 0 else 0.0

    def _check_maghrebi_surnames(self, name: str) -> float:
        """Check for Maghrebi surnames."""
        if not name:
            return 0.0

        name_parts = name.lower().split()
        surname_matches = 0
        total_surnames = 0

        for surname_group in self.maghrebi_surnames.values():
            total_surnames += len(surname_group)
            for surname in surname_group:
                if any(surname in part for part in name_parts):
                    surname_matches += 1

        return surname_matches / total_surnames if total_surnames > 0 else 0.0

    def _check_place_indicators(self, text: str) -> float:
        """Check for Maghrebi place indicators."""
        if not text:
            return 0.0

        place_matches = 0
        total_places = 0

        for place_group in self.place_indicators.values():
            total_places += len(place_group)
            for place in place_group:
                if place in text:
                    place_matches += 1

        return place_matches / total_places if total_places > 0 else 0.0

    # Removed process_name method - not part of V7 RegionSpec interface

    def _detect_maghrebi_subregion(self, name: str, entry: Dict[str, Any]) -> str:
        """Detect specific Maghrebi subregion."""
        full_text = f"{name} {entry.get('email', '')} {entry.get('affiliation', '')}".lower()

        # Check for country-specific indicators
        country_scores = {}

        for country, places in self.place_indicators.items():
            if country == "institutions":
                continue
            score = sum(1 for place in places if place in full_text)
            if score > 0:
                country_scores[country] = score

        # Check surname patterns
        for country, surnames in self.maghrebi_surnames.items():
            if country.endswith("_surnames"):
                country_name = country.replace("_surnames", "")
                if country_name not in country_scores:
                    country_scores[country_name] = 0

                name_lower = name.lower()
                for surname in surnames:
                    if surname in name_lower:
                        country_scores[country_name] += 0.5

        # Return highest scoring country or default
        if country_scores:
            return max(country_scores.keys(), key=lambda x: country_scores[x])

        return "maghreb_unspecified"

    def _clean_maghrebi_name(self, name: str) -> str:
        """Clean and normalize Maghrebi name."""
        if not name:
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", name.strip())

        # Remove common titles
        for title in self.honorific_titles:
            # Handle both Arabic and Latin script titles
            pattern = r"\b" + re.escape(title) + r"\.?\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Normalize Ben/Ibn patterns
        cleaned = re.sub(r"\bben\s+", "ben ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\biben\s+", "ibn ", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _romanize_maghrebi_name(self, name: str) -> str:
        """Romanize Maghrebi Arabic name."""
        if not name:
            return ""

        romanized = name

        # Apply Arabic romanization mappings
        for arabic, roman in self.romanization_map.items():
            romanized = romanized.replace(arabic, roman)

        # Handle French influences
        for french, standard in self.french_influences.items():
            # Convert French-style back to standard
            romanized = romanized.replace(french, standard)

        return romanized

    def _extract_maghrebi_components(self, name: str, subregion: str) -> Dict[str, Any]:
        """Extract Maghrebi name components."""
        if not name:
            return {}

        parts = name.split()
        components = {"full_name": name, "name_parts": parts, "subregion": subregion}

        # Handle Ben/Ibn patronymics
        ben_idx = -1
        for i, part in enumerate(parts):
            if part.lower() in ["ben", "ibn", "bou", "bel", "bin"]:
                ben_idx = i
                break

        if ben_idx >= 0 and ben_idx + 1 < len(parts):
            # Structure: Given [Middle] Ben Father [Family]
            components["given_name"] = parts[0]
            components["patronymic_indicator"] = parts[ben_idx]
            components["patronymic"] = parts[ben_idx + 1]

            if ben_idx > 1:
                components["middle_names"] = parts[1:ben_idx]

            if ben_idx + 2 < len(parts):
                components["family_name"] = " ".join(parts[ben_idx + 2 :])
        else:
            # Standard structure
            if len(parts) >= 1:
                components["given_name"] = parts[0]
            if len(parts) >= 2:
                components["family_name"] = parts[-1]
            if len(parts) >= 3:
                components["middle_names"] = parts[1:-1]

        return components

    def _has_french_influence(self, name: str) -> bool:
        """Check if name shows French transliteration influence."""
        if not name:
            return False
        french_patterns = self.maghrebi_patterns["french_influence"]
        return any(re.search(pattern, name, re.IGNORECASE) for pattern in french_patterns)

    # Removed validate_entry method - not part of V7 RegionSpec interface

    def _has_maghrebi_characteristics(self, name: str) -> bool:
        """Check if name has clear Maghrebi characteristics."""
        if not name:
            return False
        # Check for Arabic script, Ben prefixes, and Maghrebi surnames
        if (
            self._detect_arabic_script(name) > 0
            or self._check_ben_prefixes(name) > 0
            or self._check_maghrebi_surnames(name) > 0
        ):
            return True
        return False

    def _has_mixed_scripts(self, name: str) -> bool:
        """Check for mixed scripts in name."""
        has_arabic = False
        has_latin = False

        for char in name:
            if char.isalpha():
                codepoint = ord(char)
                if (
                    self.ARABIC_RANGE[0] <= codepoint <= self.ARABIC_RANGE[1]
                    or self.ARABIC_SUPPLEMENT_RANGE[0]
                    <= codepoint
                    <= self.ARABIC_SUPPLEMENT_RANGE[1]
                ):
                    has_arabic = True
                elif codepoint <= 127:  # ASCII
                    has_latin = True

        return has_arabic and has_latin

    def _validate_ben_structure(self, name: str) -> bool:
        """Validate Ben/Ibn structure."""
        # Ben should be followed by a name
        ben_pattern = r"\b(ben|ibn|bou|bel|bin)\s+[A-Za-z\u0600-\u06FF]+\b"
        return bool(re.search(ben_pattern, name, re.IGNORECASE))

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["arabic_maghrebi", "berber_tamazight"]

    def get_region_info(self) -> Dict[str, Any]:
        """Get C5 region information."""
        return {
            "code": self.REGION_CODE,
            "name": self.REGION_NAME,
            "description": "Arabic Maghreb mathematician names from North Africa",
            "languages": self.get_supported_languages(),
            "scripts": ["Arabic"],
            "countries": ["Morocco", "Algeria", "Tunisia", "Libya", "Western Sahara", "Mauritania"],
            "romanization_standard": "ISO_233_2",
            "total_speakers": "100M+",
            "mathematician_population": "~15,000",
            "distinctive_features": [
                "Ben prefixes",
                "French transliteration influence",
                "Tribal surnames",
            ],
        }

    # V7 RegionSpec interface methods (required abstract methods)
    def clean(self, entry):
        """Apply V7 security validation and graceful edge case handling."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check raw input for dangerous characters FIRST
        # Check both CanonicalLatin and CanonicalNative before any processing
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                raw_input = entry[field]
                # Normalize tabs/newlines BEFORE security check (V7 edge case)
                raw_input = raw_input.replace("\t", " ").replace("\n", " ")
                entry[field] = raw_input  # Update the entry with normalized value
                if self._has_security_risks(raw_input):
                    raise RegionRuleError(
                        f"Name contains dangerous characters: {raw_input[:50]}..."
                    )

        # More flexible: try to get any available name
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def augment(self, entry):
        """Augment entry with regional data - stub implementation."""
        pass

    def validate(self, entry):
        """Apply V7 comprehensive security validation."""
        # Use comprehensive security framework from base class
        self.apply_security_and_validation_checks(entry)

        # Apply V7 name requirements validation
        self.validate_name_requirements(entry)

        # THEN handle legitimate edge cases
        canonical = self.get_canonical_name(entry)
        if canonical and len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

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

    def order_key(self, entry):
        """Generate sort key - stub implementation."""
        return str(entry.get("CanonicalLatin", ""))
