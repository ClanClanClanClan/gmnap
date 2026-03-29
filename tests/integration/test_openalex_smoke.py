import pytest

import os, httpx, pytest

pytestmark = pytest.mark.liveapi


@pytest.mark.skipif(os.getenv("OFFLINE", "1") == "1", reason="OFFLINE=1")
@pytest.mark.timeout(15)
def test_openalex_smoke():
    with httpx.Client(timeout=10.0, headers={"User-Agent": "gmnap-ci"}) as c:
        r = c.get("https://api.openalex.org/")
        r.raise_for_status()
        assert r.status_code == 200
