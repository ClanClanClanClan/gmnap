"""OFFLINE contract of the LIVE tier orchestrator (R51).

Previously imported the dead parallel src/authorities/manager.py (single-
entry API, deleted this round); now pins the real batch contract of
src/authorities/manager_tier01.enrich_all: list in -> list out, 1:1, with
the _sources queried-audit trail populated even when OFFLINE short-circuits
live calls. NOTE: a warm on-disk authority cache can legitimately
contribute at OFFLINE (cache hits are real provenance), so _sources_hit is
asserted to be a subset of the audit trail, not empty.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.authorities.manager_tier01 import enrich_all


@pytest.mark.timeout(15)
def test_enrich_all_offline(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    entry = {"GlobalID": "X", "CanonicalLatin": "Euler, Leonhard"}
    out = asyncio.run(enrich_all([entry]))
    assert isinstance(out, list) and len(out) == 1
    e = out[0]
    assert e["CanonicalLatin"] == "Euler, Leonhard"
    assert isinstance(e.get("_sources"), list) and len(e["_sources"]) >= 1
    assert "OpenAlex" in e["_sources"]  # tier-0 queried even offline
    # hits (live or cache) must be a subset of what was queried
    assert set(e.get("_sources_hit") or []) <= set(e["_sources"])
