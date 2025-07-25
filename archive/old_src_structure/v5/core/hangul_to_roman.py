#!/usr/bin/env python3
"""
Convert Hangul back to romanized Korean.
Essential for round-trip validation.
"""

import json
from typing import Optional, List, Dict
import unicodedata


class HangulToRomanConverter:
    """Convert Korean Hangul to romanized form"""
    
    def __init__(self, system: str = "rr"):
        """
        Initialize converter with specified romanization system.
        
        Args:
            system: Romanization system to use ('rr', 'mr', 'yale', 'mltr')
        """
        self.system = system
        self._load_forward_mappings()
        self._load_name_database()
    
    def _load_forward_mappings(self):
        """Load Hangul to romanization mappings"""
        try:
            with open("data/all_romanization_systems.json", "r", encoding="utf-8") as f:
                all_systems = json.load(f)
                
            if self.system in all_systems:
                self.hangul_to_roman = all_systems[self.system]
            else:
                print(f"Warning: System {self.system} not found. Using RR.")
                self.hangul_to_roman = all_systems.get("rr", {})
        except FileNotFoundError:
            print("Warning: Romanization tables not found.")
            self.hangul_to_roman = {}
    
    def _load_name_database(self):
        """Load Korean name database for preferred romanizations"""
        try:
            from .korean_name_database import KOREAN_NAME_MAPPINGS
            # Create reverse mapping from Hangul to preferred romanization
            self.name_preferences = {}
            for roman, hangul in KOREAN_NAME_MAPPINGS.items():
                # Keep the most common romanization (first one we see)
                if hangul not in self.name_preferences:
                    self.name_preferences[hangul] = roman
        except:
            self.name_preferences = {}
    
    def is_hangul_syllable(self, char: str) -> bool:
        """Check if a character is a Hangul syllable"""
        if not char:
            return False
        code = ord(char)
        return 0xAC00 <= code <= 0xD7A3
    
    def convert_syllable(self, hangul_char: str) -> str:
        """
        Convert a single Hangul syllable to romanized form.
        
        Args:
            hangul_char: Single Hangul character
            
        Returns:
            Romanized form
        """
        # Check name preferences first
        if hangul_char in self.name_preferences:
            return self.name_preferences[hangul_char]
        
        # Use romanization table
        if hangul_char in self.hangul_to_roman:
            return self.hangul_to_roman[hangul_char]
        
        # Return as-is if not found
        return hangul_char
    
    def convert_word(self, hangul_word: str) -> str:
        """
        Convert a Hangul word to romanized form.
        
        Args:
            hangul_word: Hangul text
            
        Returns:
            Romanized text
        """
        result = []
        
        for char in hangul_word:
            if self.is_hangul_syllable(char):
                romanized = self.convert_syllable(char)
                result.append(romanized)
            else:
                # Keep non-Hangul characters as-is
                result.append(char)
        
        return ''.join(result)
    
    def convert_text(self, text: str, preserve_spaces: bool = True) -> str:
        """
        Convert Hangul text to romanized form.
        
        Args:
            text: Input text containing Hangul
            preserve_spaces: If True, preserve word boundaries
            
        Returns:
            Romanized text
        """
        if preserve_spaces:
            # Convert word by word
            words = text.split()
            converted_words = [self.convert_word(word) for word in words]
            return ' '.join(converted_words)
        else:
            # Convert entire text as one unit
            return self.convert_word(text)
    
    def convert_name(self, hangul_name: str) -> str:
        """
        Convert a Korean name from Hangul to romanized form.
        Attempts to match common name romanization patterns.
        
        Args:
            hangul_name: Korean name in Hangul
            
        Returns:
            Romanized name
        """
        # Remove spaces for processing
        name_no_space = hangul_name.replace(' ', '').replace('-', '')
        
        # Check if entire name is in preferences
        if name_no_space in self.name_preferences:
            return self.name_preferences[name_no_space]
        
        # Convert syllable by syllable
        syllables = []
        for char in name_no_space:
            if self.is_hangul_syllable(char):
                syllables.append(self.convert_syllable(char))
        
        # Join syllables
        # For names, typically surname is one syllable, given name is 2 syllables
        if len(syllables) == 3:
            # Most common pattern: 1 surname + 2 given name
            return syllables[0] + syllables[1] + syllables[2]
        elif len(syllables) == 2:
            # 1 surname + 1 given name
            return syllables[0] + syllables[1]
        else:
            # Just concatenate
            return ''.join(syllables)


def create_hangul_converter(system: str = "rr") -> HangulToRomanConverter:
    """Create a Hangul to Roman converter with specified system"""
    return HangulToRomanConverter(system)


# Round-trip conversion helper
def round_trip_convert(romanized: str, roman_to_hangul_fn, system: str = "rr") -> str:
    """
    Perform round-trip conversion: Roman → Hangul → Roman
    
    Args:
        romanized: Original romanized text
        roman_to_hangul_fn: Function to convert to Hangul
        system: Romanization system for back-conversion
        
    Returns:
        Back-converted romanized text
    """
    # Convert to Hangul
    hangul = roman_to_hangul_fn(romanized)
    
    # Convert back to romanized
    converter = HangulToRomanConverter(system)
    back_converted = converter.convert_name(hangul)
    
    return back_converted


# Testing
if __name__ == "__main__":
    converter = HangulToRomanConverter("rr")
    
    print("Hangul to Roman Conversion Tests:")
    print("=" * 50)
    
    # Test individual characters
    test_chars = ["김", "이", "박", "최", "정", "강", "태", "형", "지", "민"]
    
    print("\nSingle character conversion:")
    for hangul in test_chars:
        roman = converter.convert_syllable(hangul)
        print(f"  {hangul} → {roman}")
    
    # Test full names
    test_names = [
        "김태형",
        "박지민",
        "이민호",
        "최수영",
        "정국",
        "송강호"
    ]
    
    print("\nFull name conversion:")
    for hangul_name in test_names:
        roman = converter.convert_name(hangul_name)
        print(f"  {hangul_name} → {roman}")
    
    # Test round-trip
    print("\nRound-trip test (needs Korean converter):")
    try:
        from .korean_converter import KoreanConverter
        korean_conv = KoreanConverter()
        
        test_roman_names = ["kim", "park", "lee", "kimtaehyung", "parkjimin"]
        
        for roman in test_roman_names:
            hangul = korean_conv.convert_word(roman)
            back = converter.convert_name(hangul)
            match = "✓" if roman.lower() == back.lower() else "✗"
            print(f"  {roman} → {hangul} → {back} [{match}]")
    except ImportError:
        print("  (Skipped - Korean converter not available)")