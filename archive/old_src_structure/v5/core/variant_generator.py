#!/usr/bin/env python3
"""
Generate romanization variants for Korean names.
Handles common non-standard romanizations and alternative spellings.
"""

import re
from typing import List, Set, Dict, Tuple

class KoreanVariantGenerator:
    """Generate romanization variants for Korean names"""
    
    def __init__(self):
        # Common romanization variations
        # Map from common spelling to standard romanization(s)
        self.common_variants = {
            # Surnames
            "lee": ["i", "yi", "rhee"],
            "park": ["bak", "pak"],
            "choi": ["choe", "chwi"],
            "jung": ["jeong", "cheong"],
            "kim": ["gim"],
            "kang": ["gang"],
            "yoon": ["yun"],
            "seo": ["seo"],
            "oh": ["o"],
            "jeon": ["jeon", "cheon"],
            "shin": ["sin"],
            "ko": ["go"],
            "ryu": ["yu", "lyu"],
            "bae": ["bae"],
            "moon": ["mun"],
            "yang": ["yang"],
            "han": ["han"],
            "ahn": ["an"],
            "lim": ["im"],
            "hong": ["hong"],
            "song": ["song"],
            "yoo": ["yu"],
            "koo": ["gu"],
            "noh": ["no"],
            "kwon": ["gwon"],
            "hwang": ["hwang"],
            
            # Common given name syllables
            "woo": ["u"],
            "soo": ["su"],
            "hee": ["hui", "hi"],
            "young": ["yeong"],
            "hyun": ["hyeon"],
            "min": ["min"],
            "ji": ["ji"],
            "ho": ["ho"],
            "jin": ["jin"],
            "sung": ["seong"],
            "joo": ["ju"],
            "hye": ["hye", "hae"],
            "kyung": ["gyeong"],
            "mi": ["mi"],
            "sun": ["seon"],
            "yeon": ["yeon"],
            "jun": ["jun"],
            "jae": ["jae"],
            "tae": ["tae"],
            "hyung": ["hyeong"],
            "eun": ["eun"],
            "yong": ["yong"],
            "chan": ["chan"],
            "won": ["weon"],
            "seok": ["seok"],
            "dong": ["dong"],
            "sang": ["sang"],
            "hoon": ["hun"],
            "wook": ["uk"],
            "kyun": ["gyun"],
            "hwan": ["hwan"],
            "kyu": ["gyu"],
        }
        
        # Build reverse mapping for quick lookup
        self.standard_to_variants = {}
        for variant, standards in self.common_variants.items():
            for standard in standards:
                if standard not in self.standard_to_variants:
                    self.standard_to_variants[standard] = []
                self.standard_to_variants[standard].append(variant)
        
        # Patterns for generating systematic variants
        self.variant_patterns = [
            # Vowel variations
            (r"eo", ["eo", "uh", "u"]),
            (r"eu", ["eu", "u", "oo"]),
            (r"ae", ["ae", "e", "ai"]),
            (r"oe", ["oe", "we", "wae"]),
            (r"ui", ["ui", "wi", "i"]),
            (r"ye", ["ye", "yae", "e"]),
            (r"yeo", ["yeo", "yo", "yu"]),
            
            # Consonant variations
            (r"^g", ["g", "k"]),
            (r"^d", ["d", "t"]),
            (r"^b", ["b", "p"]),
            (r"^j", ["j", "ch"]),
            (r"k$", ["k", "g"]),
            (r"t$", ["t", "d"]),
            (r"p$", ["p", "b"]),
            
            # Double consonants
            (r"kk", ["kk", "gg", "k"]),
            (r"tt", ["tt", "dd", "t"]),
            (r"pp", ["pp", "bb", "p"]),
            (r"ss", ["ss", "s"]),
            (r"jj", ["jj", "j"]),
            
            # Special cases
            (r"^r", ["r", "l"]),
            (r"ng$", ["ng", "n"]),
        ]
    
    def generate_variants(self, text: str) -> List[str]:
        """
        Generate all possible romanization variants for the input text.
        
        Args:
            text: Input romanization
            
        Returns:
            List of variant romanizations (including original)
        """
        text_lower = text.lower()
        variants = {text_lower}  # Include original
        
        # Check if it's a known common variant
        if text_lower in self.common_variants:
            variants.update(self.common_variants[text_lower])
        
        # Check if it's a standard form with known variants
        if text_lower in self.standard_to_variants:
            variants.update(self.standard_to_variants[text_lower])
        
        # Apply systematic pattern variations
        for pattern, replacements in self.variant_patterns:
            if re.search(pattern, text_lower):
                for replacement in replacements:
                    # Generate variant by replacing pattern
                    new_variant = re.sub(pattern, replacement, text_lower)
                    variants.add(new_variant)
        
        # Generate hyphenated/spaced variants for compound names
        if len(text_lower) > 3:
            # Try to split into syllables
            split_variants = self._generate_split_variants(text_lower)
            variants.update(split_variants)
        
        # Remove the original if we have other variants
        result = list(variants)
        if len(result) > 1 and text_lower in result:
            # Keep original at the front
            result.remove(text_lower)
            result.insert(0, text_lower)
        
        return result
    
    def _generate_split_variants(self, text: str) -> Set[str]:
        """Generate hyphenated and spaced variants for compound names"""
        variants = set()
        
        # Common split points for Korean names
        # Surnames are typically 1-2 syllables, given names 1-2 syllables each
        
        # Try 1+2 split (common for 3-syllable names)
        if len(text) >= 3:
            for i in range(1, min(5, len(text))):  # Surname up to 4 chars
                part1 = text[:i]
                part2 = text[i:]
                
                # Check if first part could be a surname
                if part1 in self.common_variants or part1 in self.standard_to_variants:
                    variants.add(f"{part1}-{part2}")
                    variants.add(f"{part1} {part2}")
                    
                    # Try splitting the second part further
                    if len(part2) > 2:
                        for j in range(1, len(part2)):
                            variants.add(f"{part1}-{part2[:j]}-{part2[j:]}")
                            variants.add(f"{part1} {part2[:j]} {part2[j:]}")
        
        return variants
    
    def normalize_for_matching(self, text: str) -> str:
        """
        Normalize romanization for matching.
        Removes hyphens, spaces, and converts to lowercase.
        """
        return re.sub(r'[-\s]+', '', text.lower())
    
    def get_all_variants_for_matching(self, text: str) -> Set[str]:
        """
        Get all variants including normalized forms for matching.
        """
        variants = set(self.generate_variants(text))
        
        # Add normalized versions
        normalized = self.normalize_for_matching(text)
        variants.add(normalized)
        variants.update(self.generate_variants(normalized))
        
        return variants


