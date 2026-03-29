import pytest

import os, pytest, httpx

pytestmark = pytest.mark.liveapi


@pytest.mark.skipif(os.getenv("OFFLINE", "1") == "1", reason="OFFLINE=1 (default)")
@pytest.mark.timeout(15)
def test_hal_smoke():
    base = os.getenv("HAL_BASE_URL", "https://api.archives-ouvertes.fr")
    with httpx.Client(timeout=10.0) as c:
        r = c.get(f"{base.rstrip('/')}/search/?wt=json&q=math")
        r.raise_for_status()
        assert r.status_code in (200, 400, 404)


@pytest.mark.skipif(os.getenv("OFFLINE", "1") == "1", reason="OFFLINE=1 (default)")
@pytest.mark.timeout(15)
def test_gnd_smoke():
    base = os.getenv("GND_BASE_URL", "https://lobid.org/gnd")
    with httpx.Client(timeout=10.0) as c:
        r = c.get(f"{base.rstrip('/')}/search?q=Euler&format=json&size=1")
        r.raise_for_status()
        assert r.status_code in (200, 400, 404)
