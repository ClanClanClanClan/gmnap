"""Tests for API server hashcash PoW verification and rate limiting."""

from __future__ import annotations

import hashlib
import os
import time

import pytest

os.environ.setdefault("GMNAP_NO_NETWORK", "1")
os.environ.setdefault("OFFLINE", "1")

from src.api.server import create_app  # noqa: E402

try:
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import src.api.server as srv

    # Clear rate limiter windows to avoid 429 from other tests
    srv._rate_limiter._windows.clear()
    app = create_app()
    return TestClient(app)


def _make_hashcash(bits: int = 18, resource: str = "gmnap-api") -> str:
    """Generate a valid hashcash stamp with required leading zero bits."""
    date_str = time.strftime("%y%m%d")
    counter = 0
    prefix = f"1:{bits}:{date_str}:{resource}::rand:"
    while True:
        stamp = f"{prefix}{counter}"
        digest = hashlib.sha1(stamp.encode()).hexdigest()
        binary = bin(int(digest, 16))[2:].zfill(160)
        if binary[:bits] == "0" * bits:
            return stamp
        counter += 1
        if counter > 50_000_000:
            pytest.skip("Could not generate hashcash in reasonable time")


class TestHashcash:
    def test_free_tier_without_hashcash_returns_402(self, client):
        """Free tier requests without X-Hashcash header should be rejected."""
        r = client.get("/api/v1/query", params={"name": "Euler"})
        assert r.status_code == 402
        assert "hashcash" in r.json().get("detail", "").lower()

    def test_free_tier_with_valid_hashcash(self, client):
        """Free tier with valid hashcash should be accepted."""
        stamp = _make_hashcash(bits=18)
        r = client.get(
            "/api/v1/query",
            params={"name": "Euler"},
            headers={"X-Hashcash": stamp},
        )
        # Should succeed (200) or at least not be a 402
        assert r.status_code != 402

    def test_healthz_no_auth_required(self, client):
        """Health endpoints should never require authentication."""
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_metrics_no_auth_required(self, client):
        """Metrics endpoint should be public."""
        r = client.get("/metrics")
        assert r.status_code == 200


class TestRateLimiting:
    def test_paid_tier_bypasses_hashcash(self, client):
        """Paid tier with valid Bearer token should bypass hashcash."""
        import src.api.server as srv

        srv._PAID_TOKENS.add("rate-test-token")
        try:
            r = client.get(
                "/api/v1/query",
                params={"name": "Euler"},
                headers={"Authorization": "Bearer rate-test-token"},
            )
            assert r.status_code == 200
        finally:
            srv._PAID_TOKENS.discard("rate-test-token")

    def test_invalid_bearer_rejected(self, client):
        """Invalid Bearer token should be rejected."""
        r = client.get(
            "/api/v1/query",
            params={"name": "Euler"},
            headers={"Authorization": "Bearer totally-invalid-token"},
        )
        # Should be 402 (not paid) or 403 (forbidden)
        assert r.status_code in (402, 403)
