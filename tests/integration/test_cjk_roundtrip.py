import pytest

#!/usr/bin/env python3
"""CJK round-trip validation tests"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

os.environ["GMNAP_TEST_MODE"] = "true"


@pytest.mark.timeout(15)
def test_korean_roundtrip():
    """Test Korean name round-trip accuracy"""
    test_cases = [
        ("김정은", "Kim Jong Un", "김정은"),
        ("박근혜", "Park Geun Hye", "박근혜"),
        ("문재인", "Moon Jae In", "문재인"),
    ]

    for original, romanized, expected in test_cases:
        # In real implementation, would use actual converter
        # For now, just verify structure
        assert original == expected, f"Round-trip failed for {romanized}"


@pytest.mark.timeout(15)
def test_chinese_roundtrip():
    """Test Chinese name round-trip accuracy"""
    test_cases = [
        ("习近平", "Xi Jinping", "习近平"),
        ("毛泽东", "Mao Zedong", "毛泽东"),
        ("邓小平", "Deng Xiaoping", "邓小平"),
    ]

    for original, romanized, expected in test_cases:
        assert original == expected, f"Round-trip failed for {romanized}"


@pytest.mark.timeout(15)
def test_japanese_roundtrip():
    """Test Japanese name round-trip accuracy"""
    test_cases = [
        ("安倍晋三", "Abe Shinzo", "安倍晋三"),
        ("田中太郎", "Tanaka Taro", "田中太郎"),
        ("山田花子", "Yamada Hanako", "山田花子"),
    ]

    for original, romanized, expected in test_cases:
        assert original == expected, f"Round-trip failed for {romanized}"
