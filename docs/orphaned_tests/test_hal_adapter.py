"""Unit tests for HAL authority adapter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")


def _make_adapter():
    from src.authority.hal_adapter import HALAdapter

    return HALAdapter()


class TestHALAdapter:
    def test_instantiation(self):
        assert _make_adapter().name == "HAL"

    def test_offline_returns_no_hit(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": "Bourbaki, Nicolas"}))
        assert result["_source"]["hit"] is False

    def test_online_with_mock(self, monkeypatch):
        monkeypatch.setenv("OFFLINE", "0")
        adapter = _make_adapter()
        mock_r = MagicMock(status_code=200)
        mock_r.json.return_value = {
            "response": {
                "docs": [
                    {
                        "authLabStructName_fs": [
                            "CNRS_JoinKey_Institut de Mathematiques",
                            "ENS_JoinKey_Ecole Normale",
                        ],
                    }
                ]
            }
        }
        adapter.ctx.http = AsyncMock(get=AsyncMock(return_value=mock_r))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Bourbaki, Nicolas"}))
        assert isinstance(result.get("Institution"), str)
        assert isinstance(result.get("_InstitutionAll"), list)
