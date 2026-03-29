import os

import httpx
import pytest

pytestmark = pytest.mark.liveapi


@pytest.mark.skipif(os.getenv("OFFLINE", "1") == "1", reason="OFFLINE=1")
@pytest.mark.timeout(15)
def test_orcid_smoke():
    with httpx.Client(timeout=10.0, headers={"User-Agent": "gmnap-ci"}) as c:
        r = c.get("https://pub.orcid.org/v3.0/expanded-search/")
        assert r.status_code in (200, 404, 405)  # endpoint behaviour may vary
