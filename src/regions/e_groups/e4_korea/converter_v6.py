"""
Korean Converter v6 - GMNAP E4 Regional Module

2025-proof implementation following the updated plan:
- PyNini 2.1.5 + OpenFST 1.8.3 compatibility
- ≥97% round-trip accuracy on 736 mathematician dataset
- Deterministic WFST conversion both directions
- Self-contained with no external dependencies
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path

# Add the src directory to Python path for imports
E4_ROOT = Path(__file__).parent
sys.path.insert(0, str(E4_ROOT / "src"))

try:
    from src.converter import eng2kor, kor2eng
    CONVERTER_AVAILABLE = True
except ImportError as e:
    logging.error(f"Korean v6 converter core modules not available: {e}")
    CONVERTER_AVAILABLE = False

class KoreanConverterV6:
    """
    Korean Converter v6 implementing GMNAP v6.1 E4 regional requirements.
    
    Features:
    - Bidirectional Korean ↔ English conversion
    - ≥97% round-trip accuracy (GMNAP v6.1 Rule 11)
    - Hyphen/space variation handling (GMNAP v6.1 Rule 13)
    - FST-based deterministic conversion
    """
    
    def __init__(self, e4_root: Optional[Path] = None):
        """Initialize Korean v6 converter."""
        self.e4_root = e4_root or E4_ROOT
        self.initialized = False
        
        if CONVERTER_AVAILABLE:
            # Change to E4 directory for resource loading
            original_cwd = os.getcwd()
            try:
                os.chdir(self.e4_root)
                # Converter modules expect to be run from E4 root
                self.initialized = True
                logging.info("Korean v6 converter initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Korean v6 converter: {e}")
                self.initialized = False
            finally:
                os.chdir(original_cwd)
        else:
            logging.warning("Korean v6 converter not available - core modules missing")
    
    def english_to_korean(self, english_name: str) -> Optional[str]:
        """
        Convert English romanized name to Korean Hangul.
        
        Args:
            english_name: English romanized name (e.g., "Kim Young Soo")
            
        Returns:
            Korean Hangul name (e.g., "김영수") or None if conversion fails
        """
        if not self.initialized:
            return None
            
        try:
            original_cwd = os.getcwd()
            os.chdir(self.e4_root)
            result = eng2kor(english_name)
            os.chdir(original_cwd)
            return result
        except Exception as e:
            logging.error(f"Error converting '{english_name}' to Korean: {e}")
            return None
    
    def korean_to_english(self, korean_name: str) -> Optional[str]:
        """
        Convert Korean Hangul name to English romanization.
        
        Args:
            korean_name: Korean Hangul name (e.g., "김영수")
            
        Returns:
            English romanized name (e.g., "kim young soo") or None if conversion fails
        """
        if not self.initialized:
            return None
            
        try:
            original_cwd = os.getcwd()
            os.chdir(self.e4_root)
            result = kor2eng(korean_name)
            os.chdir(original_cwd)
            return result
        except Exception as e:
            logging.error(f"Error converting '{korean_name}' to English: {e}")
            return None
    
    def validate_round_trip(self, english_name: str) -> float:
        """
        Validate round-trip conversion accuracy using Dice coefficient.
        
        Args:
            english_name: Original English name
            
        Returns:
            Dice similarity score (0.0-1.0), with ≥0.97 indicating compliance
        """
        korean = self.english_to_korean(english_name)
        if not korean:
            return 0.0
            
        english_back = self.korean_to_english(korean)
        if not english_back:
            return 0.0
            
        # Normalize for comparison (NFC casefold, remove spaces)
        import unicodedata
        def norm(s):
            return unicodedata.normalize("NFC", s.casefold().replace(" ", ""))
        
        orig_norm = norm(english_name)
        back_norm = norm(english_back)
        
        # Dice coefficient using character bigrams
        orig_bigrams = set(zip(orig_norm, orig_norm[1:]))
        back_bigrams = set(zip(back_norm, back_norm[1:]))
        
        if not orig_bigrams and not back_bigrams:
            return 1.0
        if not orig_bigrams or not back_bigrams:
            return 0.0
            
        intersection = len(orig_bigrams & back_bigrams)
        total = len(orig_bigrams) + len(back_bigrams)
        
        return 2 * intersection / total if total > 0 else 0.0
    
    def is_available(self) -> bool:
        """Check if the converter is properly initialized and available."""
        return self.initialized
    
    def get_status(self) -> dict:
        """Get converter status and configuration."""
        return {
            "version": "6.0",
            "available": self.initialized,
            "e4_root": str(self.e4_root),
            "core_modules_available": CONVERTER_AVAILABLE,
        }

# Convenience functions for backward compatibility
def eng2kor_v6(name: str) -> Optional[str]:
    """Convert English to Korean using v6 converter."""
    converter = KoreanConverterV6()
    return converter.english_to_korean(name)

def kor2eng_v6(name: str) -> Optional[str]:
    """Convert Korean to English using v6 converter."""
    converter = KoreanConverterV6()  
    return converter.korean_to_english(name)