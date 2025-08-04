"""
E1 - Sinophone Mainland region implementation.

Covers: Mainland China (PRC)
Features: Simplified Chinese characters, pinyin romanization, family-given order
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class E1_SinophoneMainland(RegionSpec):
    """
    Sinophone Mainland region (E1).
    
    Handles mainland Chinese names:
    - Simplified Chinese characters
    - Pinyin romanization
    - Family-Given order
    - Generation names
    """
    
    def __init__(self):
        super().__init__(
            code="E1",
            yaml_files=["e1_sinophone_mainland.yaml"],
            scripts=["Simplified Chinese"],
            mixed_scripts=True,
            canonical_order="Family Given",
            romanisation_standards=["Pinyin", "Wade-Giles"]
        )
        
        # Common Chinese surnames (top 100)
        self.common_surnames = {
            "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
            "徐", "孙", "朱", "马", "胡", "郭", "林", "何", "高", "梁",
            "郑", "罗", "宋", "谢", "唐", "韩", "曹", "许", "邓", "萧",
            "冯", "曾", "程", "蔡", "彭", "潘", "袁", "于", "董", "余",
            "苏", "叶", "吕", "魏", "蒋", "田", "杜", "丁", "沈", "姜",
            "范", "江", "傅", "钟", "卢", "汪", "戴", "崔", "任", "陆",
            "廖", "姚", "方", "金", "邱", "夏", "谭", "韦", "贾", "邹",
            "石", "熊", "孟", "秦", "阎", "薛", "侯", "雷", "白", "龙",
            "段", "郝", "孔", "邵", "史", "毛", "常", "万", "顾", "赖",
            "武", "康", "贺", "严", "尹", "钱", "施", "牛", "洪", "龚"
        }
        
        # Common titles to remove
        self.titles = {
            "教授", "博士", "硕士", "学士", "院士", "研究员", "讲师", "副教授",
            "先生", "女士", "小姐", "同志", "老师", "主任", "经理", "总裁",
            "Prof", "Dr", "Mr", "Mrs", "Ms", "Professor", "Doctor"
        }
        
        # CJK character ranges
        self.cjk_ranges = [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x20000, 0x2A6DF), # CJK Extension B
            (0x2A700, 0x2B73F), # CJK Extension C
            (0x2B740, 0x2B81F), # CJK Extension D
            (0x2B820, 0x2CEAF), # CJK Extension E
            (0x2CEB0, 0x2EBEF), # CJK Extension F
            (0x3000, 0x303F),  # CJK Symbols and Punctuation
            (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
        ]
    
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E1 rules."""
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
        
        # Handle Chinese punctuation
        name = name.replace('，', ', ')
        name = name.replace('。', '.')
        name = name.replace('！', '!')
        name = name.replace('？', '?')
        
        # Remove trailing punctuation
        name = re.sub(r'[,;:]$', '', name)
        
        return name.strip()
    
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E1-specific data."""
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
        
        # Add pinyin variant if original is Chinese
        if self._is_chinese(canonical):
            # Only generate pinyin if CanonicalLatin is not already romanized
            canonical_latin = entry.get("CanonicalLatin", "")
            if not canonical_latin or self._is_chinese(canonical_latin):
                pinyin = self._generate_pinyin(canonical)
                if pinyin != canonical:
                    # Update CanonicalLatin to be romanized
                    entry["CanonicalLatin"] = pinyin
                    entry["Variants"]["Synthesised"].append({
                        "str": pinyin,
                    "type": "pinyin"
                })
        
        # Add traditional character variant
        traditional = self._to_traditional(canonical)
        if traditional != canonical:
            entry["Variants"]["Synthesised"].append({
                "str": traditional,
                "type": "traditional"
            })
    
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}
        
        if self._is_chinese(name):
            # Chinese names are typically 2-4 characters
            # First character(s) are family name, rest are given name
            if len(name) >= 2:
                # Common pattern: 1 char family + 1-2 char given
                if name[0] in self.common_surnames:
                    components["family_name"] = name[0]
                    components["given_name"] = name[1:]
                elif len(name) >= 3:
                    # Try 2-char family name
                    two_char_family = name[:2]
                    if self._is_compound_surname(two_char_family):
                        components["family_name"] = two_char_family
                        components["given_name"] = name[2:]
                    else:
                        # Default to 1-char family
                        components["family_name"] = name[0]
                        components["given_name"] = name[1:]
                else:
                    # Single character name (rare)
                    components["family_name"] = name
        else:
            # Romanized name - assume space-separated
            words = name.split()
            if len(words) >= 2:
                components["family_name"] = words[0]
                components["given_name"] = " ".join(words[1:])
            else:
                components["family_name"] = name
        
        return components
    
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.cjk_ranges):
                return True
        return False
    
    def _is_compound_surname(self, surname: str) -> bool:
        """Check if it's a known compound surname."""
        # Common compound surnames in Chinese
        compound_surnames = {
            "司马", "欧阳", "夏侯", "诸葛", "上官", "太史", "端木", "申屠",
            "公孙", "慕容", "鲜于", "宇文", "长孙", "公羊", "淳于", "单于",
            "东方", "西门", "南宫", "北堂", "司徒", "司空", "司寇", "太叔"
        }
        return surname in compound_surnames
    
    def _generate_pinyin(self, name: str) -> str:
        """Generate pinyin romanization."""
        # This is a simplified pinyin generator
        # In a real implementation, you'd use a proper pinyin library
        
        # Basic character to pinyin mapping (very limited)
        pinyin_map = {
            # Common surnames
            "王": "Wang", "李": "Li", "张": "Zhang", "刘": "Liu", "陈": "Chen",
            "杨": "Yang", "黄": "Huang", "赵": "Zhao", "周": "Zhou", "吴": "Wu",
            "徐": "Xu", "孙": "Sun", "朱": "Zhu", "马": "Ma", "胡": "Hu",
            "郭": "Guo", "林": "Lin", "何": "He", "高": "Gao", "梁": "Liang",
            
            # Common given name characters
            "明": "Ming", "华": "Hua", "伟": "Wei", "强": "Qiang", "军": "Jun",
            "丽": "Li", "静": "Jing", "敏": "Min", "芳": "Fang", "英": "Ying",
            "娜": "Na", "秀": "Xiu", "红": "Hong", "霞": "Xia", "燕": "Yan",
            "东": "Dong", "南": "Nan", "西": "Xi", "北": "Bei", "中": "Zhong",
            "国": "Guo", "建": "Jian", "文": "Wen", "志": "Zhi", "德": "De",
            "义": "Yi", "礼": "Li", "智": "Zhi", "信": "Xin", "仁": "Ren",
            "小": "Xiao", "大": "Da", "天": "Tian", "人": "Ren", "山": "Shan",
            "水": "Shui", "火": "Huo", "土": "Tu", "金": "Jin", "木": "Mu"
        }
        
        result = []
        for char in name:
            if char in pinyin_map:
                result.append(pinyin_map[char])
            else:
                # Fallback - use romanized approximation
                # This is a simplified approach - in reality you'd use a proper pinyin library
                result.append(f"[{char}]")
        
        # For Chinese names, join with spaces: Family Given
        if len(result) == 3:  # Common pattern: 1 char family + 2 char given
            return f"{result[0]} {result[1]}{result[2]}"
        elif len(result) == 2:  # Pattern: 1 char family + 1 char given
            return f"{result[0]} {result[1]}"
        else:
            return " ".join(result)
    
    def _to_traditional(self, name: str) -> str:
        """Convert simplified to traditional characters."""
        # Simple mapping (very limited)
        traditional_map = {
            "国": "國", "华": "華", "经": "經", "学": "學", "书": "書",
            "长": "長", "门": "門", "车": "車", "马": "馬", "鸟": "鳥",
            "鱼": "魚", "龙": "龍", "电": "電", "风": "風", "飞": "飛",
            "时": "時", "间": "間", "开": "開", "关": "關", "头": "頭",
            "团": "團", "选": "選", "连": "連", "过": "過", "对": "對",
            "观": "觀", "现": "現", "实": "實", "宝": "寶", "贝": "貝"
        }
        
        result = []
        for char in name:
            if char in traditional_map:
                result.append(traditional_map[char])
            else:
                result.append(char)
        
        return "".join(result)
    
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E1 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")
        
        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")
        
        # If CanonicalNative exists, it should be Chinese
        if canonical_native:
            if not self._is_chinese(canonical_native):
                raise RegionRuleError(f"CanonicalNative should be Chinese: {canonical_native}")
            
            # Check length - Chinese names are typically 2-4 characters
            if len(canonical_native) < 2 or len(canonical_native) > 4:
                raise RegionRuleError(f"Chinese name length unusual: {canonical_native}")
        
        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_chinese(canonical_latin):
                raise RegionRuleError(f"CanonicalLatin should be romanized: {canonical_latin}")
            
            # Check for valid pinyin pattern
            if not self._is_valid_pinyin(canonical_latin):
                raise RegionRuleError(f"Invalid pinyin format: {canonical_latin}")
        
        # Rule 11: CJK Round-Trip ≥97% Dice coefficient validation (V7 requirement)
        if canonical_native and canonical_latin:
            dice_score = self._validate_cjk_roundtrip(canonical_native, canonical_latin)
            if dice_score < 0.97:
                raise RegionRuleError(f"Rule 11 violation: CJK round-trip Dice coefficient {dice_score:.3f} < 0.97")
    
    def _is_valid_pinyin(self, text: str) -> bool:
        """Check if text is valid pinyin."""
        # Remove punctuation for validation
        text_clean = text.replace(',', ' ').replace('.', ' ')
        # Basic pinyin validation
        words = text_clean.split()
        for word in words:
            # Should only contain Latin letters and basic marks
            if word and not re.match(r'^[a-zA-ZüÜ]+$', word):
                return False
        return True
    
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})
        
        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        
        # Use pinyin for sorting if available
        canonical = entry.get("CanonicalLatin", "")
        
        # If no Latin form, generate pinyin
        if not canonical:
            native = entry.get("CanonicalNative", "")
            if native and self._is_chinese(native):
                canonical = self._generate_pinyin(native)
        
        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""
        
        # Remove punctuation for sorting
        sort_family = re.sub(r'[^\w\s]', '', sort_family)
        sort_given = re.sub(r'[^\w\s]', '', sort_given)
        
        # Generate key - Chinese names are Family Given
        key = f"{sort_family} {sort_given}"
        
        # Ensure determinism
        key = " ".join(key.split())
        
        return key
    
    def _validate_cjk_roundtrip(self, canonical_native: str, canonical_latin: str) -> float:
        """
        Rule 11: CJK Round-Trip validation with Dice coefficient.
        
        Process:
        1. romanise CJK → get expected romanization  
        2. back-convert romanization → get reconstructed CJK
        3. calculate Dice coefficient between original and reconstructed
        4. must achieve ≥97% match for V7 compliance
        
        Args:
            canonical_native: Original CJK text
            canonical_latin: Provided romanization
            
        Returns:
            Dice coefficient (0.0 to 1.0)
        """
        import unicodedata
        
        try:
            # Step 1: Romanize original CJK to get expected romanization
            expected_romanization = self._generate_pinyin(canonical_native)
            
            # Step 2: Back-convert provided romanization to CJK
            reconstructed_cjk = self._pinyin_to_cjk(canonical_latin)
            
            # Step 3: Apply NFC casefold normalization as per V7 spec
            original_normalized = unicodedata.normalize('NFC', canonical_native.casefold())
            reconstructed_normalized = unicodedata.normalize('NFC', reconstructed_cjk.casefold())
            
            # Step 4: Calculate Dice coefficient
            dice_score = self._calculate_dice_coefficient(original_normalized, reconstructed_normalized)
            
            # Store round-trip metadata for debugging
            self.logger.debug(f"Rule 11 Round-trip: {canonical_native} → {expected_romanization} → {reconstructed_cjk} (Dice: {dice_score:.3f})")
            
            return dice_score
            
        except Exception as e:
            self.logger.warning(f"CJK round-trip validation failed: {e}")
            # Conservative approach: return 0.0 if validation fails
            return 0.0
    
    def _pinyin_to_cjk(self, pinyin: str) -> str:
        """
        Convert pinyin romanization back to CJK characters.
        
        This is a simplified back-conversion. In a production system,
        you'd use a proper pinyin-to-Chinese conversion library.
        """
        # Reverse pinyin mapping (simplified)
        reverse_pinyin_map = {
            "wang": "王", "li": "李", "zhang": "张", "liu": "刘", "chen": "陈",
            "yang": "杨", "huang": "黄", "zhao": "赵", "zhou": "周", "wu": "吴",
            "xu": "徐", "sun": "孙", "zhu": "朱", "ma": "马", "hu": "胡",
            "guo": "郭", "lin": "林", "he": "何", "gao": "高", "liang": "梁",
            
            # Common given name syllables
            "ming": "明", "hua": "华", "wei": "伟", "qiang": "强", "jun": "军",
            "jing": "静", "min": "敏", "fang": "芳", "ying": "英", "na": "娜",
            "xiu": "秀", "hong": "红", "xia": "霞", "yan": "燕", "dong": "东",
            "nan": "南", "xi": "西", "bei": "北", "zhong": "中", "jian": "建",
            "wen": "文", "zhi": "志", "de": "德", "yi": "义", "ren": "仁",
            "xiao": "小", "da": "大", "tian": "天", "shan": "山", "jin": "金"
        }
        
        # Clean and normalize pinyin input
        pinyin_clean = pinyin.lower().replace(',', ' ').strip()
        syllables = pinyin_clean.split()
        
        result = []
        for syllable in syllables:
            # Remove tone marks for matching
            syllable_clean = self._remove_tone_marks(syllable)
            
            if syllable_clean in reverse_pinyin_map:
                result.append(reverse_pinyin_map[syllable_clean])
            else:
                # Unknown syllable - attempt best guess or return placeholder
                # In production, this would use a comprehensive pinyin dictionary
                result.append("？")  # Question mark to indicate unknown
        
        return "".join(result)
    
    def _remove_tone_marks(self, syllable: str) -> str:
        """Remove tone marks from pinyin syllable."""
        # Basic tone mark removal
        tone_map = {
            'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a',
            'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e', 
            'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i',
            'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
            'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u',
            'ǖ': 'ü', 'ǘ': 'ü', 'ǚ': 'ü', 'ǜ': 'ü'
        }
        
        result = []
        for char in syllable:
            result.append(tone_map.get(char, char))
        return "".join(result)
    
    def _calculate_dice_coefficient(self, text1: str, text2: str) -> float:
        """
        Calculate Dice coefficient between two strings.
        
        Dice coefficient = 2 * |intersection| / (|set1| + |set2|)
        
        Args:
            text1: First string
            text2: Second string
            
        Returns:
            Dice coefficient (0.0 to 1.0)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # Create character bigrams for better matching
        bigrams1 = set(text1[i:i+2] for i in range(len(text1)-1))
        bigrams2 = set(text2[i:i+2] for i in range(len(text2)-1))
        
        # Handle single character case
        if len(text1) == 1:
            bigrams1 = set([text1])
        if len(text2) == 1:
            bigrams2 = set([text2])
        
        # Calculate intersection
        intersection = bigrams1.intersection(bigrams2)
        
        # Calculate Dice coefficient
        dice = 2.0 * len(intersection) / (len(bigrams1) + len(bigrams2))
        
        return dice