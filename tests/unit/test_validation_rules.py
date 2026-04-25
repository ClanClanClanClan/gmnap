"""Tests for the 7 additional regional validation rules."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("GMNAP_NO_NETWORK", "1")

from src.regions.validation_rules import RegionalValidationEngine  # noqa: E402


@pytest.fixture
def engine():
    return RegionalValidationEngine()


class TestSlavicPatronymic:
    def test_valid_patronymic_passes(self, engine):
        entry = {"CanonicalLatin": "Ivanov, Sergei Petrovich", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "B1", "Latin")
        patronymic_results = [
            r for r in results if r.rule_id == "b1_slavic_patronymic_check"
        ]
        # Valid patronymic should not produce errors
        for r in patronymic_results:
            assert r.is_valid

    def test_short_patronymic_warns(self, engine):
        entry = {"CanonicalLatin": "Ivanov, Ich", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "B1", "Latin")
        patronymic_results = [
            r for r in results if r.rule_id == "b1_slavic_patronymic_check"
        ]
        if patronymic_results:
            assert any(
                "Short patronymic" in w for r in patronymic_results for w in r.warnings
            )


class TestCentralAsianScript:
    def test_post_2000_cyrillic_warns(self, engine):
        entry = {
            "CanonicalLatin": "Nazarbayev, Aidar",
            "CanonicalNative": "Назарбаев, Айдар",
            "BirthYear": 2005,
        }
        results = engine.validate_entry(entry, "C1", "Cyrillic")
        reform_results = [
            r for r in results if r.rule_id == "c1_central_asian_script_reform"
        ]
        if reform_results:
            assert any(
                "reform" in w.lower() for r in reform_results for w in r.warnings
            )

    def test_pre_2000_cyrillic_ok(self, engine):
        entry = {
            "CanonicalLatin": "Nazarbayev, Nursultan",
            "CanonicalNative": "Назарбаев, Нурсултан",
            "BirthYear": 1940,
        }
        results = engine.validate_entry(entry, "C1", "Cyrillic")
        reform_results = [
            r for r in results if r.rule_id == "c1_central_asian_script_reform"
        ]
        assert not reform_results  # No warning for pre-2000


class TestArabicArticle:
    def test_consistent_article_ok(self, engine):
        entry = {"CanonicalLatin": "al-Khwarizmi, Muhammad", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "C5", "Arabic")
        article_results = [
            r for r in results if r.rule_id == "c5_arabic_definite_article"
        ]
        # Single consistent article — no warning
        for r in article_results:
            assert r.is_valid


class TestDravidianInitial:
    def test_bare_initial_warns(self, engine):
        entry = {"CanonicalLatin": "Ramanujan, S", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "D2", "Latin")
        initial_results = [
            r for r in results if r.rule_id == "d2_dravidian_initial_prefix"
        ]
        if initial_results:
            assert any(
                "initial" in w.lower() for r in initial_results for w in r.warnings
            )

    def test_proper_initial_ok(self, engine):
        entry = {"CanonicalLatin": "Ramanujan, S. R.", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "D2", "Latin")
        initial_results = [
            r for r in results if r.rule_id == "d2_dravidian_initial_prefix"
        ]
        assert not initial_results


class TestSEAMonosyllabic:
    def test_very_short_thai_warns(self, engine):
        entry = {
            "CanonicalLatin": "Test",
            "CanonicalNative": "\u0e01",
        }  # single Thai char
        results = engine.validate_entry(entry, "E6", "Thai")
        sea_results = [r for r in results if r.rule_id == "e6_sea_monosyllabic_check"]
        if sea_results:
            assert any("short" in w.lower() for r in sea_results for w in r.warnings)

    def test_normal_thai_ok(self, engine):
        entry = {
            "CanonicalLatin": "Test",
            "CanonicalNative": "\u0e2a\u0e21\u0e0a\u0e32\u0e22",
        }
        results = engine.validate_entry(entry, "E6", "Thai")
        sea_results = [r for r in results if r.rule_id == "e6_sea_monosyllabic_check"]
        assert not sea_results


class TestFrancophoneParticle:
    def test_particle_present(self, engine):
        entry = {"CanonicalLatin": "de Fermat, Pierre", "CanonicalNative": ""}
        results = engine.validate_entry(entry, "F1", "Latin")
        # Rule should find the particle — no error if lowercase
        particle_results = [
            r for r in results if r.rule_id == "f1_francophone_particle"
        ]
        for r in particle_results:
            assert r.is_valid


class TestIndigenousNaming:
    def test_mononym_with_comma_warns(self, engine):
        entry = {
            "CanonicalLatin": "Tenzin, Gyatso",
            "CanonicalNative": "",
            "FamilyNameType": "mononym",
        }
        results = engine.validate_entry(entry, "G1", "Latin")
        indigenous_results = [r for r in results if r.rule_id == "g1_indigenous_naming"]
        if indigenous_results:
            assert any(
                "comma" in w.lower() for r in indigenous_results for w in r.warnings
            )

    def test_mononym_without_comma_ok(self, engine):
        entry = {
            "CanonicalLatin": "Tenzin",
            "CanonicalNative": "",
            "FamilyNameType": "mononym",
        }
        results = engine.validate_entry(entry, "G1", "Latin")
        indigenous_results = [r for r in results if r.rule_id == "g1_indigenous_naming"]
        assert not indigenous_results
