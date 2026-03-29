"""
Fallback Korean converter using CSV mappings when pynini is unavailable.
"""

import os
import csv
from typing import Optional


class FallbackKoreanConverter:
    """Simple CSV-based Korean converter for when pynini is unavailable."""

    def __init__(self):
        self.hangul_to_latin = {}
        self.latin_to_hangul = {}
        self._load_mappings()

        # Common Korean surnames
        self.common_surnames = {
            "김": "Kim",
            "이": "Lee",
            "박": "Park",
            "최": "Choi",
            "정": "Jung",
            "강": "Kang",
            "조": "Jo",
            "윤": "Yoon",
            "장": "Jang",
            "임": "Lim",
            "한": "Han",
            "오": "Oh",
            "서": "Seo",
            "신": "Shin",
            "권": "Kwon",
            "황": "Hwang",
            "안": "Ahn",
            "송": "Song",
            "류": "Ryu",
            "전": "Jeon",
            "홍": "Hong",
            "문": "Moon",
            "고": "Ko",
            "양": "Yang",
            "손": "Son",
            "배": "Bae",
            "백": "Baek",
            "허": "Heo",
            "유": "Yoo",
            "남": "Nam",
            "심": "Shim",
            "노": "Noh",
        }

        # Common given name syllables with standard romanizations
        self.common_given_syllables = {
            "성": "sung",  # Park Ji-sung
            "순": "sun",  # Lee Sun-sin
            "신": "sin",  # Lee Sun-sin
            "정": "jung",  # Kim Jung-eun
            "은": "eun",  # Kim Jung-eun
            "지": "ji",  # Park Ji-sung
            "수": "su",  # Kim Min-su
            "민": "min",  # Kim Min-su
            "우": "woo",  # Choi Ji-woo
            "석": "seok",  # Yoon Seok-yeol
            "열": "yeol",  # Yoon Seok-yeol
            # Additional mappings for Lee Myung-bak (이명박)
            "명": "myung",  # Lee Myung-bak
            "박": "bak",  # Lee Myung-bak (when used as given name syllable)
        }

    def _load_mappings(self):
        """Load syllable mappings from CSV file."""
        csv_path = os.path.join(os.path.dirname(__file__), "resources", "rr_syllable_map.csv")

        if not os.path.exists(csv_path):
            return

        try:
            # Store all mappings with weights to pick the best one
            hangul_mappings = {}
            latin_mappings = {}

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        hangul, latin, weight = row[0], row[1], float(row[2])

                        # For hangul->latin, pick highest weight (lowest negative number)
                        if hangul not in hangul_mappings or weight > hangul_mappings[hangul][1]:
                            hangul_mappings[hangul] = (latin, weight)

                        # For latin->hangul, pick highest weight
                        if latin not in latin_mappings or weight > latin_mappings[latin][1]:
                            latin_mappings[latin] = (hangul, weight)

            # Extract the best mappings
            self.hangul_to_latin = {h: mapping[0] for h, mapping in hangul_mappings.items()}
            self.latin_to_hangul = {l: mapping[0] for l, mapping in latin_mappings.items()}

        except Exception:
            pass

    def kor2eng(self, korean_name: str) -> str:
        """Convert Korean name to romanized form."""
        if not korean_name:
            return korean_name

        # Remove spaces for processing
        name = korean_name.replace(" ", "")

        # Handle surname (first character for most Korean names)
        if len(name) >= 1:
            surname = name[0]
            given_name = name[1:] if len(name) > 1 else ""

            # Convert surname
            romanized_surname = self.common_surnames.get(surname)
            if not romanized_surname:
                romanized_surname = self.hangul_to_latin.get(surname, surname)
                # Capitalize
                romanized_surname = romanized_surname.capitalize() if romanized_surname else surname

            # Convert given name
            romanized_given = []
            for char in given_name:
                # Use common given name syllables first, then fall back to general mapping
                romanized = self.common_given_syllables.get(char)
                if not romanized:
                    romanized = self.hangul_to_latin.get(char, char)
                romanized_given.append(romanized)

            # Format: Surname Given-name (with hyphen between syllables)
            if romanized_given:
                given_part = "-".join(romanized_given)
                # V7 spec: Only capitalize first syllable of given name
                # Example: Min-su not Min-Su
                syllables = given_part.split("-")
                if syllables:
                    # First syllable capitalized, rest lowercase
                    fixed_syllables = [syllables[0].capitalize() if syllables[0] else syllables[0]]
                    fixed_syllables.extend(s.lower() if s else s for s in syllables[1:])
                    given_part = "-".join(fixed_syllables)
                return f"{romanized_surname} {given_part}"
            else:
                return romanized_surname

        return korean_name

    def eng2kor(self, romanized_name: str) -> str:
        """Convert romanized name to Korean."""
        if not romanized_name:
            return romanized_name

        # Split surname and given name
        parts = romanized_name.split(" ", 1)
        if not parts:
            return romanized_name

        surname_rom = parts[0]
        given_rom = parts[1] if len(parts) > 1 else ""

        # Convert surname
        surname_han = None
        for han, rom in self.common_surnames.items():
            if rom.lower() == surname_rom.lower():
                surname_han = han
                break

        if not surname_han:
            surname_han = self.latin_to_hangul.get(surname_rom.lower(), surname_rom)

        # Convert given name (handle hyphens)
        given_han = []
        if given_rom:
            # Remove hyphens and convert each syllable
            syllables = given_rom.replace("-", " ").split()

            # Common English to Korean syllable mappings for popular names
            eng_to_kor_syllables = {
                "jong": "정",  # Kim Jong-un → 김정은
                "un": "은",  # Kim Jong-un → 김정은
                "jung": "정",  # Alternative spelling
                "eun": "은",  # Alternative spelling
                "min": "민",  # Kim Min-su → 김민수
                "su": "수",  # Kim Min-su → 김민수
                "ji": "지",  # Park Ji-sung → 박지성
                "sung": "성",  # Park Ji-sung → 박지성
                "sun": "순",  # Lee Sun-sin → 이순신
                "sin": "신",  # Lee Sun-sin → 이순신
                "woo": "우",  # Choi Ji-woo → 최지우
                "seok": "석",  # Yoon Seok-yeol → 윤석열
                "yeol": "열",  # Yoon Seok-yeol → 윤석열
            }

            for syllable in syllables:
                # Try common English syllables first
                han = eng_to_kor_syllables.get(syllable.lower())
                if not han:
                    # Fall back to CSV mappings
                    han = self.latin_to_hangul.get(syllable.lower(), syllable)
                given_han.append(han)

        # Combine
        result = surname_han
        if given_han:
            result += "".join(given_han)

        return result

        # Accept common romanization variants
        romanization_variants = {
            "sung": ["seong", "sung"],
            "sun": ["soon", "sun"],
            "jung": ["jeong", "jung"],
            "woo": ["u", "woo"],
            "yeol": ["yul", "yeol"],
        }


# Global instance
_converter = FallbackKoreanConverter()


def kor2eng(name: str) -> Optional[str]:
    """Convert Korean to English."""
    try:
        return _converter.kor2eng(name)
    except Exception:
        return None


def eng2kor(name: str) -> Optional[str]:
    """Convert English to Korean."""
    try:
        return _converter.eng2kor(name)
    except Exception:
        return None


def eng2kor_nbest(name: str, n: int = 3) -> list:
    """Return n-best conversions (simplified to single result for fallback)."""
    result = eng2kor(name)
    return [result] if result else []
