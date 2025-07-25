#!/usr/bin/env python3
"""
Style-preserving Hangul to Roman converter.
Preserves original romanization style when converting back from Hangul.
"""

import json
from typing import Dict, Optional, Tuple, List
import unicodedata


class StylePreservingConverter:
    """
    Convert between romanized Korean and Hangul while preserving romanization style.
    """
    
    def __init__(self):
        """Initialize the style-preserving converter"""
        self._load_mappings()
        self._build_style_registry()
    
    def _load_mappings(self):
        """Load all necessary mappings"""
        # Load comprehensive V4 mappings (roman -> hangul)
        try:
            with open("data/v4_comprehensive_mappings.json", "r", encoding="utf-8") as f:
                self.roman_to_hangul = json.load(f)
        except:
            self.roman_to_hangul = {}
        
        # Load reverse romanization maps (hangul -> [roman variants])
        try:
            with open("data/reverse_romanization_maps.json", "r", encoding="utf-8") as f:
                self.reverse_maps = json.load(f)
        except:
            self.reverse_maps = {}
        
        # Load all romanization systems (hangul -> roman)
        try:
            with open("data/all_romanization_systems.json", "r", encoding="utf-8") as f:
                self.all_systems = json.load(f)
        except:
            self.all_systems = {}
    
    def _build_style_registry(self):
        """Build a registry of all possible romanization styles for each Hangul"""
        self.hangul_to_styles = {}
        
        # Collect all possible romanizations for each Hangul
        for system_name, mappings in self.reverse_maps.items():
            for roman, hangul_list in mappings.items():
                for hangul in hangul_list:
                    if hangul not in self.hangul_to_styles:
                        self.hangul_to_styles[hangul] = {}
                    self.hangul_to_styles[hangul][roman] = system_name
        
        # Add from forward mappings
        for roman, hangul in self.roman_to_hangul.items():
            if hangul not in self.hangul_to_styles:
                self.hangul_to_styles[hangul] = {}
            self.hangul_to_styles[hangul][roman] = "v4"
    
    def detect_romanization_style(self, romanized: str) -> Dict[str, str]:
        """
        Detect the romanization style used for each part of the input.
        
        Returns:
            Dictionary mapping romanized parts to their detected styles
        """
        style_map = {}
        parts = self._split_name(romanized)
        
        for part in parts:
            part_lower = part.lower()
            if part_lower in self.roman_to_hangul:
                # Check which system this romanization belongs to
                hangul = self.roman_to_hangul[part_lower]
                if hangul in self.hangul_to_styles and part_lower in self.hangul_to_styles[hangul]:
                    style_map[part] = self.hangul_to_styles[hangul][part_lower]
                else:
                    style_map[part] = "unknown"
            else:
                style_map[part] = "unknown"
        
        return style_map
    
    def _split_name(self, name: str) -> List[str]:
        """Split a name into components (handles various formats)"""
        # Handle hyphenated names
        if '-' in name:
            parts = []
            for segment in name.split('-'):
                parts.extend(self._split_camel_case(segment))
            return parts
        # Handle space-separated names
        elif ' ' in name:
            parts = []
            for segment in name.split(' '):
                parts.extend(self._split_camel_case(segment))
            return parts
        else:
            return self._split_camel_case(name)
    
    def _split_camel_case(self, text: str) -> List[str]:
        """Split CamelCase text into components"""
        if not text:
            return []
        
        parts = []
        current = text[0]
        
        for i in range(1, len(text)):
            if text[i].isupper() and current[-1].islower():
                parts.append(current)
                current = text[i]
            else:
                current += text[i]
        
        if current:
            parts.append(current)
        
        return parts
    
    def roman_to_hangul_with_style(self, romanized: str) -> Tuple[str, Dict[str, str]]:
        """
        Convert romanized Korean to Hangul and record the style.
        
        Returns:
            Tuple of (hangul, style_info)
        """
        style_info = self.detect_romanization_style(romanized)
        parts = self._split_name(romanized)
        hangul_parts = []
        
        for part in parts:
            part_lower = part.lower()
            if part_lower in self.roman_to_hangul:
                hangul_parts.append(self.roman_to_hangul[part_lower])
            else:
                # Keep as-is if can't convert
                hangul_parts.append(part)
        
        return ''.join(hangul_parts), style_info
    
    def hangul_to_roman_preserving_style(self, hangul: str, style_info: Dict[str, str], 
                                         original_format: str = None) -> str:
        """
        Convert Hangul back to romanized form, preserving original style.
        
        Args:
            hangul: Hangul text
            style_info: Style information from original romanization
            original_format: Original format string (e.g., "Kim-JongUn" to preserve hyphenation)
            
        Returns:
            Style-preserved romanized text
        """
        result_parts = []
        
        # Convert each Hangul character
        for char in hangul:
            if self._is_hangul_syllable(char):
                # Find the best romanization based on style preference
                best_roman = self._find_best_romanization(char, style_info)
                result_parts.append(best_roman)
            else:
                result_parts.append(char)
        
        result = ''.join(result_parts)
        
        # Apply original formatting if provided
        if original_format:
            result = self._apply_format(result, original_format)
        
        return result
    
    def _is_hangul_syllable(self, char: str) -> bool:
        """Check if a character is a Hangul syllable"""
        if not char:
            return False
        code = ord(char)
        return 0xAC00 <= code <= 0xD7A3
    
    def _find_best_romanization(self, hangul_char: str, style_info: Dict[str, str]) -> str:
        """
        Find the best romanization for a Hangul character based on style preferences.
        """
        if hangul_char not in self.hangul_to_styles:
            # Default to RR system
            if "rr" in self.all_systems and hangul_char in self.all_systems["rr"]:
                return self.all_systems["rr"][hangul_char]
            return hangul_char
        
        possible_romans = self.hangul_to_styles[hangul_char]
        
        # Check if any of the original style romanizations match
        for orig_roman, orig_style in style_info.items():
            if orig_roman.lower() in possible_romans:
                # Try to match the original capitalization
                for roman in possible_romans:
                    if roman.lower() == orig_roman.lower():
                        return self._match_case(roman, orig_roman)
        
        # Otherwise, use the first available romanization
        if possible_romans:
            return list(possible_romans.keys())[0]
        
        # Fallback to RR system
        if "rr" in self.all_systems and hangul_char in self.all_systems["rr"]:
            return self.all_systems["rr"][hangul_char]
        
        return hangul_char
    
    def _match_case(self, text: str, pattern: str) -> str:
        """Match the case pattern of the original text"""
        if pattern.isupper():
            return text.upper()
        elif pattern[0].isupper():
            return text.capitalize()
        else:
            return text.lower()
    
    def _apply_format(self, text: str, format_pattern: str) -> str:
        """Apply original formatting pattern (hyphenation, spacing, etc.)"""
        # This is a simplified implementation
        # In a full implementation, we'd match the exact pattern
        if '-' in format_pattern:
            # Try to apply hyphenation at similar positions
            parts = []
            # Simple heuristic: add hyphen after first syllable
            if len(text) > 3:
                parts = [text[:3], text[3:]]
                return '-'.join(parts)
        return text
    
    def round_trip_preserving_style(self, romanized: str) -> str:
        """
        Perform a round-trip conversion while preserving style.
        
        Args:
            romanized: Original romanized text
            
        Returns:
            Back-converted romanized text preserving original style
        """
        # Convert to Hangul and record style
        hangul, style_info = self.roman_to_hangul_with_style(romanized)
        
        # Convert back preserving style
        back_converted = self.hangul_to_roman_preserving_style(
            hangul, style_info, original_format=romanized
        )
        
        return back_converted


# Convenience functions
def create_style_preserving_converter():
    """Create a style-preserving converter instance"""
    return StylePreservingConverter()


def round_trip_with_style_preservation(romanized: str) -> str:
    """
    Perform round-trip conversion with style preservation.
    
    Args:
        romanized: Original romanized Korean text
        
    Returns:
        Back-converted text preserving original style
    """
    converter = create_style_preserving_converter()
    return converter.round_trip_preserving_style(romanized)