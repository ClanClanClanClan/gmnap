import os

import pytest

pytest.skip("Test needs major refactoring", allow_module_level=True)

# from src.authorities.manager import Crossref_Thesis, Wikidata_P184, OAI_University, HAL, GND, zbMATH_Open

LIVE = os.getenv("OFFLINE", "1") == "0" and os.getenv("LIVE_AUTH", "0") == "1"


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=0 or OFFLINE=1")
@pytest.mark.timeout(15)
def test_crossref_contract():
    out = Crossref_Thesis().query(author="Gauss")
    assert out.get("ok")
    if not out.get("offline"):
        msg = out["data"].get("message")
        assert msg is not None and ("items" in msg or "total-results" in msg)
