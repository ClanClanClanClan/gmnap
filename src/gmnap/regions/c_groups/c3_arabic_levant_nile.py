"""
C3 - Arabic Levant-Nile region implementation.

Covers: Iraq, Jordan, Lebanon, Syria, Palestine, Egypt, Sudan, South Sudan
Features: Arabic script, patronymic (ibn/bint), flexible order
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from src.regions.base import RegionRuleError, RegionSpec


class C3_ArabicLevantNile(RegionSpec):
    """
    Arabic Levant-Nile region (C3).
    
    Handles Arabic names from Levant and Nile regions:
    - Arabic script support
    - Patronymic handling (ibn, bint, abu, um)
    - Flexible name order
    - Romanization support
    """
    
    def __init__(self):
        super().__init__(
            code="C3",
            yaml_files=["c3_arabic_levant_nile.yaml"],
            scripts=["Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "DIN", "ISO"]
        )
        
        # Common patronymic/matrionymic patterns
        self.patronymic_patterns = {
            # Arabic patronymics
            "ibn": "son of",
            "ابن": "son of",
            "bin": "son of",
            "بن": "son of",
            "bint": "daughter of",
            "بنت": "daughter of",
            "abu": "father of",
            "أبو": "father of",
            "um": "mother of",
            "أم": "mother of",
            "umm": "mother of",
            
            # Regional variations
            "ould": "son of",  # Mauritanian
            "mint": "daughter of",  # Mauritanian
        }
        
        # Common titles to remove
        self.titles = {
            # Arabic titles
            "دكتور", "أستاذ", "بروفيسور", "مهندس", "محامي", "طبيب",
            "الشيخ", "الأستاذ", "الدكتور", "المهندس", "القاضي",
            "سيد", "سيدة", "آنسة", "حضرة", "معالي", "سعادة",
            
            # English equivalents
            "Dr", "Dr.", "Prof", "Prof.", "Professor", "Engineer",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.", "Sheikh",
            "His Excellency", "Her Excellency"
        }
        
        # Arabic character ranges
        self.arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]
        
        # Common Arabic name elements
        self.common_elements = {
            "عبد": "Abd",  # Servant of (Allah)
            "محمد": "Muhammad",
            "أحمد": "Ahmad",
            "علي": "Ali",
            "حسن": "Hassan",
            "حسين": "Hussein",
            "عمر": "Omar",
            "خالد": "Khalid",
            "يوسف": "Yusuf",
            "إبراهيم": "Ibrahim",
            "صالح": "Saleh",
            "عثمان": "Othman",
            "طارق": "Tariq",
            "نبيل": "Nabil",
            "وليد": "Walid"
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C3 rules."""
        # Clean canonical forms
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])
        
        # Clean variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])
    
    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        if not name:
            return name
        
        # Remove titles
        name = self._remove_titles(name)
        
        # Normalize whitespace
        name = " ".join(name.split())
        
        # Normalize punctuation
        name = self._normalize_punctuation(name)
        
        return name
    
    def _remove_titles(self, text: str) -> str:
        """Remove titles from text."""
        if not text:
            return text
        
        words = text.split()
        cleaned = []
        
        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            if clean_word not in self.titles:
                cleaned.append(word)
        
        return " ".join(cleaned)
    
    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name)
        
        # Handle Arabic punctuation
        name = name.replace('،', ', ')
        name = name.replace('؛', '; ')
        name = name.replace('؟', '?')
        name = name.replace('؍', '/')
        
        # Normalize dashes
        name = re.sub(r'[-—–]', '-', name)
        
        # Remove trailing punctuation
        name = re.sub(r'[,;:]$', '', name)
        
        return name.strip()
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C3-specific data."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return
        
        # Extract components
        components = self._extract_components(canonical)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        entry["RegionalExtras"].update(components)
        
        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        
        # Add romanized variant if original is Arabic
        if self._is_arabic(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
                # Update CanonicalLatin to be romanized
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append({
                    "str": romanized,
                    "type": "romanization"
                })
        
        # Add variant without patronymic
        if components.get("patronymic"):
            without_patronymic = self._generate_no_patronymic_variant(canonical, components)
            if without_patronymic and without_patronymic != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": without_patronymic,
                    "type": "no-patronymic"
                })
        
        # Add variant with definite article removed
        if components.get("has_definite_article"):
            without_article = self._remove_definite_article(canonical)
            if without_article != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": without_article,
                    "type": "no-article"
                })
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}
        
        # Split into words
        words = name.split()
        
        # Look for patronymic indicators
        patronymic_info = self._find_patronymic(words)
        if patronymic_info:
            components.update(patronymic_info)
        
        # Look for definite article (al-, el-, etc.)
        if self._has_definite_article(name):
            components["has_definite_article"] = True
        
        # Extract given and family names
        if patronymic_info and "patronymic_index" in patronymic_info:
            idx = patronymic_info["patronymic_index"]
            # Pattern: Given [Patronymic] Family
            if idx > 0:
                components["given_name"] = " ".join(words[:idx])
            if idx + 2 < len(words):
                components["family_name"] = " ".join(words[idx+2:])
        else:
            # No patronymic found - assume Given Family format
            if len(words) >= 2:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
            else:
                components["given_name"] = name
        
        return components
    
    def _find_patronymic(self, words: List[str]) -> Optional[Dict[str, Any]]:
        """Find patronymic indicators in word list."""
        for i, word in enumerate(words):
            word_lower = word.lower()
            if word_lower in self.patronymic_patterns or word in self.patronymic_patterns:
                return {
                    "patronymic": word,
                    "patronymic_index": i,
                    "patronymic_type": self.patronymic_patterns.get(word_lower, self.patronymic_patterns.get(word, "unknown"))
                }
        return None
    
    def _has_definite_article(self, name: str) -> bool:
        """Check if name contains definite article."""
        # Arabic definite article patterns
        articles = ["ال", "al-", "el-", "Al-", "El-"]
        for article in articles:
            if article in name:
                return True
        return False
    
    def _remove_definite_article(self, name: str) -> str:
        """Remove definite article from name."""
        # Remove Arabic definite article
        name = re.sub(r'\bال', '', name)
        name = re.sub(r'\bal-', '', name)
        name = re.sub(r'\bel-', '', name)
        name = re.sub(r'\bAl-', '', name)
        name = re.sub(r'\bEl-', '', name)
        
        # Normalize spaces
        name = " ".join(name.split())
        
        return name
    
    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                return True
        return False
    
    def _romanize_name(self, name: str) -> str:
        """Romanize Arabic name using ALA-LC standard."""
        # Simple romanization mapping (ALA-LC)
        romanization_map = {
            'ا': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'j', 'ح': 'h',
            'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z', 'س': 's',
            'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': '',
            'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm',
            'ن': 'n', 'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'h',
            'ء': '', 'أ': 'a', 'إ': 'i', 'آ': 'a', 'ؤ': 'u', 'ئ': 'i',
            
            # Vowel marks
            'َ': 'a', 'ُ': 'u', 'ِ': 'i', 'ً': 'an', 'ٌ': 'un', 'ٍ': 'in',
            'ْ': '', 'ّ': '', 'ٰ': 'a',
            
            # Numbers
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        result = []
        for char in name:
            if char in romanization_map:
                result.append(romanization_map[char])
            else:
                result.append(char)
        
        romanized = ''.join(result)
        
        # Clean up multiple spaces and capitalize
        romanized = " ".join(romanized.split())
        return romanized.title()
    
    def _generate_no_patronymic_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate variant without patronymic."""
        given = components.get("given_name", "")
        family = components.get("family_name", "")
        
        if given and family:
            return f"{given} {family}"
        elif given:
            return given
        
        return None
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to C3 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")
        
        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")
        
        # If CanonicalNative exists, it should be Arabic
        if canonical_native:
            if not self._is_arabic(canonical_native):
                raise RegionRuleError(f"CanonicalNative should be Arabic: {canonical_native}")
        
        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_arabic(canonical_latin):
                raise RegionRuleError(f"CanonicalLatin should be romanized: {canonical_latin}")
        
        # Check name structure
        for canonical in [canonical_native, canonical_latin]:
            if canonical:
                words = canonical.split()
                if len(words) < 2:
                    raise RegionRuleError(f"Name should have at least 2 words: {canonical}")
                
                # Check for invalid characters
                if not self._has_valid_characters(canonical):
                    raise RegionRuleError(f"Invalid characters in name: {canonical}")
    
    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters."""
        for char in name:
            # Allow Latin, Arabic, spaces, hyphens, apostrophes
            if char.isalpha() or char in " -'":
                continue
            # Check if it's valid Arabic
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                continue
            # Invalid character found
            return False
        return True
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        
        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        
        # Use romanized form for sorting if available
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        
        # If we have Arabic, romanize for sorting
        if self._is_arabic(canonical):
            canonical = self._romanize_name(canonical)
        
        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""
        
        # Remove punctuation for sorting
        sort_family = re.sub(r'[^\w\s]', '', sort_family)
        sort_given = re.sub(r'[^\w\s]', '', sort_given)
        
        # Generate key
        key = f"{sort_family} {sort_given}"
        
        # Ensure determinism
        key = " ".join(key.split())
        
        return key