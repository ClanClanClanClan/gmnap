"""
Unicode normalization pipeline for GMNAP.
Implements the NFC → NFKD → custom fold → NFC chain as specified.
"""

import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class UnicodeConfig:
    """Configuration for Unicode normalization."""
    preserve_combining: bool = True
    handle_ligatures: bool = True
    handle_sharp_s: bool = True
    handle_greek_tonos: bool = True


class UnicodeNormalizer:
    """
    Unicode normalization pipeline following the spec:
    NFC → NFKD → custom fold → NFC
    """
    
    def __init__(self, config: Optional[UnicodeConfig] = None):
        self.config = config or UnicodeConfig()
        self._init_fold_mappings()
    
    def _init_fold_mappings(self):
        """Initialize custom fold mappings for Rule 16."""
        # Ligature decomposition mappings
        self.ligature_mappings = {
            'æ': 'ae', 'Æ': 'AE',
            'œ': 'oe', 'Œ': 'Oe', 
            'ß': 'ss', 'ẞ': 'SS',
            'ĳ': 'ij', 'Ĳ': 'IJ',
            'ﬁ': 'fi', 'ﬂ': 'fl',
            'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
            'ﬆ': 'st'
        }
        
        # Greek tonos = oxia equivalencies
        self.greek_tonos_mappings = {
            'ά': 'ά',  # tonos -> oxia
            'έ': 'έ',
            'ή': 'ή',
            'ί': 'ί',
            'ό': 'ό',
            'ύ': 'ύ',
            'ώ': 'ώ'
        }
        
        # Sharp S handling variants
        self.sharp_s_variants = {
            'ß': ['ss', 'ß'],
            'ẞ': ['SS', 'ẞ']
        }
    
    def normalize(self, text: str) -> str:
        """
        Apply full normalization pipeline.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return text
            
        # Step 0: Remove dangerous characters
        dangerous_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', 
                          '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x1f', '\r', '\n', '\t',
                          '\u200b', '\u200c', '\u200d', '\u200e', '\u200f',
                          '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
                          '\u2066', '\u2067', '\u2068', '\u2069', '\ufeff']
        for char in dangerous_chars:
            text = text.replace(char, '')
            
        # Step 1: NFC normalization
        text = unicodedata.normalize('NFC', text)
        
        # Step 2: NFKD normalization
        text = unicodedata.normalize('NFKD', text)
        
        # Step 3: Custom fold rules
        text = self._apply_custom_fold(text)
        
        # Step 4: Final NFC normalization
        text = unicodedata.normalize('NFC', text)
        
        return text
    
    def _apply_custom_fold(self, text: str) -> str:
        """Apply custom folding rules from Rule 16."""
        # Handle ligatures if enabled
        if self.config.handle_ligatures:
            for ligature, replacement in self.ligature_mappings.items():
                # Skip sharp-s ligatures if sharp-s handling is disabled
                if not self.config.handle_sharp_s and ligature in ('ß', 'ẞ'):
                    continue
                if ligature in text:
                    # Simple rule: use the case from the mapping
                    text = text.replace(ligature, replacement)
        
        # Handle Greek tonos = oxia
        if self.config.handle_greek_tonos:
            for tonos, oxia in self.greek_tonos_mappings.items():
                text = text.replace(tonos, oxia)
        
        return text
    
    def generate_variants(self, text: str) -> List[str]:
        """
        Generate variants based on Unicode folding rules.
        
        Args:
            text: Input text
            
        Returns:
            List of text variants
        """
        variants = [text]
        
        # Generate sharp-s variants
        if self.config.handle_sharp_s:
            for sharp_s, replacements in self.sharp_s_variants.items():
                if sharp_s in text:
                    for replacement in replacements:
                        variant = text.replace(sharp_s, replacement)
                        if variant not in variants:
                            variants.append(variant)
        
        # Generate ligature variants
        if self.config.handle_ligatures:
            for ligature, decomposed in self.ligature_mappings.items():
                # Skip sharp-s ligatures if sharp-s handling is disabled
                if not self.config.handle_sharp_s and ligature in ('ß', 'ẞ'):
                    continue
                if ligature in text:
                    variant = text.replace(ligature, decomposed)
                    if variant not in variants:
                        variants.append(variant)
        
        return variants
    
    def get_script_info(self, text: str) -> Dict[str, int]:
        """
        Analyze Unicode script composition of text.
        
        Args:
            text: Input text
            
        Returns:
            Dict mapping script names to character counts
        """
        script_counts = {}
        
        for char in text:
            if char.isspace() or char in '.,;:!?()-[]{}':
                continue
                
            script = unicodedata.name(char, '').split(' ')[0]
            if script.startswith('LATIN'):
                script = 'Latin'
            elif script.startswith('CYRILLIC'):
                script = 'Cyrillic'
            elif script.startswith('GREEK'):
                script = 'Greek'
            elif script.startswith('ARABIC'):
                script = 'Arabic'
            elif script.startswith('HEBREW'):
                script = 'Hebrew'
            elif script.startswith('DEVANAGARI'):
                script = 'Devanagari'
            elif script.startswith('BENGALI'):
                script = 'Bengali'
            elif script.startswith('TAMIL'):
                script = 'Tamil'
            elif script.startswith('THAI'):
                script = 'Thai'
            elif script.startswith('KHMER'):
                script = 'Khmer'
            elif script.startswith('LAO'):
                script = 'Lao'
            elif script.startswith('MYANMAR'):
                script = 'Myanmar'
            elif script.startswith('GEORGIAN'):
                script = 'Georgian'
            elif script.startswith('ARMENIAN'):
                script = 'Armenian'
            elif script.startswith('HANGUL'):
                script = 'Hangul'
            elif script.startswith('HIRAGANA') or script.startswith('KATAKANA'):
                script = 'Kana'
            elif script.startswith('CJK'):
                script = 'CJK'
            else:
                script = 'Other'
                
            script_counts[script] = script_counts.get(script, 0) + 1
        
        return script_counts
    
    def detect_primary_script(self, text: str) -> str:
        """
        Detect the primary script of a text.
        
        Args:
            text: Input text
            
        Returns:
            Primary script name
        """
        script_counts = self.get_script_info(text)
        if not script_counts:
            return 'Unknown'
        
        return max(script_counts, key=script_counts.get)
    
    def is_mixed_script(self, text: str, threshold: float = 0.1) -> bool:
        """
        Check if text contains mixed scripts above threshold.
        
        Args:
            text: Input text
            threshold: Minimum proportion for secondary script
            
        Returns:
            True if mixed script detected
        """
        script_counts = self.get_script_info(text)
        if len(script_counts) <= 1:
            return False
        
        total_chars = sum(script_counts.values())
        if total_chars == 0:
            return False
        
        sorted_scripts = sorted(script_counts.items(), key=lambda x: x[1], reverse=True)
        secondary_ratio = sorted_scripts[1][1] / total_chars
        
        return secondary_ratio >= threshold
    
    def validate_normalization(self, original: str, normalized: str) -> bool:
        """
        Validate that normalization is reversible where required.
        
        Args:
            original: Original text
            normalized: Normalized text
            
        Returns:
            True if normalization is valid
        """
        # Check that critical characters are preserved
        critical_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        
        orig_critical = set(char for char in original if char in critical_chars)
        norm_critical = set(char for char in normalized if char in critical_chars)
        
        # All critical characters should be preserved
        return orig_critical.issubset(norm_critical)


def normalize_name(name: str, config: Optional[UnicodeConfig] = None) -> str:
    """
    Convenience function to normalize a name.
    
    Args:
        name: Name to normalize
        config: Optional configuration
        
    Returns:
        Normalized name
    """
    normalizer = UnicodeNormalizer(config)
    return normalizer.normalize(name)


def generate_name_variants(name: str, config: Optional[UnicodeConfig] = None) -> List[str]:
    """
    Convenience function to generate name variants.
    
    Args:
        name: Name to generate variants for
        config: Optional configuration
        
    Returns:
        List of name variants
    """
    normalizer = UnicodeNormalizer(config)
    return normalizer.generate_variants(name)