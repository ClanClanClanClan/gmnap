"""Comprehensive unit tests for the GDPR compliance module.

Covers field marking, birth-year privacy masking (small vs large cohorts),
source scrubbing, ShadowNode conversion, and the end-to-end gdpr_pipeline.
"""

import pytest

from src.core.gdpr import (
    MIN_COHORT_SIZE,
    PERSONAL_DATA_FIELDS,
    apply_birth_year_privacy,
    apply_drop_personal,
    gdpr_pipeline,
    mark_gdpr_fields,
    scrub_sources,
)

# ---------------------------------------------------------------------------
# mark_gdpr_fields
# ---------------------------------------------------------------------------


class TestMarkGDPRFields:
    def test_mark_gdpr_fields_with_birth_year(self):
        """Entry containing BirthYear should be marked GDPR_DATA=True."""
        entry = {"CanonicalLatin": "Ramanujan, Srinivasa", "BirthYear": 1887}
        mark_gdpr_fields(entry)
        assert entry["GDPR_DATA"] is True

    def test_mark_gdpr_fields_without_personal(self):
        """Entry with only structural fields should be marked False."""
        entry = {"CanonicalLatin": "Hilbert, David", "GlobalID": "mgp:hilbert"}
        mark_gdpr_fields(entry)
        assert entry["GDPR_DATA"] is False

    @pytest.mark.parametrize("field", sorted(PERSONAL_DATA_FIELDS))
    def test_each_personal_field_triggers_flag(self, field):
        """Every field in PERSONAL_DATA_FIELDS should trigger the flag."""
        entry = {field: "some_value"}
        mark_gdpr_fields(entry)
        assert entry["GDPR_DATA"] is True, f"{field} should trigger GDPR_DATA"


# ---------------------------------------------------------------------------
# apply_birth_year_privacy
# ---------------------------------------------------------------------------


class TestBirthYearPrivacy:
    def test_small_cohort_is_masked(self):
        """Cohort of 3 (< MIN_COHORT_SIZE=5) should be decade-masked."""
        batch = [
            {
                "CanonicalLatin": f"Person{i}",
                "BirthYear": 1972,
                "DetectedRegion": "B1",
            }
            for i in range(3)
        ]
        result = apply_birth_year_privacy(batch)
        for e in result:
            assert e["BirthYear"] == "1970s"
            assert e["BirthYear_Original"] == 1972
            assert e["BirthYear_Privacy"] == "decade_masked"

    def test_large_cohort_is_preserved(self):
        """Cohort of 6 (>= MIN_COHORT_SIZE) should keep exact year."""
        batch = [
            {
                "CanonicalLatin": f"Person{i}",
                "BirthYear": 1995,
                "DetectedRegion": "A1",
            }
            for i in range(6)
        ]
        result = apply_birth_year_privacy(batch)
        for e in result:
            assert e["BirthYear"] == 1995
            assert "BirthYear_Privacy" not in e

    def test_exact_threshold_preserves(self):
        """Cohort of exactly MIN_COHORT_SIZE should NOT be masked."""
        batch = [
            {
                "CanonicalLatin": f"Person{i}",
                "BirthYear": 2001,
                "DetectedRegion": "C3",
            }
            for i in range(MIN_COHORT_SIZE)
        ]
        result = apply_birth_year_privacy(batch)
        for e in result:
            assert e["BirthYear"] == 2001

    def test_mixed_cohorts(self):
        """Different regions should have independent cohort counts."""
        small = [
            {"CanonicalLatin": f"S{i}", "BirthYear": 1980, "DetectedRegion": "A1"}
            for i in range(2)
        ]
        large = [
            {"CanonicalLatin": f"L{i}", "BirthYear": 1980, "DetectedRegion": "B2"}
            for i in range(6)
        ]
        result = apply_birth_year_privacy(small + large)
        # A1 cohort (size 2) should be masked
        for e in result[:2]:
            assert e["BirthYear"] == "1980s"
        # B2 cohort (size 6) should be preserved
        for e in result[2:]:
            assert e["BirthYear"] == 1980

    def test_no_birth_year_untouched(self):
        """Entries without BirthYear should pass through unchanged."""
        batch = [{"CanonicalLatin": "Test", "DetectedRegion": "A1"}]
        result = apply_birth_year_privacy(batch)
        assert "BirthYear" not in result[0]
        assert "BirthYear_Privacy" not in result[0]


# ---------------------------------------------------------------------------
# scrub_sources
# ---------------------------------------------------------------------------


class TestScrubSources:
    def test_scrub_google_scholar(self):
        """GoogleScholar should be removed from _sources and AuthorityIDs."""
        entry = {
            "GlobalID": "test:1",
            "_sources": ["OpenAlex", "GoogleScholar"],
            "AuthorityIDs": {
                "GoogleScholar": "gs:abc",
                "OpenAlex": "oa:123",
            },
        }
        scrub_sources(entry)
        assert "GoogleScholar" not in entry["_sources"]
        assert "GoogleScholar" not in entry["AuthorityIDs"]
        # Other sources remain
        assert "OpenAlex" in entry["_sources"]
        assert "OpenAlex" in entry["AuthorityIDs"]

    def test_scrub_proquest(self):
        """ProQuest should also be scrubbed."""
        entry = {
            "_sources": ["ProQuest", "Crossref"],
            "AuthorityIDs": {"ProQuest": "pq:999"},
        }
        scrub_sources(entry)
        assert "ProQuest" not in entry["_sources"]

    def test_scrub_cnki(self):
        """CNKI should also be scrubbed."""
        entry = {
            "_sources": ["CNKI"],
            "AuthorityIDs": {"CNKI": "cnki:42"},
        }
        scrub_sources(entry)
        assert "CNKI" not in entry["_sources"]

    def test_no_scrubber_sources_is_noop(self):
        """Entry with only clean sources should be unchanged."""
        entry = {
            "_sources": ["OpenAlex", "Crossref"],
            "AuthorityIDs": {"OpenAlex": "oa:1"},
        }
        scrub_sources(entry)
        assert entry["_sources"] == ["OpenAlex", "Crossref"]


