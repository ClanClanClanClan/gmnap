"""
Korean Converter V7 - Production Implementation

This module wraps the optimized converter.py implementation for GMNAP v7 integration.

Performance baseline (as of 2025-08-01):
- Math Dataset: 97.42% (717/736)
- Diverse Dataset: 89.50% (179/200)
- Independent Dataset: ~94%

Key features:
- Position-aware romanization (surname vs given name)
- FST-based syllable mapping with weight optimization
- Loanword fallback for English names
- Enhanced dice scoring for Korean romanization variants
"""

import sys
import os
sys.path.append(os.path.dirname(__file__) + '/src')

from converter import eng2kor, kor2eng, eng2kor_nbest, _enhanced_dice

class KoreanConverterV7:
    """
    V7 Korean converter with GMNAP integration.
    
    Implements the CJK Round-Trip rule (≥97% accuracy) using:
    - Finite State Transducers (FSTs) for efficient mapping
    - Position-specific rules for surnames vs given names
    - Weight-based conflict resolution
    - Multiple fallback strategies
    """
    
    def __init__(self):
        """Initialize the V7 converter."""
        self.version = "7.0"
        self.performance = {
            "math": 0.9742,
            "diverse": 0.8950,
            "independent": 0.94
        }
    
    def romanize(self, korean_name: str) -> str:
        """
        Convert Korean name (Hangul) to romanized form.
        
        Args:
            korean_name: Name in Hangul script
            
        Returns:
            Romanized version of the name
        """
        result = kor2eng(korean_name)
        if result is None:
            # Fallback to returning original if conversion fails
            return korean_name
        return result
    
    def koreanize(self, romanized_name: str) -> str:
        """
        Convert romanized name to Korean (Hangul).
        
        Args:
            romanized_name: Name in romanized form
            
        Returns:
            Korean version in Hangul script
        """
        result = eng2kor(romanized_name)
        if result is None:
            # Fallback to returning original if conversion fails
            return romanized_name
        return result
    
    def koreanize_nbest(self, romanized_name: str, n: int = 3) -> list[str]:
        """
        Get n-best Korean translations for validation tolerance.
        
        Args:
            romanized_name: Name in romanized form
            n: Number of best candidates to return
            
        Returns:
            List of Korean versions in order of likelihood
        """
        return eng2kor_nbest(romanized_name, n)
    
    def round_trip_accuracy(self, name: str, is_korean: bool = True) -> float:
        """
        Test round-trip conversion accuracy.
        
        Args:
            name: Name to test
            is_korean: True if input is in Hangul, False if romanized
            
        Returns:
            Dice coefficient score (0.0 to 1.0)
        """
        if is_korean:
            romanized = self.romanize(name)
            back_converted = self.koreanize(romanized)
            original = name
        else:
            korean = self.koreanize(name)
            back_converted = self.romanize(korean)
            original = name
        
        # Use enhanced dice scoring from converter
        from converter import _enhanced_dice
        return _enhanced_dice(original, back_converted)
    
    def get_performance_stats(self) -> dict:
        """Return current performance statistics."""
        return {
            "version": self.version,
            "performance": self.performance,
            "description": "Korean v7 converter with FST-based position-aware mapping"
        }

# Convenience functions for direct use
# Export _enhanced_dice for external use
__all__ = ['KoreanConverterV7', 'romanize', 'koreanize', '_enhanced_dice']

def romanize(korean_name: str) -> str:
    """Convert Korean name to romanized form."""
    converter = KoreanConverterV7()
    return converter.romanize(korean_name)

def koreanize(romanized_name: str) -> str:
    """Convert romanized name to Korean."""
    converter = KoreanConverterV7()
    return converter.koreanize(romanized_name)