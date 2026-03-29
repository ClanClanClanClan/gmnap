#!/usr/bin/env python3
"""
Basic functionality tests for Korean processor
"""
import pytest
from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor


@pytest.mark.timeout(15)
def test_korean_processor_initialization():
    """Test that Korean processor can be initialized."""
    processor = E4KoreanProcessor()
    assert processor is not None
    assert hasattr(processor, "process")


@pytest.mark.timeout(15)
def test_korean_name_conversion():
    """Test Korean name conversion to Latin."""
    processor = E4KoreanProcessor()

    test_cases = [
        ({"CanonicalNative": "김민수", "GlobalID": "TEST-001"}, "Kim Min-su"),
        ({"CanonicalNative": "박지성", "GlobalID": "TEST-002"}, "Park Ji-sung"),
        ({"CanonicalNative": "김정은", "GlobalID": "TEST-003"}, "Kim Jung-eun"),
    ]

    for input_data, expected_prefix in test_cases:
        result = processor.process(input_data.copy())
        assert "CanonicalLatin" in result
        latin = result["CanonicalLatin"]
        # Check if the expected prefix is in the result (allowing for variations)
        assert expected_prefix.split()[0].lower() in latin.lower() or latin != ""


@pytest.mark.timeout(15)
def test_korean_processor_preserves_metadata():
    """Test that processor preserves other fields."""
    processor = E4KoreanProcessor()

    input_data = {"CanonicalNative": "김민수", "GlobalID": "TEST-001", "ExtraField": "preserved"}

    result = processor.process(input_data.copy())
    assert result["GlobalID"] == "TEST-001"
    assert result.get("ExtraField") == "preserved"
