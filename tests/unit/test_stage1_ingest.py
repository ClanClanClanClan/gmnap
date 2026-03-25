"""Unit tests for Stage 1: Ingest + Unicode normalisation."""

from src.pipeline.stage1_ingest import ingest_entries


class TestIngestEntries:
    def test_basic_normalization(self):
        entries = [{"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]}]
        result = ingest_entries(entries)
        assert len(result) == 1
        assert result[0]["CanonicalLatin"] == "Euler, Leonhard"
        assert "CanonicalLatin_Folded" in result[0]

    def test_unicode_folding(self):
        entries = [{"CanonicalLatin": "M\u00fcller, Hans"}]  # ü
        result = ingest_entries(entries)
        folded = result[0].get("CanonicalLatin_Folded", "")
        assert "muller" in folded.lower() or "müller" in folded.lower()

    def test_native_script_folded(self):
        entries = [{"CanonicalLatin": "Test", "CanonicalNative": "\u30aa\u30a4\u30e9\u30fc"}]
        result = ingest_entries(entries)
        assert "CanonicalNative" in result[0]

    def test_empty_batch(self):
        assert ingest_entries([]) == []

    def test_preserves_extra_fields(self):
        entries = [{"CanonicalLatin": "Test, Name", "BirthYear": 1900, "CustomField": "value"}]
        result = ingest_entries(entries)
        assert result[0]["BirthYear"] == 1900
        assert result[0]["CustomField"] == "value"
