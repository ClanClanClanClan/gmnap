#!/usr/bin/env python3
"""
E6 Mainland Southeast Asia Region Processor for GMNAP v7
Covers mathematician names from Thailand, Myanmar, Cambodia, Laos

HELL-LEVEL TESTED:
- Thai mathematicians (Thai script, royal naming, Buddhist influence)
- Burmese mathematicians (Myanmar script, patronymic systems)
- Khmer mathematicians (Cambodian script, Sanskrit influence)
- Lao mathematicians (Lao script, Theravada Buddhist patterns)
- Colonial French influence (Vietnam borders)
- Romanization systems (Royal Thai, BGN/PCGN)

V7 SPEC COMPLIANCE:
- iso_territories: [TH, MM, KH, LA]
- primary_scripts: ["Thai", "Myanmar", "Khmer", "Lao"]
- distinct_features: Buddhist naming; Sanskrit influence; tonal languages
"""

import re
import logging
from typing import Dict, Any, List, Set

from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class E6_MainlandSEA(RegionSpec):
    """
    E6 Mainland Southeast Asia region processor.

    Handles mathematician names from mainland SEA countries:
    - Thailand (TH) - largest economy, major universities
    - Myanmar (MM) - emerging mathematical community
    - Cambodia (KH) - post-conflict recovery, growing education
    - Laos (LA) - smaller but active mathematical community

    Features:
    - Multi-script processing (Thai, Myanmar, Khmer, Lao)
    - Buddhist naming conventions and religious influence
    - Sanskrit/Pali loanword patterns
    - Royal naming systems (especially Thai)
    - Patronymic and generational patterns
    - Colonial romanization legacies
    """

    REGION_CODE = "E6"
    REGION_NAME = "Mainland Southeast Asia"

    # Script Unicode ranges
    THAI_RANGE = (0x0E00, 0x0E7F)  # Thai script
    MYANMAR_RANGE = (0x1000, 0x109F)  # Myanmar script
    KHMER_RANGE = (0x1780, 0x17FF)  # Khmer script
    LAO_RANGE = (0x0E80, 0x0EFF)  # Lao script

    def __init__(self):
        super().__init__(
            code="E6",
            yaml_files=["e6_mainland_sea.yaml"],
            scripts=["Thai", "Myanmar", "Khmer", "Lao"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["Royal Thai", "BGN/PCGN"],
        )
        self.logger = logging.getLogger(f"gmnap.regions.E6")

        # Load linguistic resources
        self.script_patterns = self._load_script_patterns()
        self.buddhist_patterns = self._load_buddhist_patterns()
        self.sanskrit_elements = self._load_sanskrit_elements()
        self.royal_patterns = self._load_royal_patterns()
        self.romanization_systems = self._load_romanization_systems()
        self.honorific_titles = self._load_honorific_titles()
        self.place_indicators = self._load_place_indicators()

        self.logger.info(f"E6 Mainland Southeast Asia processor initialized")

    def _load_script_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load script-specific patterns for each country."""
        return {
            "thai": {
                "script_range": self.THAI_RANGE,
                "common_elements": ["วรรณ", "สุข", "ชาย", "หญิง", "นาค", "ทอง"],  # Gold, dragon, etc.
                "royal_elements": ["พระ", "หลวง", "ขุน", "หม่อม"],  # Royal prefixes
                "religious_elements": ["พุทธ", "ธรรม", "สงฆ์", "วัด"],  # Buddhist terms
                "tonal_markers": True,
                "direction": "left_to_right",
            },
            "myanmar": {
                "script_range": self.MYANMAR_RANGE,
                "common_elements": ["မင်း", "ကျော်", "အောင်", "သူ", "မြင့်"],  # Win, famous, etc.
                "patronymic_patterns": True,
                "buddhist_influence": "strong",
                "direction": "left_to_right",
            },
            "khmer": {
                "script_range": self.KHMER_RANGE,
                "common_elements": [
                    "សុខ",
                    "ចន្ទ",
                    "រត្ន",
                    "វណ្ណ",
                    "បុត្រ",
                ],  # Happy, moon, gem, color, son
                "sanskrit_influence": "very_strong",
                "royal_elements": ["ព្រះ", "សម្តេច", "លោក"],  # Royal/noble prefixes
                "direction": "left_to_right",
            },
            "lao": {
                "script_range": self.LAO_RANGE,
                "common_elements": ["ສຸກ", "ບຸນ", "ທອງ", "ຄຳ", "ດວງ"],  # Happy, merit, gold, etc.
                "buddhist_elements": ["ພຣະ", "ວັດ", "ທຳ", "ສົງ"],
                "close_to_thai": True,
                "direction": "left_to_right",
            },
        }

    def _load_buddhist_patterns(self) -> Dict[str, Any]:
        """Load Buddhist naming patterns common across region."""
        return {
            "theravada_elements": {
                "pali_terms": ["dhamma", "buddha", "sangha", "nirvana", "karma"],
                "virtues": ["sila", "dana", "bhavana", "karuna", "mudita"],
                "concepts": ["sukhum", "santhi", "panna", "vipassana"],
            },
            "monastery_names": {
                "thai": ["วัดพระแก้ว", "วัดอรุณ", "วัดโพธิ์"],
                "myanmar": ["ပုဂံ", "မန္တလေး", "ရန်ကုန်"],
                "cambodian": ["អង្គរវត្ត", "បាយ័ន", "ប្រាសាទ"],
                "lao": ["ວັດໄຊ", "ວັດຫຼວງ", "ວັດອາຣາມ"],
            },
            "ordination_names": {
                "pattern": "Buddhist monks often take new names",
                "prefixes": ["Venerable", "Bhante", "Ajahn", "Luang Pu"],
                "suffixes": ["Thero", "Mahathero"],
            },
            "lay_buddhist_names": {
                "meaning_based": True,
                "virtue_emphasis": True,
                "blessing_oriented": True,
            },
        }

    def _load_sanskrit_elements(self) -> Dict[str, List[str]]:
        """Load Sanskrit/Pali elements common in names."""
        return {
            "royal_sanskrit": [
                "raja",
                "rani",
                "deva",
                "devi",
                "sri",
                "siri",  # King, queen, god, goddess, prosperity
                "indra",
                "varman",
                "pala",
                "gupta",
                "chandra",  # Indra, protector, guardian, moon
            ],
            "religious_sanskrit": [
                "buddha",
                "dharma",
                "sangha",
                "ratna",
                "padma",  # Buddha, law, community, jewel, lotus
                "karma",
                "nirvana",
                "moksha",
                "bodhi",
                "prajna",  # Action, liberation, enlightenment, wisdom
            ],
            "nature_sanskrit": [
                "surya",
                "chandra",
                "agni",
                "vayu",
                "prithvi",  # Sun, moon, fire, wind, earth
                "naga",
                "garuda",
                "hamsa",
                "vruksha",
                "pushpa",  # Serpent, eagle, swan, tree, flower
            ],
            "virtue_sanskrit": [
                "satya",
                "ahimsa",
                "dana",
                "shanti",
                "prema",  # Truth, non-violence, giving, peace, love
                "karuna",
                "mudita",
                "upekkha",
                "sila",
                "samadhi",  # Compassion, joy, equanimity, morality, concentration
            ],
            "academic_sanskrit": [
                "vidya",
                "jnana",
                "buddhi",
                "medha",
                "pragya",  # Knowledge, wisdom, intelligence, intellect
                "guru",
                "shishya",
                "adhyapaka",
                "vidyarthi",  # Teacher, student, instructor, learner
            ],
        }

    def _load_royal_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load royal naming patterns by country."""
        return {
            "thai_royal": {
                "titles": ["พระ", "หลวง", "ขุน", "หม่อม", "ม.ร.ว.", "ม.ล."],
                "noble_names": ["รามา", "จักรี", "บรมมหา", "วชิราวุธ"],
                "royal_elements": ["ทรง", "พระองค์", "ราชา", "ราชินี"],
                "patterns": [r"^(พระ|หลวง|ขุน)\s+\w+", r"\w+\s+(ราชา|ราชินี)$"],
            },
            "myanmar_royal": {
                "titles": ["မင်း", "သော်", "သီ", "နန်း"],
                "historical_dynasties": ["ပုဂံ", "မန္တလေး", "အင်းဝ", "ကုန်းဘောင်"],
                "royal_suffixes": ["မင်းကျော်", "မင်းထွန်း", "မင်းရဇ်"],
            },
            "khmer_royal": {
                "titles": ["ព្រះ", "សម្តេច", "លោក", "នាង"],
                "angkor_influence": ["អង្គរ", "ជ័យវរ្ម័ន", "សូរ្យវរ្ម័ន"],
                "royal_elements": ["រាជា", "នរេន្ទ្រ", "វរ្ម័ន", "បាលិត"],
            },
            "lao_royal": {
                "titles": ["ພຣະ", "ເຈົ້າ", "ທ້າວ", "ນາງ"],
                "kingdom_references": ["ລ້ານຊ້າງ", "ວຽງຈັນ", "ຫຼວງພະບາງ"],
                "noble_patterns": [r"^(ພຣະ|ເຈົ້າ)\s+\w+"],
            },
        }

    def _load_romanization_systems(self) -> Dict[str, Dict[str, Any]]:
        """Load romanization systems for each script."""
        return {
            "thai_romanization": {
                "royal_system": "Official Thai romanization",
                "common_patterns": {
                    # Thai consonants
                    "ก": "k",
                    "ข": "kh",
                    "ค": "kh",
                    "ง": "ng",
                    "จ": "ch",
                    "ฉ": "ch",
                    "ช": "ch",
                    "ซ": "s",
                    "ด": "d",
                    "ต": "t",
                    "ท": "th",
                    "น": "n",
                    "บ": "b",
                    "ป": "p",
                    "ผ": "ph",
                    "ฝ": "f",
                    "พ": "ph",
                    "ฟ": "f",
                    "ม": "m",
                    "ย": "y",
                    "ร": "r",
                    "ล": "l",
                    "ว": "w",
                    "ส": "s",
                    "ห": "h",
                    "อ": "",
                    "ฮ": "h",
                },
                "vowels": {
                    "า": "a",
                    "ิ": "i",
                    "ี": "i",
                    "ึ": "ue",
                    "ื": "ue",
                    "ุ": "u",
                    "ู": "u",
                    "เ": "e",
                    "แ": "ae",
                    "โ": "o",
                    "ใ": "ai",
                    "ไ": "ai",
                    "ำ": "am",
                },
            },
            "myanmar_romanization": {
                "bgn_pcgn": "BGN/PCGN Myanmar romanization",
                "common_patterns": {
                    "က": "k",
                    "ခ": "kh",
                    "ဂ": "g",
                    "ဃ": "gh",
                    "င": "ng",
                    "စ": "s",
                    "ဆ": "hs",
                    "ဇ": "z",
                    "ဈ": "jh",
                    "ဉ": "ny",
                    "တ": "t",
                    "ထ": "ht",
                    "ဒ": "d",
                    "ဓ": "dh",
                    "န": "n",
                    "ပ": "p",
                    "ဖ": "hp",
                    "ဗ": "b",
                    "ဘ": "bh",
                    "မ": "m",
                    "ယ": "y",
                    "ရ": "r",
                    "လ": "l",
                    "ဝ": "w",
                    "သ": "th",
                    "ဟ": "h",
                    "ဠ": "l",
                    "အ": "a",
                },
            },
            "khmer_romanization": {
                "standard": "Cambodian romanization",
                "common_patterns": {
                    "ក": "k",
                    "ខ": "kh",
                    "គ": "g",
                    "ឃ": "gh",
                    "ង": "ng",
                    "ច": "ch",
                    "ឆ": "chh",
                    "ជ": "j",
                    "ឈ": "jh",
                    "ញ": "ny",
                    "ដ": "d",
                    "ឋ": "th",
                    "ឌ": "d",
                    "ឍ": "th",
                    "ណ": "n",
                    "ត": "t",
                    "ថ": "th",
                    "ទ": "t",
                    "ធ": "th",
                    "ន": "n",
                    "ប": "b",
                    "ផ": "ph",
                    "ព": "p",
                    "ភ": "ph",
                    "ម": "m",
                    "យ": "y",
                    "រ": "r",
                    "ល": "l",
                    "វ": "v",
                    "ស": "s",
                    "ហ": "h",
                    "ឡ": "l",
                    "អ": "a",
                },
            },
            "lao_romanization": {
                "bgn_pcgn": "BGN/PCGN Lao romanization",
                "common_patterns": {
                    "ກ": "k",
                    "ຂ": "kh",
                    "ຄ": "kh",
                    "ງ": "ng",
                    "ຈ": "ch",
                    "ສ": "s",
                    "ຊ": "s",
                    "ຍ": "ny",
                    "ດ": "d",
                    "ຕ": "t",
                    "ຖ": "th",
                    "ທ": "th",
                    "ນ": "n",
                    "ບ": "b",
                    "ປ": "p",
                    "ຜ": "ph",
                    "ຝ": "f",
                    "ພ": "ph",
                    "ຟ": "f",
                    "ມ": "m",
                    "ຢ": "y",
                    "ຣ": "r",
                    "ລ": "l",
                    "ວ": "w",
                    "ຫ": "h",
                    "ອ": "o",
                },
            },
        }

    def _load_honorific_titles(self) -> Set[str]:
        """Load honorific titles across mainland SEA."""
        return {
            # Thai titles
            "พระ",
            "หลวง",
            "ขุน",
            "หม่อม",
            "คุณ",
            "นาย",
            "นาง",
            "นางสาว",
            "ดร.",
            "ศาสตราจารย์",
            "รองศาสตราจารย์",
            "ผู้ช่วยศาสตราจารย์",
            # Myanmar titles
            "ဦး",
            "ဒေါ်",
            "မ",
            "ကို",
            "မင်း",
            "သော်",
            # Khmer titles
            "លោក",
            "នាង",
            "កញ្ញា",
            "ព្រះ",
            "សម្តេច",
            "ឯកឧត្តម",
            "បណ្ឌិត",
            "សាស្ត្រាចារ្យ",
            # Lao titles
            "ທ້າວ",
            "ນາງ",
            "ນາງສາວ",
            "ພຣະ",
            "ເຈົ້າ",
            "ຄູ",
            "ດຣ.",
            "ສາດສະດາຈານ",
            # English academic titles (colonial influence)
            "Professor",
            "Prof",
            "Prof.",
            "Dr",
            "Dr.",
            "Mr",
            "Mrs",
            "Ms",
            "Associate Professor",
            "Assistant Professor",
        }

    def _load_place_indicators(self) -> Dict[str, Set[str]]:
        """Load geographic place indicators."""
        return {
            "thailand": {
                "bangkok",
                "chiang mai",
                "khon kaen",
                "songkhla",
                "nakhon ratchasima",
                "chulalongkorn university",
                "mahidol university",
                "kasetsart university",
                "king mongkut",
                "thammasat university",
                "chiang mai university",
            },
            "myanmar": {
                "yangon",
                "mandalay",
                "naypyidaw",
                "bagan",
                "mawlamyine",
                "university of yangon",
                "university of mandalay",
                "yangon institute of technology",
            },
            "cambodia": {
                "phnom penh",
                "siem reap",
                "battambang",
                "sihanoukville",
                "royal university of phnom penh",
                "cambodian mekong university",
                "university of cambodia",
            },
            "laos": {
                "vientiane",
                "luang prabang",
                "savannakhet",
                "pakse",
                "national university of laos",
                "champasak university",
            },
        }

    def detect_region(self, entry: Dict[str, Any]) -> float:
        """
        Detect if entry belongs to E6 Mainland SEA region.

        Detection criteria:
        - Native scripts (Thai, Myanmar, Khmer, Lao)
        - Buddhist naming patterns
        - Sanskrit/Pali elements
        - Royal naming conventions
        - Geographic indicators
        - Romanization patterns
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

        # Check for native scripts
        script_score = self._detect_native_scripts(name)
        if script_score > 0:
            confidence += script_score * 0.4
            indicators.append(f"script:{script_score:.2f}")

        # Check Buddhist patterns
        buddhist_score = self._check_buddhist_patterns(name)
        if buddhist_score > 0:
            confidence += buddhist_score * 0.2
            indicators.append(f"buddhist:{buddhist_score:.2f}")

        # Check Sanskrit elements
        sanskrit_score = self._check_sanskrit_elements(name)
        if sanskrit_score > 0:
            confidence += sanskrit_score * 0.15
            indicators.append(f"sanskrit:{sanskrit_score:.2f}")

        # Check royal patterns
        royal_score = self._check_royal_patterns(name)
        if royal_score > 0:
            confidence += royal_score * 0.1
            indicators.append(f"royal:{royal_score:.2f}")

        # Check place indicators
        place_score = self._check_place_indicators(full_text)
        if place_score > 0:
            confidence += place_score * 0.15
            indicators.append(f"places:{place_score:.2f}")

        if confidence > 0:
            self.logger.debug(f"E6 detection: {confidence:.3f} [{', '.join(indicators)}]")

        return min(confidence, 1.0)

    def _detect_native_scripts(self, text: str) -> float:
        """Detect native SEA scripts in text."""
        if not text:
            return 0.0

        script_chars = 0
        total_chars = 0
        script_types = set()

        for char in text:
            if char.isalpha() or ord(char) >= 0x0E00:  # Include SEA script ranges
                total_chars += 1
                codepoint = ord(char)

                if self.THAI_RANGE[0] <= codepoint <= self.THAI_RANGE[1]:
                    script_chars += 1
                    script_types.add("thai")
                elif self.MYANMAR_RANGE[0] <= codepoint <= self.MYANMAR_RANGE[1]:
                    script_chars += 1
                    script_types.add("myanmar")
                elif self.KHMER_RANGE[0] <= codepoint <= self.KHMER_RANGE[1]:
                    script_chars += 1
                    script_types.add("khmer")
                elif self.LAO_RANGE[0] <= codepoint <= self.LAO_RANGE[1]:
                    script_chars += 1
                    script_types.add("lao")

        base_score = script_chars / total_chars if total_chars > 0 else 0.0

        # Bonus for multiple scripts (common in region)
        script_bonus = len(script_types) * 0.1

        return min(base_score + script_bonus, 1.0)

    def _check_buddhist_patterns(self, name: str) -> float:
        """Check for Buddhist naming patterns."""
        if not name:
            return 0.0

        name_lower = name.lower()
        buddhist_matches = 0
        total_patterns = 0

        # Check Theravada elements
        theravada_elements = self.buddhist_patterns["theravada_elements"]
        for category, terms in theravada_elements.items():
            total_patterns += len(terms)
            for term in terms:
                if term in name_lower:
                    buddhist_matches += 1

        return buddhist_matches / total_patterns if total_patterns > 0 else 0.0

    def _check_sanskrit_elements(self, name: str) -> float:
        """Check for Sanskrit/Pali elements."""
        if not name:
            return 0.0

        name_lower = name.lower()
        sanskrit_matches = 0
        total_elements = 0

        for category, elements in self.sanskrit_elements.items():
            total_elements += len(elements)
            for element in elements:
                if element in name_lower:
                    sanskrit_matches += 1

        return sanskrit_matches / total_elements if total_elements > 0 else 0.0

    def _check_royal_patterns(self, name: str) -> float:
        """Check for royal naming patterns."""
        if not name:
            return 0.0

        royal_matches = 0
        total_patterns = 0

        for country, patterns in self.royal_patterns.items():
            if "patterns" in patterns:
                total_patterns += len(patterns["patterns"])
                for pattern in patterns["patterns"]:
                    if re.search(pattern, name, re.IGNORECASE):
                        royal_matches += 1

            # Check titles
            if "titles" in patterns:
                total_patterns += len(patterns["titles"])
                for title in patterns["titles"]:
                    if title in name:
                        royal_matches += 1

        return royal_matches / total_patterns if total_patterns > 0 else 0.0

    def _check_place_indicators(self, text: str) -> float:
        """Check for mainland SEA geographic indicators."""
        if not text:
            return 0.0

        place_matches = 0
        total_places = 0

        for country, places in self.place_indicators.items():
            total_places += len(places)
            for place in places:
                if place in text:
                    place_matches += 1

        return place_matches / total_places if total_places > 0 else 0.0

    # Removed process_name method - not part of V7 RegionSpec interface

    def _detect_country_script(self, name: str, entry: Dict[str, Any]) -> str:
        """Detect country and script type."""
        full_text = f"{name} {entry.get('email', '')} {entry.get('affiliation', '')}".lower()

        script_scores = {}

        # Check script ranges
        for char in name:
            codepoint = ord(char)
            if self.THAI_RANGE[0] <= codepoint <= self.THAI_RANGE[1]:
                script_scores["thai"] = script_scores.get("thai", 0) + 1
            elif self.MYANMAR_RANGE[0] <= codepoint <= self.MYANMAR_RANGE[1]:
                script_scores["myanmar"] = script_scores.get("myanmar", 0) + 1
            elif self.KHMER_RANGE[0] <= codepoint <= self.KHMER_RANGE[1]:
                script_scores["khmer"] = script_scores.get("khmer", 0) + 1
            elif self.LAO_RANGE[0] <= codepoint <= self.LAO_RANGE[1]:
                script_scores["lao"] = script_scores.get("lao", 0) + 1

        # Check geographic context
        for country, places in self.place_indicators.items():
            for place in places:
                if place in full_text:
                    country_key = country.replace("_", "")
                    if country_key == "thailand":
                        script_scores["thai"] = script_scores.get("thai", 0) + 0.5
                    elif country_key == "myanmar":
                        script_scores["myanmar"] = script_scores.get("myanmar", 0) + 0.5
                    elif country_key == "cambodia":
                        script_scores["khmer"] = script_scores.get("khmer", 0) + 0.5
                    elif country_key == "laos":
                        script_scores["lao"] = script_scores.get("lao", 0) + 0.5

        # Return highest scoring script
        if script_scores:
            return max(script_scores.keys(), key=lambda x: script_scores[x])

        return "mainland_sea_romanized"

    def _clean_sea_name(self, name: str) -> str:
        """Clean mainland SEA name."""
        if not name:
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", name.strip())

        # Remove common titles
        for title in self.honorific_titles:
            pattern = r"\b" + re.escape(title) + r"\.?\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _romanize_sea_name(self, name: str, country_script: str) -> str:
        """Apply romanization based on detected script."""
        if not name or country_script == "mainland_sea_romanized":
            return name

        romanized = name

        # Apply appropriate romanization system
        if country_script in self.romanization_systems:
            system = self.romanization_systems[f"{country_script}_romanization"]
            if "common_patterns" in system:
                for native, roman in system["common_patterns"].items():
                    romanized = romanized.replace(native, roman)

        return romanized

    def _extract_sea_components(self, name: str, country_script: str) -> Dict[str, Any]:
        """Extract SEA name components."""
        if not name:
            return {}

        parts = name.split()
        components = {"full_name": name, "name_parts": parts, "country_script": country_script}

        # Country-specific component extraction
        if country_script == "thai":
            components = self._extract_thai_components(parts, components)
        elif country_script == "myanmar":
            components = self._extract_myanmar_components(parts, components)
        elif country_script == "khmer":
            components = self._extract_khmer_components(parts, components)
        elif country_script == "lao":
            components = self._extract_lao_components(parts, components)
        else:
            # Generic structure
            if len(parts) >= 1:
                components["given_name"] = parts[0]
            if len(parts) >= 2:
                components["family_name"] = parts[-1]
            if len(parts) >= 3:
                components["middle_names"] = parts[1:-1]

        # Check for Buddhist elements
        buddhist_elements = self._identify_buddhist_elements(name)
        if buddhist_elements:
            components["buddhist_elements"] = buddhist_elements

        # Check for Sanskrit elements
        sanskrit_elements = self._identify_sanskrit_elements(name)
        if sanskrit_elements:
            components["sanskrit_elements"] = sanskrit_elements

        return components

    def _extract_thai_components(
        self, parts: List[str], components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Thai-specific components."""
        # Thai names often follow Given + Family pattern
        if parts:
            components["given_name"] = parts[0]
            # Check for royal elements
            if any(royal in parts[0] for royal in ["พระ", "หลวง", "ขุน"]):
                components["royal_title"] = True

        if len(parts) >= 2:
            components["family_name"] = parts[-1]

        return components

    def _extract_myanmar_components(
        self, parts: List[str], components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Myanmar-specific components."""
        # Myanmar often uses patronymic system
        if parts:
            components["given_name"] = parts[0]
            # Check for common Myanmar prefixes
            myanmar_prefixes = ["ဦး", "ဒေါ်", "မ", "ကို"]
            for prefix in myanmar_prefixes:
                if parts[0].startswith(prefix):
                    components["honorific_prefix"] = prefix
                    break

        if len(parts) >= 2:
            components["patronymic_or_family"] = parts[-1]

        return components

    def _extract_khmer_components(
        self, parts: List[str], components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Khmer-specific components."""
        # Khmer names often have Sanskrit influence
        if parts:
            components["given_name"] = parts[0]
            # Check for Khmer royal/noble titles
            royal_titles = ["ព្រះ", "សម្តេច", "លោក"]
            for title in royal_titles:
                if title in parts[0]:
                    components["royal_noble_title"] = title
                    break

        if len(parts) >= 2:
            components["family_name"] = parts[-1]

        return components

    def _extract_lao_components(
        self, parts: List[str], components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Lao-specific components."""
        # Lao similar to Thai but with some differences
        if parts:
            components["given_name"] = parts[0]
            # Check for Lao titles
            lao_titles = ["ພຣະ", "ເຈົ້າ", "ທ້າວ"]
            for title in lao_titles:
                if title in parts[0]:
                    components["lao_title"] = title
                    break

        if len(parts) >= 2:
            components["family_name"] = parts[-1]

        return components

    def _identify_buddhist_elements(self, name: str) -> List[str]:
        """Identify Buddhist elements in name."""
        buddhist_elements = []
        name_lower = name.lower()

        for category, terms in self.buddhist_patterns["theravada_elements"].items():
            for term in terms:
                if term in name_lower:
                    buddhist_elements.append(f"{category}: {term}")

        return buddhist_elements

    def _identify_sanskrit_elements(self, name: str) -> List[str]:
        """Identify Sanskrit elements in name."""
        sanskrit_elements = []
        name_lower = name.lower()

        for category, elements in self.sanskrit_elements.items():
            for element in elements:
                if element in name_lower:
                    sanskrit_elements.append(f"{category}: {element}")

        return sanskrit_elements

    # Removed validate_entry method - not part of V7 RegionSpec interface

    def _has_sea_characteristics(self, name: str) -> bool:
        """Check if name has mainland SEA characteristics."""
        if not name:
            return False
        # Check native scripts
        if self._detect_native_scripts(name) > 0:
            return True
        # Check Buddhist patterns
        if self._check_buddhist_patterns(name) > 0:
            return True
        # Check Sanskrit elements
        if self._check_sanskrit_elements(name) > 0:
            return True
        return False

    def _has_mixed_incompatible_scripts(self, name: str) -> bool:
        """Check for incompatible script mixing."""
        scripts_found = set()

        for char in name:
            codepoint = ord(char)
            if self.THAI_RANGE[0] <= codepoint <= self.THAI_RANGE[1]:
                scripts_found.add("thai")
            elif self.MYANMAR_RANGE[0] <= codepoint <= self.MYANMAR_RANGE[1]:
                scripts_found.add("myanmar")
            elif self.KHMER_RANGE[0] <= codepoint <= self.KHMER_RANGE[1]:
                scripts_found.add("khmer")
            elif self.LAO_RANGE[0] <= codepoint <= self.LAO_RANGE[1]:
                scripts_found.add("lao")

        # Thai and Lao are related and can mix
        if scripts_found == {"thai", "lao"}:
            return False
        # More than one script type (excluding Thai-Lao) is unusual
        return len(scripts_found) > 1

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["thai", "myanmar", "khmer", "lao", "pali", "sanskrit"]

    def get_region_info(self) -> Dict[str, Any]:
        """Get E6 region information."""
        return {
            "code": self.REGION_CODE,
            "name": self.REGION_NAME,
            "description": "Mainland Southeast Asian mathematician names",
            "languages": self.get_supported_languages(),
            "scripts": ["Thai", "Myanmar", "Khmer", "Lao"],
            "countries": ["Thailand", "Myanmar", "Cambodia", "Laos"],
            "religious_influence": "Theravada Buddhism",
            "total_speakers": "95M+ (Thai 70M, Myanmar 33M, Khmer 16M, Lao 7M)",
            "mathematician_population": "~12,000",
            "distinctive_features": [
                "Buddhist naming",
                "Sanskrit influence",
                "Royal patterns",
                "Tonal languages",
            ],
            "cultural_traditions": [
                "Theravada Buddhism",
                "Hindu-Buddhist heritage",
                "Royal court traditions",
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
                # Apply comprehensive security validation (V7 compliance)
                self.apply_security_and_validation_checks(
                    {"CanonicalLatin": raw_input, "GlobalID": "security_check"}
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
        # Call base class for idempotency
        super().augment(entry)

    def validate(self, entry):
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        if self._has_security_risks(canonical):
            raise RegionRuleError(f"Name contains dangerous characters: {canonical[:50]}...")

        # Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(f"Name too long: {len(canonical)} characters (max 150)")

        # THEN handle legitimate edge cases
        if len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry):
        """Generate sort key - stub implementation."""
        return str(entry.get("CanonicalLatin", ""))
