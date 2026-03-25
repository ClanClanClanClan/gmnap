"""Unit tests for Stage 7: TagShortForms."""

from src.pipeline.stage7_tag_short_forms import tag_short_forms


class TestTagShortForms:
    def test_basic_tagging(self):
        batch = [{"CanonicalLatin": "Euler, Leonhard"}]
        result, clusters = tag_short_forms(batch)
        assert len(result) == 1
        assert "ShortFormClusters" in result[0]

    def test_initials_detected(self):
        batch = [{"CanonicalLatin": "Euler, L."}]
        result, _ = tag_short_forms(batch)
        assert "initials_only" in result[0].get("ShortFormTags", [])

    def test_abbreviation_detected(self):
        batch = [{"CanonicalLatin": "Smith, J. P. Jr"}]
        result, _ = tag_short_forms(batch)
        tags = result[0].get("ShortFormTags", [])
        assert "has_abbreviations" in tags

    def test_clusters_populated(self):
        batch = [
            {"CanonicalLatin": "Euler, Leonhard"},
            {"CanonicalLatin": "Euler, L."},
        ]
        result, clusters = tag_short_forms(batch)
        assert "Euler" in clusters
        assert clusters["Euler"] >= 2  # Both entries produce "Euler" short form

    def test_empty_batch(self):
        result, clusters = tag_short_forms([])
        assert result == []
        assert clusters == {}
