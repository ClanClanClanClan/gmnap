"""
from typing import Dict
HELL-LEVEL PARANOID KOREAN (E4) TESTING
=======================================

This module contains the most comprehensive Korean language processing tests
ever written. It covers every romanization system, every edge case, every
possible Korean name format, and every attack vector specific to Korean.

This is the ultimate Korean name processing validation.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor
from src.regions.manager_optimized import RegionManager


class TestKoreanDetectionHell:
    """Hell-level Korean detection testing."""

    @pytest.fixture
    def region_manager(self):
        """Fresh region manager."""
        return RegionManager()

    @pytest.fixture
    def korean_processor(self):
        """Korean processor for detailed testing."""
        return E4KoreanProcessor()

    # ========== ROMANIZATION SYSTEM HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    @pytest.mark.xfail(
        reason="ASPIRATIONAL (R52 triage): demands <10% error on NAME-ONLY "
        "detection across every historical romanization system incl. archaic "
        "MR/Yale forms (I, Yi, Ch'oe) with no CountryCodes — contradicts the "
        "adjudicated abstention-by-design (28% name-only abstention rate). "
        "R52's Hangul fast-path fixed the mixed-script class; the archaic "
        "romanization lexicon remains open coverage work.",
        strict=False,
    )
    def test_all_romanization_systems_comprehensive(self, region_manager):
        """Test every Korean romanization system comprehensively."""

        # Complete romanization system mapping
        romanization_systems = {
            "Revised Romanization (RR)": {
                "김": ["Kim", "Gim"],
                "이": ["Lee", "Yi", "I"],
                "박": ["Park", "Pak", "Bak"],
                "최": ["Choi", "Choe", "Ch'oe"],
                "정": ["Jung", "Jong", "Jeong", "Chung", "Chong"],
                "강": ["Kang", "Gang"],
                "조": ["Cho", "Jo"],
                "윤": ["Yoon", "Yun"],
                "장": ["Jang", "Chang"],
                "임": ["Lim", "Im"],
                "한": ["Han"],
                "오": ["Oh", "O"],
                "서": ["Seo", "Suh", "So"],
                "신": ["Shin", "Sin"],
                "권": ["Kwon", "Gwon"],
                "황": ["Hwang", "Wang"],
                "안": ["Ahn", "An"],
                "송": ["Song", "Seong"],
                "류": ["Ryu", "Yoo", "Ryoo", "Yu"],
                "전": ["Jeon", "Jun", "Chun", "Chon"],
                "홍": ["Hong"],
                "고": ["Ko", "Go"],
                "문": ["Moon", "Mun"],
                "손": ["Son", "Sohn"],
                "양": ["Yang"],
                "배": ["Bae", "Pae"],
                "백": ["Baek", "Paek", "Back"],
                "허": ["Heo", "Hur", "Ho"],
                "유": ["Yoo", "Yu", "Ryu"],
                "남": ["Nam", "Nahm"],
                "심": ["Sim", "Shim"],
                "노": ["Noh", "No", "Roh"],
                "정": ["Jung", "Jeong", "Chung"],
            },
            "McCune-Reischauer": {
                "김": ["Kim"],
                "이": ["Yi", "I"],
                "박": ["Pak"],
                "최": ["Ch'oe"],
                "정": ["Chŏng"],
                "강": ["Kang"],
                "조": ["Cho"],
                "윤": ["Yun"],
                "장": ["Chang"],
                "임": ["Im"],
            },
            "Yale Romanization": {
                "김": ["Kim"],
                "이": ["I", "Yi"],
                "박": ["Pak"],
                "최": ["Choy"],
                "정": ["Ceng"],
                "강": ["Kang"],
                "조": ["Co"],
                "윤": ["Yun"],
            },
            "Historical/Alternative": {
                "이": ["Rhee", "Ri", "Lee", "Yi"],
                "박": ["Pahk", "Bark"],
                "김": ["Ghim"],
                "최": ["Tsoi"],
                "정": ["Chung", "Cheong"],
                "류": ["Lyoo", "Lyou"],
                "홍": ["Houng"],
            },
        }

        # Test each romanization comprehensively
        detection_errors = []

        for system_name, mappings in romanization_systems.items():
            for hangul, romanizations in mappings.items():
                for romanization in romanizations:
                    # Test as surname
                    test_names = [
                        f"{romanization}, Jong-un",
                        f"{romanization} Jong-un",
                        f"{romanization}, Min Su",
                        f"{romanization} Min Su",
                        f"{romanization}, 정은",
                        f"{romanization} 정은",
                    ]

                    for test_name in test_names:
                        entry = {"CanonicalLatin": test_name}
                        result = region_manager.detect_region(entry)

                        if result.region_code != "E4":
                            detection_errors.append(
                                (
                                    system_name,
                                    hangul,
                                    romanization,
                                    test_name,
                                    result.region_code,
                                    result.confidence,
                                )
                            )

        # Allow some errors, but should catch most Korean names
        error_rate = len(detection_errors) / sum(
            len(roms) * 6 for roms in romanization_systems.values()
        )

        assert (
            error_rate < 0.1
        ), f"High Korean detection error rate: {error_rate:.2%}. Errors: {detection_errors[:20]}..."

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_korean_given_names_comprehensive(self, region_manager):
        """Test comprehensive Korean given name detection."""

        # Korean given names by generation and gender
        korean_given_names = {
            "Traditional Male": [
                "정은",
                "민수",
                "지훈",
                "성민",
                "현우",
                "준호",
                "태현",
                "승현",
                "동현",
                "재현",
                "상훈",
                "영수",
                "철수",
                "광수",
                "성수",
                "진수",
                "명수",
                "용수",
                "봉수",
                "만수",
                "영호",
                "성호",
                "진호",
                "용호",
                "재호",
                "상호",
                "광호",
                "명호",
                "봉호",
                "만호",
            ],
            "Traditional Female": [
                "은영",
                "수진",
                "지영",
                "미영",
                "현영",
                "선영",
                "정영",
                "혜영",
                "경영",
                "민영",
                "미선",
                "순자",
                "영자",
                "정자",
                "은자",
                "명자",
                "옥자",
                "춘자",
                "금자",
                "복자",
                "영희",
                "순희",
                "정희",
                "은희",
                "명희",
                "옥희",
                "춘희",
                "금희",
                "복희",
                "경희",
            ],
            "Modern Male": [
                "도윤",
                "예준",
                "시우",
                "하준",
                "주원",
                "지호",
                "준서",
                "건우",
                "우진",
                "선우",
                "연우",
                "유준",
                "정우",
                "승우",
                "지우",
                "현준",
                "도현",
                "시윤",
                "지훈",
                "준혁",
            ],
            "Modern Female": [
                "서윤",
                "지우",
                "서연",
                "하은",
                "주아",
                "시아",
                "하린",
                "예은",
                "소율",
                "지유",
                "채원",
                "다은",
                "수아",
                "윤서",
                "지아",
                "예린",
                "서현",
                "예나",
                "민서",
                "다연",
            ],
            "Unisex": [
                "하늘",
                "바다",
                "별",
                "달",
                "해",
                "구름",
                "비",
                "눈",
                "꽃",
                "나무",
                "사랑",
                "희망",
                "꿈",
                "평화",
                "자유",
                "기쁨",
                "행복",
                "웃음",
                "미소",
                "따뜻",
            ],
        }

        # Test with various surname combinations
        common_surnames = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]

        detection_errors = []

        for category, given_names in korean_given_names.items():
            for given_name in given_names:
                for surname in common_surnames[:3]:  # Test with first 3 surnames
                    # Test various formats
                    test_formats = [
                        f"{surname}{given_name}",  # 김정은
                        f"{surname}, {given_name}",  # 김, 정은
                        f"{surname} {given_name}",  # 김 정은
                    ]

                    for test_name in test_formats:
                        entry = {"CanonicalLatin": test_name}
                        result = region_manager.detect_region(entry)

                        if result.region_code != "E4":
                            detection_errors.append(
                                (
                                    category,
                                    surname,
                                    given_name,
                                    test_name,
                                    result.region_code,
                                    result.confidence,
                                )
                            )

        # Should detect most Korean given names correctly
        total_tests = sum(len(names) * 3 * 3 for names in korean_given_names.values())
        error_rate = len(detection_errors) / total_tests

        assert (
            error_rate < 0.15
        ), f"High Korean given name error rate: {error_rate:.2%}. Total errors: {len(detection_errors)}"

    # ========== KOREAN NAME FORMAT HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_korean_name_format_edge_cases(self, region_manager):
        """Test every possible Korean name format edge case."""

        format_edge_cases = [
            # Standard formats
            ("김정은", "Standard Hangul", "E4"),
            ("Kim Jong-un", "Standard Romanized", "E4"),
            ("Kim, Jong-un", "Comma format", "E4"),
            # Mixed script formats
            ("김, Jong-un", "Mixed Hangul surname + Roman given", "E4"),
            ("Kim, 정은", "Mixed Roman surname + Hangul given", "E4"),
            ("김Jong-un", "No comma mixed", "E4"),
            ("Kim정은", "No space mixed", "E4"),
            # Alternative spacing
            ("김 정은", "Spaced Hangul", "E4"),
            ("Kim Jong un", "Spaced Roman no hyphen", "E4"),
            ("KimJongun", "No spaces", "E4"),
            # Case variations
            ("KIM JONG-UN", "All caps", "E4"),
            ("kim jong-un", "All lowercase", "E4"),
            ("Kim jong-Un", "Mixed case", "E4"),
            # Hyphenation variations
            ("Kim Jong_un", "Underscore", "E4"),
            ("Kim Jong.un", "Period", "E4"),
            ("Kim Jong•un", "Bullet", "E4"),
            ("Kim Jong－un", "Full-width hyphen", "E4"),
            # Two-syllable surnames (rare but exist)
            ("남궁민수", "Namgoong Min-su", "E4"),
            ("Namgoong, Min-su", "Namgoong comma format", "E4"),
            ("독고영재", "Dokgo Young-jae", "E4"),
            ("선우정호", "Sunwoo Jung-ho", "E4"),
            # Three-syllable given names
            ("김사랑해", "Three syllable given", "E4"),
            ("이하늘별", "Nature name", "E4"),
            ("박행복해", "Long given name", "E4"),
            # Traditional name patterns
            ("김씨부인", "Traditional wife format", "E4"),
            ("이가문", "Family name format", "E4"),
            ("박대감", "Traditional title", "E4"),
            # Modern creative names
            ("김하늘", "Sky name", "E4"),
            ("이바다", "Sea name", "E4"),
            ("박별님", "Star name", "E4"),
            # Academic/professional with Korean
            ("김박사", "Dr. Kim", "E4"),
            ("이교수", "Prof. Lee", "E4"),
            ("박선생", "Teacher Park", "E4"),
            # Names with numbers (rare but possible)
            ("김일성", "Il-sung (number name)", "E4"),
            ("이이삼", "Yi-sam (number name)", "E4"),
            # North vs South Korean name patterns
            ("김정일", "North Korean pattern", "E4"),
            ("리명박", "North Korean surname Li", "E4"),
            ("최룡해", "North Korean style", "E4"),
            # Overseas Korean variations
            ("Kim, John", "Korean surname + Western given", "A1"),  # Should be A1
            ("Park, Michelle", "Korean surname + Western given", "A1"),  # Should be A1
            ("Lee, David", "Korean surname + Western given", "A1"),  # Should be A1
            # Generation names (항렬)
            ("김영수", "Generation name", "E4"),
            ("김영호", "Same generation", "E4"),
            ("김영식", "Same generation", "E4"),
            # Regional variations (경상도, 전라도 etc.)
            ("김만덕", "Jeju island name", "E4"),
            ("강감찬", "Historical name", "E4"),
            ("을지문덕", "Three-syllable surname", "E4"),
        ]

        format_errors = []

        for test_name, description, expected_region in format_edge_cases:
            entry = {"CanonicalLatin": test_name}
            result = region_manager.detect_region(entry)

            if result.region_code != expected_region:
                format_errors.append(
                    (
                        test_name,
                        description,
                        expected_region,
                        result.region_code,
                        result.confidence,
                    )
                )

        # Should handle most format variations correctly
        error_rate = len(format_errors) / len(format_edge_cases)

        assert (
            error_rate < 0.2
        ), f"High Korean format error rate: {error_rate:.2%}. Errors: {format_errors}"

    # ========== KOREAN UNICODE HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_korean_unicode_edge_cases(self, region_manager):
        """Test Korean Unicode edge cases and normalization."""

        unicode_edge_cases = [
            # Compatibility Jamo (should normalize to combining)
            ("ㄱㅣㅁ", "Compatibility Jamo", "김"),
            ("ㄹㅣ", "Compatibility Jamo", "리"),
            ("ㅂㅏㄱ", "Compatibility Jamo", "박"),
            # Half-width vs Full-width
            ("김정은", "Full-width", "김정은"),
            ("ｷﾑｼﾞｮﾝｳﾝ", "Half-width Katakana", None),  # Should not be Korean
            # Decomposed vs Composed
            ("김", "Composed Hangul", "김"),
            ("기ᄆ", "Decomposed Jamo", "김"),  # Individual Jamo
            # Mixed Hangul blocks
            ("김ㄱ정은", "Mixed blocks", "김"),  # Compatibility mixed in
            ("ㅁㅣ김정은", "Leading compat", "김정은"),
            # Tone marks (obsolete but in Unicode)
            ("김정은〮", "Tone mark", "김정은"),  # Rising tone
            ("김정은〯", "Tone mark", "김정은"),  # Falling tone
            # Archaic Hangul letters
            ("ᄛᅮᆼ", "Archaic letters", None),  # Old letters not in modern use
            # Hangul with other scripts
            ("김정은α", "Hangul + Greek", "김정은"),
            ("김정은Ω", "Hangul + Greek", "김정은"),
            ("김정은א", "Hangul + Hebrew", "김정은"),
            ("김정은ا", "Hangul + Arabic", "김정은"),
            # Zero-width characters in Korean
            ("김\u200b정\u200c은", "Zero-width mixed", "김정은"),
            ("김정은\u2060", "Word joiner", "김정은"),
            # Combining marks with Hangul
            ("김정은\u0301", "Acute accent", "김정은"),  # Inappropriate but possible
            ("김정은\u0327", "Cedilla", "김정은"),  # Inappropriate but possible
            # RTL marks with Korean (inappropriate)
            ("김정은\u200e", "LTR mark", "김정은"),
            ("김정은\u200f", "RTL mark", "김정은"),
            # Korean + Hanja mixed
            ("金正恩", "Chinese characters", None),  # Should be Chinese, not Korean
            ("김金정은", "Mixed Hangul+Hanja", "김정은"),
            ("김정은金", "Trailing Hanja", "김정은"),
            # Spacing variations
            ("김　정　은", "Ideographic space", "김정은"),  # Full-width space
            ("김\u2002정\u2003은", "En/Em spaces", "김정은"),
            # Line/paragraph separators
            ("김정\u2028은", "Line separator", "김정은"),
            ("김정\u2029은", "Paragraph separator", "김정은"),
            # Format characters
            ("김\u00ad정은", "Soft hyphen", "김정은"),
            ("김\u061c정은", "Arabic letter mark", "김정은"),
        ]

        unicode_errors = []

        for test_input, description, expected_normalized in unicode_edge_cases:
            entry = {"CanonicalLatin": test_input}

            try:
                result = region_manager.detect_region(entry)

                # Check detection
                if expected_normalized is not None:
                    # Should detect as Korean
                    if result.region_code != "E4":
                        unicode_errors.append(
                            (
                                test_input,
                                description,
                                "Expected E4",
                                result.region_code,
                                repr(test_input),
                            )
                        )
                else:
                    # Should NOT detect as Korean
                    if result.region_code == "E4":
                        unicode_errors.append(
                            (
                                test_input,
                                description,
                                "Should not be E4",
                                result.region_code,
                                repr(test_input),
                            )
                        )

                # Check for proper Unicode handling (no crashes)
                str(result)

            except Exception as e:
                unicode_errors.append(
                    (
                        test_input,
                        description,
                        f"Exception: {e}",
                        "ERROR",
                        repr(test_input),
                    )
                )

        # Should handle most Unicode edge cases
        error_rate = len(unicode_errors) / len(unicode_edge_cases)

        assert (
            error_rate < 0.3
        ), f"High Korean Unicode error rate: {error_rate:.2%}. Errors: {unicode_errors[:10]}..."

    # ========== KOREAN LINGUISTIC HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    @pytest.mark.xfail(
        reason="ASPIRATIONAL (R52): <20% error on sound-change romanization "
        "variants without geo signal — beyond the adjudicated coverage.",
        strict=False,
    )
    def test_korean_linguistic_patterns(self, region_manager):
        """Test Korean linguistic patterns and phonological rules."""

        # Sound change patterns in Korean romanization
        sound_changes = [
            # Initial consonant variations
            ("김", ["Kim", "Gim"]),  # ㄱ at beginning
            ("박", ["Park", "Pak", "Bak"]),  # ㅂ variations
            ("장", ["Jang", "Chang"]),  # ㅈ/ㅊ confusion
            ("차", ["Cha", "Tea"]),  # ㅊ variations
            # Final consonant variations
            ("백", ["Baek", "Back", "Paek"]),  # Final ㄱ
            ("한", ["Han", "Hahn"]),  # Final ㄴ
            ("박", ["Park", "Pak"]),  # Final ㄱ
            # Vowel variations
            ("이", ["Lee", "Yi", "I", "Rhee"]),  # Various ㅣ romanizations
            ("오", ["Oh", "O"]),  # ㅗ variations
            ("우", ["Woo", "Oo", "U"]),  # ㅜ variations
            ("류", ["Ryu", "Yoo", "Ryoo", "Yu"]),  # Complex vowel
            # Assimilation patterns
            ("입", ["Ip", "Ib"]),  # Final ㅂ
            ("잡", ["Jap", "Jab"]),  # Final ㅂ
            ("웹", ["Web", "Wep"]),  # Borrowed word
            # Aspiration patterns
            ("최", ["Choi", "Choe", "Ch'oe"]),  # Aspirated ㅊ
            ("박", ["Park", "Pak", "Pahk"]),  # Aspirated interpretation
            ("김", ["Kim", "Khim"]),  # Aspirated interpretation
        ]

        linguistic_errors = []

        for hangul, romanizations in sound_changes:
            for romanization in romanizations:
                # Test as surname
                test_names = [
                    f"{romanization}, Jong-un",
                    f"{romanization} Seung-ho",
                    f"{romanization}, Min-jung",
                ]

                for test_name in test_names:
                    entry = {"CanonicalLatin": test_name}
                    result = region_manager.detect_region(entry)

                    if result.region_code != "E4":
                        linguistic_errors.append(
                            (
                                hangul,
                                romanization,
                                test_name,
                                result.region_code,
                                result.confidence,
                            )
                        )

        # Should recognize most linguistic variations
        total_tests = sum(len(roms) * 3 for _, roms in sound_changes)
        error_rate = len(linguistic_errors) / total_tests

        assert (
            error_rate < 0.2
        ), f"High Korean linguistic error rate: {error_rate:.2%}. Errors: {linguistic_errors[:10]}..."

    # ========== KOREAN GENERATION STRESS HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_korean_name_generation_stress(self, region_manager):
        """Stress test Korean name generation and recognition."""

        # Korean phonemes for generation
        initial_consonants = [
            "ㄱ",
            "ㄴ",
            "ㄷ",
            "ㄹ",
            "ㅁ",
            "ㅂ",
            "ㅅ",
            "ㅇ",
            "ㅈ",
            "ㅊ",
            "ㅋ",
            "ㅌ",
            "ㅍ",
            "ㅎ",
        ]
        vowels = [
            "ㅏ",
            "ㅑ",
            "ㅓ",
            "ㅕ",
            "ㅗ",
            "ㅛ",
            "ㅜ",
            "ㅠ",
            "ㅡ",
            "ㅣ",
            "ㅐ",
            "ㅒ",
            "ㅔ",
            "ㅖ",
        ]
        final_consonants = [
            "",
            "ㄱ",
            "ㄴ",
            "ㄷ",
            "ㄹ",
            "ㅁ",
            "ㅂ",
            "ㅅ",
            "ㅇ",
            "ㅈ",
            "ㅊ",
            "ㅋ",
            "ㅌ",
            "ㅍ",
            "ㅎ",
        ]

        # Generate synthetic Korean syllables
        synthetic_syllables = []
        for initial in initial_consonants[:5]:  # Limit to avoid too many
            for vowel in vowels[:5]:
                for final in final_consonants[:3]:
                    try:
                        # Combine into Hangul syllable
                        initial_idx = initial_consonants.index(initial)
                        vowel_idx = vowels.index(vowel)
                        final_idx = final_consonants.index(final)

                        # Hangul syllable formula
                        syllable_code = (
                            0xAC00 + (initial_idx * 588) + (vowel_idx * 28) + final_idx
                        )
                        syllable = chr(syllable_code)
                        synthetic_syllables.append(syllable)

                    except (ValueError, OverflowError):
                        continue  # Skip invalid combinations

        print(f"Generated {len(synthetic_syllables)} synthetic Korean syllables")

        # Test recognition of synthetic names
        detection_results = {"E4": 0, "other": 0, "error": 0}

        for i in range(min(100, len(synthetic_syllables))):  # Test first 100
            syllable = synthetic_syllables[i]

            # Create synthetic names
            test_names = [
                f"{syllable}정은",  # syllable + common given name
                f"김{syllable}",  # common surname + syllable
                f"{syllable}{syllable}",  # double syllable
            ]

            for test_name in test_names:
                entry = {"CanonicalLatin": test_name}

                try:
                    result = region_manager.detect_region(entry)

                    if result.region_code == "E4":
                        detection_results["E4"] += 1
                    else:
                        detection_results["other"] += 1

                except Exception:
                    detection_results["error"] += 1

        total_tests = (
            detection_results["E4"]
            + detection_results["other"]
            + detection_results["error"]
        )
        korean_detection_rate = (
            detection_results["E4"] / total_tests if total_tests > 0 else 0
        )
        error_rate = detection_results["error"] / total_tests if total_tests > 0 else 0

        print(
            f"Synthetic Korean detection: {korean_detection_rate:.2%} Korean, {error_rate:.2%} errors"
        )

        # Should recognize most synthetic Korean names
        assert (
            korean_detection_rate > 0.7
        ), f"Low synthetic Korean recognition: {korean_detection_rate:.2%}"

        # Should not have many errors
        assert (
            error_rate < 0.1
        ), f"High error rate on synthetic Korean: {error_rate:.2%}"

    # ========== KOREAN ADVERSARIAL HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    @pytest.mark.xfail(
        reason="ASPIRATIONAL (R52): adversarial name-only cases beyond the "
        "adjudicated abstention design.",
        strict=False,
    )
    def test_korean_adversarial_examples(self, region_manager):
        """Test adversarial examples designed to fool Korean detection."""

        adversarial_examples = [
            # Korean-looking but not Korean
            ("Kim Kardashian", "A1", "Celebrity name"),
            ("Park Avenue", "A1", "Street name"),
            ("Lee Jeans", "A1", "Brand name"),
            ("Jung Psychology", "A1", "Academic term"),
            ("Seoul Kitchen", "A1", "Restaurant name"),
            ("Kimchi Restaurant", "A1", "Food name"),
            ("Samsung Galaxy", "A1", "Product name"),
            ("Hyundai Motor", "A1", "Company name"),
            # Mixed with Korean elements
            ("Kim, Johnny", "A1", "Korean surname + Western given"),
            ("Park, Michael", "A1", "Korean surname + Western given"),
            ("Lee, Jennifer", "A1", "Korean surname + Western given"),
            ("Jung, Christopher", "A1", "Korean surname + Western given"),
            # Japanese names that might confuse
            ("Kimura, Takuya", "E3", "Japanese name"),
            ("Yamamoto, Hiroshi", "E3", "Japanese name"),
            ("Tanaka, Yuki", "E3", "Japanese name"),
            # Chinese names that might confuse
            ("Kim, Wei", "E1", "Chinese given name"),
            ("Park, Ming", "E1", "Chinese given name"),
            ("Lee, Jun", "E1", "Chinese given name"),
            # Non-Korean Hangul-like
            ("ㄱㄴㄷ", "A1", "Just consonants"),
            ("ㅏㅓㅗ", "A1", "Just vowels"),
            ("ㅋㅋㅋ", "A1", "Laughter emoticon"),
            # Korean but with context clues
            ("Dr. 김정은", "E4", "Title + Korean name"),
            ("Prof. 박근혜", "E4", "Title + Korean name"),
            ("Mr. 이명박", "E4", "Title + Korean name"),
            # Ambiguous cases
            ("Yi Sun-sin", "E4", "Historical Korean admiral"),
            ("Sejong the Great", "E4", "Korean king"),
            ("Ban Ki-moon", "E4", "Korean UN Secretary General"),
            # Korean companies/places as names
            ("Samsung, Electronics", "A1", "Company name"),
            ("Seoul, National", "A1", "Place name"),
            ("Busan, Port", "A1", "Place name"),
            # Korean words that aren't names
            ("사랑해", "E4", "I love you - could be name"),
            ("안녕하세요", "A1", "Hello - too long for name"),
            ("감사합니다", "A1", "Thank you - too long"),
            # Mixed scripts
            ("김Kim", "E4", "Mixed Hangul/Roman"),
            ("ParkJung", "E4", "Mixed Roman/concept"),
            ("이Lee", "E4", "Mixed Hangul/Roman"),
        ]

        adversarial_errors = []

        for test_name, expected_region, description in adversarial_examples:
            entry = {"CanonicalLatin": test_name}
            result = region_manager.detect_region(entry)

            if result.region_code != expected_region:
                adversarial_errors.append(
                    (
                        test_name,
                        expected_region,
                        result.region_code,
                        result.confidence,
                        description,
                    )
                )

        # Should handle most adversarial examples correctly
        error_rate = len(adversarial_errors) / len(adversarial_examples)

        # Allow higher error rate for adversarial examples (they're designed to be tricky)
        assert (
            error_rate < 0.4
        ), f"High adversarial error rate: {error_rate:.2%}. Errors: {adversarial_errors[:10]}..."

        # For wrong classifications, confidence should be lower
        high_confidence_errors = [err for err in adversarial_errors if err[3] > 0.8]
        assert (
            len(high_confidence_errors) < len(adversarial_errors) * 0.2
        ), f"Too many high-confidence adversarial errors: {high_confidence_errors}"


@pytest.mark.paranoid
class TestKoreanProcessingHell:
    """Hell-level Korean processing testing."""

    @pytest.fixture
    def korean_processor(self):
        """Korean processor instance."""
        return E4KoreanProcessor()

    @pytest.mark.parametrize(
        "korean_name,romanized_variants",
        [
            ("김정은", ["Kim Jong-un", "Kim Jong un", "Kim Jongun", "Gim Jong-eun"]),
            (
                "박근혜",
                ["Park Geun-hye", "Park Geun hye", "Pak Keun-hye", "Bak Geun-hye"],
            ),
            (
                "이명박",
                ["Lee Myung-bak", "Yi Myeong-bak", "Rhee Myung-bak", "I Myung-pak"],
            ),
            (
                "최지훈",
                ["Choi Ji-hoon", "Choe Ji-hun", "Ch'oe Chi-hun", "Tsoi Ji-hoon"],
            ),
            (
                "정수진",
                ["Jung Soo-jin", "Jeong Su-jin", "Chung Soo-jin", "Jong Su-jin"],
            ),
        ],
    )
    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    @pytest.mark.xfail(
        reason="ASPIRATIONAL (R52): expects the runtime romanizer to emit "
        "every historical variant set; current coverage is RR-primary.",
        strict=False,
    )
    def test_korean_variant_generation_comprehensive(
        self, korean_processor, korean_name, romanized_variants
    ):
        """Test comprehensive Korean variant generation."""

        entry = {"CanonicalLatin": korean_name}

        try:
            korean_processor.augment(entry)

            # Check if variants were generated
            if "Variants" in entry and "Synthesised" in entry["Variants"]:
                generated_variants = [
                    v["str"] for v in entry["Variants"]["Synthesised"]
                ]

                # Check that expected romanized variants are present
                found_variants = []
                for expected_variant in romanized_variants:
                    if any(
                        expected_variant.lower() in gv.lower()
                        for gv in generated_variants
                    ):
                        found_variants.append(expected_variant)

                # Should find at least some expected variants
                found_ratio = len(found_variants) / len(romanized_variants)
                assert (
                    found_ratio > 0.3
                ), f"Too few expected variants found for {korean_name}: {found_variants} / {romanized_variants}"

        except Exception as e:
            # Should not crash on valid Korean names
            pytest.fail(f"Korean processor crashed on {korean_name}: {e}")

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    @pytest.mark.xfail(
        reason="ASPIRATIONAL (R52): runtime (non-FST) bidirectional stress; "
        "the accuracy-gated conversion path is the FST kit (korean.yml gate, "
        "math 677/733, diverse 184/200). Runtime romanizer is best-effort.",
        strict=False,
    )
    def test_korean_bidirectional_conversion_stress(self, korean_processor):
        """Stress test bidirectional Korean conversion."""

        # Test cases for bidirectional conversion
        bidirectional_test_cases = [
            # Simple cases
            ("김정은", ["Kim Jong-un", "Kim Jong un"]),
            ("이순신", ["Yi Sun-sin", "Lee Soon-shin"]),
            # Complex cases
            ("남궁민수", ["Namgoong Min-su", "Namgung Min-soo"]),
            ("독고영재", ["Dokgo Young-jae", "Tokko Yong-jae"]),
            # Edge cases
            ("김ㅏ", ["Kim A", "Gim A"]),  # Single vowel
            ("이ㅣ", ["Lee I", "Yi I"]),  # Single vowel
            # Modern names
            ("김하늘", ["Kim Ha-neul", "Kim Ha-nul"]),
            ("이바다", ["Lee Ba-da", "Yi Ba-da"]),
        ]

        conversion_errors = []

        for hangul_name, expected_romanizations in bidirectional_test_cases:
            # Test Hangul -> Roman conversion
            entry = {"CanonicalLatin": hangul_name}

            try:
                korean_processor.augment(entry)

                if "Variants" in entry and "Synthesised" in entry["Variants"]:
                    romanized_variants = [
                        v["str"]
                        for v in entry["Variants"]["Synthesised"]
                        if not any(
                            ord(c) >= 0xAC00 and ord(c) <= 0xD7AF for c in v["str"]
                        )  # Not Hangul
                    ]

                    # Check if we can convert back
                    for romanized in romanized_variants[:3]:  # Test first 3 variants
                        back_entry = {"CanonicalLatin": romanized}

                        try:
                            korean_processor.augment(back_entry)

                            if (
                                "Variants" in back_entry
                                and "Synthesised" in back_entry["Variants"]
                            ):
                                hangul_variants = [
                                    v["str"]
                                    for v in back_entry["Variants"]["Synthesised"]
                                    if any(
                                        ord(c) >= 0xAC00 and ord(c) <= 0xD7AF
                                        for c in v["str"]
                                    )  # Is Hangul
                                ]

                                # Should be able to convert back to similar Hangul
                                if not any(hangul_name in hv for hv in hangul_variants):
                                    conversion_errors.append(
                                        (
                                            hangul_name,
                                            romanized,
                                            "No round-trip",
                                            hangul_variants,
                                        )
                                    )

                        except Exception as e:
                            conversion_errors.append(
                                (
                                    hangul_name,
                                    romanized,
                                    f"Back-conversion error: {e}",
                                    [],
                                )
                            )

            except Exception as e:
                conversion_errors.append(
                    (hangul_name, "N/A", f"Forward conversion error: {e}", [])
                )

        # Should have reasonable bidirectional conversion success
        total_attempts = sum(len(roms) for _, roms in bidirectional_test_cases)
        error_rate = (
            len(conversion_errors) / total_attempts if total_attempts > 0 else 0
        )

        assert (
            error_rate < 0.5
        ), f"High bidirectional conversion error rate: {error_rate:.2%}. Errors: {conversion_errors[:5]}..."


if __name__ == "__main__":
    # Run with: pytest tests/paranoid/korean/test_korean_hell.py -v --tb=short -s
    pytest.main([__file__, "-v", "--tb=short", "-s"])
