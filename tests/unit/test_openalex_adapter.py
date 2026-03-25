"""Unit tests for OpenAlex authority adapter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")


def _make_adapter():
    from src.authority.openalex_adapter import OpenAlexAdapter

    return OpenAlexAdapter()


class TestOpenAlexAdapter:
    def test_instantiation(self):
        adapter = _make_adapter()
        assert adapter.name == "OpenAlex"

    def test_offline_returns_no_hit(self):
        adapter = _make_adapter()
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is False

    def test_empty_name_returns_no_hit(self):
        adapter = _make_adapter()
        result = asyncio.run(adapter.enrich({"CanonicalLatin": ""}))
        assert result["_source"]["hit"] is False

    def test_missing_name_returns_no_hit(self):
        adapter = _make_adapter()
        result = asyncio.run(adapter.enrich({}))
        assert result["_source"]["hit"] is False

    def test_online_with_mock_response(self, monkeypatch):
        monkeypatch.delenv("GMNAP_NO_NETWORK", raising=False)
        adapter = _make_adapter()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/A123",
                    "orcid": "https://orcid.org/0000-0001-2345-6789",
                    "display_name": "Leonhard Euler",
                    "works_count": 42,
                    "last_known_institutions": [
                        {"display_name": "ETH Zurich", "country_code": "CH"}
                    ],
                    "summary_stats": {"h_index": 15},
                }
            ]
        }
        adapter.ctx.http = AsyncMock()
        adapter.ctx.http.get = AsyncMock(return_value=mock_response)
        adapter.ctx.cache = AsyncMock()
        adapter.ctx.cache.get_json = AsyncMock(return_value=None)
        adapter.ctx.cache.set_json = AsyncMock()
        adapter.ctx.limiter = AsyncMock()
        adapter.ctx.limiter.acquire = AsyncMock()

        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is True
        assert result["OpenAlexID"] == "A123"
        assert result["ORCID"] == "0000-0001-2345-6789"
        assert result["Institution"] == "ETH Zurich"
        assert result["InstitutionCountry"] == "CH"

    def test_online_error_handled(self, monkeypatch):
        monkeypatch.delenv("GMNAP_NO_NETWORK", raising=False)
        adapter = _make_adapter()
        adapter.ctx.http = AsyncMock()
        adapter.ctx.http.get = AsyncMock(side_effect=Exception("Network error"))
        adapter.ctx.cache = AsyncMock()
        adapter.ctx.cache.get_json = AsyncMock(return_value=None)
        adapter.ctx.cache.set_json = AsyncMock()
        adapter.ctx.limiter = AsyncMock()
        adapter.ctx.limiter.acquire = AsyncMock()

        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Test, Name"}))
        assert "_source" in result
        assert result.get("_source", {}).get("hit") is not True
