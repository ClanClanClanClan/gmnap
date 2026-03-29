import pytest
import os, pytest
from src.authorities.manager import (
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
@pytest.mark.timeout(15)
def test_mathscinet_contract():
    out = MathSciNet_HTML().query("einstein")
    assert out.get("ok") or out.get("reason")


@cond
@pytest.mark.timeout(15)
def test_scopus_contract():
    if os.getenv("SCOPUS_API_KEY"):
        out = Scopus().query()
        assert out.get("ok")
    else:
        pytest.skip("SCOPUS_API_KEY not set")
