"""R57 privacy gate — the API must not hand out name-origin labels to
anonymous callers on EITHER classification endpoint.

Regression guard for the exact defect the R60 assessment found live on
the public repo: /api/v1/query was gated but /api/v1/process was NOT, so
the web UI (which calls /process anonymously) and any script could walk
the ~39.9k enrichment names to reconstitute the labelled corpus that
PRIVACY.md says is not published.

The invariant, per PRIVACY.md:
  - anonymous callers get the GENEALOGY surface (name, IDs, and — where
    enrichment has it — advisors/institution/birth year), the same class
    of data MGP/OpenAlex already publish;
  - the NAME-ORIGIN classification (region code, split axes, candidates,
    confidence, method) is returned ONLY to authenticated research
    callers holding a bearer token.
"""

import os

import pytest

os.environ.setdefault("OFFLINE", "1")
os.environ["GMNAP_REQUIRE_HASHCASH"] = "0"
os.environ["GMNAP_API_TOKENS"] = "test-research-token"

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from src.api.server import create_app  # noqa: E402

# Every field name that reveals the name-origin classification. Kept in
# sync with server._ORIGIN_FIELDS by the last test below.
ORIGIN_FIELDS = {
    "DetectedRegion",
    "region_code",
    "NameRegion",
    "GroupRegion",
    "GeoRegion",
    "ResolutionLevel",
    "RegionCandidates",
    "RegionConflict",
    "DetectionConfidence",
    "confidence",
    "DetectionMethod",
    "detection_method",
}
AUTH = {"Authorization": "Bearer test-research-token"}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# /api/v1/query
# ---------------------------------------------------------------------------


def test_query_anonymous_hides_origin(client):
    r = client.get("/api/v1/query?name=Yılmaz,%20Ayşe")
    assert r.status_code == 200
    body = r.json()
    leaked = ORIGIN_FIELDS & set(body)
    assert not leaked, f"/query leaked origin fields to anon: {sorted(leaked)}"
    assert "restricted" in body.get("name_origin", "")


def test_query_authenticated_returns_origin(client):
    r = client.get("/api/v1/query?name=Yılmaz,%20Ayşe", headers=AUTH)
    assert r.status_code == 200
    assert r.json().get("region_code") == "C1"


# ---------------------------------------------------------------------------
# /api/v1/process — the endpoint the assessment found ungated
# ---------------------------------------------------------------------------


def _entry(resp):
    return (resp.json().get("entries") or [{}])[0]


def test_process_anonymous_hides_origin(client):
    r = client.post(
        "/api/v1/process", json={"entries": [{"CanonicalLatin": "Yılmaz, Ayşe"}]}
    )
    assert r.status_code == 200
    e = _entry(r)
    leaked = ORIGIN_FIELDS & set(e)
    assert not leaked, f"/process leaked origin fields to anon: {sorted(leaked)}"
    assert "restricted" in e.get("name_origin", "")
    # ... but the genealogy/identity surface is preserved.
    assert e.get("GlobalID"), "anon /process must still return the GlobalID"
    assert "CanonicalLatin" in e


def test_process_authenticated_returns_origin(client):
    r = client.post(
        "/api/v1/process",
        json={"entries": [{"CanonicalLatin": "Yılmaz, Ayşe"}]},
        headers=AUTH,
    )
    assert r.status_code == 200
    e = _entry(r)
    assert e.get("DetectedRegion") == "C1", e.get("DetectedRegion")


def test_process_batch_harvest_is_blocked(client):
    """The bulk-harvest vector: many names in one anonymous batch must all
    come back label-free."""
    names = ["Yılmaz, Ayşe", "Wang, Wei", "Silva, João", "Cohen, David", "Nguyen, Van"]
    r = client.post(
        "/api/v1/process",
        json={"entries": [{"CanonicalLatin": n} for n in names]},
    )
    assert r.status_code == 200
    for e in r.json().get("entries", []):
        leaked = ORIGIN_FIELDS & set(e)
        assert not leaked, f"batch entry leaked {sorted(leaked)}"


def test_strip_set_matches_server_constant():
    """This test's ORIGIN_FIELDS must not drift below the server's real
    strip set — otherwise the guard could pass while a field leaks."""
    from src.api import server

    missing = (
        server._ORIGIN_FIELDS
        - ORIGIN_FIELDS
        - {"_region_code", "_region_processed", "RegionalExtras"}
    )
    assert (
        not missing
    ), f"server strips fields this test does not assert: {sorted(missing)}"
