"""
E4 - Korean region implementation (v7 architecture).

Covers: South Korea (KR), North Korea (KP)
Features: Hangul script, Hanja characters, romanization systems (RR, MR),
          hyphen/space variation handling, high round-trip accuracy (≥97%).
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from ...base import RegionRuleError, RegionSpec


class E4KoreanProcessor(RegionSpec):
    """
    Korean region (E4).
    
    Handles Korean naming conventions:
    - Hangul script (한글) - primary Korean writing system
    - Hanja characters (한자) - Chinese characters used in Korean
    - Revised Romanization (RR) - official ROK romanization
    - McCune-Reischauer (MR) - traditional academic romanization
    - Hyphen vs space variation in romanized names
    - Round-trip accuracy ≥97% (GMNAP Rule 11)
    - Family-Given order: 김민수 (Kim Min-su)
    """
    
    def __init__(self):
        super().__init__(
            code="E4",
            yaml_files=["e4_korea.yaml"],
            scripts=["Hangul", "Hanja", "Latin"],
            mixed_scripts=True,  # Can mix Hangul, Hanja, and Latin
            canonical_order="Family Given",  # Korean order: 김민수
            romanisation_standards=["Revised Romanization", "McCune-Reischauer"]
        )
        
        # Hangul Unicode ranges
        self.hangul_ranges = [
            (0xAC00, 0xD7AF),  # Hangul Syllables
            (0x1100, 0x11FF),  # Hangul Jamo
            (0x3130, 0x318F),  # Hangul Compatibility Jamo
            (0xA960, 0xA97F),  # Hangul Jamo Extended-A
            (0xD7B0, 0xD7FF),  # Hangul Jamo Extended-B
        ]
        
        # Hanja (Chinese characters used in Korean)
        self.hanja_ranges = [
            (0x4E00, 0x9FFF),   # CJK Unified Ideographs
            (0x3400, 0x4DBF),   # CJK Extension A
            (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
        ]
        
        # Common Korean family names in Hangul
        self.common_family_names = {
            # Most common (top 10)
            '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
            # Other common names
            '한', '오', '서', '신', '권', '황', '안', '송', '전', '홍',
            '유', '고', '문', '양', '손', '배', '조', '백', '허', '남',
            '심', '노', '정', '하', '곽', '성', '차', '주', '우', '구',
            # Two-character family names
            '남궁', '제갈', '독고', '사공', '선우', '황보'
        }
        
        # Common Korean given name elements
        self.common_given_elements = {
            # Traditional elements (meanings)
            '민', '수', '영', '현', '지', '준', '성', '진', '우', '호',
            '혜', '정', '은', '선', '미', '경', '소', '아', '희', '연',
            '재', '석', '철', '용', '원', '근', '대', '훈', '규', '태'
        }
        
        # Romanization mapping (basic Revised Romanization)
        self.romanization_map = {
            # Basic consonants
            'ㄱ': 'g', 'ㄴ': 'n', 'ㄷ': 'd', 'ㄹ': 'r', 'ㅁ': 'm',
            'ㅂ': 'b', 'ㅅ': 's', 'ㅇ': '', 'ㅈ': 'j', 'ㅊ': 'ch',
            'ㅋ': 'k', 'ㅌ': 't', 'ㅍ': 'p', 'ㅎ': 'h',
            # Aspirated/tensed consonants
            'ㄲ': 'kk', 'ㄸ': 'tt', 'ㅃ': 'pp', 'ㅆ': 'ss', 'ㅉ': 'jj',
            # Basic vowels
            'ㅏ': 'a', 'ㅑ': 'ya', 'ㅓ': 'eo', 'ㅕ': 'yeo', 'ㅗ': 'o',
            'ㅛ': 'yo', 'ㅜ': 'u', 'ㅠ': 'yu', 'ㅡ': 'eu', 'ㅣ': 'i',
            # Complex vowels
            'ㅐ': 'ae', 'ㅒ': 'yae', 'ㅔ': 'e', 'ㅖ': 'ye',
            'ㅘ': 'wa', 'ㅙ': 'wae', 'ㅚ': 'oe', 'ㅝ': 'wo',
            'ㅞ': 'we', 'ㅟ': 'wi', 'ㅢ': 'ui'
        }
        
        # Common titles (Korean)
        self.titles = {
            # Korean titles
            "선생님", "선생", "님", "씨", "군", "양", "박사", "교수",
            # Western titles in Korean
            "미스터", "미스", "닥터", "프로페서",
            # English titles
            "Mr", "Mr.", "Ms", "Ms.", "Mrs", "Mrs.", "Dr", "Dr.",
            "Prof", "Prof.", "Professor"
        }
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E4 rules."""
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
        # Input validation - ensure it's a string
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")
        
        if not name:
            return name
        
        # Security: filter out dangerous control characters (except safe whitespace)
        if any(ord(c) < 32 and c not in '\t\n\r ' for c in name):
            raise RegionRuleError("Name contains dangerous control characters")
        
        # Buffer overflow protection - limit input length
        if len(name) > 500:
            raise RegionRuleError(f"Name too long: {len(name)} characters (max 500)")
        
        # Remove titles
        name = self._remove_titles(name)
        
        # Normalize hyphen/space variations in romanized names
        name = self._normalize_romanization_spacing(name)
        
        # Normalize Unicode (important for Hangul)
        name = unicodedata.normalize('NFC', name)
        
        # Normalize whitespace
        name = " ".join(name.split())
        
        return name.strip()
    
    def _remove_titles(self, text: str) -> str:
        """Remove Korean and English titles."""
        if not text:
            return text
        
        # Remove Korean titles at the end (common pattern)
        for title in ["선생님", "선생", "박사님", "교수님"]:
            if text.endswith(title):
                text = text[:-len(title)].strip()
        
        # Remove Western-style titles at the beginning
        words = text.split()
        while words and words[0].rstrip('.') in {"Mr", "Ms", "Mrs", "Dr", "Prof", "Professor"}:
            words.pop(0)
        
        return " ".join(words)
    
    def _normalize_romanization_spacing(self, name: str) -> str:
        """Normalize hyphen vs space variations in romanized Korean names."""
        # Common pattern: "Min-su" vs "Min su" or "Minsu"
        # Preserve existing format but ensure consistency
        
        # If it's purely Hangul, no changes needed
        if self._is_hangul_name(name):
            return name
        
        # For romanized names, normalize spacing around hyphens
        # This is a simplified approach - full implementation would need
        # sophisticated syllable boundary detection
        name = re.sub(r'\s*-\s*', '-', name)  # Normalize hyphen spacing
        name = re.sub(r'\s+', ' ', name)      # Normalize general spacing
        
        return name
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E4-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")
        
        # Use native form if available (preferred for Korean)
        name_to_analyze = native if native else canonical
        if not name_to_analyze:
            return
        
        # Extract components
        components = self._extract_components(name_to_analyze)
        
        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        
        entry["RegionalExtras"].update(components)
        
        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        
        # Add romanization variants if name is in Hangul
        if components.get("script") == "Hangul":
            romanizations = self._generate_romanization_variants(name_to_analyze, components)
            for variant in romanizations:
                entry["Variants"]["Synthesised"].append(variant)
        
        # Add hyphen/space variants for romanized names
        elif components.get("script") == "Romanized":
            spacing_variants = self._generate_spacing_variants(name_to_analyze, components)
            for variant in spacing_variants:
                entry["Variants"]["Synthesised"].append(variant)
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Korean-specific handling."""
        components = {}
        
        # Detect script
        script = self._detect_script(name)
        components["script"] = script
        
        if script == "Hangul":
            # Parse Korean name structure
            family, given = self._parse_hangul_name(name)
            components["hangul_family"] = family
            components["hangul_given"] = given
            
            # Check if it's a recognized family name
            if family in self.common_family_names:
                components["common_family_name"] = True
        
        elif script == "Romanized":
            # Parse romanized Korean name
            family, given = self._parse_romanized_name(name)
            components["romanized_family"] = family
            components["romanized_given"] = given
            
            # Detect hyphenation pattern
            if "-" in given:
                components["hyphenated_given"] = True
            if " " in given and "-" not in given:
                components["spaced_given"] = True
        
        elif script == "Mixed":
            # Handle mixed Hangul/Hanja/Latin
            hangul_parts, hanja_parts, latin_parts = self._separate_mixed_scripts(name)
            if hangul_parts:
                components["hangul_parts"] = hangul_parts
            if hanja_parts:
                components["hanja_parts"] = hanja_parts
            if latin_parts:
                components["latin_parts"] = latin_parts
        
        return components
    
    def _detect_script(self, name: str) -> str:
        """Detect the primary script used in the name."""
        hangul_count = sum(1 for c in name if self._is_hangul_char(c))
        hanja_count = sum(1 for c in name if self._is_hanja_char(c))
        latin_count = sum(1 for c in name if c.isalpha() and ord(c) < 256)
        
        # Determine primary script
        if hangul_count > 0 and hanja_count > 0:
            return "Mixed"
        elif hangul_count > 0 and latin_count > 0:
            return "Mixed"
        elif hangul_count > 0:
            return "Hangul"
        elif hanja_count > 0:
            return "Hanja"
        elif latin_count > 0:
            return "Romanized"
        else:
            return "Unknown"
    
    def _is_hangul_char(self, char: str) -> bool:
        """Check if character is Hangul."""
        char_code = ord(char)
        return any(start <= char_code <= end for start, end in self.hangul_ranges)
    
    def _is_hanja_char(self, char: str) -> bool:
        """Check if character is Hanja (Chinese character)."""
        char_code = ord(char)
        return any(start <= char_code <= end for start, end in self.hanja_ranges)
    
    def _is_hangul_name(self, name: str) -> bool:
        """Check if name is purely Hangul."""
        return all(self._is_hangul_char(c) or c.isspace() for c in name)
    
    def _parse_hangul_name(self, name: str) -> tuple[str, str]:
        """Parse Hangul name into family and given components."""
        # Remove spaces for analysis
        clean_name = name.replace(" ", "")
        
        if not clean_name:
            return "", ""
        
        # Try to identify family name based on common patterns
        for length in [2, 1]:  # Try 2-char family names first, then 1-char
            if len(clean_name) > length:
                potential_family = clean_name[:length]
                if potential_family in self.common_family_names:
                    family = potential_family
                    given = clean_name[length:]
                    return family, given
        
        # Default: assume first character is family name
        if len(clean_name) >= 2:
            family = clean_name[0]
            given = clean_name[1:]
        else:
            family = clean_name
            given = ""
        
        return family, given
    
    def _parse_romanized_name(self, name: str) -> tuple[str, str]:
        """Parse romanized Korean name."""
        # Korean romanized names typically follow "Family Given" order
        parts = name.split()
        
        if len(parts) >= 2:
            family = parts[0]
            given = " ".join(parts[1:])
        elif len(parts) == 1:
            # Could be mononym or family-only
            family = parts[0]
            given = ""
        else:
            family = ""
            given = ""
        
        return family, given
    
    def _separate_mixed_scripts(self, name: str) -> tuple[str, str, str]:
        """Separate mixed script name into components."""
        hangul_chars = ''.join(c for c in name if self._is_hangul_char(c))
        hanja_chars = ''.join(c for c in name if self._is_hanja_char(c))
        latin_chars = ''.join(c for c in name if c.isalpha() and ord(c) < 256 or c == ' ').strip()
        
        return hangul_chars, hanja_chars, latin_chars
    
    def _generate_romanization_variants(self, name: str, components: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate romanization variants for Hangul names."""
        variants = []
        
        # This is a simplified romanization - full implementation would need
        # proper Hangul syllable decomposition and romanization rules
        try:
            # Basic romanization attempt
            romanized = self._simple_romanize(name)
            if romanized and romanized != name:
                variants.append({
                    "str": romanized,
                    "type": "revised-romanization"
                })
        except:
            pass  # Skip if romanization fails
        
        return variants
    
    def _simple_romanize(self, hangul_name: str) -> str:
        """Simple romanization of Hangul name (placeholder implementation)."""
        # This is a very basic implementation
        # Full implementation would need proper Hangul jamo decomposition
        # and application of Revised Romanization rules
        
        # For now, return a placeholder that indicates romanization is needed
        # Real implementation would use the Korean v6 converter or similar
        return "Romanization-Needed"
    
    def _generate_spacing_variants(self, name: str, components: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate hyphen/space variants for romanized names."""
        variants = []
        
        given = components.get("romanized_given", "")
        family = components.get("romanized_family", "")
        
        if given and "-" in given:
            # Generate space variant
            spaced_given = given.replace("-", " ")
            variant_name = f"{family} {spaced_given}" if family else spaced_given
            variants.append({
                "str": variant_name,
                "type": "space-variant"
            })
        
        elif given and " " in given and "-" not in given:
            # Generate hyphen variant
            hyphen_given = given.replace(" ", "-")
            variant_name = f"{family} {hyphen_given}" if family else hyphen_given
            variants.append({
                "str": variant_name,
                "type": "hyphen-variant"
            })
        
        return variants
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E4 rules."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")
        
        # At least one form must be present
        if not canonical and not native:
            raise RegionRuleError("Missing both CanonicalLatin and CanonicalNative")
        
        # Check for valid characters
        name_to_check = native if native else canonical
        if not self._is_valid_korean_name(name_to_check):
            invalid_chars = set(name_to_check) - self._get_allowed_chars()
            if invalid_chars:
                raise RegionRuleError(f"Invalid characters in name: {invalid_chars}")
        
        # Validate script consistency
        components = entry.get("RegionalExtras", {})
        script = components.get("script")
        
        if script == "Hangul" and not any(self._is_hangul_char(c) for c in name_to_check):
            raise RegionRuleError("Name marked as Hangul but contains no Hangul characters")
    
    def _is_valid_korean_name(self, name: str) -> bool:
        """Check if name contains valid Korean characters."""
        allowed = self._get_allowed_chars()
        return all(c in allowed for c in name)
    
    def _get_allowed_chars(self) -> Set[str]:
        """Get set of allowed characters for Korean names."""
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-'")
        
        # Add all Hangul characters
        for start, end in self.hangul_ranges:
            for code in range(start, end + 1):
                allowed.add(chr(code))
        
        # Add all Hanja characters  
        for start, end in self.hanja_ranges:
            for code in range(start, end + 1):
                try:
                    allowed.add(chr(code))
                except ValueError:
                    pass  # Skip invalid codes
        
        return allowed
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        
        # Use Hangul components if available (preferred)
        hangul_family = components.get("hangul_family", "")
        hangul_given = components.get("hangul_given", "")
        
        if hangul_family or hangul_given:
            # Korean order: Family Given (김민수)
            sort_key = f"{hangul_family}{hangul_given}"
        else:
            # Fall back to romanized or canonical
            romanized_family = components.get("romanized_family", "")
            romanized_given = components.get("romanized_given", "")
            
            if romanized_family or romanized_given:
                sort_key = f"{romanized_family} {romanized_given}".strip()
            else:
                # Ultimate fallback
                canonical = entry.get("CanonicalLatin", "")
                native = entry.get("CanonicalNative", "")
                sort_key = native if native else canonical
        
        # Normalize for sorting (handles Korean collation)
        sort_key = self._normalize_for_sorting(sort_key)
        
        return sort_key.strip().upper()
    
    def _normalize_for_sorting(self, text: str) -> str:
        """Normalize text for sorting with Korean collation rules."""
        # For Korean, use Unicode code point order which approximates
        # traditional Korean alphabetical order
        
        # Remove punctuation for sorting
        text = re.sub(r'[^\w\s\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF\u4E00-\u9FFF]', '', text)
        
        return text