#!/usr/bin/env python3
"""
WFST-based Korean converter using proper PyNini architecture.
Converts romanized Korean to Hangul using segmentation + WFST composition.
"""

import pynini as pn
import logging
from pathlib import Path

# Import segmenter
import sys
import os
sys.path.append(os.path.dirname(__file__))
from wfst_segmenter import WFSTSegmenter

logger = logging.getLogger(__name__)

class WFSTKoreanConverter:
    """Convert romanized Korean to Hangul using WFST"""
    
    def __init__(self):
        self._load_resources()
        self.segmenter = WFSTSegmenter()
    
    def _load_resources(self):
        """Load WFST and related resources"""
        try:
            self.roman2hangul_fst = pn.Fst.read("data/roman2hangul.fst")
            logger.info("Loaded roman2hangul FST")
        except:
            logger.error("Failed to load roman2hangul FST")
            raise
    
    def convert_word(self, romanized):
        """Convert a single romanized word to Hangul"""
        romanized = romanized.lower().strip()
        if not romanized:
            return ""
        
        # First try direct conversion
        hangul = self._direct_convert(romanized)
        if hangul and self._is_pure_hangul(hangul):
            return hangul
        
        # If direct conversion fails or produces mixed output,
        # use segmentation approach
        segments = self.segmenter.segment(romanized)
        if segments:
            hangul_segments = []
            
            for segment in segments:
                segment_hangul = self._direct_convert(segment)
                if segment_hangul and self._is_pure_hangul(segment_hangul):
                    hangul_segments.append(segment_hangul)
                else:
                    # If any segment fails, fall back to original
                    return romanized
            
            return ''.join(hangul_segments)
        
        return romanized  # Return original if conversion fails
    
    def _direct_convert(self, roman_text):
        """Convert text directly using WFST"""
        try:
            # Create acceptor for input
            input_fst = pn.accep(roman_text)
            
            # Compose with romanization FST
            result = pn.compose(input_fst, self.roman2hangul_fst)
            
            # Get shortest path (best conversion)
            shortest = pn.shortestpath(result)
            
            # Extract output string
            if shortest.num_states() > 0:
                # Use correct PyNini string extraction with UTF-8
                paths_iter = shortest.paths(output_token_type="utf8")
                if not paths_iter.done():
                    return paths_iter.ostring()
            
            return None
            
        except Exception as e:
            logger.debug(f"Direct conversion failed for '{roman_text}': {e}")
            return None
    
    def _is_pure_hangul(self, text):
        """Check if text contains only Hangul characters"""
        if not text:
            return False
        return all(0xAC00 <= ord(char) <= 0xD7A3 for char in text)
    
    def convert_name(self, full_name):
        """Convert a full name (may have spaces, hyphens, commas)"""
        # Handle name formatting
        if ',' in full_name:
            # "Last, First" format
            parts = full_name.split(',', 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Assume first word is family name
            words = full_name.split()
            family = words[0] if words else ""
            given = ' '.join(words[1:]) if len(words) > 1 else ""
        
        # Convert each part
        hangul_parts = []
        
        if family:
            family_hangul = self.convert_word(family)
            hangul_parts.append(family_hangul)
        
        if given:
            # Handle hyphenated given names
            given_words = given.replace('-', ' ').split()
            given_hangul_parts = []
            
            for word in given_words:
                word_hangul = self.convert_word(word)
                given_hangul_parts.append(word_hangul)
            
            if given_hangul_parts:
                hangul_parts.extend(given_hangul_parts)
        
        return ''.join(hangul_parts)

def test_wfst_converter():
    """Test the WFST converter"""
    converter = WFSTKoreanConverter()
    
    test_cases = [
        # Basic names
        "kim", "lee", "park", "choi", "jung",
        
        # Compound names from failures
        "kimtaehyung", "parkjimin", "jeonjungkook",
        "leesangwook", "choiyongkyu", "kanghyunsuk",
        "baesangun", "baekhyeongchan",
        
        # Problem cases from earlier
        "kimdonghwan", "hongjinseok", "yoonseokho"
    ]
    
    print("\nWFST Converter Results:")
    print("=" * 50)
    
    for roman in test_cases:
        hangul = converter.convert_word(roman)
        is_pure = converter._is_pure_hangul(hangul)
        status = "✓" if is_pure else "✗"
        print(f"{roman:15} → {hangul:10} {status}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_wfst_converter()