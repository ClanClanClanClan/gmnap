"""Unit tests for zbMATH Open authority adapter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")


def _make_adapter():
    from src.authority.zbmath_open_adapter import ZbMathOpenAdapter

    return ZbMathOpenAdapter()


class TestZbMathOpenAdapter:
    def test_instantiation(self):
        assert _make_adapter().name == "zbMATH"

    def test_offline_returns_no_hit(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result["_source"]["hit"] is False

    def test_online_with_mock(self, monkeypatch):
        monkeypatch.setenv("OFFLINE", "0")
        adapter = _make_adapter()
        mock_r = MagicMock(status_code=200)
        mock_r.json.return_value = {"hits": [{"id": "euler.leonhard"}]}
        adapter.ctx.http = AsyncMock(get=AsyncMock(return_value=mock_r))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Euler, Leonhard"}))
        assert result.get("Publications") == ["zb:euler.leonhard"]
