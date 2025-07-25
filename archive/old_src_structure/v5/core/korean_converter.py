#!/usr/bin/env python3
"""
Korean romanization to Hangul converter with frequency-based weighting.
Pure Python implementation replacing PyNini FSTs.
"""

import json
import math
import re
from typing import List, Tuple, Dict, Optional

class KoreanConverter:
    """Convert romanized Korean to Hangul using weighted multi-system approach"""
    
    def __init__(self):
        # Load romanization tables
        self.reverse_maps = self._load_reverse_maps()
        self.syllable_freq = self._load_syllable_frequencies()
        self.total_freq = sum(self.syllable_freq.values())
        
        # System weights (can be tuned)
        self.system_weights = {
            'rr': 1.0,    # Revised Romanization (official)
            'mr': 0.8,    # McCune-Reischauer  
            'yale': 0.6,  # Yale
            'mltr': 0.9   # MLTR
        }
        
    def _load_reverse_maps(self) -> Dict[str, Dict[str, List[str]]]:
        """Load reverse romanization mappings"""
        try:
            with open("data/reverse_romanization_maps.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: Reverse romanization maps not found. Run generate_tables.py first.")
            return {}
    
    def _load_syllable_frequencies(self) -> Dict[str, int]:
        """Load Korean syllable frequencies"""
        try:
            with open("data/syllable_freq.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: Syllable frequencies not found. Using uniform weights.")
            return {}
    
    def get_syllable_weight(self, hangul: str) -> float:
        """Calculate weight for a Korean syllable based on frequency"""
        if not self.syllable_freq:
            return 1.0  # Uniform weight if no frequency data
        
        freq = self.syllable_freq.get(hangul, 1)  # Smoothing: use 1 for unseen
        # Negative log probability (lower is better)
        return -math.log((freq + 1) / (self.total_freq + len(self.syllable_freq)))
    
    def romanize_to_hangul_candidates(self, roman_syllable: str) -> List[Tuple[str, float]]:
        """
        Get all possible Hangul candidates for a romanized syllable with weights.
        Returns: List of (hangul, weight) tuples sorted by weight.
        """
        candidates = []
        
        # First try direct lookup
        self._add_candidates_for_syllable(roman_syllable, candidates)
        
        # If no candidates found, try variants
        if not candidates:
            from .variant_generator import get_standard_romanization
            standard_forms = get_standard_romanization(roman_syllable)
            
            for standard in standard_forms:
                self._add_candidates_for_syllable(standard, candidates)
        
        # Remove duplicates, keeping best weight
        seen = {}
        for hangul, weight in candidates:
            if hangul not in seen or weight < seen[hangul]:
                seen[hangul] = weight
        
        # Sort by weight (lower is better)
        result = sorted(seen.items(), key=lambda x: x[1])
        return result
    
    def _add_candidates_for_syllable(self, syllable: str, candidates: List[Tuple[str, float]]):
        """Add candidates for a specific syllable form"""
        # Try each romanization system
        for system, system_weight in self.system_weights.items():
            if system in self.reverse_maps:
                hangul_list = self.reverse_maps[system].get(syllable.lower(), [])
                
                for i, hangul in enumerate(hangul_list):
                    # System weight is most important
                    base_weight = (1.0 - system_weight) * 10.0  # Higher penalty for less preferred systems
                    
                    # Position penalty (prefer first match in list)
                    position_weight = i * 0.5
                    
                    # Frequency weight (less important than system match)
                    freq_weight = self.get_syllable_weight(hangul) * 0.1  # Reduced importance
                    
                    total_weight = base_weight + position_weight + freq_weight
                    candidates.append((hangul, total_weight))
    
    def convert_syllable(self, roman_syllable: str) -> Optional[str]:
        """Convert a single romanized syllable to Hangul"""
        # First check the Korean name database for known names
        from .korean_name_database import KOREAN_NAME_MAPPINGS
        
        if roman_syllable.lower() in KOREAN_NAME_MAPPINGS:
            return KOREAN_NAME_MAPPINGS[roman_syllable.lower()]
        
        # Otherwise use the romanization tables
        candidates = self.romanize_to_hangul_candidates(roman_syllable)
        if candidates:
            return candidates[0][0]  # Return best candidate
        return None
    
    def is_korean_syllable(self, char: str) -> bool:
        """Check if a character is a Korean syllable"""
        if not char:
            return False
        code = ord(char)
        return 0xAC00 <= code <= 0xD7A3  # 가 to 힣
    
    def convert_word(self, roman_word: str, use_segmenter: bool = True) -> str:
        """
        Convert a romanized Korean word to Hangul.
        
        Args:
            roman_word: Romanized Korean word
            use_segmenter: If True, use segmenter for compound names
        """
        # First check if it's a single known syllable in the name database
        from .korean_name_database import KOREAN_NAME_MAPPINGS
        
        if roman_word.lower() in KOREAN_NAME_MAPPINGS:
            return KOREAN_NAME_MAPPINGS[roman_word.lower()]
        
        # Try to match whole word in romanization tables
        full_candidates = self.romanize_to_hangul_candidates(roman_word)
        if full_candidates:
            # But still prefer name database if it exists
            if roman_word.lower() not in KOREAN_NAME_MAPPINGS:
                return full_candidates[0][0]
        
        # Use segmenter for compound names
        if use_segmenter:
            from .segmenter import segment_korean_name
            syllables = segment_korean_name(roman_word)
            
            # Convert each syllable
            hangul_syllables = []
            for syllable in syllables:
                hangul = self.convert_syllable(syllable)
                if hangul:
                    hangul_syllables.append(hangul)
                else:
                    # Keep original if can't convert
                    hangul_syllables.append(syllable)
            
            return ''.join(hangul_syllables)
        
        return roman_word  # Return as-is if all else fails
    
    def convert_text(self, text: str, preserve_non_korean: bool = True) -> str:
        """
        Convert romanized Korean text to Hangul.
        
        Args:
            text: Input text potentially containing romanized Korean
            preserve_non_korean: If True, keep non-Korean text as-is
            
        Returns:
            Text with romanized Korean converted to Hangul
        """
        import re
        
        # Pattern to match potential Korean words (letters only)
        word_pattern = r'\b[a-zA-Z]+\b'
        
        def convert_match(match):
            word = match.group(0)
            
            # Check if it looks like a Korean name/word
            # (you could make this more sophisticated)
            if self._looks_like_korean(word):
                converted = self.convert_word(word)
                # Only use converted if it contains Korean characters
                if any(self.is_korean_syllable(ch) for ch in converted):
                    return converted
            
            return word
        
        # Replace potential Korean words
        result = re.sub(word_pattern, convert_match, text)
        return result
    
    def _looks_like_korean(self, word: str) -> bool:
        """Simple heuristic to check if a word might be Korean"""
        word_lower = word.lower()
        
        # Common Korean name indicators
        korean_patterns = [
            'kim', 'lee', 'park', 'choi', 'jung', 'kang', 'yoon', 'song',
            'min', 'ho', 'tae', 'hyung', 'jin', 'ji', 'woo', 'soo'
        ]
        
        # Check if word contains Korean syllable patterns
        for pattern in korean_patterns:
            if pattern in word_lower:
                return True
        
        # Check if it's a potential Korean syllable (1-7 chars, no weird patterns)
        if 1 <= len(word) <= 7 and re.match(r'^[a-zA-Z]+$', word):
            # Try to convert and see if we get candidates
            candidates = self.romanize_to_hangul_candidates(word)
            return len(candidates) > 0
        
        return False


