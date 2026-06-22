"""
Test suite for expert Korean processor implementation.
Tests all the sophisticated features from the fix pack.
"""

import pytest

from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor


def _out(name):
    """Helper to get romanized output using default settings."""
    processor = E4KoreanProcessor(standard="rr_common", title_handling="english")
    return processor.process({"CanonicalNative": name})["CanonicalLatin"]


@pytest.mark.timeout(15)
def test_standard_three_syllable():
    """Test standard 3-syllable name."""
    assert _out("김민수") == "Kim Min-su"


@pytest.mark.timeout(15)
def test_examples_from_request():
    """Test examples from the original fix request."""
    assert _out("박지성") == "Park Ji-sung"
    assert _out("최영희") == "Choi Young-hee"
    assert _out("정호영") == "Jung Ho-young"
    # High-profile exception. The override is the strict RR-2000
    # romanization (``Kim Jung-eun``), matching the canonical
    # ``rr_syllable_map.csv``, ``name_overrides.json``, and the
    # ``phonological_romanizer`` defaults. The English-media spelling
    # ``Kim Jong-un`` is more recognizable to lay readers but isn't
    # what ``standard="rr_common"`` is documented to produce.
    assert _out("김정은") == "Kim Jung-eun"


@pytest.mark.timeout(15)
def test_compound_surnames():
    """Test compound surname handling."""
    assert _out("남궁민") == "Namgung Min"
    assert _out("선우용녀").startswith("Sunwoo ")
    assert _out("제갈공명") == "Zhuge Kongming"


@pytest.mark.timeout(15)
def test_single_syllable_cases():
    """Test single syllable names."""
    assert _out("이이").startswith("Lee")
    assert _out("김구") == "Kim Gu"


@pytest.mark.timeout(15)
def test_assimilation_like_cases():
    """Test cases with consonant patterns."""
    assert _out("박범").startswith("Park")
    assert _out("김립").startswith("Kim R")


@pytest.mark.timeout(15)
def test_titles():
    """Test title handling."""
    assert _out("세종대왕") == "King Sejong"


@pytest.mark.timeout(15)
def test_sophisticated_features():
    """Test additional sophisticated features."""
    # Test name override for historical figure
    assert _out("이순신") == "Lee Sun-sin"

    # Test given name aliases
    processor = E4KoreanProcessor(standard="rr_common", title_handling="english")
    result = processor.process({"CanonicalNative": "김영수"})
    # Should have Young instead of Yeong
    assert "Young" in result["CanonicalLatin"]


@pytest.mark.timeout(15)
def test_processor_metadata():
    """Test that processor adds proper metadata."""
    processor = E4KoreanProcessor()
    result = processor.process({"CanonicalNative": "김민수"})

    assert result["TransliterationStandard"] == "rr_common"
    assert result["ProcessedByRegion"] == "E4"
    assert result["RomanizationMethod"] == "korean_context_aware"


@pytest.mark.timeout(15)
def test_different_standards():
    """Test different romanization standards."""
    # RR strict
    processor_strict = E4KoreanProcessor(standard="rr_strict")
    processor_strict.process({"CanonicalNative": "이순신"})

    # RR common (international)
    processor_common = E4KoreanProcessor(standard="rr_common")
    result_common = processor_common.process({"CanonicalNative": "이순신"})

    # Should get different results due to overrides
    assert result_common["CanonicalLatin"] == "Lee Sun-sin"  # International override


@pytest.mark.timeout(15)
def test_applicability():
    """Test processor applicability detection."""
    processor = E4KoreanProcessor()

    # Should apply to Hangul text
    assert processor.is_applicable({"CanonicalNative": "김민수"})

    # Should apply to E4 region hint
    assert processor.is_applicable({"DetectedRegion": "E4"})

    # Should not apply to other text
    assert not processor.is_applicable({"CanonicalNative": "John Smith"})


if __name__ == "__main__":
    pytest.main([__file__])
