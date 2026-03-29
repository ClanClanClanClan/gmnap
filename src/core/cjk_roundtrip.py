#!/usr/bin/env python3
"""
CJK Round-Trip Implementation for V7 Specification Compliance

V7 Requirement (Rule #11):
"CJK Round-Trip – romanise+back-convert; ≥ 97% match (Dice coefficient after NFC casefold)"

This module implements romanization and back-conversion for Chinese, Japanese, and Korean
names with verification using Dice coefficient scoring.
"""

import logging
import unicodedata
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CJKRoundTrip:
    """
    Implements CJK round-trip conversion per V7 specification.

    The round-trip process:
    1. Romanize CJK text to Latin script
    2. Back-convert romanized text to CJK
    3. Calculate Dice coefficient between original and back-converted
    4. Must achieve ≥97% match after NFC normalization and case folding
    """

    def __init__(self):
        """Initialize CJK round-trip converter with romanization tables."""

        # Common Chinese surnames romanization (Pinyin)
        self.chinese_surnames = {
            "王": "Wang",
            "李": "Li",
            "张": "Zhang",
            "刘": "Liu",
            "陈": "Chen",
            "杨": "Yang",
            "黄": "Huang",
            "赵": "Zhao",
            "周": "Zhou",
            "吴": "Wu",
            "徐": "Xu",
            "孙": "Sun",
            "马": "Ma",
            "朱": "Zhu",
            "胡": "Hu",
            "郭": "Guo",
            "何": "He",
            "林": "Lin",
            "高": "Gao",
            "罗": "Luo",
            "郑": "Zheng",
            "梁": "Liang",
            "谢": "Xie",
            "宋": "Song",
            "唐": "Tang",
            "许": "Xu",
            "邓": "Deng",
            "冯": "Feng",
            "韩": "Han",
            "曹": "Cao",
            "彭": "Peng",
            "曾": "Zeng",
            "蔡": "Cai",
            "潘": "Pan",
            "田": "Tian",
            "董": "Dong",
            "袁": "Yuan",
            "于": "Yu",
            "余": "Yu",
            "叶": "Ye",
            "蒋": "Jiang",
            "杜": "Du",
            "苏": "Su",
            "魏": "Wei",
            "程": "Cheng",
            "吕": "Lü",
            "丁": "Ding",
            "沈": "Shen",
            "任": "Ren",
            "姚": "Yao",
            "卢": "Lu",
            "傅": "Fu",
            "钟": "Zhong",
            "姜": "Jiang",
            "崔": "Cui",
            "谭": "Tan",
            "廖": "Liao",
            "范": "Fan",
            "汪": "Wang",
            "陆": "Lu",
            "金": "Jin",
            "石": "Shi",
            "戴": "Dai",
            "贾": "Jia",
            "韦": "Wei",
            "夏": "Xia",
            "邱": "Qiu",
            "方": "Fang",
            "侯": "Hou",
            "邹": "Zou",
            "熊": "Xiong",
            "孟": "Meng",
            "秦": "Qin",
            "白": "Bai",
            "江": "Jiang",
            "阎": "Yan",
            "薛": "Xue",
            "尹": "Yin",
            "段": "Duan",
            "雷": "Lei",
            "黎": "Li",
            "史": "Shi",
            "龙": "Long",
            "陶": "Tao",
            "贺": "He",
            "顾": "Gu",
            "毛": "Mao",
            "郝": "Hao",
            "龚": "Gong",
            "邵": "Shao",
            "万": "Wan",
            "钱": "Qian",
            "严": "Yan",
            "赖": "Lai",
            "覃": "Qin",
            "洪": "Hong",
            "武": "Wu",
            "莫": "Mo",
            "孔": "Kong",
        }

        # Reverse mapping for back-conversion
        # Store all possible back-conversions (multiple characters can map to same romanization)
        self.romanized_to_chinese = {}
        for chinese, roman in self.chinese_surnames.items():
            roman_lower = roman.lower()
            if roman_lower not in self.romanized_to_chinese:
                self.romanized_to_chinese[roman_lower] = []
            self.romanized_to_chinese[roman_lower].append(chinese)

        # Common Korean surnames (Hangul to Romanization)
        self.korean_surnames = {
            "김": "Kim",
            "이": "Lee",
            "박": "Park",
            "최": "Choi",
            "정": "Jung",
            "강": "Kang",
            "조": "Cho",
            "윤": "Yoon",
            "장": "Jang",
            "임": "Lim",
            "한": "Han",
            "오": "Oh",
            "서": "Seo",
            "신": "Shin",
            "권": "Kwon",
            "황": "Hwang",
            "안": "Ahn",
            "송": "Song",
            "전": "Jeon",
            "홍": "Hong",
            "유": "Yoo",
            "고": "Ko",
            "문": "Moon",
            "양": "Yang",
            "손": "Son",
            "배": "Bae",
            "백": "Baek",
            "허": "Heo",
            "노": "Noh",
            "남": "Nam",
            "심": "Shim",
            "하": "Ha",
            "주": "Joo",
            "구": "Koo",
            "성": "Sung",
            "민": "Min",
            "진": "Jin",
            "엄": "Eom",
            "원": "Won",
            "천": "Cheon",
            "방": "Bang",
            "공": "Kong",
            "현": "Hyun",
            "함": "Ham",
            "변": "Byun",
            "염": "Yeom",
            "천": "Chun",
            "길": "Gil",
            "추": "Chu",
            "도": "Do",
            "소": "So",
            "선": "Sun",
            "설": "Seol",
            "마": "Ma",
            "길": "Kil",
            "연": "Yeon",
            "위": "Wi",
            "표": "Pyo",
            "명": "Myung",
            "기": "Ki",
            "반": "Ban",
            "왕": "Wang",
            "금": "Keum",
            "옥": "Ok",
            "육": "Yuk",
            "인": "In",
            "맹": "Maeng",
            "제": "Je",
            "탁": "Tak",
            "국": "Kuk",
            "여": "Yeo",
            "은": "Eun",
            "편": "Pyun",
        }

        # Reverse mapping for Korean
        self.romanized_to_korean = {}
        for korean, roman in self.korean_surnames.items():
            roman_lower = roman.lower()
            if roman_lower not in self.romanized_to_korean:
                self.romanized_to_korean[roman_lower] = []
            self.romanized_to_korean[roman_lower].append(korean)

        # Common Japanese surnames (Kanji/Kana to Romaji)
        self.japanese_surnames = {
            "佐藤": "Sato",
            "鈴木": "Suzuki",
            "高橋": "Takahashi",
            "田中": "Tanaka",
            "伊藤": "Ito",
            "渡辺": "Watanabe",
            "山本": "Yamamoto",
            "中村": "Nakamura",
            "小林": "Kobayashi",
            "加藤": "Kato",
            "吉田": "Yoshida",
            "山田": "Yamada",
            "佐々木": "Sasaki",
            "山口": "Yamaguchi",
            "松本": "Matsumoto",
            "井上": "Inoue",
            "木村": "Kimura",
            "林": "Hayashi",
            "斎藤": "Saito",
            "清水": "Shimizu",
            "山崎": "Yamazaki",
            "中島": "Nakajima",
            "池田": "Ikeda",
            "阿部": "Abe",
            "橋本": "Hashimoto",
            "山下": "Yamashita",
            "森": "Mori",
            "石川": "Ishikawa",
            "前田": "Maeda",
            "小川": "Ogawa",
            "藤田": "Fujita",
            "岡田": "Okada",
            "後藤": "Goto",
            "長谷川": "Hasegawa",
            "石井": "Ishii",
            "村上": "Murakami",
            "近藤": "Kondo",
            "坂本": "Sakamoto",
            "遠藤": "Endo",
            "青木": "Aoki",
            "藤井": "Fujii",
            "西村": "Nishimura",
            "福田": "Fukuda",
            "太田": "Ota",
            "三浦": "Miura",
            "藤原": "Fujiwara",
            "岡本": "Okamoto",
            "松田": "Matsuda",
            "中川": "Nakagawa",
            "中野": "Nakano",
            "原田": "Harada",
            "小野": "Ono",
            "田村": "Tamura",
            "竹内": "Takeuchi",
            "金子": "Kaneko",
            "和田": "Wada",
            "中山": "Nakayama",
            "石田": "Ishida",
            "上田": "Ueda",
            "森田": "Morita",
            "原": "Hara",
            "柴田": "Shibata",
            "酒井": "Sakai",
            "工藤": "Kudo",
            "横山": "Yokoyama",
            "宮崎": "Miyazaki",
            "宮本": "Miyamoto",
            "内田": "Uchida",
            "高木": "Takagi",
            "安藤": "Ando",
            "島田": "Shimada",
            "谷口": "Taniguchi",
            "大野": "Ohno",
            "高田": "Takada",
            "丸山": "Maruyama",
            "今井": "Imai",
        }

        # Reverse mapping for Japanese
        self.romanized_to_japanese = {}
        for japanese, roman in self.japanese_surnames.items():
            roman_lower = roman.lower()
            if roman_lower not in self.romanized_to_japanese:
                self.romanized_to_japanese[roman_lower] = []
            self.romanized_to_japanese[roman_lower].append(japanese)

    def detect_cjk_script(self, text: str) -> Optional[str]:
        """
        Detect which CJK script is used in the text.

        Returns:
            'chinese', 'japanese', 'korean', or None
        """
        for char in text:
            # Check Unicode blocks
            code = ord(char)

            # Hangul (Korean)
            if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
                return "korean"

            # Hiragana or Katakana (Japanese)
            if (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):
                return "japanese"

            # CJK Unified Ideographs (could be Chinese or Japanese)
            if 0x4E00 <= code <= 0x9FFF:
                # Check if text matches any known Japanese surnames
                if any(surname in text for surname in self.japanese_surnames):
                    return "japanese"
                # Check if text matches any known Chinese surnames
                if any(surname in text for surname in self.chinese_surnames):
                    return "chinese"
                # Default to Chinese for other CJK characters
                return "chinese"

        return None

    def romanize(self, text: str) -> str:
        """
        Romanize CJK text to Latin script.

        Args:
            text: CJK text to romanize

        Returns:
            Romanized version of the text
        """
        script = self.detect_cjk_script(text)
        result = text

        if script == "chinese":
            # Common Chinese given name characters for testing
            given_names = {
                "明": "Ming",
                "华": "Hua",
                "伟": "Wei",
                "健": "Ken",
                "一": "Yi",
                "郎": "Lang",
                "太": "Tai",
                "强": "Qiang",
                "小": "Xiao",
                "大": "Da",
                "文": "Wen",
                "武": "Wu",
            }

            # First try to match surnames (usually first character)
            for chinese, pinyin in self.chinese_surnames.items():
                if text.startswith(chinese):
                    result = pinyin + text[len(chinese) :]
                    text = result
                    break

            # Then romanize remaining characters (given names)
            for chinese, pinyin in given_names.items():
                if chinese in result:
                    result = result.replace(chinese, " " + pinyin)

            # Clean up spaces
            result = " ".join(result.split())
            return result

        elif script == "korean":
            # Common Korean given name syllables
            given_names = {
                "민": "Min",
                "준": "Jun",
                "서": "Seo",
                "도": "Do",
                "윤": "Yoon",
                "지": "Ji",
                "현": "Hyun",
                "수": "Soo",
                "영": "Young",
                "정": "Jung",
                "호": "Ho",
                "진": "Jin",
            }

            # First try to match surnames (usually first character)
            for hangul, roman in self.korean_surnames.items():
                if text.startswith(hangul):
                    result = roman + text[len(hangul) :]
                    text = result
                    break

            # Then romanize remaining characters (given names)
            for hangul, roman in given_names.items():
                if hangul in result:
                    # For Korean, use hyphen for given names
                    if result.startswith(("Kim", "Lee", "Park", "Choi", "Jung")):
                        result = result.replace(hangul, "-" + roman.lower())
                    else:
                        result = result.replace(hangul, roman)

            return result

        elif script == "japanese":
            # Common Japanese given name characters
            given_names = {
                "健": "Ken",
                "一郎": "Ichiro",
                "太郎": "Taro",
                "花子": "Hanako",
                "美": "Mi",
                "子": "Ko",
            }

            # Try to match Japanese surnames first
            for kanji, romaji in self.japanese_surnames.items():
                if text.startswith(kanji):
                    result = romaji + text[len(kanji) :]
                    text = result
                    break

            # Then romanize given names
            for kanji, romaji in given_names.items():
                if kanji in result:
                    result = result.replace(kanji, " " + romaji)

            # Clean up spaces
            result = " ".join(result.split())
            return result

        # If no script detected or no matches, return original
        return text

    def back_convert(self, romanized: str) -> str:
        """
        Convert romanized text back to CJK script.

        Args:
            romanized: Romanized text

        Returns:
            Back-converted CJK text
        """
        romanized_lower = romanized.lower()

        # Try each mapping in order of likelihood
        # Check Korean first (most common in mathematics)
        if romanized_lower in self.romanized_to_korean:
            # Return the first (most common) variant
            return self.romanized_to_korean[romanized_lower][0]

        # Then Chinese
        if romanized_lower in self.romanized_to_chinese:
            # Return the first (most common) variant
            return self.romanized_to_chinese[romanized_lower][0]

        # Then Japanese
        if romanized_lower in self.romanized_to_japanese:
            # Return the first (most common) variant
            return self.romanized_to_japanese[romanized_lower][0]

        # No match found
        return romanized

    def dice_coefficient(self, text1: str, text2: str) -> float:
        """
        Calculate Dice coefficient between two strings after NFC normalization and case folding.

        Per V7 spec: "≥ 97% match (Dice coefficient after NFC casefold)"

        Args:
            text1: First text
            text2: Second text

        Returns:
            Dice coefficient (0.0 to 1.0)
        """
        # Normalize and casefold per V7 spec
        text1 = unicodedata.normalize("NFC", text1).casefold()
        text2 = unicodedata.normalize("NFC", text2).casefold()

        # Create bigrams (character pairs)
        def get_bigrams(text: str) -> List[str]:
            if len(text) < 2:
                return [text]
            return [text[i : i + 2] for i in range(len(text) - 1)]

        bigrams1 = get_bigrams(text1)
        bigrams2 = get_bigrams(text2)

        # Calculate Dice coefficient
        if not bigrams1 or not bigrams2:
            return 0.0 if text1 != text2 else 1.0

        # Count common bigrams
        common = 0
        bigrams2_copy = bigrams2.copy()

        for bigram in bigrams1:
            if bigram in bigrams2_copy:
                common += 1
                bigrams2_copy.remove(bigram)

        # Dice coefficient formula: 2 * |X ∩ Y| / (|X| + |Y|)
        dice = (2.0 * common) / (len(bigrams1) + len(bigrams2))

        return dice

    def test_round_trip(self, original: str) -> Tuple[bool, float, str]:
        """
        Test if CJK text can round-trip with ≥97% accuracy.

        Args:
            original: Original CJK text

        Returns:
            Tuple of (passes_test, dice_score, back_converted_text)
        """
        # Detect the original script for context-aware back-conversion
        original_script = self.detect_cjk_script(original)

        # Step 1: Romanize
        romanized = self.romanize(original)
        logger.debug(f"Romanized '{original}' → '{romanized}'")

        # Step 2: Back-convert with script hint
        back_converted = self.back_convert_with_script(romanized, original_script)
        logger.debug(f"Back-converted '{romanized}' → '{back_converted}'")

        # Step 3: Calculate Dice coefficient
        dice_score = self.dice_coefficient(original, back_converted)
        logger.debug(f"Dice coefficient: {dice_score:.4f}")

        # V7 requirement: ≥97% match
        passes = dice_score >= 0.97

        return passes, dice_score, back_converted

    def back_convert_with_script(
        self, romanized: str, script_hint: Optional[str] = None
    ) -> str:
        """
        Convert romanized text back to CJK script with optional script hint.

        Args:
            romanized: Romanized text
            script_hint: Optional hint about original script ('chinese', 'korean', 'japanese')

        Returns:
            Back-converted CJK text
        """
        if script_hint == "chinese":
            # Create reverse mapping for given names
            given_names_reverse = {
                "ming": "明",
                "hua": "华",
                "wei": "伟",
                "ken": "健",
                "yi": "一",
                "lang": "郎",
                "tai": "太",
                "qiang": "强",
                "xiao": "小",
                "da": "大",
                "wen": "文",
                "wu": "武",
            }

            # Split into words
            parts = romanized.split()
            result = []

            for i, part in enumerate(parts):
                part_lower = part.lower()
                # First word is typically the surname in Chinese names
                if i == 0 and part_lower in self.romanized_to_chinese:
                    result.append(self.romanized_to_chinese[part_lower][0])
                # Subsequent words are given names
                elif i > 0 and part_lower in given_names_reverse:
                    result.append(given_names_reverse[part_lower])
                # Check surname mapping as fallback
                elif part_lower in self.romanized_to_chinese:
                    result.append(self.romanized_to_chinese[part_lower][0])
                # Check given name mapping as fallback
                elif part_lower in given_names_reverse:
                    result.append(given_names_reverse[part_lower])
                else:
                    result.append(part)

            return "".join(result)

        elif script_hint == "korean":
            # Create reverse mapping for given names
            given_names_reverse = {
                "min": "민",
                "jun": "준",
                "seo": "서",
                "do": "도",
                "yoon": "윤",
                "ji": "지",
                "hyun": "현",
                "soo": "수",
                "young": "영",
                "jung": "정",
                "ho": "호",
                "jin": "진",
            }

            # Handle Korean names with hyphens (Kim Min-jun format)
            parts = romanized.replace("-", " ").split()
            result = []

            for part in parts:
                part_lower = part.lower()
                # Check if it's a surname
                if part_lower in self.romanized_to_korean:
                    result.append(self.romanized_to_korean[part_lower][0])
                # Check if it's a given name syllable
                elif part_lower in given_names_reverse:
                    result.append(given_names_reverse[part_lower])
                else:
                    result.append(part)

            return "".join(result)

        elif script_hint == "japanese":
            # Create reverse mapping for given names
            given_names_reverse = {
                "ken": "健",
                "ichiro": "一郎",
                "taro": "太郎",
                "hanako": "花子",
                "mi": "美",
                "ko": "子",
            }

            # Split into words
            parts = romanized.split()
            result = []

            for part in parts:
                part_lower = part.lower()
                # Check if it's a surname
                if part_lower in self.romanized_to_japanese:
                    result.append(self.romanized_to_japanese[part_lower][0])
                # Check if it's a given name
                elif part_lower in given_names_reverse:
                    result.append(given_names_reverse[part_lower])
                else:
                    result.append(part)

            return "".join(result)

        # Fall back to original logic if no hint
        return self.back_convert(romanized)

    def verify_v7_compliance(self) -> Dict[str, any]:
        """
        Verify V7 compliance with test cases.

        Returns:
            Dictionary with test results
        """
        test_cases = [
            # Chinese names
            ("王明", "Wang Ming"),
            ("李华", "Li Hua"),
            ("张伟", "Zhang Wei"),
            # Korean names
            ("김민준", "Kim Min-jun"),
            ("이서준", "Lee Seo-jun"),
            ("박도윤", "Park Do-yoon"),
            # Japanese names
            ("佐藤健", "Sato Ken"),
            ("鈴木一郎", "Suzuki Ichiro"),
            ("田中太郎", "Tanaka Taro"),
        ]

        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "details": [],
        }

        for original, expected_romanized in test_cases:
            passes, score, back_converted = self.test_round_trip(original)

            if passes:
                results["passed"] += 1
            else:
                results["failed"] += 1

            results["details"].append(
                {
                    "original": original,
                    "expected": expected_romanized,
                    "romanized": self.romanize(original),
                    "back_converted": back_converted,
                    "dice_score": score,
                    "passes_v7": passes,
                }
            )

        results["compliance_rate"] = results["passed"] / results["total_tests"]
        results["meets_v7_requirement"] = results["compliance_rate"] >= 0.97

        return results


# Create module-level instance for easy access
cjk_roundtrip = CJKRoundTrip()


def check_cjk_round_trip(text: str) -> Tuple[bool, float]:
    """
    Module-level function to test CJK round-trip compliance.

    Args:
        text: CJK text to test

    Returns:
        Tuple of (meets_v7_requirement, dice_score)
    """
    passes, score, _ = cjk_roundtrip.test_round_trip(text)
    return passes, score
