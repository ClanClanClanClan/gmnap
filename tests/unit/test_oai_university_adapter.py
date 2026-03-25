"""Unit tests for OAI University (BASE) authority adapter."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")


def _make_adapter():
    from src.authority.oai_university_adapter import OAIUniversityAdapter

    return OAIUniversityAdapter()


class TestOAIUniversityAdapter:
    def test_instantiation(self):
        assert _make_adapter().name == "OAI_University"

    def test_offline_returns_no_hit(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": "Gauss, Carl"}))
        assert result["_source"]["hit"] is False

    def test_empty_name(self):
        result = asyncio.run(_make_adapter().enrich({"CanonicalLatin": ""}))
        assert result["_source"]["hit"] is False

    def test_online_with_mock(self, monkeypatch):
        monkeypatch.setenv("OFFLINE", "0")
        adapter = _make_adapter()
        mock_r = MagicMock(status_code=200)
        mock_r.json.return_value = {
            "response": {
                "docs": [
                    {
                        "dctitle": "On the theory of numbers",
                        "dcpublisher": "University of Goettingen",
                        "dcyear": "1799",
                        "dcidentifier": "10.1234/thesis",
                    }
                ]
            }
        }
        adapter.ctx.http = AsyncMock(get=AsyncMock(return_value=mock_r))
        adapter.ctx.cache = AsyncMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
        adapter.ctx.limiter = AsyncMock(acquire=AsyncMock())
        result = asyncio.run(adapter.enrich({"CanonicalLatin": "Gauss, Carl"}))
        assert result["_source"]["hit"] is True
        assert result["ThesisTitle"] == "On the theory of numbers"
        assert result["Institution"] == "University of Goettingen"
        assert result["DegreeDate"]["date"] == "1799"
