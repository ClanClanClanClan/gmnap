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

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.server as srv  # noqa: E402
from src.api.server import create_app  # noqa: E402

RESEARCH_TOKEN = "test-research-token"

# Every field name that reveals the name-origin classification. Kept in
# sync with server._ORIGIN_FIELDS by the last test below.
ORIGIN_FIELDS = {
    "DetectedRegion",
    "region_code",
    # R67: 11 region processors stamp THIS casing, and it was absent from the
    # server's strip-set — so the name-origin classification shipped to
    # anonymous callers under it. The server now also regex-matches any
    # region-code spelling.
    "RegionCode",
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
AUTH = {"Authorization": f"Bearer {RESEARCH_TOKEN}"}


@pytest.fixture(scope="module")
def _research_caller():
    """Make this process look like it has one authenticated research token.

    R72 — THIS FIXTURE REPLACES TWO MODULE-LEVEL `os.environ[...] = ...`
    WRITES, and the difference is not cosmetic.

    Module-level statements in a test file run at pytest COLLECTION
    time, before any test executes, and nothing undoes them. So those
    two lines set GMNAP_REQUIRE_HASHCASH=0 and GMNAP_API_TOKENS for
    **every other test in the same pytest process**. Measured when R72
    wired this file into CI for the first time, it broke 12 tests in two
    other files that had been green:

      * tests/unit/test_api_server.py (2) — the leaked
        GMNAP_REQUIRE_HASHCASH=0 disabled the gate whose enforcement
        those tests assert, so `/api/v1/query` answered 200 where they
        require 402. `_hashcash_required()` re-reads the env per
        request, so the leak takes effect immediately.
      * tests/unit/test_config.py (10) — `_load_from_env` turns
        GMNAP_API_TOKENS into `config["api"]["tokens"]`, and APIConfig
        has no `tokens` field: `TypeError: APIConfig.__init__() got an
        unexpected keyword argument 'tokens'`.

    And the leak broke this file in return: `server._PAID_TOKENS` is
    computed ONCE at server-import time, so setting the env var only
    worked while this module happened to import `src.api.server` first.
    Once test_api_server.py imported it earlier in the run, _PAID_TOKENS
    was empty, the Bearer token below was not recognised, the
    authenticated requests got the anonymous surface, and the two
    `*_returns_origin` tests failed on `region_code is None`.

    Both halves are fixed by scoping: monkeypatch unsets the env on
    teardown, and _PAID_TOKENS is seeded directly so import order stops
    mattering (the pattern tests/unit/test_api_server.py already uses).
    No assertion in this file changed.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GMNAP_REQUIRE_HASHCASH", "0")
        mp.setenv("GMNAP_API_TOKENS", RESEARCH_TOKEN)
        # server._rate_limiter is ANOTHER import-time global: a single
        # in-memory 60-req/min window shared by the whole pytest
        # process. tests/unit/test_api_server.py spends that budget
        # before this file runs, so the anonymous requests below came
        # back 429 instead of 200 — a second order-dependence this file
        # never hit while nothing else ran with it. Give this module its
        # own limiter; monkeypatch restores the original on teardown.
        mp.setattr(
            srv,
            "_rate_limiter",
            srv.APIRateLimiter(free_rpm=srv._free_rpm, paid_rpm=srv._paid_rpm),
        )
        already_present = RESEARCH_TOKEN in srv._PAID_TOKENS
        srv._PAID_TOKENS.add(RESEARCH_TOKEN)
        try:
            yield
        finally:
            if not already_present:
                srv._PAID_TOKENS.discard(RESEARCH_TOKEN)


@pytest.fixture(scope="module")
def client(_research_caller):
    # Depends on _research_caller explicitly rather than relying on
    # autouse ordering: the app must be built with the token in place.
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
