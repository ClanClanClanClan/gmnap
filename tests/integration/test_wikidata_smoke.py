import os

import httpx
import pytest

pytestmark = pytest.mark.liveapi


@pytest.mark.skipif(os.getenv("OFFLINE", "1") == "1", reason="OFFLINE=1")
@pytest.mark.timeout(15)
def test_wikidata_smoke():
    with httpx.Client(timeout=10.0) as c:
        r = c.get("https://query.wikidata.org/sparql", params={"query": "ASK{}"})
        r.raise_for_status()
        assert "text" in r.headers.get("content-type", "").lower()
