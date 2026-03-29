"""
from typing import Any
Unit tests for A3 Nordic-Baltic regional processor.

Tests cover:
- Icelandic patronymic system
- Scandinavian noble particles
- Baltic gendered surname endings
- Nordic/Baltic diacritics
- Special sorting rules
"""

import pytest
from typing import Dict, Any

from src.regions.a_groups.a3_nordic_baltic import A3NordicBalticProcessor
from src.regions.base import RegionRuleError


class TestA3NordicBaltic:
    """Test suite for A3 Nordic-Baltic processor."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return A3NordicBalticProcessor()

    @pytest.fixture
    def sample_entry(self) -> Dict[str, Any]:
        """Create sample entry for testing."""
        return {
            "CanonicalLatin": "Eriksson, Lars",
            "CanonicalNative": "Eriksson, Lars",
            "GivenName": "Lars",
            "FamilyName": "Eriksson",
        }

    # Test Icelandic Patronymic System (Rule 8)

    @pytest.mark.timeout(15)
    def test_icelandic_patronymic_male(self, processor):
        """Test male Icelandic patronymic detection."""
        entry = {
            "CanonicalLatin": "Magnússon, Jón",
            "CanonicalNative": "Magnússon, Jón",
        }

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["is_patronymic"] == True
        assert entry["RegionalExtras"]["patronymic_root"] == "Magnús"
        assert entry["RegionalExtras"]["patronymic_type"] == "son"
        assert entry["FamilyNameType"] == "patronymic"

    @pytest.mark.timeout(15)
    def test_icelandic_patronymic_female(self, processor):
        """Test female Icelandic patronymic detection."""
        entry = {
            "CanonicalLatin": "Guðmundsdóttir, Helga",
            "CanonicalNative": "Guðmundsdóttir, Helga",
        }

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["is_patronymic"] == True
        assert entry["RegionalExtras"]["patronymic_root"] == "Guðmunds"
        assert entry["RegionalExtras"]["patronymic_type"] == "daughter"
        assert entry["FamilyNameType"] == "patronymic"

    @pytest.mark.timeout(15)
    def test_icelandic_no_comma_format(self, processor):
        """Test Icelandic name without comma (Given Patronymic)."""
        entry = {"CanonicalLatin": "Ólafur Sigurðsson"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["given_name"] == "Ólafur"
        assert entry["RegionalExtras"]["family_name"] == "Sigurðsson"
        assert entry["RegionalExtras"]["is_patronymic"] == True

    @pytest.mark.timeout(15)
    def test_patronymic_sorting(self, processor):
        """Test Icelandic patronymic sorting by given name."""
        entry1 = {"CanonicalLatin": "Magnússon, Ari", "RegionalExtras": {}}
        entry2 = {"CanonicalLatin": "Magnússon, Björn", "RegionalExtras": {}}

        processor.augment(entry1)
        processor.augment(entry2)

        # Icelandic names should sort by given name
        key1 = processor.order_key(entry1)
        key2 = processor.order_key(entry2)

        assert key1 < key2  # Ari before Björn

    # Test Scandinavian Noble Particles

    @pytest.mark.timeout(15)
    def test_scandinavian_particle_af(self, processor):
        """Test Swedish/Norwegian 'af' particle."""
        entry = {"CanonicalLatin": "af Klint, Hilma"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["particle"] == "af"
        assert entry["RegionalExtras"]["main_surname"] == "Klint"

        # Check particle-drop variant
        variants = [
            v["str"]
            for v in entry["Variants"]["Synthesised"]
            if v["type"] == "particle-drop"
        ]
        assert "Klint, Hilma" in variants

    @pytest.mark.timeout(15)
    def test_scandinavian_particle_von(self, processor):
        """Test German-influenced 'von' particle."""
        entry = {"CanonicalLatin": "von Linné, Carl"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["particle"] == "von"
        assert entry["RegionalExtras"]["main_surname"] == "Linné"

    @pytest.mark.timeout(15)
    def test_multiple_particles(self, processor):
        """Test multiple particle handling."""
        entry = {"CanonicalLatin": "von der Leyen, Ursula"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["particle"] == "von der"
        assert entry["RegionalExtras"]["main_surname"] == "Leyen"

    # Test Baltic Gendered Endings

    @pytest.mark.timeout(15)
    def test_lithuanian_male_surname(self, processor):
        """Test Lithuanian male surname ending -as."""
        entry = {"CanonicalLatin": "Kazlauskas, Jonas"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Male surnames don't have gender_inflected flag
        assert "gender_inflected" not in entry["RegionalExtras"]

    @pytest.mark.timeout(15)
    def test_lithuanian_female_married(self, processor):
        """Test Lithuanian married female surname -ienė."""
        entry = {"CanonicalLatin": "Kazlauskienė, Marija"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["gender_inflected"] == True
        assert entry["RegionalExtras"]["gender"] == "female"
        assert entry["RegionalExtras"]["male_form"] == "Kazlauskis"

    @pytest.mark.timeout(15)
    def test_lithuanian_female_unmarried(self, processor):
        """Test Lithuanian unmarried female surname -ytė."""
        entry = {"CanonicalLatin": "Kazlauskytė, Elena"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["gender_inflected"] == True
        assert entry["RegionalExtras"]["gender"] == "female"
        assert entry["RegionalExtras"]["male_form"] == "Kazlauskus"

    @pytest.mark.timeout(15)
    def test_latvian_gendered_surname(self, processor):
        """Test Latvian surname with gendered ending."""
        entry = {"CanonicalLatin": "Bērziņš, Jānis"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Latvian -iņš is not gendered
        assert "gender_inflected" not in entry["RegionalExtras"]

    # Test Nordic/Baltic Diacritics

    @pytest.mark.timeout(15)
    def test_swedish_diacritics(self, processor):
        """Test Swedish characters å, ä, ö."""
        entry = {"CanonicalLatin": "Sjöström, Åsa"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Check ASCII variant generation
        ascii_variants = [
            v["str"]
            for v in entry["Variants"]["Synthesised"]
            if v["type"] == "ascii-lossy"
        ]
        assert "Sjostrom, Asa" in ascii_variants

    @pytest.mark.timeout(15)
    def test_danish_norwegian_ae_oe(self, processor):
        """Test Danish/Norwegian æ, ø."""
        entry = {"CanonicalLatin": "Kjærgaard, Søren"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Check ASCII variant
        ascii_variants = [
            v["str"]
            for v in entry["Variants"]["Synthesised"]
            if v["type"] == "ascii-lossy"
        ]
        assert "Kjaergaard, Soren" in ascii_variants

    @pytest.mark.timeout(15)
    def test_icelandic_special_chars(self, processor):
        """Test Icelandic þ (thorn) and ð (eth)."""
        entry = {"CanonicalLatin": "Þórðarson, Björn"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Check ASCII variant
        ascii_variants = [
            v["str"]
            for v in entry["Variants"]["Synthesised"]
            if v["type"] == "ascii-lossy"
        ]
        assert "THordarson, Bjorn" in ascii_variants

    @pytest.mark.timeout(15)
    def test_baltic_special_chars(self, processor):
        """Test Baltic č, š, ž."""
        entry = {"CanonicalLatin": "Žukauskas, Česlovas"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        # Check ASCII variant
        ascii_variants = [
            v["str"]
            for v in entry["Variants"]["Synthesised"]
            if v["type"] == "ascii-lossy"
        ]
        assert "Zukauskas, Ceslovas" in ascii_variants

    # Test Special Sorting Rules

    @pytest.mark.timeout(15)
    def test_nordic_sorting_order(self, processor):
        """Test Nordic sorting where å, ä, ö come after z."""
        entries = [
            {"CanonicalLatin": "Zachrisson, Erik", "RegionalExtras": {}},
            {"CanonicalLatin": "Åberg, Anna", "RegionalExtras": {}},
            {"CanonicalLatin": "Ärlig, Per", "RegionalExtras": {}},
            {"CanonicalLatin": "Öberg, Maria", "RegionalExtras": {}},
        ]

        for entry in entries:
            processor.augment(entry)

        keys = [processor.order_key(e) for e in entries]
        sorted_keys = sorted(keys)

        # Z should come before Å, Ä, Ö
        assert sorted_keys[0] == keys[0]  # Zachrisson first
        assert sorted_keys[1] == keys[1]  # Åberg second
        assert sorted_keys[2] == keys[2]  # Ärlig third
        assert sorted_keys[3] == keys[3]  # Öberg last

    # Test Title Removal

    @pytest.mark.timeout(15)
    def test_title_removal(self, processor):
        """Test removal of Nordic/Baltic titles."""
        entry = {"CanonicalLatin": "Prof. Andersen, Hans Christian"}

        processor.clean(entry)

        assert entry["CanonicalLatin"] == "Andersen, Hans Christian"

    @pytest.mark.timeout(15)
    def test_baltic_title_removal(self, processor):
        """Test removal of Baltic-specific titles."""
        entry = {"CanonicalLatin": "Ponas Kazlauskas, Jonas"}

        processor.clean(entry)

        assert entry["CanonicalLatin"] == "Kazlauskas, Jonas"

    # Test Common Nordic Names

    @pytest.mark.timeout(15)
    def test_common_swedish_names(self, processor):
        """Test recognition of common Swedish names."""
        entry = {"CanonicalLatin": "Eriksson, Karl"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["given_name"] == "Karl"
        assert entry["RegionalExtras"]["family_name"] == "Eriksson"

    @pytest.mark.timeout(15)
    def test_common_finnish_names(self, processor):
        """Test recognition of common Finnish names."""
        entry = {"CanonicalLatin": "Virtanen, Matti"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["given_name"] == "Matti"
        assert entry["RegionalExtras"]["family_name"] == "Virtanen"

    # Test Validation Errors

    @pytest.mark.timeout(15)
    def test_invalid_characters(self, processor):
        """Test validation rejects invalid characters."""
        entry = {"CanonicalLatin": "Smith@gmail, John"}

        with pytest.raises(RegionRuleError, match="Invalid characters"):
            processor.validate(entry)

    @pytest.mark.timeout(15)
    def test_missing_canonical(self, processor):
        """Test validation requires CanonicalLatin."""
        entry = {}

        with pytest.raises(RegionRuleError, match="Missing CanonicalLatin"):
            processor.validate(entry)

    @pytest.mark.timeout(15)
    def test_patronymic_validation_error(self, processor):
        """Test patronymic validation catches mismatches."""
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionalExtras": {"is_patronymic": True, "family_name": "Smith"},
        }

        with pytest.raises(RegionRuleError, match="doesn't match pattern"):
            processor.validate(entry)

    @pytest.mark.timeout(15)
    def test_gender_mismatch_validation(self, processor):
        """Test validation catches gender ending mismatches."""
        entry = {
            "CanonicalLatin": "Kazlauskas, Marija",
            "RegionalExtras": {
                "gender_inflected": True,
                "gender": "female",
                "family_name": "Kazlauskas",
            },
        }

        with pytest.raises(RegionRuleError, match="Gender mismatch"):
            processor.validate(entry)

    # Test Edge Cases

    @pytest.mark.timeout(15)
    def test_empty_name(self, processor):
        """Test handling of empty names."""
        entry = {"CanonicalLatin": ""}

        processor.clean(entry)
        # Should not crash
        assert entry["CanonicalLatin"] == ""

    @pytest.mark.timeout(15)
    def test_hyphenated_names(self, processor):
        """Test handling of hyphenated Nordic names."""
        entry = {"CanonicalLatin": "Svensson-Berg, Anna-Liisa"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["family_name"] == "Svensson-Berg"
        assert entry["RegionalExtras"]["given_name"] == "Anna-Liisa"

    @pytest.mark.timeout(15)
    def test_multiple_given_names(self, processor):
        """Test handling of multiple given names."""
        entry = {"CanonicalLatin": "Andersson, Karl Johan Erik"}

        processor.clean(entry)
        processor.augment(entry)
        processor.validate(entry)

        assert entry["RegionalExtras"]["given_name"] == "Karl Johan Erik"
        assert entry["RegionalExtras"]["family_name"] == "Andersson"

    @pytest.mark.timeout(15)
    def test_particle_sorting_ignored(self, processor):
        """Test that particles are ignored in sorting."""
        entry1 = {"CanonicalLatin": "von Sydow, Max", "RegionalExtras": {}}
        entry2 = {"CanonicalLatin": "Svensson, Anders", "RegionalExtras": {}}

        processor.augment(entry1)
        processor.augment(entry2)

        key1 = processor.order_key(entry1)
        key2 = processor.order_key(entry2)

        # "Sydow" should sort after "Svensson" (particle ignored)
        assert key2 < key1
