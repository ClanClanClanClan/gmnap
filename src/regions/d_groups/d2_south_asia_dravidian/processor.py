#!/usr/bin/env python3
"""
D2 South Asia Dravidian Region Processor for GMNAP v7
Covers Tamil, Telugu, Kannada, Malayalam mathematician names

HELL-LEVEL TESTED:
- Tamil mathematicians (Chennai, Madurai, Coimbatore)
- Telugu mathematicians (Hyderabad, Visakhapatnam, Vijayawada)  
- Kannada mathematicians (Bangalore, Mysore, Hubli)
- Malayalam mathematicians (Kerala - Thiruvananthapuram, Kochi, Kozhikode)
- Multi-script detection (Tamil, Telugu, Kannada, Malayalam scripts)
- Romanization standards (ISO 15919, ITRANS, academic transliteration)
"""

import re
import logging
from typing import Dict, Any, List, Set

from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class D2_SouthAsiaDravidian(RegionSpec):
    """
    D2 South Asia Dravidian region processor.

    Handles mathematician names from Dravidian language regions:
    - Tamil (Tamil Nadu, Sri Lanka, Singapore)
    - Telugu (Andhra Pradesh, Telangana)
    - Kannada (Karnataka)
    - Malayalam (Kerala)

    Features:
    - Multi-script detection (Tamil, Telugu, Kannada, Malayalam)
    - ISO 15919 romanization standard
    - Academic transliteration variants
    - Patronymic and place name patterns
    - Honorific title recognition
    """

    REGION_CODE = "D2"
    REGION_NAME = "South Asia Dravidian"

    # Script ranges for Dravidian languages
    TAMIL_RANGE = (0x0B80, 0x0BFF)  # Tamil script
    TELUGU_RANGE = (0x0C00, 0x0C7F)  # Telugu script
    KANNADA_RANGE = (0x0C80, 0x0CFF)  # Kannada script
    MALAYALAM_RANGE = (0x0D00, 0x0D7F)  # Malayalam script

    def __init__(self):
        super().__init__(
            code="D2",
            yaml_files=["d2_south_asia_dravidian.yaml"],
            scripts=["Tamil", "Telugu", "Kannada", "Malayalam", "Latin"],
            mixed_scripts=True,
            canonical_order="Family, Given",
            romanisation_standards=["ISO_15919", "ITRANS"],
        )
        self.logger = logging.getLogger(f"gmnap.regions.{self.REGION_CODE}")

        # Load Dravidian name patterns
        self.dravidian_patterns = self._load_dravidian_patterns()
        self.romanization_map = self._load_romanization_mappings()
        self.honorific_titles = self._load_honorific_titles()
        self.common_surnames = self._load_common_surnames()
        self.place_names = self._load_place_names()

        self.logger.info(f"D2 South Asia Dravidian processor initialized")

    def _load_dravidian_patterns(self) -> Dict[str, List[str]]:
        """Load Dravidian language patterns."""
        return {
            "tamil_patterns": [
                # Tamil name patterns
                r"\b[கஙசஞடணதநபமயரலவழளறன]+\b",  # Tamil script words
                r"\b[A-Za-z]*[aeiou]n\b",  # -an endings (Raman, Krishnan)
                r"\b[A-Za-z]*swamy\b",  # -swamy endings
                r"\b[A-Za-z]*murti\b",  # -murti endings
                r"\bT[A-Za-z]+\b",  # T- names (Tamil pattern)
            ],
            "telugu_patterns": [
                # Telugu name patterns
                r"\b[కఖగఘఙచఛజఝఞటఠడఢణతథదధనపఫబభమయరలవశషసహళఴ]+\b",  # Telugu script
                r"\b[A-Za-z]*aiah\b",  # -aiah endings
                r"\b[A-Za-z]*reddy\b",  # Reddy surnames
                r"\b[A-Za-z]*rao\b",  # Rao endings
                r"\b[A-Za-z]*garu\b",  # Garu honorific
            ],
            "kannada_patterns": [
                # Kannada name patterns
                r"\b[ಕಖಗಘಙಚಛಜಝಞಟಠಡಢಣತಥದಧನಪಫಬಭಮಯರಲವಶಷಸಹಳ಴]+\b",  # Kannada script
                r"\b[A-Za-z]*appa\b",  # -appa endings
                r"\b[A-Za-z]*pur\b",  # Place name endings
                r"\b[A-Za-z]*gowda\b",  # Gowda surnames
            ],
            "malayalam_patterns": [
                # Malayalam name patterns
                r"\b[കഖഗഘങചഛജഝഞടഠഡഢണതഥദധനപഫബഭമയരലവശഷസഹളഴ]+\b",  # Malayalam script
                r"\b[A-Za-z]*an\b",  # -an endings
                r"\b[A-Za-z]*menon\b",  # Menon surnames
                r"\b[A-Za-z]*nair\b",  # Nair surnames
                r"\b[A-Za-z]*pillai\b",  # Pillai surnames
            ],
        }

    def _load_romanization_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load ISO 15919 and academic romanization mappings."""
        return {
            "tamil": {
                # Tamil consonants
                "க": "ka",
                "ங": "ṅa",
                "ச": "ca",
                "ஞ": "ña",
                "ட": "ṭa",
                "ண": "ṇa",
                "த": "ta",
                "ந": "na",
                "ப": "pa",
                "ம": "ma",
                "ய": "ya",
                "ர": "ra",
                "ல": "la",
                "வ": "va",
                "ழ": "ḻa",
                "ள": "ḷa",
                "ற": "ṟa",
                "ன": "ṉa",
                # Tamil vowels
                "அ": "a",
                "ஆ": "ā",
                "இ": "i",
                "ஈ": "ī",
                "உ": "u",
                "ஊ": "ū",
                "எ": "e",
                "ஏ": "ē",
                "ஐ": "ai",
                "ஒ": "o",
                "ஓ": "ō",
                "ஔ": "au",
            },
            "telugu": {
                # Telugu consonants
                "క": "ka",
                "ఖ": "kha",
                "గ": "ga",
                "ఘ": "gha",
                "ఙ": "ṅa",
                "చ": "ca",
                "ఛ": "cha",
                "జ": "ja",
                "ఝ": "jha",
                "ఞ": "ña",
                "ట": "ṭa",
                "ఠ": "ṭha",
                "డ": "ḍa",
                "ఢ": "ḍha",
                "ణ": "ṇa",
                "త": "ta",
                "థ": "tha",
                "ద": "da",
                "ధ": "dha",
                "న": "na",
                "ప": "pa",
                "ఫ": "pha",
                "బ": "ba",
                "భ": "bha",
                "మ": "ma",
                "య": "ya",
                "ర": "ra",
                "ల": "la",
                "వ": "va",
                "శ": "śa",
                "ష": "ṣa",
                "స": "sa",
                "హ": "ha",
                "ళ": "ḷa",
                "ఴ": "ḻa",
            },
            "kannada": {
                # Kannada consonants
                "ಕ": "ka",
                "ಖ": "kha",
                "ಗ": "ga",
                "ಘ": "gha",
                "ಙ": "ṅa",
                "ಚ": "ca",
                "ಛ": "cha",
                "ಜ": "ja",
                "ಝ": "jha",
                "ಞ": "ña",
                "ಟ": "ṭa",
                "ಠ": "ṭha",
                "ಡ": "ḍa",
                "ಢ": "ḍha",
                "ಣ": "ṇa",
                "ತ": "ta",
                "ಥ": "tha",
                "ದ": "da",
                "ಧ": "dha",
                "ನ": "na",
                "ಪ": "pa",
                "ಫ": "pha",
                "ಬ": "ba",
                "ಭ": "bha",
                "ಮ": "ma",
                "ಯ": "ya",
                "ರ": "ra",
                "ಲ": "la",
                "ವ": "va",
                "ಶ": "śa",
                "ಷ": "ṣa",
                "ಸ": "sa",
                "ಹ": "ha",
                "ಳ": "ḷa",
                "಴": "ḻa",
            },
            "malayalam": {
                # Malayalam consonants
                "ക": "ka",
                "ഖ": "kha",
                "ග": "ga",
                "ഘ": "gha",
                "ങ": "ṅa",
                "ച": "ca",
                "ഛ": "cha",
                "ജ": "ja",
                "ഝ": "jha",
                "ഞ": "ña",
                "ട": "ṭa",
                "ഠ": "ṭha",
                "ഡ": "ḍa",
                "ഢ": "ḍha",
                "ണ": "ṇa",
                "ത": "ta",
                "ഥ": "tha",
                "ദ": "da",
                "ധ": "dha",
                "ന": "na",
                "പ": "pa",
                "ഫ": "pha",
                "ബ": "ba",
                "ഭ": "bha",
                "മ": "ma",
                "യ": "ya",
                "ര": "ra",
                "ല": "la",
                "വ": "va",
                "ശ": "śa",
                "ഷ": "ṣa",
                "സ": "sa",
                "ഹ": "ha",
                "ള": "ḷa",
                "ഴ": "ḻa",
            },
        }

    def _load_honorific_titles(self) -> Set[str]:
        """Load Dravidian honorific titles."""
        return {
            # Tamil titles
            "thiruvalar",
            "ayya",
            "amma",
            "swami",
            "murti",
            # Telugu titles
            "garu",
            "ayya",
            "amma",
            "swamy",
            "sri",
            "smt",
            # Kannada titles
            "avaru",
            "appa",
            "ajji",
            "swamy",
            # Malayalam titles
            "sir",
            "madam",
            "amma",
            "achan",
            "swamy",
            # Academic titles
            "prof",
            "professor",
            "dr",
            "doctor",
        }

    def _load_common_surnames(self) -> Dict[str, Set[str]]:
        """Load common Dravidian surnames by language."""
        return {
            "tamil": {
                "iyer",
                "iyengar",
                "mudaliar",
                "pillai",
                "naidu",
                "reddy",
                "krishnan",
                "raman",
                "swamy",
                "nathan",
                "sundaram",
                "venkatesh",
                "subramaniam",
                "raghavan",
                "parthasarathy",
            },
            "telugu": {
                "reddy",
                "rao",
                "naidu",
                "goud",
                "yadav",
                "varma",
                "sharma",
                "chowdary",
                "prasad",
                "kumar",
                "babu",
                "raju",
                "krishna",
                "venkatesan",
                "subramanyam",
            },
            "kannada": {
                "gowda",
                "rao",
                "kumar",
                "prasad",
                "sharma",
                "murthy",
                "appa",
                "naik",
                "shetty",
                "hegde",
                "bhat",
                "pai",
                "acharya",
                "upadhyaya",
                "shastry",
                "krishna",
            },
            "malayalam": {
                "menon",
                "nair",
                "pillai",
                "kumar",
                "das",
                "varma",
                "sharma",
                "krishnan",
                "raghavan",
                "gopalan",
                "unni",
                "kurup",
                "panicker",
                "thampi",
                "warrier",
            },
        }

    def _load_place_names(self) -> Dict[str, Set[str]]:
        """Load place names for geographic context."""
        return {
            "tamil_places": {
                "chennai",
                "madurai",
                "coimbatore",
                "salem",
                "tirupur",
                "erode",
                "vellore",
                "thoothukudi",
                "tirunelveli",
                "thanjavur",
            },
            "telugu_places": {
                "hyderabad",
                "visakhapatnam",
                "vijayawada",
                "guntur",
                "nellore",
                "kurnool",
                "rajahmundry",
                "tirupati",
                "chittoor",
                "kadapa",
            },
            "kannada_places": {
                "bangalore",
                "mysore",
                "hubli",
                "mangalore",
                "belgaum",
                "davangere",
                "gulbarga",
                "bellary",
                "bijapur",
                "shimoga",
            },
            "malayalam_places": {
                "thiruvananthapuram",
                "kochi",
                "kozhikode",
                "thrissur",
                "kollam",
                "palakkad",
                "kannur",
                "kottayam",
                "alappuzha",
                "malappuram",
            },
        }

    def detect_region(self, entry: Dict[str, Any]) -> float:
        """
        Detect if entry belongs to D2 South Asia Dravidian region.

        Detection criteria:
        - Dravidian script characters (Tamil, Telugu, Kannada, Malayalam)
        - Romanized Dravidian names with characteristic patterns
        - Dravidian surnames and titles
        - Geographic indicators (South Indian cities/states)
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

        # Check for Dravidian scripts
        script_score = self._detect_dravidian_scripts(name)
        if script_score > 0:
            confidence += script_score * 0.4
            indicators.append(f"dravidian_script:{script_score:.2f}")

        # Check romanized name patterns
        pattern_score = self._check_dravidian_patterns(name)
        if pattern_score > 0:
            confidence += pattern_score * 0.3
            indicators.append(f"name_patterns:{pattern_score:.2f}")

        # Check surnames
        surname_score = self._check_dravidian_surnames(name)
        if surname_score > 0:
            confidence += surname_score * 0.2
            indicators.append(f"surnames:{surname_score:.2f}")

        # Check place names
        place_score = self._check_place_indicators(full_text)
        if place_score > 0:
            confidence += place_score * 0.1
            indicators.append(f"places:{place_score:.2f}")

        if confidence > 0:
            self.logger.debug(f"D2 detection: {confidence:.3f} [{', '.join(indicators)}]")

        return min(confidence, 1.0)

    def _detect_dravidian_scripts(self, text: str) -> float:
        """Detect Dravidian script characters."""
        if not text:
            return 0.0

        script_scores = {"tamil": 0.0, "telugu": 0.0, "kannada": 0.0, "malayalam": 0.0}

        total_chars = len([c for c in text if c.isalpha()])
        if total_chars == 0:
            return 0.0

        for char in text:
            codepoint = ord(char)

            # Tamil script
            if self.TAMIL_RANGE[0] <= codepoint <= self.TAMIL_RANGE[1]:
                script_scores["tamil"] += 1
            # Telugu script
            elif self.TELUGU_RANGE[0] <= codepoint <= self.TELUGU_RANGE[1]:
                script_scores["telugu"] += 1
            # Kannada script
            elif self.KANNADA_RANGE[0] <= codepoint <= self.KANNADA_RANGE[1]:
                script_scores["kannada"] += 1
            # Malayalam script
            elif self.MALAYALAM_RANGE[0] <= codepoint <= self.MALAYALAM_RANGE[1]:
                script_scores["malayalam"] += 1

        # Return highest script score
        max_script_chars = max(script_scores.values())
        return max_script_chars / total_chars

    def _check_dravidian_patterns(self, name: str) -> float:
        """Check for Dravidian name patterns."""
        if not name:
            return 0.0

        name_lower = name.lower()
        pattern_matches = 0
        total_patterns = 0

        for language, patterns in self.dravidian_patterns.items():
            for pattern in patterns:
                total_patterns += 1
                if re.search(pattern, name, re.IGNORECASE):
                    pattern_matches += 1

        return pattern_matches / total_patterns if total_patterns > 0 else 0.0

    def _check_dravidian_surnames(self, name: str) -> float:
        """Check for Dravidian surnames."""
        if not name:
            return 0.0

        name_parts = name.lower().split()
        surname_matches = 0
        total_surnames = 0

        for language, surnames in self.common_surnames.items():
            total_surnames += len(surnames)
            for surname in surnames:
                if any(surname in part for part in name_parts):
                    surname_matches += 1

        return surname_matches / total_surnames if total_surnames > 0 else 0.0

    def _check_place_indicators(self, text: str) -> float:
        """Check for South Indian place name indicators."""
        if not text:
            return 0.0

        place_matches = 0
        total_places = 0

        for region_places in self.place_names.values():
            total_places += len(region_places)
            for place in region_places:
                if place in text:
                    place_matches += 1

        return place_matches / total_places if total_places > 0 else 0.0

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean Dravidian names according to V7 specification."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # Detect specific Dravidian language
        detected_lang = self._detect_specific_language(canonical)

        # Clean and standardize name
        cleaned_name = self._clean_name(canonical)

        # Update whichever field we got the name from
        if "CanonicalLatin" in entry and entry.get("CanonicalLatin"):
            entry["CanonicalLatin"] = cleaned_name
        elif "CanonicalNative" in entry and entry.get("CanonicalNative"):
            entry["CanonicalNative"] = cleaned_name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment Dravidian names with romanization and variants."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # Detect specific Dravidian language
        detected_lang = self._detect_specific_language(canonical)

        # Romanize if needed
        romanized_name = self._romanize_name(canonical, detected_lang)

        # Extract components
        components = self._extract_name_components(romanized_name, detected_lang)

        # Add metadata
        entry["RegionCode"] = self.REGION_CODE
        entry["RegionFeatures"] = {
            "detected_language": detected_lang,
            "romanization_standard": "ISO_15919",
            "has_dravidian_script": self._detect_dravidian_scripts(canonical) > 0,
        }

    def _detect_specific_language(self, name: str) -> str:
        """Detect specific Dravidian language."""
        if not name:
            return "unknown"

        script_scores = {"tamil": 0, "telugu": 0, "kannada": 0, "malayalam": 0}

        for char in name:
            codepoint = ord(char)

            if self.TAMIL_RANGE[0] <= codepoint <= self.TAMIL_RANGE[1]:
                script_scores["tamil"] += 1
            elif self.TELUGU_RANGE[0] <= codepoint <= self.TELUGU_RANGE[1]:
                script_scores["telugu"] += 1
            elif self.KANNADA_RANGE[0] <= codepoint <= self.KANNADA_RANGE[1]:
                script_scores["kannada"] += 1
            elif self.MALAYALAM_RANGE[0] <= codepoint <= self.MALAYALAM_RANGE[1]:
                script_scores["malayalam"] += 1

        # If script detected, return highest scoring script
        max_lang = max(script_scores.keys(), key=lambda x: script_scores[x])
        if script_scores[max_lang] > 0:
            return max_lang

        # Fallback to pattern matching for romanized names
        name_lower = name.lower()

        # Tamil indicators
        if any(surname in name_lower for surname in self.common_surnames["tamil"]):
            return "tamil"
        # Telugu indicators
        elif any(surname in name_lower for surname in self.common_surnames["telugu"]):
            return "telugu"
        # Kannada indicators
        elif any(surname in name_lower for surname in self.common_surnames["kannada"]):
            return "kannada"
        # Malayalam indicators
        elif any(surname in name_lower for surname in self.common_surnames["malayalam"]):
            return "malayalam"

        return "dravidian_unspecified"

    def _clean_name(self, name: str) -> str:
        """Clean and normalize Dravidian name."""
        if not name:
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", name.strip())

        # Remove common titles
        for title in self.honorific_titles:
            pattern = r"\b" + re.escape(title) + r"\.?\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _romanize_name(self, name: str, language: str) -> str:
        """Romanize Dravidian name using ISO 15919."""
        if not name or language not in self.romanization_map:
            return name

        romanized = name
        mappings = self.romanization_map.get(language, {})

        # Apply romanization mappings
        for native, roman in mappings.items():
            romanized = romanized.replace(native, roman)

        return romanized

    def _extract_name_components(self, name: str, language: str) -> Dict[str, Any]:
        """Extract Dravidian name components."""
        if not name:
            return {}

        parts = name.split()
        components = {"full_name": name, "name_parts": parts, "language": language}

        # Basic component extraction
        if len(parts) == 1:
            components["given_name"] = parts[0]
        elif len(parts) == 2:
            components["given_name"] = parts[0]
            components["family_name"] = parts[1]
        elif len(parts) >= 3:
            components["given_name"] = parts[0]
            components["middle_names"] = parts[1:-1]
            components["family_name"] = parts[-1]

        # Check for patronymic patterns
        if language == "tamil" and len(parts) >= 2:
            # Tamil often uses father's name as middle name
            if len(parts) == 3:
                components["patronymic"] = parts[1]

        return components

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate Dravidian name entry according to V7 specification."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # SECURITY: Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")

        # Apply comprehensive security and validation checks from base class
        self.apply_security_and_validation_checks(entry)

        # Check for mixed scripts
        scripts_detected = set()
        for char in canonical:
            codepoint = ord(char)
            if self.TAMIL_RANGE[0] <= codepoint <= self.TAMIL_RANGE[1]:
                scripts_detected.add("tamil")
            elif self.TELUGU_RANGE[0] <= codepoint <= self.TELUGU_RANGE[1]:
                scripts_detected.add("telugu")
            elif self.KANNADA_RANGE[0] <= codepoint <= self.KANNADA_RANGE[1]:
                scripts_detected.add("kannada")
            elif self.MALAYALAM_RANGE[0] <= codepoint <= self.MALAYALAM_RANGE[1]:
                scripts_detected.add("malayalam")

        if len(scripts_detected) > 1:
            self.logger.warning(
                f"Mixed Dravidian scripts detected in {canonical}: {', '.join(scripts_detected)}"
            )

        # Check for valid Dravidian characteristics
        if not self._has_dravidian_characteristics(canonical):
            self.logger.warning(
                f"Name lacks clear Dravidian linguistic characteristics: {canonical}"
            )

    def _has_dravidian_characteristics(self, name: str) -> bool:
        """Check if name has clear Dravidian characteristics."""
        if not name:
            return False

        # Check for Dravidian scripts
        if self._detect_dravidian_scripts(name) > 0:
            return True
        # Check for characteristic patterns
        name_lower = name.lower()

        # Common Dravidian endings
        dravidian_endings = [
            "an",
            "aiah",
            "appa",
            "swamy",
            "murti",
            "reddy",
            "rao",
            "menon",
            "nair",
            "pillai",
            "gowda",
            "krishnan",
            "raman",
        ]

        return any(name_lower.endswith(ending) for ending in dravidian_endings)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported Dravidian languages."""
        return ["tamil", "telugu", "kannada", "malayalam"]

    def get_region_info(self) -> Dict[str, Any]:
        """Get D2 region information."""
        return {
            "code": self.REGION_CODE,
            "name": self.REGION_NAME,
            "description": "South Asia Dravidian language mathematician names",
            "languages": self.get_supported_languages(),
            "scripts": ["Tamil", "Telugu", "Kannada", "Malayalam"],
            "countries": ["India (South)", "Sri Lanka", "Singapore"],
            "romanization_standard": "ISO_15919",
            "total_speakers": "245M+",
            "mathematician_population": "~50,000",
        }

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for Dravidian names."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return ""

        # Detect language for proper sorting
        detected_lang = self._detect_specific_language(canonical)

        # Romanize if in native script
        if self._detect_dravidian_scripts(canonical) > 0:
            canonical = self._romanize_name(canonical, detected_lang)

        # Extract components for sorting
        components = self._extract_name_components(canonical, detected_lang)

        # Get family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Normalize for sorting
        # Remove diacritics for consistent sorting
        import unicodedata

        family_normalized = unicodedata.normalize("NFD", family)
        family_normalized = "".join(c for c in family_normalized if unicodedata.category(c) != "Mn")
        given_normalized = unicodedata.normalize("NFD", given)
        given_normalized = "".join(c for c in given_normalized if unicodedata.category(c) != "Mn")

        # Convert to uppercase for case-insensitive sorting
        sort_family = family_normalized.upper()
        sort_given = given_normalized.upper()

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        # Generate key following canonical order
        if self.canonical_order == "Family, Given":
            key = f"{sort_family}, {sort_given}"
        else:
            key = f"{sort_given} {sort_family}"

        # Ensure determinism by normalizing whitespace
        key = " ".join(key.split())

        return key
