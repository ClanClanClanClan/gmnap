"""
Unit tests for the authority enrichment manager.

Tests tier registration, handler dispatch, offline mode,
caching, enrichment merging, and individual adapter implementations.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.authority.manager_tier01 import (
    TIER_HANDLERS,
    _cache_get,
    _cache_key,
    _cache_set,
    _fetch_crossref_thesis,
    _fetch_dimensions,
    _fetch_google_scholar,
    _fetch_mathscinet,
    _fetch_oai_university,
    _fetch_proquest,
    _fetch_wikidata_p184,
    _get_handlers_for_tiers,
    enrich_by_tiers,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tier Registry ────────────────────────────────────────────────────────


class TestTierRegistry:
    """Test tier handler registration."""

    def test_tier_0_has_4_sources(self):
        assert len(TIER_HANDLERS[0]) == 4
        names = [n for n, _ in TIER_HANDLERS[0]]
        assert "OpenAlex" in names
        assert "Crossref" in names
        assert "ORCID_ETD" in names
        assert "Crossref_Thesis" in names

    def test_tier_1_has_5_sources(self):
        assert len(TIER_HANDLERS[1]) == 5
        names = [n for n, _ in TIER_HANDLERS[1]]
        assert "Wikidata_P184" in names
        assert "GND" in names
        assert "zbMATH_Open" in names

    def test_tier_2_has_3_sources(self):
        assert len(TIER_HANDLERS[2]) == 3

    def test_tier_3_has_2_sources(self):
        assert len(TIER_HANDLERS[3]) == 2

    def test_total_14_sources(self):
        total = sum(len(v) for v in TIER_HANDLERS.values())
        assert total == 14


# ── Handler Selection ────────────────────────────────────────────────────


class TestHandlerSelection:
    """Test tier-based handler selection."""

    def test_get_tier_0(self):
        handlers = _get_handlers_for_tiers([0])
        assert len(handlers) == 4

    def test_get_tier_0_1(self):
        handlers = _get_handlers_for_tiers([0, 1])
        assert len(handlers) == 9

    def test_get_all_tiers(self):
        handlers = _get_handlers_for_tiers([0, 1, 2, 3])
        assert len(handlers) == 14

    def test_empty_tiers(self):
        handlers = _get_handlers_for_tiers([])
        assert len(handlers) == 0


# ── Cache ────────────────────────────────────────────────────────────────


class TestCache:
    """Test authority cache operations."""

    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                key = _cache_key("test", {"name": "Smith"})
                obj = {"hit": True, "source_id": "12345"}
                _cache_set(key, obj)
                result = _cache_get(key)
                assert result == obj

    def test_cache_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                key = _cache_key("nonexistent", {"name": "Nobody"})
                assert _cache_get(key) is None


# ── Enrichment ───────────────────────────────────────────────────────────


class TestEnrichment:
    """Test entry enrichment."""

    def test_offline_enrichment(self):
        entries = [{"CanonicalLatin": "Smith, John"}]
        with patch("src.authority.manager_tier01.OFFLINE", True):
            result = _run(enrich_by_tiers(entries, tiers=[0]))
        assert len(result) == 1
        assert "_sources" in result[0]

    def test_enrichment_preserves_entry_data(self):
        entries = [{"CanonicalLatin": "Smith, John", "BirthYear": 1975}]
        result = _run(enrich_by_tiers(entries, tiers=[0]))
        assert result[0]["CanonicalLatin"] == "Smith, John"
        assert result[0]["BirthYear"] == 1975

    def test_enrichment_adds_sources(self):
        entries = [{"CanonicalLatin": "Smith, John"}]
        result = _run(enrich_by_tiers(entries, tiers=[0]))
        assert "_sources" in result[0]
        assert isinstance(result[0]["_sources"], list)

    def test_empty_entries(self):
        result = _run(enrich_by_tiers([], tiers=[0]))
        assert result == []

    def test_default_tier_is_0(self):
        entries = [{"CanonicalLatin": "Test"}]
        result = _run(enrich_by_tiers(entries))
        assert len(result) == 1

    def test_wikidata_advisor_merge(self):
        entries = [{"CanonicalLatin": "Smith, John", "Advisors": ["Advisor One"]}]
        result = _run(enrich_by_tiers(entries, tiers=[0, 1]))
        assert "Advisor One" in result[0].get("Advisors", [])


# ── Individual Adapter Tests ─────────────────────────────────────────────


class TestWikidataP184:
    """Test Wikidata P184 adapter."""

    def test_offline_returns_no_hit(self):
        entry = {"CanonicalLatin": "Euler, Leonhard"}
        with patch("src.authority.manager_tier01.OFFLINE", True):
            result = _run(_fetch_wikidata_p184(entry))
        assert result["Wikidata_P184"]["hit"] is False

    def test_empty_name_returns_no_hit(self):
        entry = {"CanonicalLatin": ""}
        result = _run(_fetch_wikidata_p184(entry))
        assert result["Wikidata_P184"]["hit"] is False
        assert result["Wikidata_P184"]["reason"] == "no_name"

    def test_cached_result_returned(self):
        entry = {"CanonicalLatin": "Gauss, Carl Friedrich"}
        cached = {"Wikidata_P184": {"hit": True, "wikidata_id": "Q6722", "edges": []}}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                ck = _cache_key("wikidata_p184", {"name": "Gauss, Carl Friedrich"})
                _cache_set(ck, cached)
                result = _run(_fetch_wikidata_p184(entry))
        assert result == cached

    def test_successful_sparql_query(self):
        """Test with mocked Wikidata API response."""
        entry = {"CanonicalLatin": "Euler, Leonhard"}
        search_response = {"search": [{"id": "Q7604", "label": "Leonhard Euler"}]}
        sparql_response = {
            "results": {
                "bindings": [
                    {
                        "advisor": {
                            "value": "http://www.wikidata.org/entity/Q131tried"
                        },
                        "advisorLabel": {"value": "Johann Bernoulli"},
                    },
                ]
            }
        }

        class MockResponse:
            def __init__(self, data):
                self.status = 200
                self._data = data

            async def json(self):
                return self._data

        class MockContextManager:
            def __init__(self, data):
                self._resp = MockResponse(data)

            async def __aenter__(self):
                return self._resp

            async def __aexit__(self, *args):
                pass

        class MockSession:
            def get(self, url, **kwargs):
                if "wbsearchentities" in url:
                    return MockContextManager(search_response)
                return MockContextManager(sparql_response)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        # Project targets py38 — parenthesized `with` is py310+, so
        # use nested context managers instead.
        with patch("src.authority.manager_tier01.OFFLINE", False):
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                    with patch("aiohttp.ClientSession", return_value=MockSession()):
                        result = _run(_fetch_wikidata_p184(entry))

        assert result["Wikidata_P184"]["hit"] is True
        assert result["Wikidata_P184"]["wikidata_id"] == "Q7604"
        assert len(result["Wikidata_P184"]["edges"]) == 1
        assert result["Wikidata_P184"]["edges"][0]["target"] == "Johann Bernoulli"


class TestCrossrefThesis:
    """Test Crossref Thesis adapter."""

    def test_offline_returns_no_match(self):
        entry = {"CanonicalLatin": "Smith, John"}
        with patch("src.authority.manager_tier01.OFFLINE", True):
            result = _run(_fetch_crossref_thesis(entry))
        assert result["Crossref_Thesis"]["match"] is False
        assert result["Crossref_Thesis"]["works"] == 0

    def test_empty_name(self):
        entry = {"CanonicalLatin": ""}
        result = _run(_fetch_crossref_thesis(entry))
        assert result["Crossref_Thesis"]["match"] is False

    def test_cached_result(self):
        entry = {"CanonicalLatin": "Test, User"}
        cached = {
            "Crossref_Thesis": {
                "works": 1,
                "match": True,
                "source_id": "10.1234/thesis",
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                ck = _cache_key("crossref_thesis", {"name": "Test, User"})
                _cache_set(ck, cached)
                result = _run(_fetch_crossref_thesis(entry))
        assert result == cached


class TestOAIUniversity:
    """Test OAI University adapter."""

    def test_offline_returns_no_hit(self):
        entry = {"CanonicalLatin": "Smith, John"}
        with patch("src.authority.manager_tier01.OFFLINE", True):
            result = _run(_fetch_oai_university(entry))
        assert result["OAI_University"]["hit"] is False

    def test_empty_name(self):
        entry = {"CanonicalLatin": ""}
        result = _run(_fetch_oai_university(entry))
        assert result["OAI_University"]["hit"] is False
        assert result["OAI_University"]["reason"] == "no_name"


class TestMathSciNet:
    """Test MathSciNet adapter."""

    def test_offline_returns_no_hit(self):
        entry = {"CanonicalLatin": "Euler, Leonhard"}
        with patch("src.authority.manager_tier01.OFFLINE", True):
            result = _run(_fetch_mathscinet(entry))
        assert result["MathSciNet"]["hit"] is False

    def test_empty_name(self):
        entry = {"CanonicalLatin": ""}
        result = _run(_fetch_mathscinet(entry))
        assert result["MathSciNet"]["hit"] is False
        assert result["MathSciNet"]["reason"] == "no_name"

    def test_cached_result(self):
        entry = {"CanonicalLatin": "Gauss, Carl Friedrich"}
        cached = {"MathSciNet": {"hit": True, "source_id": "MR0001234"}}
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.authority.manager_tier01.CACHE_DIR", Path(tmpdir)):
                ck = _cache_key("mathscinet", {"name": "Gauss, Carl Friedrich"})
                _cache_set(ck, cached)
                result = _run(_fetch_mathscinet(entry))
        assert result == cached


class TestDimensions:
    """Test Dimensions adapter."""

    def test_no_api_key_returns_reason(self):
        entry = {"CanonicalLatin": "Smith, John"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DIMENSIONS_API_KEY", None)
            result = _run(_fetch_dimensions(entry))
        assert result["Dimensions"]["hit"] is False
        assert result["Dimensions"]["reason"] == "no_api_key"

    def test_empty_name(self):
        entry = {"CanonicalLatin": ""}
        result = _run(_fetch_dimensions(entry))
        assert result["Dimensions"]["hit"] is False
        assert result["Dimensions"]["reason"] == "no_name"

    def test_offline_returns_no_hit(self):
        entry = {"CanonicalLatin": "Smith, John"}
        # py38-compatible nested context (project pyproject pins py38).
        with patch("src.authority.manager_tier01.OFFLINE", True):
            with patch.dict(os.environ, {"DIMENSIONS_API_KEY": "test_key"}):
                result = _run(_fetch_dimensions(entry))
        assert result["Dimensions"]["hit"] is False


class TestDeferredAdapters:
    """Test ProQuest and GoogleScholar return proper defer reasons."""

    def test_proquest_deferred(self):
        entry = {"CanonicalLatin": "Smith, John"}
        result = _run(_fetch_proquest(entry))
        assert result["ProQuest"]["hit"] is False
        assert result["ProQuest"]["reason"] == "requires_institutional_access"

    def test_google_scholar_deferred(self):
        entry = {"CanonicalLatin": "Smith, John"}
        result = _run(_fetch_google_scholar(entry))
        assert result["GoogleScholar"]["hit"] is False
        assert result["GoogleScholar"]["reason"] == "tos_optin_required"
