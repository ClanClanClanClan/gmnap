#!/usr/bin/env python3
"""
E4 Korea region handler for GMNAP v6.1.
Integrates V5 Korean processing system.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import Korean v6 converter (fallback to basic implementation if not available)
try:
    from .converter_v6 import KoreanConverterV6
    V6_AVAILABLE = True
except ImportError:
    V6_AVAILABLE = False
    logging.warning("Korean v6 converter not yet implemented")

from ...base import RegionSpec, RegionRuleError


@dataclass
class E4_RegionSpec:
    """Region specification for E4 Korea"""
    code: str = "E4"
    name: str = "Korea"
    iso_territories: List[str] = None
    primary_scripts: List[str] = None
    distinct_features: str = "Hyphen/space variation in romanization"
    
    def __post_init__(self):
        if self.iso_territories is None:
            self.iso_territories = ["KR", "KP"]
        if self.primary_scripts is None:
            self.primary_scripts = ["Hangul", "Hanja"]


class E4KoreaProcessor(RegionSpec):
    """
    Handler for Korean names (South Korea and North Korea).
    Implements GMNAP v6.1 specs for 97% round-trip accuracy.
    """
    
    REGION_CODE = "E4"
    REGION_NAME = "Korea"
    
    def __init__(self):
        super().__init__(
            code="E4",
            yaml_files=["e4_korea.yaml"],
            scripts=["Hangul", "Hanja"]
        )
        self.spec = E4_RegionSpec()
        self.logger = logging.getLogger(f"gmnap.regions.{self.REGION_CODE}")
        
        # Initialize V6 Korean processing if available
        if V6_AVAILABLE:
            self.korean_converter = KoreanConverterV6()
            self.logger.info("V6 Korean processing initialized")
        else:
            self.korean_converter = None
            self.logger.error("V6 Korean processing not available")
    
    def clean(self, entry: Dict) -> Dict:
        """
        Clean Korean name entry.
        
        Handles:
        - Hyphen/space normalization
        - Romanization variant consolidation
        - Script detection
        """
        # Normalize name format
        canonical_latin = entry.get("CanonicalLatin", "")
        if canonical_latin:
            # Remove extra spaces around hyphens
            canonical_latin = canonical_latin.replace(" - ", "-")
            entry["CanonicalLatin"] = canonical_latin
        
        # Detect and tag script
        entry["_script"] = self._detect_script(entry)
        
        return entry
    
    def augment(self, entry: Dict) -> Dict:
        """
        Augment Korean name entry with variants and native script.
        """
        if not V6_AVAILABLE:
            self.logger.warning("Cannot augment without V6 Korean processing")
            return entry
        
        canonical_latin = entry.get("CanonicalLatin", "")
        
        # Generate native Hangul if not present
        if canonical_latin and not entry.get("CanonicalNative"):
            # Extract name without formatting
            name_parts = canonical_latin.replace(",", "").split()
            if name_parts:
                # Convert family name and given name
                hangul_parts = []
                for part in name_parts:
                    hangul = self.korean_converter.convert_word(part.lower())
                    if self._contains_hangul(hangul):
                        hangul_parts.append(hangul)
                
                if hangul_parts:
                    # Format as "Family, Given" in Hangul
                    if len(hangul_parts) >= 2:
                        entry["CanonicalNative"] = f"{hangul_parts[0]}, {' '.join(hangul_parts[1:])}"
                    else:
                        entry["CanonicalNative"] = hangul_parts[0]
        
        # Generate romanization variants
        variants = self._generate_variants(entry)
        if variants:
            existing = set(entry.get("AllCommonVariants", []))
            existing.update(variants)
            entry["AllCommonVariants"] = sorted(list(existing))
        
        return entry
    
    def validate(self, entry: Dict) -> Tuple[bool, List[str]]:
        """
        Validate Korean name entry.
        
        Checks:
        - Round-trip accuracy ≥ 97%
        - Required fields present
        - Script consistency
        """
        errors = []
        
        # Check required fields
        if not entry.get("CanonicalLatin"):
            errors.append("Missing CanonicalLatin")
        
        # Validate round-trip accuracy if V6 available
        if V6_AVAILABLE and entry.get("CanonicalLatin"):
            canonical = entry["CanonicalLatin"].replace(",", "").replace(" ", "").lower()
            
            # Test round-trip
            result = validate_round_trip(
                canonical,
                self.korean_converter.convert_word,
                self.hangul_converter.convert_name,
                threshold=0.97
            )
            
            if not result.passes_threshold:
                errors.append(f"Round-trip accuracy {result.dice_score:.1%} < 97%")
            
            # Store accuracy for reporting
            entry["_roundtrip_accuracy"] = result.dice_score
        
        # Check script consistency
        if entry.get("CanonicalNative"):
            if not self._contains_hangul(entry["CanonicalNative"]):
                errors.append("CanonicalNative does not contain Hangul")
        
        return len(errors) == 0, errors
    
    def order_key(self, entry: Dict) -> str:
        """
        Generate order key for Korean names.
        
        Implements linguistic rule #13: Korean Hyphen/Space variant collapsed.
        """
        canonical = entry.get("CanonicalLatin", "")
        
        # Extract family and given names
        if "," in canonical:
            family, given = canonical.split(",", 1)
            family = family.strip()
            given = given.strip()
        else:
            # Assume first token is family name
            parts = canonical.split()
            if parts:
                family = parts[0]
                given = " ".join(parts[1:]) if len(parts) > 1 else ""
            else:
                family = canonical
                given = ""
        
        # Normalize: remove hyphens, spaces, lowercase
        family_normalized = family.replace("-", "").replace(" ", "").lower()
        given_normalized = given.replace("-", "").replace(" ", "").lower()
        
        # Korean order: Family Given (no comma)
        order_key = f"{family_normalized}{given_normalized}"
        
        return order_key
    
    # Helper methods
    
    def _detect_script(self, entry: Dict) -> str:
        """Detect primary script used in entry"""
        # Check CanonicalNative first
        native = entry.get("CanonicalNative", "")
        if native:
            if self._contains_hangul(native):
                return "Hangul"
            elif self._contains_hanja(native):
                return "Hanja"
        
        # Check CJK field
        cjk = entry.get("CJK", "")
        if cjk and self._contains_hanja(cjk):
            return "Hanja"
        
        return "Latin"
    
    def _contains_hangul(self, text: str) -> bool:
        """Check if text contains Hangul characters"""
        return any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in text)
    
    def _contains_hanja(self, text: str) -> bool:
        """Check if text contains Hanja (Chinese characters used in Korean)"""
        return any(0x4E00 <= ord(ch) <= 0x9FFF for ch in text)
    
    def _generate_variants(self, entry: Dict) -> List[str]:
        """Generate Korean-specific name variants"""
        variants = []
        canonical = entry.get("CanonicalLatin", "")
        
        if not canonical:
            return variants
        
        # Extract clean name
        if "," in canonical:
            family, given = canonical.split(",", 1)
            family = family.strip()
            given = given.strip()
        else:
            parts = canonical.split()
            family = parts[0] if parts else ""
            given = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        # Generate hyphen/space variants
        if family and given:
            # With hyphen
            variants.append(f"{family}-{given.replace(' ', '-')}")
            # With space
            variants.append(f"{family} {given.replace('-', ' ')}")
            # Concatenated
            variants.append(f"{family}{given.replace('-', '').replace(' ', '')}")
            # Western order
            variants.append(f"{given} {family}")
        
        return variants
    
    def quality_gate(self, entry: Dict) -> bool:
        """
        Check if entry meets quality requirements.
        
        For Korean: Round-trip accuracy must be ≥ 97%
        """
        if "_roundtrip_accuracy" in entry:
            return entry["_roundtrip_accuracy"] >= 0.97
        
        # If no accuracy calculated, validate now
        valid, _ = self.validate(entry)
        return valid


# Register the handler
def register():
    """Register E4_Korea handler"""
    return E4_Korea


if __name__ == "__main__":
    # Test the handler
    handler = E4_Korea()
    
    test_entry = {
        "CanonicalLatin": "Kim, Tae-Hyung",
        "AllCommonVariants": ["Kim Taehyung", "Kim Tae Hyung"],
    }
    
    print("Testing E4_Korea handler:")
    print(f"Original: {test_entry}")
    
    # Process through pipeline
    cleaned = handler.clean(test_entry)
    print(f"\nAfter clean: {cleaned}")
    
    augmented = handler.augment(cleaned)
    print(f"\nAfter augment: {augmented}")
    
    valid, errors = handler.validate(augmented)
    print(f"\nValidation: {'PASS' if valid else 'FAIL'}")
    if errors:
        print(f"Errors: {errors}")
    
    order_key = handler.order_key(augmented)
    print(f"\nOrder key: {order_key}")