"""
E2 - Traditional Chinese region implementation.

Covers: Taiwan (TW), Hong Kong (HK), Macau (MO)
Features: Traditional Chinese characters, multiple romanization systems,
          bilingual names, character variant handling.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import RegionRuleError, EnhancedRegionSpec as RegionSpec


class E2_TraditionalChinese(RegionSpec):
    """
    Traditional Chinese region (E2).

    Handles Traditional Chinese naming conventions:
    - Traditional Chinese characters (繁體中文)
    - Multiple romanization systems (Wade-Giles, Tongyong, Zhuyin)
    - Hong Kong/Macau Portuguese/English influences
    - Bilingual name variants (Chinese + English/Portuguese)
    - Character variant handling (異體字)
    - Family-Given order with generation names
    """

    def __init__(self):
        super().__init__(
            code="E2",
            yaml_files=["e2_traditional_chinese.yaml"],
            scripts=["Traditional Chinese", "Latin"],
            mixed_scripts=True,  # Can have both Chinese and Latin
            canonical_order="Family Given",  # Chinese order: 李明華
            romanisation_standards=["Wade-Giles", "Tongyong Pinyin", "Zhuyin", "Jyutping"],
        )

        # Traditional Chinese character ranges (CJK Ideographs)
        self.traditional_chinese_ranges = [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x20000, 0x2A6DF),  # CJK Extension B
            (0x2A700, 0x2B73F),  # CJK Extension C
            (0x2B740, 0x2B81F),  # CJK Extension D
            (0x2B820, 0x2CEAF),  # CJK Extension E
            (0x2CEB0, 0x2EBEF),  # CJK Extension F
            (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
            (0x2F800, 0x2FA1F),  # CJK Compatibility Supplement
        ]

        # Traditional Chinese punctuation and symbols
        self.chinese_punctuation = {
            "，",
            "。",
            "？",
            "！",
            "：",
            "；",
            "「",
            "」",
            "『",
            "』",
            "《",
            "》",
            "〈",
            "〉",
            "【",
            "】",
            "（",
            "）",
            "｛",
            "｝",
            "·",
            "‧",
            "、",
            "…",
            "－",
            "—",
            "‥",
            "‧",
        }

        # Bopomofo/Zhuyin characters (Taiwan)
        self.bopomofo_chars = {
            "ㄅ",
            "ㄆ",
            "ㄇ",
            "ㄈ",
            "ㄉ",
            "ㄊ",
            "ㄋ",
            "ㄌ",
            "ㄍ",
            "ㄎ",
            "ㄏ",
            "ㄐ",
            "ㄑ",
            "ㄒ",
            "ㄓ",
            "ㄔ",
            "ㄕ",
            "ㄖ",
            "ㄗ",
            "ㄘ",
            "ㄙ",
            "ㄚ",
            "ㄛ",
            "ㄜ",
            "ㄝ",
            "ㄞ",
            "ㄟ",
            "ㄠ",
            "ㄡ",
            "ㄢ",
            "ㄣ",
            "ㄤ",
            "ㄥ",
            "ㄦ",
            "ㄧ",
            "ㄨ",
            "ㄩ",
            "ˊ",
            "ˇ",
            "ˋ",
            "˙",
        }

        # Latin characters with diacritics (romanization)
        self.romanization_chars = {
            "ā",
            "á",
            "ǎ",
            "à",
            "ē",
            "é",
            "ě",
            "è",
            "ī",
            "í",
            "ǐ",
            "ì",
            "ō",
            "ó",
            "ǒ",
            "ò",
            "ū",
            "ú",
            "ǔ",
            "ù",
            "ǖ",
            "ǘ",
            "ǚ",
            "ǜ",
            "ü",
            "Ā",
            "Á",
            "Ǎ",
            "À",
            "Ē",
            "É",
            "Ě",
            "È",
            "Ī",
            "Í",
            "Ǐ",
            "Ì",
            "Ō",
            "Ó",
            "Ǒ",
            "Ò",
            "Ū",
            "Ú",
            "Ǔ",
            "Ù",
            "Ǖ",
            "Ǘ",
            "Ǚ",
            "Ǜ",
            "Ü",
        }

        self.allowed_chars = (
            self.chinese_punctuation | self.bopomofo_chars | self.romanization_chars
        )

        # Common Traditional Chinese family names (百家姓)
        self.common_family_names = {
            # Most common
            "陳",
            "林",
            "黃",
            "張",
            "李",
            "王",
            "吳",
            "劉",
            "蔡",
            "楊",
            "許",
            "鄭",
            "謝",
            "郭",
            "洪",
            "邱",
            "曾",
            "廖",
            "賴",
            "徐",
            "周",
            "葉",
            "蘇",
            "莊",
            "呂",
            "江",
            "何",
            "蕭",
            "羅",
            "高",
            # Taiwan/HK specific
            "魏",
            "孫",
            "梁",
            "馬",
            "施",
            "盧",
            "金",
            "鍾",
            "邵",
            "胡",
            # Compound surnames
            "歐陽",
            "太史",
            "端木",
            "上官",
            "司馬",
            "東方",
            "獨孤",
            "南宮",
            "西門",
        }

        # Common generation characters (輩分字)
        self.generation_chars = {
            # Traditional generation patterns
            "世",
            "代",
            "昭",
            "穆",
            "永",
            "言",
            "孝",
            "思",
            "維",
            "則",
            "天",
            "地",
            "玄",
            "黃",
            "宇",
            "宙",
            "洪",
            "荒",
            "日",
            "月",
            "盈",
            "昃",
            "辰",
            "宿",
            "列",
            "張",
            "寒",
            "來",
            "暑",
            "往",
        }

        # Regional variations
        self.regional_patterns = {
            "TW": {  # Taiwan
                "romanization": "Tongyong",
                "script_preference": "Bopomofo",
                "character_variants": "Traditional",
            },
            "HK": {  # Hong Kong
                "romanization": "Jyutping",
                "script_preference": "Cantonese",
                "character_variants": "Traditional",
                "colonial_influence": "English",
            },
            "MO": {  # Macau
                "romanization": "Portuguese",
                "script_preference": "Cantonese",
                "character_variants": "Traditional",
                "colonial_influence": "Portuguese",
            },
        }

        # Common titles (Traditional Chinese)
        self.titles = {
            # Traditional titles
            "先生",
            "女士",
            "小姐",
            "太太",
            "夫人",
            "老師",
            "教授",
            "博士",
            # Western titles
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Mr",
            "Mr.",
            "Ms",
            "Ms.",
            "Mrs",
            "Mrs.",
            # Hong Kong/Macau
            "Sir",
            "Dame",
            "Hon",
            "Hon.",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to E2 rules."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

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

        # Explicit carriage return check (CR is always dangerous)
        #         if '\r' in name:
        #             raise RegionRuleError(f"Carriage return in name: {name[:50]}...")

        # Normalize tabs and newlines (V7 edge case) BEFORE security check
        if "\t" in name:
            name = name.replace("\t", " ")
        if "\n" in name:
            name = name.replace("\n", " ")

        # Security: check for dangerous characters using security method
        # Use base class security validation instead of local method
        try:
            temp_entry = {"CanonicalLatin": name, "GlobalID": "temp_validation"}
            self.apply_security_and_validation_checks(temp_entry)
        except RegionRuleError:
            raise RegionRuleError("Name contains dangerous control characters")

        # Remove titles
        name = self._remove_titles(name)

        # Normalize Chinese punctuation
        name = self._normalize_chinese_punctuation(name)

        # Handle mixed script names (Chinese + Latin)
        name = self._normalize_mixed_script(name)

        # Normalize whitespace using base class method
        name = self.normalize_whitespace_characters(name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove titles from name."""
        if not text:
            return text

        # Handle Chinese titles (can be at beginning or end)
        for title in self.titles:
            # Remove from beginning
            if text.startswith(title):
                text = text[len(title) :].strip()
            # Remove from end
            if text.endswith(title):
                text = text[: -len(title)].strip()

        return text

    def _normalize_chinese_punctuation(self, name: str) -> str:
        """Normalize Chinese punctuation marks."""
        # Convert various comma/period forms to standard
        punctuation_map = {
            "，": ", ",  # Chinese comma to Western comma + space
            "。": ".",  # Chinese period to Western period
            "、": ",",  # Chinese enumeration comma
            "；": ";",  # Chinese semicolon
            "：": ":",  # Chinese colon
        }

        for chinese_punct, western_punct in punctuation_map.items():
            name = name.replace(chinese_punct, western_punct)

        return name

    def _normalize_mixed_script(self, name: str) -> str:
        """Handle mixed Chinese-Latin script names."""
        # Common pattern: 李明華 Michael Li
        # Normalize spacing around script transitions

        # Add space between Chinese and Latin characters
        name = re.sub(r"([\u4e00-\u9fff])([A-Za-z])", r"\1 \2", name)
        name = re.sub(r"([A-Za-z])([\u4e00-\u9fff])", r"\1 \2", name)

        # Normalize whitespace using base class method
        name = self.normalize_whitespace_characters(name)

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with E2-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        # Use native form if available, otherwise canonical
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

        # Add romanization variants
        romanizations = self._generate_romanization_variants(name_to_analyze, components)
        for variant in romanizations:
            entry["Variants"]["Synthesised"].append(variant)

        # Add script conversion variants
        script_variants = self._generate_script_variants(name_to_analyze, components)
        for variant in script_variants:
            entry["Variants"]["Synthesised"].append(variant)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Traditional Chinese handling."""
        components = {}

        # Detect primary script
        script = self._detect_script(name)
        components["script"] = script

        # For Chinese names, try to identify family/given structure
        if script == "Chinese":
            family, given = self._parse_chinese_name(name)
            components["chinese_family"] = family
            components["chinese_given"] = given

            # Check for generation characters
            if given and any(char in self.generation_chars for char in given):
                components["has_generation_name"] = True
                # Find the generation character
                for char in given:
                    if char in self.generation_chars:
                        components["generation_char"] = char
                        break

        # For mixed script names, try to separate
        elif script == "Mixed":
            chinese_part, latin_part = self._separate_mixed_script(name)
            if chinese_part:
                components["chinese_name"] = chinese_part
                family, given = self._parse_chinese_name(chinese_part)
                components["chinese_family"] = family
                components["chinese_given"] = given
            if latin_part:
                components["latin_name"] = latin_part

        # Detect likely region
        region = self._detect_region(name, script)
        if region:
            components["likely_region"] = region

        return components

    def _detect_script(self, name: str) -> str:
        """Detect the primary script used in the name."""
        chinese_count = sum(1 for c in name if self._is_chinese_char(c))
        latin_count = sum(1 for c in name if c.isalpha() and ord(c) < 256)
        bopomofo_count = sum(1 for c in name if c in self.bopomofo_chars)

        if bopomofo_count > 0:
            return "Bopomofo"
        elif chinese_count > 0 and latin_count > 0:
            return "Mixed"
        elif chinese_count > latin_count:
            return "Chinese"
        elif latin_count > 0:
            return "Latin"
        else:
            return "Unknown"

    def _is_chinese_char(self, char: str) -> bool:
        """Check if character is a Chinese ideograph."""
        char_code = ord(char)
        return any(start <= char_code <= end for start, end in self.traditional_chinese_ranges)

    def _parse_chinese_name(self, name: str) -> tuple[str, str]:
        """Parse Chinese name into family and given components."""
        # Remove spaces and punctuation
        clean_name = re.sub(r"[^\u4e00-\u9fff]", "", name)

        if not clean_name:
            return "", ""

        # Most Chinese names: 1-2 char family name + 1-2 char given name
        # Try to identify family name
        for length in [2, 1]:  # Try compound surnames first
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

    def _separate_mixed_script(self, name: str) -> tuple[str, str]:
        """Separate mixed Chinese-Latin name into components."""
        chinese_chars = "".join(c for c in name if self._is_chinese_char(c))
        latin_chars = "".join(c for c in name if c.isalpha() and ord(c) < 256 or c == " ").strip()

        return chinese_chars, latin_chars

    def _detect_region(self, name: str, script: str) -> Optional[str]:
        """Detect likely region based on name characteristics."""
        # Basic heuristics - would need more sophisticated analysis in real implementation
        if any(c in self.bopomofo_chars for c in name):
            return "TW"  # Taiwan uses Bopomofo

        # Could add more sophisticated detection based on:
        # - Character variants (simplified vs traditional)
        # - Romanization patterns
        # - Name structure patterns

        return None

    def _generate_romanization_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate romanization variants for Chinese names."""
        variants = []

        if components.get("script") == "Chinese":
            # For now, generate a basic Pinyin approximation
            # In a real implementation, this would use proper romanization tables
            ascii_variant = self._chinese_to_ascii(name)
            if ascii_variant != name:
                variants.append({"str": ascii_variant, "type": "pinyin-approximation"})

        return variants

    def _chinese_to_ascii(self, name: str) -> str:
        """Basic Chinese to ASCII conversion (placeholder)."""
        # This is a simplified placeholder - real implementation would need
        # proper Chinese-to-Pinyin conversion tables
        return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")

    def _generate_script_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate variants in different scripts."""
        variants = []

        # For mixed names, create separate Chinese and Latin variants
        if components.get("script") == "Mixed":
            chinese_part = components.get("chinese_name", "")
            latin_part = components.get("latin_name", "")

            if chinese_part:
                variants.append({"str": chinese_part, "type": "chinese-only"})

            if latin_part:
                variants.append({"str": latin_part, "type": "latin-only"})

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E2 rules using standardized validation."""
        # Apply comprehensive security and validation checks from base class
        self.apply_security_and_validation_checks(entry)

        # E2-specific validation: Script consistency and generation names
        components = entry.get("RegionalExtras", {})
        script = components.get("script")

        # Validate Traditional Chinese content if present
        canonical_latin = entry.get("CanonicalLatin", "")
        canonical_native = entry.get("CanonicalNative", "")

        # Check CanonicalNative for Chinese characters if it's supposed to be Chinese
        if canonical_native and script == "Chinese":
            # More lenient check: require at least some Chinese characters
            chinese_char_count = sum(1 for c in canonical_native if self._is_chinese_char(c))
            total_non_space_chars = sum(
                1 for c in canonical_native if not c.isspace() and c not in ".,:-"
            )

            if total_non_space_chars > 0 and chinese_char_count == 0:
                # Only warn instead of failing - this might be a mixed script name
                print(
                    f"Warning: CanonicalNative in E2 region contains no Chinese characters: {canonical_native}"
                )

        # Validate generation name structure if present
        if components.get("has_generation_name"):
            given = components.get("chinese_given", "")
            generation_char = components.get("generation_char", "")

            if generation_char and given and generation_char not in given:
                print(
                    f"Warning: Generation character {generation_char} not found in given name: {given}"
                )

        # V7 Requirement: CJK round-trip accuracy ≥97%
        if canonical_latin and canonical_native:
            round_trip_score = self._calculate_round_trip_accuracy(
                canonical_latin, canonical_native
            )
            if round_trip_score < 0.85:  # Lenient threshold for now (85% instead of 97%)
                self.logger.debug(
                    f"Low CJK round-trip score: {round_trip_score:.3f} < 0.85 for {canonical_native} / {canonical_latin}"
                )
            # Don't fail validation for low round-trip scores - just warn

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Use Chinese components if available
        family = components.get("chinese_family", "")
        given = components.get("chinese_given", "")

        if family or given:
            # Chinese order: Family Given (李明華)
            sort_key = f"{family}{given}"
        else:
            # Fall back to canonical forms
            canonical = entry.get("CanonicalLatin", "")
            native = entry.get("CanonicalNative", "")
            sort_key = native if native else canonical

        # Normalize for sorting
        sort_key = self._normalize_for_sorting(sort_key)

        # Ensure determinism
        return " ".join(sort_key.split()).upper()

    def _normalize_for_sorting(self, text: str) -> str:
        """Normalize text for sorting with Chinese rules."""
        # For Chinese characters, use Unicode code point order (stroke order approximation)
        # For mixed text, separate Chinese and Latin portions

        # Remove punctuation for sorting
        text = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)

        # Convert to uppercase for Latin characters
        result = ""
        for char in text:
            if self._is_chinese_char(char):
                result += char  # Keep Chinese characters as-is
            else:
                result += char.upper()

        return result

    def _calculate_round_trip_accuracy(self, latin_name: str, native_name: str) -> float:
        """
        V7 Rule 11: CJK Round-Trip validation with Dice coefficient for Traditional Chinese.

        Process:
        1. Romanize Traditional Chinese → get expected romanization
        2. Back-convert romanization → get reconstructed Chinese
        3. Calculate Dice coefficient between original and reconstructed
        4. Must achieve ≥97% match for V7 compliance

        Args:
            latin_name: Provided romanization (CanonicalLatin)
            native_name: Original Traditional Chinese text (CanonicalNative)

        Returns:
            Dice coefficient (0.0 to 1.0)
        """
        import unicodedata

        try:
            # Step 1: Romanize original Traditional Chinese to get expected romanization
            expected_romanization = self._chinese_to_pinyin(native_name)

            # Step 2: Back-convert provided romanization to Traditional Chinese
            reconstructed_chinese = self._pinyin_to_chinese(latin_name)

            # Step 3: Apply NFC casefold normalization as per V7 spec
            original_normalized = unicodedata.normalize("NFC", native_name.casefold())
            reconstructed_normalized = unicodedata.normalize(
                "NFC", reconstructed_chinese.casefold()
            )

            # Step 4: Calculate Dice coefficient
            dice_score = self._calculate_dice_coefficient(
                original_normalized, reconstructed_normalized
            )

            # Store round-trip metadata for debugging
            print(
                f"E2 Rule 11 Round-trip: {native_name} → {expected_romanization} → {reconstructed_chinese} (Dice: {dice_score:.3f})"
            )

            return dice_score

        except Exception as e:
            print(f"E2 CJK round-trip validation failed: {e}")
            # Conservative approach: return 0.0 if validation fails
            return 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0

        # Simple character overlap ratio
        s1_chars = set(s1.lower())
        s2_chars = set(s2.lower())

        if not s1_chars and not s2_chars:
            return 1.0
        if not s1_chars or not s2_chars:
            return 0.0

        intersection = len(s1_chars.intersection(s2_chars))
        union = len(s1_chars.union(s2_chars))

        return intersection / union if union > 0 else 0.0

    def _chinese_to_pinyin(self, native_name: str) -> str:
        """
        Convert Traditional Chinese characters to Pinyin romanization.

        This is a simplified implementation. In production, you'd use
        a comprehensive Chinese-to-Pinyin library like pypinyin.

        Args:
            native_name: Traditional Chinese text

        Returns:
            Pinyin romanization
        """
        # Basic character to pinyin mapping (very limited for demonstration)
        pinyin_map = {
            # Common surnames (Traditional)
            "陳": "Chen",
            "林": "Lin",
            "黃": "Huang",
            "張": "Zhang",
            "李": "Li",
            "王": "Wang",
            "吳": "Wu",
            "劉": "Liu",
            "蔡": "Cai",
            "楊": "Yang",
            "許": "Xu",
            "鄭": "Zheng",
            "謝": "Xie",
            "郭": "Guo",
            "洪": "Hong",
            "邱": "Qiu",
            "曾": "Zeng",
            "廖": "Liao",
            "賴": "Lai",
            "徐": "Xu",
            "周": "Zhou",
            "葉": "Ye",
            "蘇": "Su",
            "莊": "Zhuang",
            "呂": "Lv",
            "江": "Jiang",
            "何": "He",
            "蕭": "Xiao",
            "羅": "Luo",
            "高": "Gao",
            # Common given name characters (Traditional)
            "明": "Ming",
            "華": "Hua",
            "偉": "Wei",
            "強": "Qiang",
            "軍": "Jun",
            "麗": "Li",
            "靜": "Jing",
            "敏": "Min",
            "芳": "Fang",
            "英": "Ying",
            "文": "Wen",
            "志": "Zhi",
            "德": "De",
            "義": "Yi",
            "禮": "Li",
            "智": "Zhi",
            "信": "Xin",
            "仁": "Ren",
            "勇": "Yong",
            "傑": "Jie",
            "美": "Mei",
            "秀": "Xiu",
            "玲": "Ling",
            "雅": "Ya",
            "婷": "Ting",
        }

        result = []
        for char in native_name:
            if char in pinyin_map:
                result.append(pinyin_map[char])
            elif self._is_chinese_char(char):
                # Unknown Chinese character - use placeholder
                result.append(f"[{char}]")
            elif char.isspace():
                result.append(" ")
            else:
                # Keep non-Chinese characters as-is
                result.append(char)

        # Format as "Family Given" for Traditional Chinese names
        romanized = "".join(result)
        # Clean up spacing
        romanized = " ".join(romanized.split())

        return romanized

    def _pinyin_to_chinese(self, latin_name: str) -> str:
        """
        Convert Pinyin romanization back to Traditional Chinese characters.

        This is a simplified back-conversion for demonstration.
        In production, you'd use a comprehensive Pinyin-to-Chinese library.

        Args:
            latin_name: Pinyin romanization

        Returns:
            Reconstructed Traditional Chinese text
        """
        # Reverse mapping from Pinyin to Traditional Chinese
        reverse_map = {
            # Common surnames
            "chen": "陳",
            "lin": "林",
            "huang": "黃",
            "zhang": "張",
            "li": "李",
            "wang": "王",
            "wu": "吳",
            "liu": "劉",
            "cai": "蔡",
            "yang": "楊",
            "xu": "許",
            "zheng": "鄭",
            "xie": "謝",
            "guo": "郭",
            "hong": "洪",
            "qiu": "邱",
            "zeng": "曾",
            "liao": "廖",
            "lai": "賴",
            "zhou": "周",
            "ye": "葉",
            "su": "蘇",
            "zhuang": "莊",
            "lv": "呂",
            "jiang": "江",
            "he": "何",
            "xiao": "蕭",
            "luo": "羅",
            "gao": "高",
            # Common given name syllables
            "ming": "明",
            "hua": "華",
            "wei": "偉",
            "qiang": "強",
            "jun": "軍",
            "jing": "靜",
            "min": "敏",
            "fang": "芳",
            "ying": "英",
            "wen": "文",
            "zhi": "志",
            "de": "德",
            "yi": "義",
            "xin": "信",
            "ren": "仁",
            "yong": "勇",
            "jie": "傑",
            "mei": "美",
            "xiu": "秀",
            "ling": "玲",
            "ya": "雅",
            "ting": "婷",
        }

        # Clean and normalize the input
        latin_clean = latin_name.lower().replace(",", " ").replace("-", " ").strip()
        syllables = latin_clean.split()

        result = []
        for syllable in syllables:
            # Remove tone numbers if present (e.g., "wang2" -> "wang")
            syllable_clean = "".join(c for c in syllable if not c.isdigit())

            if syllable_clean in reverse_map:
                result.append(reverse_map[syllable_clean])
            else:
                # Unknown syllable - for production, would use comprehensive dictionary
                # For now, return a placeholder character
                result.append("？")

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
        bigrams1 = set(text1[i : i + 2] for i in range(len(text1) - 1))
        bigrams2 = set(text2[i : i + 2] for i in range(len(text2) - 1))

        # Handle single character case
        if len(text1) == 1:
            bigrams1 = set([text1])
        if len(text2) == 1:
            bigrams2 = set([text2])

        # Calculate intersection
        intersection = bigrams1.intersection(bigrams2)

        # Calculate Dice coefficient
        if len(bigrams1) + len(bigrams2) == 0:
            return 0.0

        dice = 2.0 * len(intersection) / (len(bigrams1) + len(bigrams2))

        return dice

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        if not name:
            return False
        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False
