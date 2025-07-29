"""
C4 - Arabic Gulf region implementation.

Covers: Saudi Arabia, UAE, Kuwait, Bahrain, Qatar, Oman, Yemen
Features: Arabic script, tribal prefixes (Al-), patronymic patterns, royal titles
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from gmnap.regions.base import RegionRuleError, RegionSpec


class C4_ArabicGulf(RegionSpec):
    """
    Arabic Gulf region (C4).
    
    Handles Arabic names from Gulf countries:
    - Arabic script support
    - Tribal/family prefixes (Al-, Bin-, etc.)
    - Patronymic handling
    - Royal and honorific titles
    - Romanization support
    """
    
    def __init__(self):
        super().__init__(
            code="C4",
            yaml_files=["c4_arabic_gulf.yaml"],
            scripts=["Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC", "BGN/PCGN", "DIN", "ISO"]
        )
        
        # Common patronymic patterns in Gulf countries
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
        }
        
        # Common tribal/family prefixes in Gulf countries
        self.family_prefixes = {
            "Al", "آل",  # Family/tribe of
            "Aal", "آل",  # Alternative spelling
            "Bani", "بني",  # Sons/tribe of
            "Banu", "بنو",  # Sons/tribe of
        }
        
        # Common titles and honorifics
        self.titles = {
            # Royal titles
            "الأمير", "أمير", "Prince", "Amir",
            "الأميرة", "أميرة", "Princess", "Amira",
            "الشيخ", "شيخ", "Sheikh", "Shaikh",
            "الشيخة", "شيخة", "Sheikha", "Shaikha",
            "الملك", "ملك", "King", "Malik",
            "الملكة", "ملكة", "Queen", "Malika",
            "السلطان", "سلطان", "Sultan",
            "السلطانة", "سلطانة", "Sultana",
            
            # Professional titles
            "دكتور", "د.", "Dr", "Dr.",
            "أستاذ", "Professor", "Prof", "Prof.",
            "مهندس", "Engineer", "Eng", "Eng.",
            "طبيب", "Physician",
            "محامي", "Lawyer",
            
            # Honorifics
            "سيد", "سيدة", "آنسة",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.",
            "حضرة", "معالي", "سعادة", "فخامة",
            "His Excellency", "Her Excellency",
            "His Highness", "Her Highness",
            "HE", "HH", "H.E.", "H.H."
        }
        
        # Arabic character ranges
        self.arabic_ranges = [
            (0x0600, 0x06FF),  # Arabic
            (0x0750, 0x077F),  # Arabic Supplement
            (0x08A0, 0x08FF),  # Arabic Extended-A
            (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
            (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
        ]
        
        # Common Gulf region name elements
        self.common_elements = {
            # Religious names
            "عبد": "Abd",  # Servant of
            "عبدالله": "Abdullah",
            "عبدالعزيز": "Abdulaziz",
            "عبدالرحمن": "Abdulrahman",
            "محمد": "Muhammad",
            "أحمد": "Ahmad",
            "علي": "Ali",
            "حسن": "Hassan",
            "حسين": "Hussein",
            
            # Common Gulf names
            "سلطان": "Sultan",
            "سعود": "Saud",
            "فيصل": "Faisal",
            "خالد": "Khalid",
            "نايف": "Naif",
            "تركي": "Turki",
            "سلمان": "Salman",
            "فهد": "Fahd",
            "ناصر": "Nasser",
            "حمد": "Hamad",
            "راشد": "Rashid",
            "زايد": "Zayed",
            "مبارك": "Mubarak",
            "صباح": "Sabah",
            "جابر": "Jaber"
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C4 rules."""
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
        
        # Handle Al- prefix normalization
        name = self._normalize_al_prefix(name)
        
        return name
    
    def _remove_titles(self, text: str) -> str:
        """Remove titles from text."""
        if not text:
            return text
        
        words = text.split()
        
        # If the text is just a single title, keep it (common in Gulf names)
        if len(words) == 1 and words[0].rstrip(".,") in self.titles:
            return text
        
        cleaned = []
        skip_next = False
        
        for i, word in enumerate(words):
            if skip_next:
                skip_next = False
                continue
                
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            
            # Check if it's a title
            if clean_word in self.titles:
                # Some titles are multi-word (e.g., "His Excellency")
                if i + 1 < len(words) and f"{clean_word} {words[i+1].rstrip('.,')}" in self.titles:
                    skip_next = True
                continue
                
            cleaned.append(word)
        
        # If cleaning removed everything, return the original (it was all titles)
        if not cleaned:
            return text
            
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
    
    def _normalize_al_prefix(self, name: str) -> str:
        """Normalize Al- prefix variations."""
        # Normalize different Al- prefix variations
        name = re.sub(r'\bAL-', 'Al-', name, flags=re.IGNORECASE)
        name = re.sub(r'\bal\s+', 'Al-', name, flags=re.IGNORECASE)
        name = re.sub(r'\bAl\s+', 'Al-', name)
        
        # Handle Arabic ال prefix
        name = re.sub(r'\bال\s+', 'ال', name)
        
        return name
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C4-specific data."""
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
        
        # Add variant with Al- prefix variations
        al_variants = self._generate_al_variants(canonical)
        for variant in al_variants:
            if variant != canonical:
                entry["Variants"]["Synthesised"].append({
                    "str": variant,
                    "type": "al-variant"
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
        
        # Look for tribal/family prefixes
        if self._has_family_prefix(name):
            components["has_family_prefix"] = True
        
        # Extract given and family names
        if patronymic_info and "patronymic_index" in patronymic_info:
            idx = patronymic_info["patronymic_index"]
            # Pattern: Given [Patronymic Father] Family
            if idx > 0:
                components["given_name"] = " ".join(words[:idx])
            if idx + 2 < len(words):
                components["family_name"] = " ".join(words[idx+2:])
            components["father_name"] = words[idx+1] if idx+1 < len(words) else ""
        else:
            # No patronymic - analyze structure
            # Common pattern in Gulf: Given [Father] Al-Family
            family_start = self._find_family_start(words)
            if family_start > 0:
                components["given_name"] = words[0]
                if family_start > 1:
                    components["father_name"] = " ".join(words[1:family_start])
                components["family_name"] = " ".join(words[family_start:])
            else:
                # Default: Given Family
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
    
    def _find_family_start(self, words: List[str]) -> int:
        """Find where family name starts (usually with Al- prefix)."""
        for i, word in enumerate(words):
            if word.startswith("Al-") or word.startswith("ال") or word in self.family_prefixes:
                return i
        return -1
    
    def _has_family_prefix(self, name: str) -> bool:
        """Check if name contains family/tribal prefix."""
        prefixes = ["Al-", "ال", "Aal", "آل", "Bani", "بني", "Banu", "بنو"]
        for prefix in prefixes:
            if prefix in name:
                return True
        return False
    
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
        
        # Handle Al- prefix capitalization
        romanized = re.sub(r'\bal-', 'Al-', romanized, flags=re.IGNORECASE)
        
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
    
    def _generate_al_variants(self, name: str) -> List[str]:
        """Generate variants with different Al- prefix forms."""
        variants = []
        
        # If name has Al-, generate variant with al-
        if "Al-" in name:
            variants.append(name.replace("Al-", "al-"))
        
        # If name has al-, generate variant with Al-
        if "al-" in name:
            variants.append(name.replace("al-", "Al-"))
        
        # If name has ال, generate romanized variants
        if "ال" in name:
            romanized = self._romanize_name(name)
            if romanized not in variants:
                variants.append(romanized)
        
        return variants
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to C4 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")
        
        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")
        
        # If CanonicalNative exists, it should be Arabic
        if canonical_native:
            if not self._is_arabic(canonical_native) and not self._is_mixed_script(canonical_native):
                raise RegionRuleError(f"CanonicalNative should contain Arabic: {canonical_native}")
        
        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_arabic(canonical_latin) and not self._is_mixed_script(canonical_latin):
                raise RegionRuleError(f"CanonicalLatin should be romanized: {canonical_latin}")
        
        # Check name structure
        for canonical in [canonical_native, canonical_latin]:
            if canonical:
                words = canonical.split()
                # Allow single-word names for titles or tribal names
                if len(words) < 1:
                    raise RegionRuleError(f"Name cannot be empty: {canonical}")
                
                # Single word is OK if it's a title or tribal name
                if len(words) == 1:
                    word = words[0]
                    # Check if it's a known title or starts with Al-/ال
                    if not (word in self.titles or 
                            word.startswith("Al-") or word.startswith("ال") or
                            word in self.family_prefixes):
                        # For now, be lenient with single words
                        pass  # Don't reject single words
                
                # Check for invalid characters
                if not self._has_valid_characters(canonical):
                    raise RegionRuleError(f"Invalid characters in name: {canonical}")
    
    def _is_mixed_script(self, text: str) -> bool:
        """Check if text contains both Arabic and Latin scripts."""
        has_arabic = False
        has_latin = False
        
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                has_arabic = True
            elif char.isalpha() and ord(char) < 256:
                has_latin = True
        
        return has_arabic and has_latin
    
    def _has_valid_characters(self, name: str) -> bool:
        """Check if name contains valid characters."""
        for char in name:
            # Allow Latin, Arabic, spaces, hyphens, apostrophes
            if char.isalpha() or char in " -'":
                continue
            # Check if it's valid Arabic
            if any(start <= ord(char) <= end for start, end in self.arabic_ranges):
                continue
            # Allow digits in some contexts (e.g., III, 3rd)
            if char.isdigit():
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
        father = components.get("father_name", "")
        
        # Use romanized form for sorting if available
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        
        # If we have Arabic, romanize for sorting
        if self._is_arabic(canonical):
            canonical = self._romanize_name(canonical)
        
        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""
        sort_father = father.upper() if father else ""
        
        # Remove punctuation for sorting
        sort_family = re.sub(r'[^\w\s]', '', sort_family)
        sort_given = re.sub(r'[^\w\s]', '', sort_given)
        sort_father = re.sub(r'[^\w\s]', '', sort_father)
        
        # Generate key: Family, Given Father
        key_parts = [sort_family]
        if sort_given:
            key_parts.append(sort_given)
        if sort_father:
            key_parts.append(sort_father)
        
        key = " ".join(key_parts)
        
        # Ensure determinism
        key = " ".join(key.split())
        
        return key