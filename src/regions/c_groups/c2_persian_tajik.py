"""
C2 - Persian-Tajik region implementation.

Covers: Iran, Afghanistan, Tajikistan
Features: Persian/Dari/Tajik scripts, patronymic patterns, flexible order
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C2_PersianTajik(RegionSpec):
    """
    Persian-Tajik region (C2).
    
    Handles Persian, Dari, and Tajik names:
    - Persian script support (Arabic-derived)
    - Cyrillic script for Tajik
    - Patronymic patterns
    - Flexible name order
    """
    
    def __init__(self):
        super().__init__(
            code="C2",
            yaml_files=["c2_persian_tajik.yaml"],
            scripts=["Persian", "Cyrillic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "Scientific"]
        )
        
        # Common Persian/Tajik patronymic patterns
        self.patronymic_patterns = {
            # Persian/Dari
            "پسر": "son of",
            "دختر": "daughter of",
            "بن": "son of",
            "بنت": "daughter of",
            
            # Tajik (Cyrillic)
            "писар": "son of",
            "духтар": "daughter of",
        }
        
        # Common titles to remove
        self.titles = {
            # Persian/Dari titles
            "دکتر", "پروفسور", "استاد", "مهندس", "آقای", "خانم",
            "حاج", "حاجی", "میرزا", "خان", "بیگم",
            
            # Tajik titles
            "доктор", "профессор", "устод", "мухандис", "ҷаноб",
            "хонум", "хоҷа", "хон", "бегум",
            
            # English equivalents
            "Dr", "Dr.", "Prof", "Prof.", "Professor", "Engineer",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms."
        }
        
        # Persian character ranges
        self.persian_ranges = [
            (0x0600, 0x06FF),  # Arabic (used for Persian)
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]
        
        # Cyrillic character ranges (for Tajik)
        self.cyrillic_ranges = [
            (0x0400, 0x04FF),  # Cyrillic
            (0x0500, 0x052F),  # Cyrillic Supplement
        ]
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C2 rules."""
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
        
        # Handle Persian punctuation
        name = name.replace('،', ', ')
        name = name.replace('؛', '; ')
        name = name.replace('؟', '?')
        
        # Normalize dashes
        name = re.sub(r'[-—–]', '-', name)
        
        # Remove trailing punctuation
        name = re.sub(r'[,;:]$', '', name)
        
        return name.strip()
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C2-specific data."""
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
        
        # Add romanized variant if original is Persian/Tajik
        if self._is_persian_or_tajik(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
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
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}
        
        # Split into words
        words = name.split()
        
        # Look for patronymic indicators
        patronymic_idx = None
        for i, word in enumerate(words):
            if word in self.patronymic_patterns:
                patronymic_idx = i
                components["patronymic"] = word
                components["patronymic_type"] = self.patronymic_patterns[word]
                break
        
        # Extract given and family names
        if patronymic_idx is not None:
            # Pattern: Given [Patronymic] Family
            if patronymic_idx > 0:
                components["given_name"] = " ".join(words[:patronymic_idx])
            if patronymic_idx + 1 < len(words):
                components["family_name"] = " ".join(words[patronymic_idx + 1:])
        else:
            # No patronymic found - assume Given Family format
            if len(words) >= 2:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
            else:
                components["given_name"] = name
        
        # Detect script
        if self._is_persian(name):
            components["script"] = "Persian"
        elif self._is_cyrillic(name):
            components["script"] = "Cyrillic"
        else:
            components["script"] = "Latin"
        
        return components
    
    def _is_persian_or_tajik(self, text: str) -> bool:
        """Check if text contains Persian or Tajik characters."""
        return self._is_persian(text) or self._is_cyrillic(text)
    
    def _is_persian(self, text: str) -> bool:
        """Check if text contains Persian characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.persian_ranges):
                return True
        return False
    
    def _is_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.cyrillic_ranges):
                return True
        return False
    
    def _romanize_name(self, name: str) -> str:
        """Romanize Persian/Tajik name."""
        if self._is_persian(name):
            return self._romanize_persian(name)
        elif self._is_cyrillic(name):
            return self._romanize_cyrillic(name)
        else:
            return name
    
    def _romanize_persian(self, name: str) -> str:
        """Romanize Persian text using ALA-LC standard."""
        # Simple Persian romanization mapping
        persian_map = {
            'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 'th', 'ج': 'j',
            'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'dh', 'ر': 'r',
            'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z',
            'ط': 't', 'ظ': 'z', 'ع': '', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
            'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'و': 'v',
            'ه': 'h', 'ی': 'y', 'ء': '',
            
            # Vowel marks
            'َ': 'a', 'ُ': 'u', 'ِ': 'i', 'ً': 'an', 'ٌ': 'un', 'ٍ': 'in',
            'ْ': '', 'ّ': '', 'ٰ': 'a',
        }
        
        result = []
        for char in name:
            if char in persian_map:
                result.append(persian_map[char])
            else:
                result.append(char)
        
        romanized = ''.join(result)
        romanized = " ".join(romanized.split())
        return romanized.title()
    
    def _romanize_cyrillic(self, name: str) -> str:
        """Romanize Tajik Cyrillic text."""
        # Simple Tajik romanization mapping
        tajik_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ғ': 'gh', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'ӣ': 'i',
            'й': 'y', 'к': 'k', 'қ': 'q', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ӯ': 'u', 'ф': 'f', 'х': 'kh', 'ҳ': 'h', 'ч': 'ch', 'ҷ': 'j',
            'ш': 'sh', 'ъ': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            
            # Uppercase
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Ғ': 'Gh', 'Д': 'D',
            'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Ӣ': 'I',
            'Й': 'Y', 'К': 'K', 'Қ': 'Q', 'Л': 'L', 'М': 'M', 'Н': 'N',
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ӯ': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ҳ': 'H', 'Ч': 'Ch', 'Ҷ': 'J',
            'Ш': 'Sh', 'Ъ': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        }
        
        result = []
        for char in name:
            if char in tajik_map:
                result.append(tajik_map[char])
            else:
                result.append(char)
        
        return ''.join(result)
    
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
        """Validate entry according to C2 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")
        
        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")
        
        # If CanonicalNative exists, it should be Persian or Cyrillic
        if canonical_native:
            if not self._is_persian_or_tajik(canonical_native):
                raise RegionRuleError(f"CanonicalNative should be Persian or Tajik: {canonical_native}")
        
        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_persian_or_tajik(canonical_latin):
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
            # Allow Latin, Persian, Cyrillic, spaces, hyphens, apostrophes
            if char.isalpha() or char in " -'":
                continue
            # Check if it's valid Persian
            if any(start <= ord(char) <= end for start, end in self.persian_ranges):
                continue
            # Check if it's valid Cyrillic
            if any(start <= ord(char) <= end for start, end in self.cyrillic_ranges):
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
        
        # If we have Persian/Tajik, romanize for sorting
        if self._is_persian_or_tajik(canonical):
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