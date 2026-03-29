import os, pytest
from overlays.authority_tier2_3.src.authority.extreme_adapters import (
    MathSciNet_HTML,
    Scopus,
    Dimensions,
    ProQuest_ETD,
    Google_Scholar,
)

LIVE = os.getenv("OFFLINE", "1") == "0" and os.getenv("LIVE_AUTH", "0") == "1"
EXTREME = os.getenv("FORCE_EXTREME", "0") == "1"

cond = pytest.mark.skipif(
    not (LIVE and EXTREME), reason="Requires LIVE_AUTH=1 and FORCE_EXTREME=1"
)


@cond
def test_mathscinet_contract():
    out = MathSciNet_HTML().query("einstein")
    assert out.get("ok") or out.get("reason") in {"FORCE_EXTREME=0"}
    if out.get("ok") and not out.get("offline"):
        assert "<html" in out["data"]


@cond
def test_scopus_contract():
    if os.getenv("SCOPUS_API_KEY"):
        out = Scopus().query()
        assert out.get("ok")
        if not out.get("offline"):
            assert "search-results" in out["data"]
    else:
        pytest.skip("SCOPUS_API_KEY not set")


@cond
def test_dimensions_contract():
    if os.getenv("DIMENSIONS_TOKEN"):
        out = Dimensions().query()
        assert out.get("ok")
        if not out.get("offline"):
            assert "docs" in out["data"]
    else:
        pytest.skip("DIMENSIONS_TOKEN not set")


@cond
def test_proquest_contract():
    if os.getenv("PROQUEST_ACCEPT") == "yes":
        out = ProQuest_ETD().query()
        assert out.get("ok")
        if not out.get("offline"):
            assert out["data"].get("status") == "ok"
    else:
        pytest.skip("PROQUEST_ACCEPT!=yes")


@cond
def test_scholar_contract():
    if os.getenv("YES_I_ACCEPT_GS_TOS") == "yes":
        out = Google_Scholar().query()
        assert out.get("ok")
        if not out.get("offline"):
            assert out["data"].get("gs_cache_hit") in {True, False}
    else:
        pytest.skip("YES_I_ACCEPT_GS_TOS!=yes")
