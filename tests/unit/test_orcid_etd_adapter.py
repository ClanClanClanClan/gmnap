"""Unit tests for ORCID ETD authority adapter."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")


def _make_adapter():
    from src.authority.orcid_etd_adapter import ORCIDETDAdapter
    return ORCIDETDAdapter()


class TestORCIDETDAdapter:
    def test_instantiation(self):
        assert _make_adapter().name == "ORCID_ETD"

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
            "expanded-result": [{
                "orcid-id": "0000-0001-2345-6789",
                "institution-name": ["MIT", "Stanford"],
            }]
        }
        adapter.ctx.http = AsyncMock(get=AsyncMock(return_value=mock_r))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is True
        assert result["ORCID"] == "0000-0001-2345-6789"
        assert result["Institution"] == "MIT"
        assert result["_InstitutionAll"] == ["MIT", "Stanford"]
