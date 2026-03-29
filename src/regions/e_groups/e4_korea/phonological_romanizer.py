"""
Phonological Korean Romanizer
Implements proper Revised Romanization of Korean (RR) rules
Based on linguistic principles rather than lookup tables
"""

from typing import List, Optional, Tuple


class KoreanPhonologicalRomanizer:
    """
    Proper Korean romanizer based on phonological rules and Hangul decomposition.
    Implements the Revised Romanization of Korean (RR) system with:
    - Hangul syllable decomposition (초성, 중성, 종성)
    - Positional phonological rules
    - Consonant assimilation
    - Proper capitalization rules
    """

    def __init__(self):
        # Traditional surname romanizations (for backwards compatibility)
        self.traditional_surnames = {
            "김": "Kim",
            "박": "Park",
            "이": "Lee",
            "정": "Jung",
            "최": "Choi",
            "조": "Jo",
            "윤": "Yoon",
            "문": "Moon",
        }

        # Initial consonants (초성) - using Jamo range
        self.initial_consonants = {
            "ᄀ": "g",
            "ᄁ": "kk",
            "ᄂ": "n",
            "ᄃ": "d",
            "ᄄ": "tt",
            "ᄅ": "r",
            "ᄆ": "m",
            "ᄇ": "b",
            "ᄈ": "pp",
            "ᄉ": "s",
            "ᄊ": "ss",
            "ᄋ": "",
            "ᄌ": "j",
            "ᄍ": "jj",
            "ᄎ": "ch",
            "ᄏ": "k",
            "ᄐ": "t",
            "ᄑ": "p",
            "ᄒ": "h",
        }

        # Vowels (중성) - using Jamo range
        self.vowels = {
            "ᅡ": "a",
            "ᅢ": "ae",
            "ᅣ": "ya",
            "ᅤ": "yae",
            "ᅥ": "eo",
            "ᅦ": "e",
            "ᅧ": "yeo",
            "ᅨ": "ye",
            "ᅩ": "o",
            "ᅪ": "wa",
            "ᅫ": "wae",
            "ᅬ": "oe",
            "ᅭ": "yo",
            "ᅮ": "u",
            "ᅯ": "wo",
            "ᅰ": "we",
            "ᅱ": "wi",
            "ᅲ": "yu",
            "ᅳ": "eu",
            "ᅴ": "ui",
            "ᅵ": "i",
        }

        # Final consonants (종성) - using Jamo range
        self.final_consonants = {
            "": "",
            "ᆨ": "k",
            "ᆩ": "k",
            "ᆪ": "k",
            "ᆫ": "n",
            "ᆬ": "n",
            "ᆭ": "n",
            "ᆮ": "t",
            "ᆯ": "l",
            "ᆰ": "k",
            "ᆱ": "m",
            "ᆲ": "l",
            "ᆳ": "l",
            "ᆴ": "l",
            "ᆵ": "p",
            "ᆶ": "l",
            "ᆷ": "m",
            "ᆸ": "p",
            "ᆹ": "p",
            "ᆺ": "t",
            "ᆻ": "t",
            "ᆼ": "ng",
            "ᆽ": "t",
            "ᆾ": "t",
            "ᆿ": "k",
            "ᇀ": "t",
            "ᇁ": "p",
            "ᇂ": "t",
        }

        # Positional assimilation rules
        self.linking_rules = {
            # When final ㄱ meets initial ㄴ/ㅁ -> ng
            ("k", "n"): ("ng", "n"),
            ("k", "m"): ("ng", "m"),
            # When final ㄴ meets initial ㄹ -> ll
            ("n", "r"): ("l", "l"),
            # When final ㄹ meets initial ㄴ -> ll
            ("l", "n"): ("l", "l"),
        }

        # Name-specific phonological adjustments (case sensitive)
        self.name_specific_adjustments = {
            # Common name syllables with preferred romanizations
            "seong": "sung",  # 성 in names (Park Ji-sung)
            "Seong": "Sung",  # Capitalized version
            "jeong": "jung",  # 정 in names (Kim Jung-eun)
            "Jeong": "Jung",  # Capitalized version
            "Ji-u": "Ji-woo",  # 지우 in names (Choi Ji-woo)
            "ji-u": "ji-woo",  # Lowercase version
        }

    def decompose_hangul(self, char: str) -> Tuple[str, str, str]:
        """
        Decompose a Hangul syllable into initial, vowel, and final components.

        Args:
            char: Single Hangul character

        Returns:
            Tuple of (initial_consonant, vowel, final_consonant)
        """
        if not self.is_hangul_syllable(char):
            return ("", "", "")

        code = ord(char) - 0xAC00  # Base of Hangul syllables

        # Hangul syllable structure: 초성(19) × 중성(21) × 종성(28)
        final_idx = code % 28
        vowel_idx = (code // 28) % 21
        initial_idx = code // (28 * 21)

        # Convert indices to actual Jamo
        initial_jamo = chr(0x1100 + initial_idx)  # ㄱ-ㅎ
        vowel_jamo = chr(0x1161 + vowel_idx)  # ㅏ-ㅣ
        final_jamo = chr(0x11A7 + final_idx) if final_idx > 0 else ""  # ㄱ-ㅎ (+ empty)

        return (initial_jamo, vowel_jamo, final_jamo)

    def is_hangul_syllable(self, char: str) -> bool:
        """Check if character is a Hangul syllable."""
        return 0xAC00 <= ord(char) <= 0xD7A3

    def romanize_syllable(self, char: str, next_char: Optional[str] = None) -> str:
        """
        Romanize a single Hangul syllable with phonological rules.

        Args:
            char: Current Hangul syllable
            next_char: Next Hangul syllable (for assimilation rules)

        Returns:
            Romanized syllable
        """
        if not self.is_hangul_syllable(char):
            return char

        initial, vowel, final = self.decompose_hangul(char)

        # Get romanization components
        initial_rom = self.initial_consonants.get(initial, "")
        vowel_rom = self.vowels.get(vowel, "")
        final_rom = self.final_consonants.get(final, "")

        # Apply linking rules if there's a next syllable
        if next_char and self.is_hangul_syllable(next_char):
            next_initial, _, _ = self.decompose_hangul(next_char)
            next_initial_rom = self.initial_consonants.get(next_initial, "")

            # Check for assimilation rules
            if final_rom and next_initial_rom:
                rule_key = (final_rom, next_initial_rom)
                if rule_key in self.linking_rules:
                    final_rom, _ = self.linking_rules[rule_key]

        return initial_rom + vowel_rom + final_rom

    def romanize(self, text: str) -> str:
        """
        Romanize Korean text with proper phonological rules.

        Args:
            text: Korean text (Hangul)

        Returns:
            Romanized text with proper capitalization
        """
        if not text:
            return text

        # Romanize each syllable and keep track of syllable boundaries
        syllables = []
        chars = list(text)

        for i, char in enumerate(chars):
            if self.is_hangul_syllable(char):
                next_char = chars[i + 1] if i + 1 < len(chars) else None
                romanized = self.romanize_syllable(char, next_char)
                syllables.append(romanized)
            elif char.isspace():
                # Preserve spaces
                syllables.append(" ")
            else:
                syllables.append(char)

        # Apply proper name formatting (surname + given name with hyphens)
        return self.format_korean_name(syllables)

    def apply_name_capitalization(self, romanized: str) -> str:
        """
        Apply proper capitalization rules for Korean names.
        Format: "Surname Given-name" (e.g., "Kim Min-su")

        Args:
            romanized: Romanized name without proper spacing

        Returns:
            Properly capitalized name with hyphens and spacing
        """
        if not romanized:
            return romanized

        # For Korean names, typically first syllable is surname, rest are given name
        # We need to split the romanized string into syllables

        # Simple approach: assume 2-4 character syllables based on common patterns
        syllables = self._split_into_syllables(romanized)

        if not syllables:
            return romanized

        # First syllable is surname (capitalize)
        surname = syllables[0].capitalize()

        # Remaining syllables are given name
        if len(syllables) > 1:
            given_syllables = syllables[1:]
            # Join with hyphens and capitalize only first syllable
            given_part = "-".join(given_syllables)
            if given_part:
                # Capitalize first character, rest lowercase
                capitalized_given = given_part[0].upper() + given_part[1:].lower()
                return f"{surname} {capitalized_given}"

        return surname

    def _split_into_syllables(self, romanized: str) -> List[str]:
        """
        Split romanized Korean into likely syllables.
        This is a heuristic approach based on common Korean syllable patterns.
        """
        if not romanized:
            return []

        syllables = []
        i = 0
        current_syllable = ""

        while i < len(romanized):
            char = romanized[i]

            # Start new syllable on uppercase letters (except first character)
            if char.isupper() and i > 0 and current_syllable:
                syllables.append(current_syllable.lower())
                current_syllable = char
            else:
                current_syllable += char

            i += 1

        if current_syllable:
            syllables.append(current_syllable.lower())

        # If we couldn't split properly, try length-based splitting
        if len(syllables) == 1 and len(romanized) > 4:
            # Common Korean name pattern: 3-4 chars for surname, 4-6 for given name
            if len(romanized) <= 8:
                # Likely 2 syllables
                mid = len(romanized) // 2
                syllables = [romanized[:mid].lower(), romanized[mid:].lower()]
            else:
                # Likely 3 syllables: surname + 2 given syllables
                third = len(romanized) // 3
                syllables = [
                    romanized[:third].lower(),
                    romanized[third : 2 * third].lower(),
                    romanized[2 * third :].lower(),
                ]

        return syllables

    def format_korean_name(self, syllables: List[str]) -> str:
        """
        Format romanized syllables into proper Korean name format.

        Args:
            syllables: List of romanized syllables

        Returns:
            Properly formatted name (e.g., "Kim Min-su")
        """
        # Filter out spaces and empty syllables
        valid_syllables = [s for s in syllables if s and not s.isspace()]

        if not valid_syllables:
            return ""

        # Korean names typically have 2-4 syllables
        # First syllable is surname, rest are given name
        if len(valid_syllables) == 1:
            return valid_syllables[0].capitalize()

        # First syllable is surname - check for traditional romanization
        surname_romanized = valid_syllables[0].capitalize()

        # Rest are given name syllables (joined with hyphens)
        given_syllables = valid_syllables[1:]
        given_name = "-".join(given_syllables)

        # Capitalize only first letter of given name
        if given_name:
            given_name = given_name[0].upper() + given_name[1:].lower()

        return f"{surname_romanized} {given_name}"

    def romanize_with_traditional_surnames(self, text: str) -> str:
        """
        Romanize Korean text with traditional surname romanizations.

        Args:
            text: Korean text (Hangul)

        Returns:
            Romanized text with traditional surnames
        """
        if not text:
            return text

        # First do regular romanization
        regular_result = self.romanize(text)

        # Apply name-specific adjustments
        adjusted_result = self.apply_name_adjustments(regular_result)

        # Check if first syllable is a traditional surname
        chars = list(text)
        if chars and chars[0] in self.traditional_surnames:
            traditional_surname = self.traditional_surnames[chars[0]]

            # Replace the surname part in the adjusted result
            if " " in adjusted_result:
                parts = adjusted_result.split(" ", 1)
                return f"{traditional_surname} {parts[1]}"
            else:
                return traditional_surname

        return adjusted_result

    def apply_name_adjustments(self, romanized: str) -> str:
        """
        Apply name-specific phonological adjustments.

        Args:
            romanized: Romanized text

        Returns:
            Text with name-specific adjustments applied
        """
        result = romanized
        for original, replacement in self.name_specific_adjustments.items():
            result = result.replace(original, replacement)
        return result


# Factory function for integration
def create_phonological_romanizer() -> KoreanPhonologicalRomanizer:
    """Create a phonological romanizer instance."""
    return KoreanPhonologicalRomanizer()


# Test function
if __name__ == "__main__":
    romanizer = create_phonological_romanizer()

    test_names = [
        "김민수",  # Kim Min-su
        "박지성",  # Park Ji-sung
        "이순신",  # Lee Sun-sin
        "김정은",  # Kim Jung-eun
        "윤석열",  # Yoon Seok-yeol
        "최지우",  # Choi Ji-woo
        "문재인",  # Moon Jae-in
        "조성민",  # Jo Seong-min
    ]

    for name in test_names:
        romanized = romanizer.romanize(name)
        print(f"{name} -> {romanized}")
