"""Tests for region overlay map detection (V7 spec §2a).

Verifies sub-national overrides: CH-FR→A2, IN-SOUTH→D2, IN-WB→D3, etc.
"""

import pytest


@pytest.fixture(scope="module")
def region_manager():
    from src.regions.manager_optimized import RegionManager

    return RegionManager()


class TestRegionOverlayMap:
    """Test sub-national overlay detection from spec §2a."""

    def test_swiss_french_detected_as_a2(self, region_manager):
        """CH + French-speaking institution → A2 via CH-FR overlay."""
        entry = {
            "CanonicalLatin": "Dupont, Jean",
            "CountryCodes": ["CH"],
            "Institution": "Université de Genève",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "A2"

    def test_indian_south_detected_as_d2(self, region_manager):
        """IN + South Indian institution → D2 via IN-SOUTH overlay."""
        entry = {
            "CanonicalLatin": "Raman, Srinivasa",
            "CountryCodes": ["IN"],
            "Institution": "Chennai Mathematical Institute",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "D2"

    def test_indian_bengali_detected_as_d3(self, region_manager):
        """IN + West Bengal institution → D3 via IN-WB overlay."""
        entry = {
            "CanonicalLatin": "Bose, Satyendra Nath",
            "CountryCodes": ["IN"],
            "Institution": "Jadavpur University",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "D3"

    def test_srilanka_tamil_detected_as_d2(self, region_manager):
        """LK + Tamil region institution → D2 via LK-TA overlay."""
        entry = {
            "CanonicalLatin": "Selvanathan, Kannan",
            "CountryCodes": ["LK"],
            "Institution": "University of Jaffna",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "D2"

    def test_russian_caucasus_detected_as_c9(self, region_manager):
        """RU + North Caucasus institution → C9 via RU-NC overlay."""
        entry = {
            "CanonicalLatin": "Magomedov, Akhmed",
            "CountryCodes": ["RU"],
            "Institution": "Dagestan State University",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "C9"

    def test_us_no_overlay_applied(self, region_manager):
        """US entries should NOT trigger overlay — normal A1 detection."""
        entry = {
            "CanonicalLatin": "Smith, John",
            "CountryCodes": ["US"],
            "Institution": "MIT",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "A1"

    def test_indian_default_hindi_belt(self, region_manager):
        """IN without southern/bengali keyword → D1 (Hindi belt default)."""
        entry = {
            "CanonicalLatin": "Sharma, Priya",
            "CountryCodes": ["IN"],
            "Institution": "Indian Institute of Technology Delhi",
        }
        result = region_manager.detect_region(entry)
        assert result.region_code == "D1"
