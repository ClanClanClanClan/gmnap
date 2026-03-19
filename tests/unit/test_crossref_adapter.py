"""Unit tests for Crossref authority adapter."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")


def _make_adapter():
    from src.authority.crossref_adapter import CrossrefAdapter
    return CrossrefAdapter()


class TestCrossrefAdapter:
    def test_instantiation(self):
        assert _make_adapter().name == "Crossref"

    def test_offline_returns_no_hit(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is False

    def test_empty_name(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": ""}))
        assert result["_source"]["hit"] is False

    def test_online_with_mock(self, monkeypatch):
        monkeypatch.delenv("GMNAP_NO_NETWORK", raising=False)
        adapter = _make_adapter()
        mock_r = MagicMock(status_code=200)
        mock_r.json.return_value = {
            "message": {
                "total-results": 5,
                "items": [{"DOI": "10.1234/test", "author": [{"family": "Euler", "given": "L"}],
                           "subject": ["Mathematics"], "container-title": ["J. Math"]}],
            }
        }
        adapter.ctx.http = AsyncMock()
        adapter.ctx.http.get = AsyncMock(return_value=mock_r)
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is True
        assert result["PublicationCount"] == 5
        assert "10.1234/test" in result["DOIs"]

    def test_error_handled(self, monkeypatch):
        monkeypatch.delenv("GMNAP_NO_NETWORK", raising=False)
        adapter = _make_adapter()
        adapter.ctx.http = AsyncMock(get=AsyncMock(side_effect=Exception("fail")))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Test"}))
        assert result.get("_source", {}).get("hit") is not True
