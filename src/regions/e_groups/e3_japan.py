"""
E3 - Japan region implementation.

Covers: Japan
Features: Kanji, Hiragana, Katakana scripts, family-given order, romanization
"""

import re
import unicodedata
from typing import Any, Dict, List

from ..base import RegionRuleError, RegionSpec


class E3_Japan(RegionSpec):
    """
    Japan region (E3).

    Handles Japanese names:
    - Kanji, Hiragana, Katakana scripts
    - Family-Given order
    - Romanization (Hepburn, Kunrei-shiki)
    - Generation names and honorifics
    """

    def __init__(self):
        super().__init__(
            code="E3",
            yaml_files=["e3_japan.yaml"],
            scripts=["Kanji", "Hiragana", "Katakana"],
            mixed_scripts=True,
            canonical_order="Family Given",
            romanisation_standards=["Hepburn", "Kunrei-shiki", "Nihon-shiki"],
        )

        # Common Japanese surnames (top 50)
        self.common_surnames = {
            "佐藤",
            "鈴木",
            "高橋",
            "田中",
            "渡辺",
            "伊藤",
            "山本",
            "中村",
            "小林",
            "加藤",
            "吉田",
            "山田",
            "佐々木",
            "山口",
            "松本",
            "井上",
            "木村",
            "林",
            "斎藤",
            "清水",
            "山崎",
            "森",
            "阿部",
            "池田",
            "橋本",
            "山下",
            "石川",
            "中島",
            "前田",
            "藤田",
            "後藤",
            "岡田",
            "長谷川",
            "石井",
            "村上",
            "近藤",
            "坂本",
            "遠藤",
            "青木",
            "藤井",
            "西村",
            "福田",
            "太田",
            "三浦",
            "藤原",
            "岡本",
            "松田",
            "中川",
            "中野",
            "原田",
        }

        # Common titles and honorifics to remove
        self.titles = {
            # Academic/professional titles
            "教授",
            "准教授",
            "助教授",
            "講師",
            "助手",
            "研究員",
            "博士",
            "修士",
            "学士",
            "先生",
            "医師",
            "弁護士",
            "技師",
            "主任",
            "課長",
            "部長",
            "社長",
            "会長",
            # Honorifics (usually kept but sometimes removed)
            "さん",
            "様",
            "君",
            "ちゃん",
            "先輩",
            "後輩",
            # English equivalents
            "Prof",
            "Dr",
            "Mr",
            "Mrs",
            "Ms",
            "Professor",
            "Doctor",
        }

        # Japanese character ranges
        self.japanese_ranges = [
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
            (0x4E00, 0x9FAF),  # CJK Unified Ideographs (Kanji)
            (0x3400, 0x4DBF),  # CJK Extension A
            (0xFF65, 0xFF9F),  # Halfwidth Katakana
            (0x3000, 0x303F),  # CJK Symbols and Punctuation
        ]

        # Common name elements for romanization
        self.common_elements = {
            # Surnames
            "佐藤": "Sato",
            "鈴木": "Suzuki",
            "高橋": "Takahashi",
            "田中": "Tanaka",
            "渡辺": "Watanabe",
            "伊藤": "Ito",
            "山本": "Yamamoto",
            "中村": "Nakamura",
            "小林": "Kobayashi",
            "加藤": "Kato",
            "吉田": "Yoshida",
            "山田": "Yamada",
            # Given names
            "太郎": "Taro",
            "次郎": "Jiro",
            "三郎": "Saburo",
            "四郎": "Shiro",
            "花子": "Hanako",
            "美子": "Yoshiko",
            "恵子": "Keiko",
            "由美": "Yumi",
            "健一": "Kenichi",
            "誠": "Makoto",
            "博": "Hiroshi",
            "明": "Akira",
            "美": "Mi",
            "子": "Ko",
            "郎": "Ro",
            "一": "Ichi",
            "二": "Ni",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E3 rules."""
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
        name = re.sub(r"\s+", " ", name)

        # Handle Japanese punctuation
        name = name.replace("、", ", ")
        name = name.replace("。", ".")
        name = name.replace("！", "!")
        name = name.replace("？", "?")
        name = name.replace("（", "(")
        name = name.replace("）", ")")

        # Convert full-width characters to half-width for Latin
        if self._is_mostly_latin(name):
            name = self._normalize_fullwidth(name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]$", "", name)

        return name.strip()

    def _is_mostly_latin(self, text: str) -> bool:
        """Check if text is mostly Latin characters."""
        latin_count = sum(1 for c in text if ord(c) < 128)
        return latin_count > len(text) / 2

    def _normalize_fullwidth(self, text: str) -> str:
        """Convert full-width characters to half-width."""
        # Unicode normalization to convert full-width to half-width
        return unicodedata.normalize("NFKC", text)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E3-specific data."""
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

        # Add romanized variant if original is Japanese
        if self._is_japanese(canonical):
            romanized = self._romanize_name(canonical)
            if romanized != canonical:
                # Update CanonicalLatin to be romanized
                entry["CanonicalLatin"] = romanized
                entry["Variants"]["Synthesised"].append({"str": romanized, "type": "romanization"})

        # Add hiragana variant if original is kanji
        if self._has_kanji(canonical):
            hiragana = self._to_hiragana(canonical)
            if hiragana != canonical:
                entry["Variants"]["Synthesised"].append({"str": hiragana, "type": "hiragana"})

        # Add katakana variant
        if self._has_hiragana(canonical):
            katakana = self._to_katakana(canonical)
            if katakana != canonical:
                entry["Variants"]["Synthesised"].append({"str": katakana, "type": "katakana"})

        # Rule 12: Japanese Post-2020 Order Rule - majority rule for English papers
        if components.get("family_name") and components.get("given_name"):
            order_variants = self._generate_post_2020_order_variants(canonical, components, entry)
            for variant in order_variants:
                entry["Variants"]["Synthesised"].append(variant)

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if self._is_japanese(name):
            # Japanese names are typically 2-4 characters
            # Try to identify surname based on common patterns
            if len(name) >= 2:
                # Check for common surnames
                for surname in self.common_surnames:
                    if name.startswith(surname):
                        components["family_name"] = surname
                        components["given_name"] = name[len(surname) :]
                        break

                # If no common surname found, guess based on length
                if "family_name" not in components:
                    if len(name) == 2:
                        # 1-1 split
                        components["family_name"] = name[0]
                        components["given_name"] = name[1]
                    elif len(name) == 3:
                        # 1-2 or 2-1 split (prefer 1-2)
                        components["family_name"] = name[0]
                        components["given_name"] = name[1:]
                    elif len(name) == 4:
                        # 2-2 split
                        components["family_name"] = name[:2]
                        components["given_name"] = name[2:]
                    else:
                        # Fallback for longer names
                        components["family_name"] = name[:2]
                        components["given_name"] = name[2:]
        else:
            # Romanized name - assume space-separated
            words = name.split()
            if len(words) >= 2:
                components["family_name"] = words[0]
                components["given_name"] = " ".join(words[1:])
            else:
                components["family_name"] = name

        # Detect script types
        if self._has_kanji(name):
            components["has_kanji"] = True
        if self._has_hiragana(name):
            components["has_hiragana"] = True
        if self._has_katakana(name):
            components["has_katakana"] = True

        return components

    def _is_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters."""
        for char in text:
            if any(start <= ord(char) <= end for start, end in self.japanese_ranges):
                return True
        return False

    def _has_kanji(self, text: str) -> bool:
        """Check if text contains Kanji characters."""
        for char in text:
            if 0x4E00 <= ord(char) <= 0x9FAF or 0x3400 <= ord(char) <= 0x4DBF:
                return True
        return False

    def _has_hiragana(self, text: str) -> bool:
        """Check if text contains Hiragana characters."""
        for char in text:
            if 0x3040 <= ord(char) <= 0x309F:
                return True
        return False

    def _has_katakana(self, text: str) -> bool:
        """Check if text contains Katakana characters."""
        for char in text:
            if 0x30A0 <= ord(char) <= 0x30FF or 0xFF65 <= ord(char) <= 0xFF9F:
                return True
        return False

    def _romanize_name(self, name: str) -> str:
        """Romanize Japanese name using Hepburn system."""
        # Simple romanization using common elements
        if name in self.common_elements:
            return self.common_elements[name]

        # For compound names, try to romanize parts
        result = []
        for element in self.common_elements:
            if element in name:
                result.append(self.common_elements[element])
                name = name.replace(element, "")

        # If we have remaining characters, use basic conversion
        if name:
            # Very basic Hepburn romanization (would need proper library)
            basic_map = {
                "あ": "a",
                "い": "i",
                "う": "u",
                "え": "e",
                "お": "o",
                "か": "ka",
                "き": "ki",
                "く": "ku",
                "け": "ke",
                "こ": "ko",
                "さ": "sa",
                "し": "shi",
                "す": "su",
                "せ": "se",
                "そ": "so",
                "た": "ta",
                "ち": "chi",
                "つ": "tsu",
                "て": "te",
                "と": "to",
                "な": "na",
                "に": "ni",
                "ぬ": "nu",
                "ね": "ne",
                "の": "no",
                "は": "ha",
                "ひ": "hi",
                "ふ": "fu",
                "へ": "he",
                "ほ": "ho",
                "ま": "ma",
                "み": "mi",
                "む": "mu",
                "め": "me",
                "も": "mo",
                "や": "ya",
                "ゆ": "yu",
                "よ": "yo",
                "ら": "ra",
                "り": "ri",
                "る": "ru",
                "れ": "re",
                "ろ": "ro",
                "わ": "wa",
                "を": "wo",
                "ん": "n",
                # Katakana equivalents
                "ア": "a",
                "イ": "i",
                "ウ": "u",
                "エ": "e",
                "オ": "o",
                "カ": "ka",
                "キ": "ki",
                "ク": "ku",
                "ケ": "ke",
                "コ": "ko",
                "サ": "sa",
                "シ": "shi",
                "ス": "su",
                "セ": "se",
                "ソ": "so",
                "タ": "ta",
                "チ": "chi",
                "ツ": "tsu",
                "テ": "te",
                "ト": "to",
                "ナ": "na",
                "ニ": "ni",
                "ヌ": "nu",
                "ネ": "ne",
                "ノ": "no",
                "ハ": "ha",
                "ヒ": "hi",
                "フ": "fu",
                "ヘ": "he",
                "ホ": "ho",
                "マ": "ma",
                "ミ": "mi",
                "ム": "mu",
                "メ": "me",
                "モ": "mo",
                "ヤ": "ya",
                "ユ": "yu",
                "ヨ": "yo",
                "ラ": "ra",
                "リ": "ri",
                "ル": "ru",
                "レ": "re",
                "ロ": "ro",
                "ワ": "wa",
                "ヲ": "wo",
                "ン": "n",
            }

            for char in name:
                if char in basic_map:
                    result.append(basic_map[char])
                else:
                    result.append(char)

        return " ".join(result).title()

    def _to_hiragana(self, name: str) -> str:
        """Convert Katakana to Hiragana."""
        # Simple Katakana to Hiragana conversion
        result = []
        for char in name:
            if 0x30A0 <= ord(char) <= 0x30FF:
                # Convert Katakana to Hiragana
                hiragana_char = chr(ord(char) - 0x60)
                result.append(hiragana_char)
            else:
                result.append(char)
        return "".join(result)

    def _to_katakana(self, name: str) -> str:
        """Convert Hiragana to Katakana."""
        # Simple Hiragana to Katakana conversion
        result = []
        for char in name:
            if 0x3040 <= ord(char) <= 0x309F:
                # Convert Hiragana to Katakana
                katakana_char = chr(ord(char) + 0x60)
                result.append(katakana_char)
            else:
                result.append(char)
        return "".join(result)

    def _generate_post_2020_order_variants(
        self, canonical: str, components: Dict[str, Any], entry: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Rule 12: Japanese Post-2020 Order Rule - majority rule for English papers.

        Since 2020, Japan officially recommends Family Given order for romanized names
        in English language publications. This method generates appropriate variants
        based on the publication context and timeframe.

        Examples:
        - Pre-2020: "Hiroshi Tanaka" (Given Family) was common in English
        - Post-2020: "Tanaka Hiroshi" (Family Given) is now recommended
        """
        variants = []
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        if not family or not given:
            return variants

        # Detect if this is likely an English publication context
        # (i.e., romanized form)
        is_romanized = not self._is_japanese(canonical)

        if is_romanized:
            # Store order information in RegionalExtras
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}
            entry["RegionalExtras"]["post_2020_order_applicable"] = True

            # Determine current order format
            if " " in canonical:
                words = canonical.split()
                first_word = words[0]

                # Check if current format is Given Family or Family Given
                if first_word.lower() == given.lower():
                    # Current is Given Family format (pre-2020 style)
                    # Generate Family Given variant (post-2020 style)
                    post_2020_variant = f"{family} {given}"
                    variants.append({"str": post_2020_variant, "type": "japanese-post-2020-order"})
                elif first_word.lower() == family.lower():
                    # Current is Family Given format (post-2020 style)
                    # Generate Given Family variant (pre-2020 style)
                    pre_2020_variant = f"{given} {family}"
                    variants.append({"str": pre_2020_variant, "type": "japanese-pre-2020-order"})

            # Also generate comma-separated canonical format
            if ", " not in canonical:
                canonical_format = f"{family}, {given}"
                variants.append({"str": canonical_format, "type": "japanese-canonical"})

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E3 rules."""
        # Check for at least one canonical form
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        if not canonical_native and not canonical_latin:
            raise RegionRuleError("Missing both CanonicalNative and CanonicalLatin")

        # If CanonicalNative exists, it should be Japanese
        if canonical_native:
            if not self._is_japanese(canonical_native):
                raise RegionRuleError(f"CanonicalNative should be Japanese: {canonical_native}")

            # Check length - Japanese names are typically 2-4 characters
            if len(canonical_native) < 2 or len(canonical_native) > 6:
                raise RegionRuleError(f"Japanese name length unusual: {canonical_native}")

        # If CanonicalLatin exists, it should be romanized
        if canonical_latin:
            if self._is_japanese(canonical_latin):
                raise RegionRuleError(f"CanonicalLatin should be romanized: {canonical_latin}")

            # Check for valid romanization pattern
            if not self._is_valid_romanization(canonical_latin):
                raise RegionRuleError(f"Invalid romanization format: {canonical_latin}")

    def _is_valid_romanization(self, text: str) -> bool:
        """Check if text is valid Japanese romanization."""
        # Remove punctuation for validation
        text_clean = text.replace(",", " ").replace(".", " ")
        # Basic validation for Japanese romanization
        words = text_clean.split()
        for word in words:
            # Should only contain Latin letters and basic marks
            if word and not re.match(r"^[a-zA-Z-]+$", word):
                return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Use romanized form for sorting if available
        canonical = entry.get("CanonicalLatin", "")

        # If no Latin form, generate romanization
        if not canonical:
            native = entry.get("CanonicalNative", "")
            if native and self._is_japanese(native):
                canonical = self._romanize_name(native)

        # Normalize for sorting
        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        # Generate key - Japanese names are Family Given
        key = f"{sort_family} {sort_given}"

        # Ensure determinism
        key = " ".join(key.split())

        return key