class WeightedKoreanFST:
    """
    Simulates PyNini FST functionality using pure Python.
    Provides weighted transduction from romanized to Hangul.
    """
    
    def __init__(self, converter: KoreanConverter):
        self.converter = converter
        self._build_trie()
    
    def _build_trie(self):
        """Build a trie structure for efficient longest-match searching"""
        self.trie = {}
        
        # Add all romanization patterns to trie
        for system in ['rr', 'mr', 'yale', 'mltr']:
            if system in self.converter.reverse_maps:
                for roman in self.converter.reverse_maps[system]:
                    self._add_to_trie(roman.lower(), system)
    
    def _add_to_trie(self, pattern: str, system: str):
        """Add a pattern to the trie"""
        node = self.trie
        for char in pattern:
            if char not in node:
                node[char] = {}
            node = node[char]
        if '_patterns' not in node:
            node['_patterns'] = []
        node['_patterns'].append(system)
    
    def find_longest_matches(self, text: str, start: int = 0) -> List[Tuple[int, str, List[str]]]:
        """
        Find all possible matches starting at position 'start'.
        Returns: List of (end_pos, matched_text, systems) tuples.
        """
        matches = []
        node = self.trie
        pos = start
        
        while pos < len(text) and text[pos].lower() in node:
            node = node[text[pos].lower()]
            pos += 1
            
            if '_patterns' in node:
                matched = text[start:pos]
                matches.append((pos, matched, node['_patterns']))
        
        return matches
    
    def transduce(self, text: str) -> List[Tuple[str, float]]:
        """
        Transduce romanized text to Hangul with weights.
        Returns all possible transductions with their weights.
        """
        # This is a simplified version - full implementation would use
        # dynamic programming for optimal path finding
        result = []
        
        # For now, return single best conversion
        converted = self.converter.convert_text(text)
        weight = sum(self.converter.get_syllable_weight(ch) 
                    for ch in converted if self.converter.is_korean_syllable(ch))
        
        result.append((converted, weight))
        return result


def create_korean_fst() -> WeightedKoreanFST:
    """Create and return a Korean FST for romanization to Hangul conversion"""
    converter = KoreanConverter()
    return WeightedKoreanFST(converter)


# Example usage and testing
if __name__ == "__main__":
    converter = KoreanConverter()
    
    # Test single syllable conversion
    test_syllables = ["kim", "park", "lee", "choi", "jung"]
    print("Single syllable conversion tests:")
    for roman in test_syllables:
        candidates = converter.romanize_to_hangul_candidates(roman)
        if candidates:
            best = candidates[0]
            print(f"  {roman} -> {best[0]} (weight: {best[1]:.3f})")
            if len(candidates) > 1:
                print(f"    Alternatives: {[c[0] for c in candidates[1:]]}")
        else:
            print(f"  {roman} -> No candidates found")
    
    # Test FST functionality
    print("\nFST transduction test:")
    fst = create_korean_fst()
    test_text = "kim park lee"
    results = fst.transduce(test_text)
    for hangul, weight in results:
        print(f"  '{test_text}' -> '{hangul}' (weight: {weight:.3f})")