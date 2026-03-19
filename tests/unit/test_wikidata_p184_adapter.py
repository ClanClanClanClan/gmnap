"""Unit tests for Wikidata P184 authority adapter."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")


def _make_adapter():
    from src.authority.wikidata_p184_adapter import WikidataP184Adapter
    return WikidataP184Adapter()


class TestWikidataP184Adapter:
    def test_instantiation(self):
        assert _make_adapter().name == "Wikidata_P184"

    def test_offline_returns_no_hit(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is False

    def test_empty_name(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": ""}))
        assert result["_source"]["hit"] is False

    def test_online_with_sparql_result(self, monkeypatch):
        monkeypatch.setenv("OFFLINE", "0")
        adapter = _make_adapter()
        mock_r = MagicMock(status_code=200)
        mock_r.json.return_value = {
            "results": {"bindings": [{
                "advisor": {"value": "Q1234"},
                "advisorLabel": {"value": "Johann Bernoulli"},
                "student": {"value": "Q5678"},
                "studentLabel": {"value": "Joseph-Louis Lagrange"},
                "orcid": {"value": "0000-0001-2345-6789"},
                "birth": {"value": "1707-04-15T00:00:00Z"},
                "death": {"value": "1783-09-18T00:00:00Z"},
            }]}
        }
        adapter.ctx.http = AsyncMock(get=AsyncMock(return_value=mock_r))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is True
        assert "Johann Bernoulli" in result["AdvisorNames"]
        assert "Joseph-Louis Lagrange" in result["StudentNames"]
        assert result["BirthYear"] == 1707
        assert result["DeathYear"] == 1783
