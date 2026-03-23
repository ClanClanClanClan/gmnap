"""Integration tests for GMNAP V7 API endpoints.

Tests the full request/response cycle including middleware (CORS, rate limiting,
request IDs), authentication (Bearer + hashcash), batch processing with
pagination, and error handling.

Uses FastAPI's TestClient (via starlette) — no live server needed.
"""

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

import pytest
from starlette.testclient import TestClient

import src.api.server as srv


# ---------------------------------------------------------------------------
# Fake pipeline module for environments where pipeline_v7 cannot be imported
# (e.g. Python 3.9 where `int | None` syntax is unsupported).
# ---------------------------------------------------------------------------

class _FakePipelineMode(Enum):
    QUICK = "quick"
    FULL = "full"
    EXTREME = "extreme"


class _FakeV7Pipeline:
    def __init__(self, mode=None, **kwargs):
        self.mode = mode or _FakePipelineMode.QUICK

    async def process_batch(self, entries):
        return {
            "entries": [
                {**e, "DetectedRegion": "A2", "OrderKey": e.get("CanonicalLatin", "").upper()}
                for e in entries
            ],
            "metrics": {"elapsed": 0.01},
            "quality_gates": {"passed": True, "gates": {}},
        }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Block network access and clear state for each test."""
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.delenv("MEMGRAPH_BOLT", raising=False)
    # Clear rate limiter between tests
    srv._rate_limiter._windows.clear()


@pytest.fixture
def client():
    """TestClient with no special auth."""
    app = srv.create_app()
    return TestClient(app)


@pytest.fixture
def paid_client():
    """TestClient with a paid Bearer token configured."""
    srv._PAID_TOKENS.add("test-token")
    app = srv.create_app()
    yield TestClient(app)
    srv._PAID_TOKENS.discard("test-token")


# ---------------------------------------------------------------------------
# Health / readiness
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    def test_healthz_returns_200(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "uptime_seconds" in body
        assert isinstance(body["uptime_seconds"], (int, float))

    def test_readyz_returns_200(self, client):
        r = client.get("/readyz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_metrics_returns_prometheus(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        # prometheus_client exposes python_info gauge by default
        assert "python_info" in r.text


# ---------------------------------------------------------------------------
# Query endpoint (paid tier — Bearer token)
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_query_with_valid_token(self, paid_client):
        r = paid_client.get(
            "/api/v1/query",
            params={"name": "Euler, Leonhard"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "region_code" in body

    def test_query_without_auth_returns_402(self, client):
        """Free tier without hashcash gets 402 Payment Required."""
        r = client.get(
            "/api/v1/query",
            params={"name": "Euler, Leonhard"},
        )
        assert r.status_code == 402
        body = r.json()
        assert "hashcash" in body.get("detail", "").lower()


# ---------------------------------------------------------------------------
# Process endpoint
# ---------------------------------------------------------------------------

class TestProcessEndpoint:
    _TWO_ENTRIES = [
        {"CanonicalLatin": "Euler, Leonhard"},
        {"CanonicalLatin": "Gauss, Carl Friedrich"},
    ]

    def test_process_batch_returns_entries(self, paid_client):
        r = paid_client.post(
            "/api/v1/process",
            json={"entries": self._TWO_ENTRIES, "mode": "quick"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "processed" in body
        assert "entries" in body
        assert "quality_gates" in body

    def test_process_batch_pagination(self, paid_client):
        r = paid_client.post(
            "/api/v1/process",
            json={
                "entries": self._TWO_ENTRIES,
                "mode": "quick",
                "offset": 0,
                "limit": 1,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["entries"]) <= 1
        assert body["has_more"] is True

    def test_process_validates_missing_canonical_latin(self, paid_client):
        r = paid_client.post(
            "/api/v1/process",
            json={"entries": [{"Name": "nobody"}], "mode": "quick"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert r.status_code == 400
        assert "CanonicalLatin" in r.json()["detail"]

    def test_process_invalid_mode_defaults_quick(self, paid_client):
        r = paid_client.post(
            "/api/v1/process",
            json={
                "entries": [{"CanonicalLatin": "Test, Person"}],
                "mode": "garbage",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        # The server accepts arbitrary mode strings but normalises via pipeline_mode
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_error_does_not_leak_internals(self, paid_client):
        """A server-side crash should return a generic message, not a traceback."""
        r = paid_client.post(
            "/api/v1/process",
            json={"entries": [{}], "mode": "quick"},
            headers={"Authorization": "Bearer test-token"},
        )
        body = r.json()
        detail = body.get("detail", "")
        # Should not contain Python traceback markers
        assert "Traceback" not in detail
        assert "File \"" not in detail


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

class TestCORS:
    def test_cors_headers_present(self, client):
        r = client.options(
            "/healthz",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORSMiddleware returns CORS headers on preflight
        assert "access-control-allow-origin" in r.headers


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------

class TestRequestID:
    def test_request_id_header_returned(self, client):
        r = client.get("/healthz")
        assert "x-request-id" in r.headers
