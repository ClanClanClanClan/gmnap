"""Unit tests for GDPR compliance module."""

import pytest
from src.core.gdpr import (
    mark_gdpr_fields,
    apply_birth_year_privacy,
    scrub_sources,
    apply_drop_personal,
    gdpr_pipeline,
    PERSONAL_DATA_FIELDS,
    SCRUBBER_SOURCES,
    MIN_COHORT_SIZE,
)


class TestMarkGDPRFields:
    def test_entry_with_personal_data_gets_flagged(self):
        entry = {"CanonicalLatin": "Euler, Leonhard", "BirthYear": 1707}
        mark_gdpr_fields(entry)
        assert entry["GDPR_DATA"] is True

    def test_entry_without_personal_data_not_flagged(self):
        entry = {"CanonicalLatin": "Euler, Leonhard", "GlobalID": "ABC"}
        mark_gdpr_fields(entry)
        assert entry["GDPR_DATA"] is False

    def test_all_personal_fields_trigger_flag(self):
        for field in PERSONAL_DATA_FIELDS:
            entry = {field: "test_value"}
            mark_gdpr_fields(entry)
            assert entry["GDPR_DATA"] is True, f"Field {field} should trigger GDPR_DATA"


class TestBirthYearPrivacy:
    def test_small_cohort_gets_masked(self):
        batch = [
            {"CanonicalLatin": f"Person{i}", "BirthYear": 1985, "DetectedRegion": "A1"}
            for i in range(3)  # cohort < 5
        ]
        result = apply_birth_year_privacy(batch)
        for e in result:
            assert e["BirthYear"] == "1980s"
            assert e["BirthYear_Original"] == 1985
            assert e["BirthYear_Privacy"] == "decade_masked"

    def test_large_cohort_keeps_exact_year(self):
        batch = [
            {"CanonicalLatin": f"Person{i}", "BirthYear": 1990, "DetectedRegion": "A1"}
            for i in range(6)  # cohort >= 5
        ]
        result = apply_birth_year_privacy(batch)
        for e in result:
            assert e["BirthYear"] == 1990

    def test_missing_birth_year_untouched(self):
        batch = [{"CanonicalLatin": "Test", "DetectedRegion": "A1"}]
        result = apply_birth_year_privacy(batch)
        assert "BirthYear" not in result[0]


class TestScrubSources:
    def test_google_scholar_scrubbed(self):
        entry = {
            "_sources": ["OpenAlex", "GoogleScholar"],
            "AuthorityIDs": {"GoogleScholar": "gs:123", "OpenAlex": "oa:456"},
        }
        scrub_sources(entry)
        assert "GoogleScholar" not in entry["_sources"]
        assert "GoogleScholar" not in entry["AuthorityIDs"]
        assert "OpenAlex" in entry["AuthorityIDs"]

    def test_no_scrubber_sources_unchanged(self):
        entry = {"_sources": ["OpenAlex", "Crossref"], "AuthorityIDs": {"OpenAlex": "x"}}
        scrub_sources(entry)
        assert entry["_sources"] == ["OpenAlex", "Crossref"]


class TestShadowNode:
    def test_drop_personal_false_returns_unchanged(self):
        batch = [{"CanonicalLatin": "Test", "BirthYear": 1990}]
        result = apply_drop_personal(batch, drop_personal=False)
        assert result[0]["BirthYear"] == 1990

    def test_drop_personal_creates_shadow_node(self):
        batch = [
            {
                "GlobalID": "TESTID",
                "CanonicalLatin": "Euler, Leonhard",
                "BirthYear": 1707,
                "DetectedRegion": "A2",
                "Advisors": ["ADV1"],
                "OrderKey": "EULER, LEONHARD",
            }
        ]
        result = apply_drop_personal(batch, drop_personal=True)
        shadow = result[0]
        assert shadow["ShadowNode"] is True
        assert shadow["GlobalID"] == "TESTID"
        assert shadow["DetectedRegion"] == "A2"
        assert shadow["Advisors"] == ["ADV1"]
        assert shadow["OrderKey"] == "EULER, LEONHARD"
        assert "ShadowHash" in shadow
        assert len(shadow["ShadowHash"]) == 16
        # Personal data stripped
        assert "CanonicalLatin" not in shadow
        assert "BirthYear" not in shadow


class TestGDPRPipeline:
    def test_full_pipeline(self):
        batch = [
            {
                "CanonicalLatin": f"Person{i}",
                "BirthYear": 1985,
                "DetectedRegion": "A1",
                "_sources": ["OpenAlex"],
            }
            for i in range(3)
        ]
        result = gdpr_pipeline(batch, drop_personal=False)
        assert len(result) == 3
        for e in result:
            assert "GDPR_DATA" in e
            assert e["BirthYear"] == "1980s"  # cohort < 5

    def test_full_pipeline_with_drop_personal(self):
        batch = [
            {
                "CanonicalLatin": "Test",
                "BirthYear": 1990,
                "GlobalID": "XYZ",
                "DetectedRegion": "A1",
                "_sources": [],
            }
        ]
        result = gdpr_pipeline(batch, drop_personal=True)
        assert result[0]["ShadowNode"] is True
        assert "CanonicalLatin" not in result[0]
