#!/usr/bin/env python3
"""V5 Korean conversion pipeline integration functions"""

from .korean_converter import KoreanConverter
from .hangul_to_roman import HangulToRomanConverter
from ..converter_with_backoff import convert_with_backoff
import sys
sys.path.append('.')
from scripts.dice_coefficient import dice_coefficient
import unicodedata

def convert(romanized_name, converter=None, segmenter=None):
    """Main conversion function using V5 system"""
    # Use the existing converter with backoff
    return convert_with_backoff(romanized_name)

def roundtrip_score(romanized_name):
    """Calculate round-trip accuracy score"""
    # Convert to Hangul
    hangul = convert(romanized_name)
    if not hangul:
        return 0.0
    
    # Convert back to romanization
    h2r_converter = HangulToRomanConverter()
    reconstructed = h2r_converter.convert_text(hangul)
    
    # Calculate Dice coefficient
    return dice_coefficient(romanized_name, reconstructed)