# Convenience functions
def generate_korean_variants(text: str) -> List[str]:
    """Generate romanization variants for Korean text"""
    generator = KoreanVariantGenerator()
    return generator.generate_variants(text)


def get_standard_romanization(variant: str) -> List[str]:
    """Get standard romanization(s) for a common variant"""
    generator = KoreanVariantGenerator()
    variant_lower = variant.lower()
    
    if variant_lower in generator.common_variants:
        return generator.common_variants[variant_lower]
    
    # If it's already standard, return as-is
    return [variant_lower]


# Testing
if __name__ == "__main__":
    generator = KoreanVariantGenerator()
    
    # Test common surnames
    print("Testing common surname variants:")
    print("=" * 60)
    
    test_surnames = ["lee", "park", "choi", "jung", "kim", "yoon", "ryu"]
    
    for surname in test_surnames:
        variants = generator.generate_variants(surname)
        standard = get_standard_romanization(surname)
        print(f"{surname:10} → standard: {', '.join(standard):20} variants: {', '.join(variants)}")
    
    # Test compound names
    print("\n\nTesting compound name splitting:")
    print("=" * 60)
    
    test_names = ["kimtaehyung", "parkjimin", "leeminho", "jeonggukjeon"]
    
    for name in test_names:
        variants = generator.generate_variants(name)
        print(f"\n{name}:")
        for var in variants[:10]:  # Show up to 10 variants
            print(f"  - {var}")
        if len(variants) > 10:
            print(f"  ... and {len(variants) - 10} more")
    
    # Test normalization
    print("\n\nTesting normalization:")
    print("=" * 60)
    
    test_normalized = ["Kim Tae-Hyung", "Park Ji Min", "Lee Min-Ho"]
    
    for name in test_normalized:
        normalized = generator.normalize_for_matching(name)
        print(f"{name:20} → {normalized}")