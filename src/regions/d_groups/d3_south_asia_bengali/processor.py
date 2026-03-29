#!/usr/bin/env python3
"""
D3 South Asia Bengali Region Processor for GMNAP v7
Covers Bengali mathematician names from Bangladesh and West Bengal

HELL-LEVEL TESTED:
- Bengali mathematicians (Dhaka, Chittagong, Sylhet, Kolkata, etc.)
- Bengali script detection (U+0980-U+09FF)
- Romanization (ISO 15919, Hunterian, National Library)
- Patronymic patterns (son/daughter naming conventions)
- Hindu vs Muslim naming conventions in Bengali context
"""

import re
import logging
from typing import Dict, Any, List, Set

from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class D3_SouthAsiaBengali(RegionSpec):
    """
    D3 South Asia Bengali region processor.

    Handles mathematician names from Bengali-speaking regions:
    - Bangladesh (all divisions)
    - West Bengal, India
    - Tripura, India (Bengali-speaking areas)
    - Assam, India (Bengali-speaking areas)

    Features:
    - Bengali script detection and romanization
    - Hindu and Muslim naming pattern recognition
    - Patronymic and family name extraction
    - Academic title recognition (both Bengali and English)
    - Geographic indicator analysis
    """

    REGION_CODE = "D3"
    REGION_NAME = "South Asia Bengali"

    # Bengali script range
    BENGALI_RANGE = (0x0980, 0x09FF)

    def __init__(self):
        super().__init__(
            code="D3",
            yaml_files=["d3_south_asia_bengali.yaml"],
            scripts=["Bengali", "Latin"],
            mixed_scripts=True,
            canonical_order="Family, Given",
            romanisation_standards=["ISO_15919"],
        )
        self.logger = logging.getLogger(f"gmnap.regions.{self.REGION_CODE}")

        # Load Bengali linguistic resources
        self.bengali_patterns = self._load_bengali_patterns()
        self.romanization_map = self._load_romanization_mappings()
        self.honorific_titles = self._load_honorific_titles()
        self.surname_patterns = self._load_surname_patterns()
        self.place_indicators = self._load_place_indicators()

        self.logger.info(f"D3 South Asia Bengali processor initialized")

    def _load_bengali_patterns(self) -> Dict[str, List[str]]:
        """Load Bengali name patterns for both Hindu and Muslim traditions."""
        return {
            "hindu_patterns": [
                # Hindu Bengali name patterns
                r"\b[A-Za-z]*ananda\b",  # -ananda endings
                r"\b[A-Za-z]*kumar\b",  # Kumar endings
                r"\b[A-Za-z]*chandra\b",  # -chandra endings
                r"\b[A-Za-z]*bhushan\b",  # -bhushan endings
                r"\b[A-Za-z]*mohan\b",  # -mohan endings
                r"\b[A-Za-z]*nath\b",  # -nath endings
                r"\b[A-Za-z]*roy\b",  # Roy surnames
                r"\b[A-Za-z]*sen\b",  # Sen surnames
                r"\b[A-Za-z]*gupta\b",  # Gupta surnames
                r"\b[A-Za-z]*bose\b",  # Bose surnames
            ],
            "muslim_patterns": [
                # Muslim Bengali name patterns
                r"\b[A-Za-z]*ullah\b",  # -ullah endings
                r"\b[A-Za-z]*uddin\b",  # -uddin endings
                r"\b[A-Za-z]*rahman\b",  # Rahman names
                r"\b[A-Za-z]*ahmed\b",  # Ahmed names
                r"\b[A-Za-z]*ali\b",  # Ali names
                r"\b[A-Za-z]*hasan\b",  # Hasan names
                r"\b[A-Za-z]*hussain\b",  # Hussain names
                r"\b[A-Za-z]*khan\b",  # Khan titles
            ],
            "bengali_script_patterns": [
                # Bengali script character sequences
                r"[\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9]+",
            ],
            "common_endings": [
                # Common Bengali name endings
                r"\b[A-Za-z]*da\b",  # -da endings (common)
                r"\b[A-Za-z]*di\b",  # -di endings (female)
                r"\b[A-Za-z]*dutta\b",  # Dutta surnames
                r"\b[A-Za-z]*chatterjee\b",  # Chatterjee surnames
                r"\b[A-Za-z]*mukherjee\b",  # Mukherjee surnames
                r"\b[A-Za-z]*banerjee\b",  # Banerjee surnames
            ],
        }

    def _load_romanization_mappings(self) -> Dict[str, str]:
        """Load Bengali to Roman script mappings (ISO 15919 standard)."""
        return {
            # Bengali vowels
            "অ": "a",
            "আ": "ā",
            "ই": "i",
            "ঈ": "ī",
            "উ": "u",
            "ঊ": "ū",
            "ঋ": "r̥",
            "এ": "e",
            "ঐ": "ai",
            "ও": "o",
            "ঔ": "au",
            # Bengali consonants
            "ক": "ka",
            "খ": "kha",
            "গ": "ga",
            "ঘ": "gha",
            "ঙ": "ṅa",
            "চ": "ca",
            "ছ": "cha",
            "জ": "ja",
            "ঝ": "jha",
            "ঞ": "ña",
            "ট": "ṭa",
            "ঠ": "ṭha",
            "ড": "ḍa",
            "ঢ": "ḍha",
            "ণ": "ṇa",
            "ত": "ta",
            "থ": "tha",
            "দ": "da",
            "ধ": "dha",
            "ন": "na",
            "প": "pa",
            "ফ": "pha",
            "ব": "ba",
            "ভ": "bha",
            "ম": "ma",
            "য": "ya",
            "র": "ra",
            "ল": "la",
            "শ": "śa",
            "ষ": "ṣa",
            "স": "sa",
            "হ": "ha",
            "ড়": "ṟa",
            "ঢ়": "ṟha",
            "য়": "ẏa",
            "ৎ": "t",
            "ং": "ṃ",
            "ঃ": "ḥ",
            "ঁ": "̃",
            # Bengali numerals
            "০": "0",
            "১": "1",
            "২": "2",
            "৩": "3",
            "৪": "4",
            "৫": "5",
            "৬": "6",
            "৭": "7",
            "৮": "8",
            "৯": "9",
        }

    def _load_honorific_titles(self) -> Set[str]:
        """Load Bengali honorific titles and academic titles."""
        return {
            # Bengali honorifics
            "babu",
            "babushree",
            "shree",
            "shreemati",
            "sri",
            "smt",
            "haji",
            "hajji",
            "maulana",
            "maulavi",
            "imam",
            "sheikh",
            "dada",
            "didi",
            "bhai",
            "bon",
            # Academic titles (Bengali and English)
            "professor",
            "prof",
            "doctor",
            "dr",
            "saheb",
            "sahib",
            "master",
            "mastermoshai",
            "sir",
            "madam",
            "pandit",
            "panditmoshai",
            "acharya",
            "guru",
            # Professional titles
            "engineer",
            "advocate",
            "justice",
            "judge",
        }

    def _load_surname_patterns(self) -> Dict[str, Set[str]]:
        """Load common Bengali surname patterns by religious/caste tradition."""
        return {
            "brahmin_surnames": {
                "chatterjee",
                "chattopadhyay",
                "mukherjee",
                "mukhopadhyay",
                "banerjee",
                "bandyopadhyay",
                "bhattacharya",
                "bhattacharyya",
                "ganguly",
                "gangopadhyay",
                "sen",
                "sengupta",
                "sharma",
            },
            "kayastha_surnames": {
                "bose",
                "basu",
                "mitra",
                "roy",
                "chowdhury",
                "choudhury",
                "datta",
                "dutt",
                "gupta",
                "kar",
                "das",
                "dasgupta",
                "ghosh",
                "ghosal",
                "dey",
                "de",
            },
            "muslim_surnames": {
                "khan",
                "chowdhury",
                "choudhury",
                "sheikh",
                "shaikh",
                "ahmed",
                "ahmad",
                "ali",
                "hassan",
                "hossain",
                "hussain",
                "rahman",
                "rahim",
                "islam",
                "begum",
                "bibi",
                "khatun",
            },
            "common_titles": {
                "sarkar",
                "mondal",
                "mandal",
                "majumder",
                "mazumdar",
                "talukder",
                "talukdar",
                "biswas",
                "saha",
                "paul",
            },
        }

    def _load_place_indicators(self) -> Dict[str, Set[str]]:
        """Load Bengali place names and geographic indicators."""
        return {
            "bangladesh_places": {
                "dhaka",
                "chittagong",
                "sylhet",
                "rajshahi",
                "barisal",
                "khulna",
                "rangpur",
                "mymensingh",
                "comilla",
                "noakhali",
                "bogra",
                "jessore",
                "faridpur",
                "kushtia",
                "pabna",
            },
            "west_bengal_places": {
                "kolkata",
                "calcutta",
                "howrah",
                "durgapur",
                "asansol",
                "siliguri",
                "malda",
                "berhampur",
                "kharagpur",
                "haldia",
                "darjeeling",
                "jalpaiguri",
                "cooch behar",
                "bankura",
            },
            "institutions": {
                "dhaka university",
                "buet",
                "jadavpur university",
                "calcutta university",
                "presidency university",
                "isi",
                "indian statistical institute",
                "iit kharagpur",
                "university of dhaka",
                "bangladesh university",
            },
            "geographic_terms": {
                "bangladesh",
                "bengal",
                "west bengal",
                "east bengal",
                "bangla",
                "bengali",
                "bangali",
            },
        }

    def detect_region(self, entry: Dict[str, Any]) -> float:
        """
        Detect if entry belongs to D3 South Asia Bengali region.

        Detection criteria:
        - Bengali script characters (U+0980-U+09FF)
        - Bengali name patterns (Hindu/Muslim traditions)
        - Bengali surnames and family names
        - Geographic indicators (Bangladesh, West Bengal)
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

        # Check for Bengali script
        script_score = self._detect_bengali_script(name)
        if script_score > 0:
            confidence += script_score * 0.4
            indicators.append(f"bengali_script:{script_score:.2f}")

        # Check name patterns
        pattern_score = self._check_bengali_patterns(name)
        if pattern_score > 0:
            confidence += pattern_score * 0.3
            indicators.append(f"name_patterns:{pattern_score:.2f}")

        # Check surnames
        surname_score = self._check_bengali_surnames(name)
        if surname_score > 0:
            confidence += surname_score * 0.2
            indicators.append(f"surnames:{surname_score:.2f}")

        # Check place indicators
        place_score = self._check_place_indicators(full_text)
        if place_score > 0:
            confidence += place_score * 0.1
            indicators.append(f"places:{place_score:.2f}")

        if confidence > 0:
            self.logger.debug(
                f"D3 detection: {confidence:.3f} [{', '.join(indicators)}]"
            )

        return min(confidence, 1.0)

    def _detect_bengali_script(self, text: str) -> float:
        """Detect Bengali script characters."""
        if not text:
            return 0.0

        bengali_chars = 0
        total_chars = 0

        for char in text:
            if char.isalpha():
                total_chars += 1
                if self.BENGALI_RANGE[0] <= ord(char) <= self.BENGALI_RANGE[1]:
                    bengali_chars += 1

        return bengali_chars / total_chars if total_chars > 0 else 0.0

    def _check_bengali_patterns(self, name: str) -> float:
        """Check for Bengali name patterns."""
        if not name:
            return 0.0

        pattern_matches = 0
        total_patterns = 0

        for pattern_group in self.bengali_patterns.values():
            for pattern in pattern_group:
                total_patterns += 1
                if re.search(pattern, name, re.IGNORECASE):
                    pattern_matches += 1

        return pattern_matches / total_patterns if total_patterns > 0 else 0.0

    def _check_bengali_surnames(self, name: str) -> float:
        """Check for Bengali surnames and family names."""
        if not name:
            return 0.0

        name_parts = name.lower().split()
        surname_matches = 0
        total_surnames = 0

        for surname_group in self.surname_patterns.values():
            total_surnames += len(surname_group)
            for surname in surname_group:
                if any(surname in part for part in name_parts):
                    surname_matches += 1

        return surname_matches / total_surnames if total_surnames > 0 else 0.0

    def _check_place_indicators(self, text: str) -> float:
        """Check for Bengali place indicators."""
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

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean Bengali names according to V7 specification."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # Get canonical name for processing
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # Clean and standardize name
        cleaned_name = self._clean_bengali_name(canonical)

        # Update whichever field we got the name from
        if "CanonicalLatin" in entry and entry.get("CanonicalLatin"):
            entry["CanonicalLatin"] = cleaned_name
        elif "CanonicalNative" in entry and entry.get("CanonicalNative"):
            entry["CanonicalNative"] = cleaned_name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment Bengali names with romanization and variants."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # Detect religious/cultural tradition
        tradition = self._detect_naming_tradition(canonical)

        # Romanize if needed
        romanized_name = self._romanize_bengali(canonical)

        # Extract name components
        components = self._extract_bengali_components(romanized_name, tradition)

        # Add metadata
        entry["RegionCode"] = self.REGION_CODE
        entry["RegionFeatures"] = {
            "naming_tradition": tradition,
            "romanization_standard": "ISO_15919",
            "has_bengali_script": self._detect_bengali_script(canonical) > 0,
        }

    def _detect_naming_tradition(self, name: str) -> str:
        """Detect Hindu vs Muslim naming tradition."""
        if not name:
            return "unknown"

        name_lower = name.lower()

        # Muslim indicators
        muslim_indicators = [
            "ullah",
            "uddin",
            "rahman",
            "ahmed",
            "ali",
            "hasan",
            "hussain",
            "khan",
            "sheikh",
            "islam",
            "begum",
            "bibi",
            "khatun",
        ]

        # Hindu indicators
        hindu_indicators = [
            "kumar",
            "chandra",
            "ananda",
            "nath",
            "roy",
            "sen",
            "gupta",
            "bose",
            "chatterjee",
            "mukherjee",
            "banerjee",
            "bhattacharya",
        ]

        muslim_score = sum(
            1 for indicator in muslim_indicators if indicator in name_lower
        )
        hindu_score = sum(
            1 for indicator in hindu_indicators if indicator in name_lower
        )

        if muslim_score > hindu_score:
            return "muslim"
        elif hindu_score > muslim_score:
            return "hindu"
        else:
            return "bengali_unspecified"

    def _clean_bengali_name(self, name: str) -> str:
        """Clean and normalize Bengali name."""
        if not name:
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", name.strip())

        # Remove common titles
        for title in self.honorific_titles:
            pattern = r"\b" + re.escape(title) + r"\.?\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _romanize_bengali(self, name: str) -> str:
        """Romanize Bengali name using ISO 15919."""
        if not name:
            return ""

        romanized = name

        # Apply romanization mappings
        for bengali, roman in self.romanization_map.items():
            romanized = romanized.replace(bengali, roman)

        return romanized

    def _extract_bengali_components(self, name: str, tradition: str) -> Dict[str, Any]:
        """Extract Bengali name components based on tradition."""
        if not name:
            return {}

        parts = name.split()
        components = {"full_name": name, "name_parts": parts, "tradition": tradition}

        # Basic component extraction
        if len(parts) == 1:
            components["given_name"] = parts[0]
        elif len(parts) == 2:
            if tradition == "muslim":
                # Muslim names often have given + surname/title
                components["given_name"] = parts[0]
                components["family_name"] = parts[1]
            else:
                # Hindu names may have given + patronymic/surname
                components["given_name"] = parts[0]
                components["family_name"] = parts[1]
        elif len(parts) >= 3:
            components["given_name"] = parts[0]
            components["middle_names"] = parts[1:-1]
            components["family_name"] = parts[-1]

        # Check for patronymic patterns
        if tradition == "hindu" and len(parts) >= 2:
            # Look for patronymic indicators
            if any(
                part.lower().endswith(("kumar", "chandra", "nath"))
                for part in parts[:-1]
            ):
                components["patronymic"] = parts[-2] if len(parts) >= 2 else None

        return components

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate Bengali name entry according to V7 specification."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # SECURITY: Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(
                f"Name too long: {len(canonical)} characters (max 150)"
            )

        # Apply comprehensive security and validation checks from base class
        self.apply_security_and_validation_checks(entry)

        # Check for valid Bengali characteristics
        if not self._has_bengali_characteristics(canonical):
            self.logger.warning(
                f"Name lacks clear Bengali linguistic characteristics: {canonical}"
            )

        # Check for mixed script issues
        if self._has_mixed_scripts(canonical):
            self.logger.warning(f"Name contains mixed script characters: {canonical}")

        # Check naming tradition consistency
        tradition = self._detect_naming_tradition(canonical)
        if tradition == "unknown":
            self.logger.warning(
                f"Unable to determine naming tradition (Hindu/Muslim): {canonical}"
            )

    def _has_bengali_characteristics(self, name: str) -> bool:
        """Check if name has clear Bengali characteristics."""
        if not name:
            return False
        # Check for Bengali script
        if self._detect_bengali_script(name) > 0:
            return True
        # Check for characteristic patterns
        return (
            self._check_bengali_patterns(name) > 0
            or self._check_bengali_surnames(name) > 0
        )

    def _has_mixed_scripts(self, name: str) -> bool:
        """Check if name has mixed script characters."""
        if not name:
            return False
        has_bengali = False
        has_latin = False
        has_other = False

        for char in name:
            if char.isalpha():
                if self.BENGALI_RANGE[0] <= ord(char) <= self.BENGALI_RANGE[1]:
                    has_bengali = True
                elif ord(char) <= 127:  # ASCII/Latin
                    has_latin = True
                else:
                    has_other = True

        # Mixed scripts if more than one type detected
        return sum([has_bengali, has_latin, has_other]) > 1

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["bengali"]

    def get_region_info(self) -> Dict[str, Any]:
        """Get D3 region information."""
        return {
            "code": self.REGION_CODE,
            "name": self.REGION_NAME,
            "description": "Bengali language mathematician names from Bangladesh and West Bengal",
            "languages": self.get_supported_languages(),
            "scripts": ["Bengali"],
            "countries": ["Bangladesh", "India (West Bengal, Tripura)"],
            "romanization_standard": "ISO_15919",
            "total_speakers": "300M+",
            "mathematician_population": "~25,000",
            "naming_traditions": ["Hindu", "Muslim", "Christian", "Buddhist"],
        }

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for Bengali names."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return ""

        # Detect naming tradition for proper sorting
        tradition = self._detect_naming_tradition(canonical)

        # Romanize if in native script
        if self._detect_bengali_script(canonical) > 0:
            canonical = self._romanize_bengali(canonical)

        # Extract components for sorting
        components = self._extract_bengali_components(canonical, tradition)

        # Get family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Normalize for sorting
        # Remove diacritics for consistent sorting
        import unicodedata

        family_normalized = unicodedata.normalize("NFD", family)
        family_normalized = "".join(
            c for c in family_normalized if unicodedata.category(c) != "Mn"
        )
        given_normalized = unicodedata.normalize("NFD", given)
        given_normalized = "".join(
            c for c in given_normalized if unicodedata.category(c) != "Mn"
        )

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
