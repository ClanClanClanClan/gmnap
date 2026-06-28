"""Unit tests for the GMNAP V7 API server endpoints.

Tests use FastAPI's TestClient (via starlette) — no live server needed.
"""

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure clean env for each test."""
    monkeypatch.delenv("MEMGRAPH_BOLT", raising=False)
    monkeypatch.delenv("GMNAP_API_TOKENS", raising=False)


@pytest.fixture
def client():
    """Create a fresh TestClient for each test."""
    from starlette.testclient import TestClient

    from src.api.server import create_app

    app = create_app()
    return TestClient(app)


class TestHealthEndpoints:
    def test_healthz_returns_ok(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "7.0"
        assert "uptime_seconds" in data

    def test_readyz_returns_ready_without_memgraph(self, client):
        r = client.get("/readyz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"


class TestLifespanShutdown:
    """The lifespan shutdown must close the authority fetcher pool's
    pooled aiohttp sessions while the loop is still alive — otherwise
    the only cleanup is the atexit hook, which cannot await inside a
    running loop and leaks sessions/sockets on every server restart."""

    def test_shutdown_closes_fetcher_pool(self, monkeypatch):
        from starlette.testclient import TestClient

        import src.authority.manager_tier01 as mt
        from src.api.server import create_app

        # GMNAP_SHUTTING_DOWN is set by the shutdown path; isolate it so
        # it doesn't bleed into other tests (would flip /readyz to 503).
        monkeypatch.delenv("GMNAP_SHUTTING_DOWN", raising=False)

        closed = {"v": False}

        class _FakeFetcher:
            async def close(self):
                closed["v"] = True

        mt._FETCHER_POOL.clear()
        mt._FETCHER_POOL["fake"] = _FakeFetcher()
        try:
            app = create_app()
            # Using TestClient as a context manager runs the lifespan:
            # startup on enter, shutdown on exit.
            with TestClient(app):
                assert "fake" in mt._FETCHER_POOL
            assert closed["v"] is True, "shutdown did not await fetcher.close()"
            assert not mt._FETCHER_POOL, "pool not cleared on shutdown"
        finally:
            mt._FETCHER_POOL.clear()


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        body = r.text
        # Should contain at least uptime gauge
        assert "gmnap_uptime_seconds" in body


class TestHashcashEnforcement:
    def test_query_without_hashcash_returns_402(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler"})
        assert r.status_code == 402
        assert "hashcash" in r.json()["detail"].lower()

    def test_process_without_hashcash_returns_402(self, client):
        r = client.post(
            "/api/v1/process",
            json={"entries": [{"CanonicalLatin": "Euler, Leonhard"}], "mode": "quick"},
        )
        assert r.status_code == 402

    def test_paid_tier_bypasses_hashcash(self, client, monkeypatch):
        monkeypatch.setenv("GMNAP_API_TOKENS", "test-token-123")
        # Need to recreate app with updated tokens
        from src.api.server import _PAID_TOKENS

        _PAID_TOKENS.add("test-token-123")
        try:
            r = client.get(
                "/api/v1/query",
                params={"name": "Euler"},
                headers={"Authorization": "Bearer test-token-123"},
            )
            # Should NOT be 402 — might be 500 if region manager unavailable, that's OK
            assert r.status_code != 402
        finally:
            _PAID_TOKENS.discard("test-token-123")


class TestLineageFormatContract:
    """The lineage `format` param: json|dot served, svg rejected (not
    silently downgraded to JSON the way the old fall-through did)."""

    def test_svg_format_rejected_422(self, client):
        import src.api.server as srv

        srv._PAID_TOKENS.add("fmt-token-svg")
        try:
            r = client.get(
                "/api/v1/lineage/name:Hilbert, David",
                params={"format": "svg"},
                headers={"Authorization": "Bearer fmt-token-svg"},
            )
            # svg is not implemented; the regex-validated Query rejects
            # it with 422 instead of returning misleading JSON.
            assert r.status_code == 422
        finally:
            srv._PAID_TOKENS.discard("fmt-token-svg")

    def test_dot_format_returns_graphviz(self, client):
        import src.api.server as srv

        srv._PAID_TOKENS.add("fmt-token-dot")
        try:
            r = client.get(
                "/api/v1/lineage/name:Hilbert, David",
                params={"format": "dot"},
                headers={"Authorization": "Bearer fmt-token-dot"},
            )
            # 200 + graphviz body when edges resolve; 404 if none.
            assert r.status_code in (200, 404)
            if r.status_code == 200:
                assert "graphviz" in r.headers.get("content-type", "")
        finally:
            srv._PAID_TOKENS.discard("fmt-token-dot")


class TestRateLimiting:
    def test_rate_limit_enforced(self, client):
        """Free tier is 60 req/min. Making 61+ should trigger 429."""
        from src.api.server import _rate_limiter

        # Reset rate limiter for this test
        _rate_limiter._windows.clear()

        for i in range(60):
            r = client.get("/healthz")
            assert r.status_code == 200, f"Request {i+1} failed with {r.status_code}"

        # 61st request should be rate-limited
        r = client.get("/healthz")
        assert r.status_code == 429


class TestBatchSizeLimit:
    def test_batch_too_large_returns_400(self, client):
        """Batch requests over 10,000 entries should be rejected."""
        import src.api.server as srv

        srv._PAID_TOKENS.add("batch-test-token")
        try:
            r = client.post(
                "/api/v1/process",
                json={
                    "entries": [{"CanonicalLatin": "Name"}] * 10_001,
                    "mode": "quick",
                },
                headers={"Authorization": "Bearer batch-test-token"},
            )
            assert r.status_code == 400
            assert "10,000" in r.json()["detail"]
        finally:
            srv._PAID_TOKENS.discard("batch-test-token")