# ---------------------------------------------------------------------------
# ShadowNode conversion (apply_drop_personal)
# ---------------------------------------------------------------------------


class TestShadowNodeConversion:
    def _make_entry(self, **overrides):
        base = {
            "GlobalID": "mgp:test-123",
            "CanonicalLatin": "Noether, Emmy",
            "BirthYear": 1882,
            "DetectedRegion": "A2",
            "Advisors": ["mgp:gordan"],
            "Students": ["mgp:vanderwaerden"],
            "OrderKey": "NOETHER, EMMY",
        }
        base.update(overrides)
        return base

    def test_shadow_node_conversion(self):
        """ShadowNode should strip personal data and add hash."""
        entry = self._make_entry()
        result = apply_drop_personal([entry], drop_personal=True)
        shadow = result[0]
        assert shadow["ShadowNode"] is True
        assert "ShadowHash" in shadow
        assert len(shadow["ShadowHash"]) == 16
        # Personal data removed
        assert "CanonicalLatin" not in shadow
        assert "BirthYear" not in shadow

    def test_shadow_node_preserves_global_id(self):
        """GlobalID must survive conversion to ShadowNode."""
        entry = self._make_entry()
        result = apply_drop_personal([entry], drop_personal=True)
        assert result[0]["GlobalID"] == "mgp:test-123"

    def test_shadow_node_preserves_structural(self):
        """Advisors, Students, OrderKey should survive."""
        entry = self._make_entry()
        result = apply_drop_personal([entry], drop_personal=True)
        shadow = result[0]
        assert shadow["Advisors"] == ["mgp:gordan"]
        assert shadow["Students"] == ["mgp:vanderwaerden"]
        assert shadow["OrderKey"] == "NOETHER, EMMY"

    def test_drop_personal_false_is_noop(self):
        """When drop_personal=False, batch should be returned unchanged."""
        entry = self._make_entry()
        result = apply_drop_personal([entry], drop_personal=False)
        assert result[0]["CanonicalLatin"] == "Noether, Emmy"
        assert result[0]["BirthYear"] == 1882

    def test_shadow_hash_is_deterministic(self):
        """Same CanonicalLatin should produce the same ShadowHash."""
        e1 = self._make_entry(GlobalID="a")
        e2 = self._make_entry(GlobalID="b")
        r1 = apply_drop_personal([e1], drop_personal=True)
        r2 = apply_drop_personal([e2], drop_personal=True)
        assert r1[0]["ShadowHash"] == r2[0]["ShadowHash"]


# ---------------------------------------------------------------------------
# gdpr_pipeline (end-to-end)
# ---------------------------------------------------------------------------


class TestGDPRPipelineEndToEnd:
    def test_gdpr_pipeline_end_to_end(self):
        """Full pipeline: mark, scrub, mask birth years, no drop."""
        batch = [
            {
                "CanonicalLatin": f"Mathematician{i}",
                "BirthYear": 1965,
                "DetectedRegion": "D1",
                "GlobalID": f"mgp:m{i}",
                "_sources": ["OpenAlex", "GoogleScholar"],
                "AuthorityIDs": {
                    "GoogleScholar": f"gs:{i}",
                    "OpenAlex": f"oa:{i}",
                },
            }
            for i in range(3)
        ]
        result = gdpr_pipeline(batch, drop_personal=False)
        assert len(result) == 3
        for e in result:
            # GDPR marking done
            assert e["GDPR_DATA"] is True
            # GoogleScholar scrubbed
            assert "GoogleScholar" not in e.get("_sources", [])
            assert "GoogleScholar" not in e.get("AuthorityIDs", {})
            # Birth year masked (cohort=3 < 5)
            assert e["BirthYear"] == "1960s"

    def test_gdpr_pipeline_with_drop_personal(self):
        """Pipeline with drop_personal=True should produce ShadowNodes."""
        batch = [
            {
                "CanonicalLatin": "Grothendieck, Alexander",
                "BirthYear": 1928,
                "DetectedRegion": "A2",
                "GlobalID": "mgp:grothendieck",
                "_sources": ["OpenAlex"],
            }
        ]
        result = gdpr_pipeline(batch, drop_personal=True)
        assert len(result) == 1
        assert result[0]["ShadowNode"] is True
        assert result[0]["GlobalID"] == "mgp:grothendieck"
        assert "CanonicalLatin" not in result[0]

    def test_gdpr_pipeline_preserves_clean_sources(self):
        """Non-scrubber sources should survive the full pipeline."""
        batch = [
            {
                "CanonicalLatin": "Tao, Terence",
                "DetectedRegion": "E3",
                "GlobalID": "mgp:tao",
                "_sources": ["OpenAlex", "Crossref"],
            }
        ]
        result = gdpr_pipeline(batch, drop_personal=False)
        assert "OpenAlex" in result[0]["_sources"]
        assert "Crossref" in result[0]["_sources"]
