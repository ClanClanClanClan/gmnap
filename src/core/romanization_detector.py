"""
Romanization Detector for GMNAP
ULTRAFIX Phase 8: Properly detect romanized names before region detection
"""

import re
from typing import Optional, List


class RomanizationDetector:
    """
    Detects romanized names and maps them to correct regions.
    Fixes issues where "Zhang Wei" → A2 instead of E1.
    """

    def __init__(self):
        # Chinese romanization patterns
        self.chinese_surnames = {
            # Most common Chinese surnames in Pinyin
            "wang",
            "li",
            "zhang",
            "liu",
            "chen",
            "yang",
            "huang",
            "zhao",
            "wu",
            "zhou",
            "xu",
            "sun",
            "ma",
            "zhu",
            "hu",
            "guo",
            "he",
            "gao",
            "lin",
            "luo",
            "zheng",
            "liang",
            "xie",
            "tang",
            "song",
            "han",
            "deng",
            "feng",
            "cao",
            "peng",
            "zeng",
            "xiao",
            "tian",
            "dong",
            "pan",
            "yuan",
            "cai",
            "jiang",
            "yu",
            "dai",
            "xia",
            "fan",
            "shi",
            "lu",
            "wei",
            "fu",
            "ren",
            "qiu",
            "kong",
            "bai",
            "cui",
            "kang",
            "mao",
            "qin",
            "gu",
            "hou",
            # Additional variants
            "chang",
            "cheng",
            "jin",
            "jia",
            "yan",
            "xin",
            "long",
            "duan",
        }

        # Japanese romanization patterns
        self.japanese_surnames = {
            # Common Japanese surnames in Hepburn romanization
            "yamada",
            "tanaka",
            "watanabe",
            "ito",
            "sato",
            "suzuki",
            "takahashi",
            "yamamoto",
            "nakamura",
            "kobayashi",
            "saito",
            "kato",
            "yoshida",
            "yamashita",
            "matsumoto",
            "inoue",
            "kimura",
            "shimizu",
            "sano",
            "hayashi",
            "sasaki",
            "yamazaki",
            "mori",
            "abe",
            "ikeda",
            "hashimoto",
            "ishikawa",
            "yamawaki",
            "ogawa",
            "okada",
            "goto",
            "hasegawa",
            "murakami",
            "kondo",
            "ishii",
            "sakamoto",
            "endo",
            "aoki",
            "fujii",
            "matsuda",
            "watabe",
            "ueda",
            "tomita",
            "takeda",
            "murata",
            "ueno",
            "sugawara",
        }

        # Korean romanization patterns
        self.korean_surnames = {
            # Common Korean surnames in Revised Romanization
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "kang",
            "cho",
            "yoon",
            "jang",
            "lim",
            "han",
            "oh",
            "seo",
            "shin",
            "kwon",
            "hwang",
            "ahn",
            "song",
            "yoo",
            "hong",
            "jeon",
            "go",
            "moon",
            "son",
            "yang",
            "baek",
            "heo",
            "nam",
            "min",
            "noh",
            "jeong",
            "cha",
            "woo",
            "kim",
            "ryu",
            "bae",
        }

        # Persian romanization patterns
        self.persian_surnames = {
            # Common Persian surnames in romanization
            "ahmadi",
            "hosseini",
            "mohammadi",
            "rezaei",
            "karimi",
            "moradi",
            "rahimi",
            "rostami",
            "nazari",
            "safari",
            "hashemi",
            "shirazi",
            "isfehani",
            "tabatabaei",
            "mousavi",
            "kazemi",
            "rahmani",
            "farahani",
            # Historical Persian scholars/mathematicians
            "khayyam",
            "tusi",
            "kashani",
            "biruni",
            "karaji",
            "razi",
            # Tajik surnames
            "rahmonov",
            "safarov",
            "karimov",
            "nazarov",
            "rustamov",
            "ismoilov",
        }

        # Arabic romanization patterns
        self.arabic_patterns = {
            # Common Arabic name elements (romanized)
            "prefixes": {"al", "el", "ibn", "abu", "abdul", "abd"},  # Articles and connectors
            "suffixes": {"allah", "rahman", "rahim", "malik", "din", "deen"},  # Religious suffixes
            "common_names": {
                "ahmad",
                "mohammed",
                "muhammad",
                "ali",
                "hassan",
                "hussein",
                "omar",
                "khalid",
                "saeed",
                "ahmed",
                "mahmoud",
                "abdallah",
                "ibrahim",
                "youssef",
                "mohamed",
                "khaled",
                "mustafa",
                "osama",
                # Historical/scholarly names
                "khwarizmi",
                "kindi",
                "rushd",
                "sina",
                "battani",
                "biruni",
                "kashi",
                "tusi",
                "jazari",
                "qalasadi",
                "farabi",
                "ghazali",
                "razi",
                "tabari",
                "masudi",
                "baghdadi",
                "damiri",
                "suyuti",
            },
            # Gulf-specific patterns (for C4 distinction)
            "gulf_indicators": {
                "al-rashid",
                "al-sabah",
                "al-thani",
                "al-nahyan",
                "al-maktoum",
                "al-khalifa",
                "al-said",
                "kuwaiti",
                "qatari",
                "emirati",
            },
            # Levant-specific patterns (for C3 distinction)
            "levant_indicators": {
                "damasci",
                "halabi",
                "shami",
                "masri",
                "baghdadi",
                "basri",
                "karkhi",
                "ansari",
                "dimashqi",
                "rumi",
                "andalusi",
            },
        }

        # Patterns for romanized name structure
        self.romanization_patterns = {
            "chinese": [
                r"^[A-Z][a-z]+ [A-Z][a-z]+$",  # Zhang Wei (surname + given)
                r"^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$",  # Li Ming Hua (3 parts)
            ],
            "japanese": [
                r"^[A-Z][a-z]+ [A-Z][a-z]+$",  # Yamada Taro
                r"^[A-Z][a-z]+-[A-Z][a-z]+$",  # Hyphenated given names
            ],
            "korean": [
                r"^[A-Z][a-z]+ [A-Z][a-z]+(?:-[a-z]+)?$",  # Kim Chul-soo (hyphen optional)
                r"^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$",  # Three-part names
            ],
            "persian": [
                r"^[A-Z][a-z]+, [A-Z][a-z]+$",  # Ahmadi, Hassan
                r"^[A-Z][a-z]+ [A-Z][a-z]+$",  # Khayyam Omar
            ],
            "arabic": [
                r"^(Al|El)-[A-Z][a-z]+$",  # Al-Khwarizmi
                r"^(Ibn|Abu) [A-Z][a-z]+$",  # Ibn Rushd
                r"^Abdul [A-Z][a-z]+$",  # Abdul Rahman
            ],
        }

    def detect_romanized(self, name: str) -> Optional[str]:
        """
        Detect if a name is romanized and return the likely region.

        Args:
            name: Name to analyze

        Returns:
            Region code (E1, E3, E4, C2, C3, C4) if romanized, None otherwise
        """
        if not name or not isinstance(name, str):
            return None

        name_lower = name.lower().strip()
        name_parts = name_lower.split()

        if not name_parts:
            return None

        # PRIORITY CHECK: Historical Persian names (highest priority)
        # Must check first before Arabic to avoid confusion with "Khayyam, Omar"
        historical_persian = {"khayyam", "tusi", "kashani", "biruni", "karaji"}
        for part in name_parts:
            # Clean punctuation from part before checking
            clean_part = part.strip(",.()[]{}'\"")
            if clean_part in historical_persian:
                return "C2"  # Definitive Persian

        # 1. Check Chinese romanization
        if self._is_chinese_romanized(name, name_parts):
            return "E1"

        # 2. Check Japanese romanization
        if self._is_japanese_romanized(name, name_parts):
            return "E3"

        # 3. Check Korean romanization
        if self._is_korean_romanized(name, name_parts):
            return "E4"

        # 4. Check Persian romanization (other cases)
        if self._is_persian_romanized(name, name_parts):
            return "C2"

        # 5. Check Arabic romanization with C3/C4 distinction
        if self._is_arabic_romanized(name, name_parts):
            return self._distinguish_arabic_region(name, name_parts)

        return None

    def _is_chinese_romanized(self, name: str, parts: List[str]) -> bool:
        """Check if name appears to be romanized Chinese"""
        if len(parts) < 2:
            return False

        surname = parts[0]

        # Direct surname match
        if surname in self.chinese_surnames:
            return True

        # Pattern match for Chinese structure
        for pattern in self.romanization_patterns["chinese"]:
            if re.match(pattern, name):
                # Additional validation: check if it could be Chinese
                if len(parts) == 2 and len(surname) > 1:
                    # Check if surname sounds Chinese-like
                    if any(
                        chinese_sound in surname
                        for chinese_sound in ["zh", "ch", "sh", "ng", "ou", "ao", "ei"]
                    ):
                        return True

        return False

    def _is_japanese_romanized(self, name: str, parts: List[str]) -> bool:
        """Check if name appears to be romanized Japanese"""
        if len(parts) < 2:
            return False

        surname = parts[0]

        # Direct surname match
        if surname in self.japanese_surnames:
            return True

        # Pattern match
        for pattern in self.romanization_patterns["japanese"]:
            if re.match(pattern, name):
                # Japanese names often end with vowels
                if surname.endswith(("a", "i", "o", "u", "e")):
                    # Additional Japanese-like sounds
                    if any(
                        jp_sound in surname
                        for jp_sound in ["ya", "ta", "ka", "sa", "na", "ma", "wa"]
                    ):
                        return True

        return False

    def _is_korean_romanized(self, name: str, parts: List[str]) -> bool:
        """Check if name appears to be romanized Korean"""
        if len(parts) < 2:
            return False

        surname = parts[0]

        # Direct surname match
        if surname in self.korean_surnames:
            return True

        # Pattern match
        for pattern in self.romanization_patterns["korean"]:
            if re.match(pattern, name):
                # Korean names often have distinctive patterns
                if len(parts) >= 2:
                    given = " ".join(parts[1:])
                    # Look for Korean-style hyphenated given names
                    if "-" in given or any(
                        korean_sound in surname.lower()
                        for korean_sound in ["kim", "park", "choi", "lee", "jung"]
                    ):
                        return True

        return False

    def _is_persian_romanized(self, name: str, parts: List[str]) -> bool:
        """Check if name appears to be romanized Persian"""
        if len(parts) < 2:
            return False

        surname = parts[0] if "," in name else parts[-1]
        surname = surname.lower()

        # Direct surname match
        if surname in self.persian_surnames:
            return True

        # Pattern match for Persian structure
        for pattern in self.romanization_patterns.get("persian", []):
            if re.match(pattern, name):
                # Additional validation: check if it could be Persian
                if any(
                    persian_sound in surname
                    for persian_sound in ["ahmadi", "hosseini", "rezaei", "karimi"]
                ):
                    return True

        # Check for historical Persian names (high priority - overrides other patterns)
        historical_persian = {"khayyam", "tusi", "kashani", "biruni", "karaji", "razi"}
        for part in parts:
            if part.lower() in historical_persian:
                return True

        # Special case: "Khayyam, Omar" - Khayyam is definitively Persian
        if any(part.lower() == "khayyam" for part in parts):
            return True

        return False

    def _is_arabic_romanized(self, name: str, parts: List[str]) -> bool:
        """Check if name appears to be romanized Arabic"""
        name_lower = name.lower()

        # Check for Arabic prefixes (both with hyphens and spaces)
        if any(
            name_lower.startswith(prefix) for prefix in ["al-", "el-", "ibn-", "abu-", "abdul-"]
        ):
            return True

        # Check for Arabic prefixes with spaces
        if any(
            name_lower.startswith(prefix + " ") for prefix in ["al", "el", "ibn", "abu", "abdul"]
        ):
            return True

        # Check for common Arabic name components
        if len(parts) >= 2:
            first_part = parts[0].lower()
            if first_part in self.arabic_patterns["prefixes"]:
                return True

            # Check for Abdul + name pattern
            if first_part == "abdul" and len(parts) > 1:
                return True

            # Check for Ibn + name pattern (historical names like "Ibn Rushd")
            if first_part == "ibn" and len(parts) > 1:
                return True

            # Check for Abu + name pattern
            if first_part == "abu" and len(parts) > 1:
                return True

        # Check for common Arabic names in any part
        for part in parts:
            if part.lower() in self.arabic_patterns["common_names"]:
                return True

        return False

    def _distinguish_arabic_region(self, name: str, parts: List[str]) -> str:
        """
        Distinguish between C3 (Levant) and C4 (Gulf) for Arabic names.
        """
        name_lower = name.lower()

        # Check for Gulf-specific indicators (C4)
        for indicator in self.arabic_patterns["gulf_indicators"]:
            if indicator in name_lower:
                return "C4"

        # Check for Levant-specific indicators (C3)
        for indicator in self.arabic_patterns["levant_indicators"]:
            if indicator in name_lower:
                return "C3"

        # Check for historical scholars (most were from Levant/Iraq region)
        historical_names = {
            "khwarizmi",
            "kindi",
            "rushd",
            "sina",
            "battani",
            "biruni",
            "farabi",
            "ghazali",
            "razi",
            "tabari",
            "baghdadi",
        }

        for part in parts:
            if part.lower() in historical_names:
                return "C3"  # Historical scholars default to Levant

        # Default to C3 (Levant) for general Arabic names
        return "C3"

    def get_confidence(self, name: str, detected_region: str) -> float:
        """
        Return confidence score for the romanization detection.

        Args:
            name: Original name
            detected_region: Detected region code

        Returns:
            Confidence score between 0.7 and 1.0
        """
        if not detected_region:
            return 0.0

        name_lower = name.lower()
        parts = name_lower.split()

        if detected_region == "E1":  # Chinese
            if parts[0] in self.chinese_surnames:
                return 0.95  # High confidence for known surnames
            return 0.8
        elif detected_region == "E3":  # Japanese
            if parts[0] in self.japanese_surnames:
                return 0.95
            return 0.8
        elif detected_region == "E4":  # Korean
            if parts[0] in self.korean_surnames:
                return 0.95
            return 0.8
        elif detected_region == "C2":  # Persian
            if parts[0] in self.persian_surnames or parts[-1] in self.persian_surnames:
                return 0.95
            return 0.8
        elif detected_region == "C3":  # Arabic
            if any(name_lower.startswith(prefix) for prefix in ["al-", "el-"]):
                return 0.9
            return 0.75

        return 0.7


# Global instance
romanization_detector = RomanizationDetector()
