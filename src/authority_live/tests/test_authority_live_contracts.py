import os

import pytest
from overlays.authority_live.src.authority.live_adapters import (
    GND,
    HAL,
    Crossref_Thesis,
    OAI_University,
    Wikidata_P184,
    zbMATH_Open,
)

LIVE = os.getenv("OFFLINE", "1") == "0" and os.getenv("LIVE_AUTH", "0") == "1"


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=0 or OFFLINE=1")
def test_crossref_contract():
    out = Crossref_Thesis().query(author="Gauss")
    assert out.get("ok")
    if not out.get("offline"):
        msg = out["data"].get("message")
        assert msg is not None and ("items" in msg or "total-results" in msg)


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=0 or OFFLINE=1")
def test_wikidata_contract():
    out = Wikidata_P184().query(limit=1)
    assert out.get("ok")
    if not out.get("offline"):
        assert "results" in out["data"] and "bindings" in out["data"]["results"]


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("OAI_BASE_URL") is None, reason="Need OAI_BASE_URL"
)
def test_oai_identify_contract():
    out = OAI_University().query()
    assert out.get("ok")
    if not out.get("offline"):
        assert "Identify" in out["data"]


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=0 or OFFLINE=1")
def test_hal_contract():
    out = HAL().query(q="thesis")
    assert out.get("ok")
    if not out.get("offline"):
        assert isinstance(out["data"], dict) and (
            "response" in out["data"] or "nhits" in out["data"]
        )


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("GND_SRU_URL") is None, reason="Need GND_SRU_URL"
)
def test_gnd_contract():
    out = GND().query()
    assert out.get("ok")
    if not out.get("offline"):
        assert "<searchRetrieveResponse" in out["data"]


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("ZBMATH_API_URL") is None, reason="Need ZBMATH_API_URL"
)
def test_zbmath_contract():
    out = zbMATH_Open().query()
    assert out.get("ok")
    if not out.get("offline"):
        assert isinstance(out["data"], dict)
