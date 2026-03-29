import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.authorities.manager import enrich_all


@pytest.mark.timeout(15)
def test_enrich_all_offline(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    entry = {"GlobalID": "X", "CanonicalLatin": "Euler, Leonhard"}
    out = asyncio.get_event_loop().run_until_complete(enrich_all(entry))
    assert isinstance(out, dict)
    assert "AuthoritySources" in out and len(out["AuthoritySources"]) >= 1
