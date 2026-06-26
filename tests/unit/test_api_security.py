"""Tests for API server security hardening (Phase 1 audit fixes)."""

import hashlib
import time
import uuid

import pytest
from fastapi.testclient import TestClient

import src.api.server as _server_mod
from src.api.server import APIRateLimiter as RateLimiter
from src.api.server import (
    _used_stamps,
    create_app,
    verify_hashcash,
)


def _make_hashcash(resource="gmnap-api", bits=18):
    """Generate a valid SHA-256 hashcash stamp with unique nonce."""
    date_str = time.strftime("%y%m%d")
    nonce = uuid.uuid4().hex[:8]
    counter = 0
    while True:
        stamp = f"1:{bits}:{date_str}:{resource}::{nonce}:{counter}"
        digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
        binary = bin(int(digest, 16))[2:].zfill(256)
        if binary[:bits] == "0" * bits:
            return stamp
        counter += 1
        if counter > 5_000_000:
            pytest.skip("Could not generate hashcash in reasonable time")


@pytest.fixture()
def client():
    """Provide a TestClient with a fresh rate limiter."""
    _server_mod._rate_limiter = RateLimiter(free_rpm=60, paid_rpm=10_000)
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def paid_client():
    """TestClient with a paid token (bypasses hashcash for /api/ endpoints)."""
    _server_mod._rate_limiter = RateLimiter(free_rpm=60, paid_rpm=10_000)
    _server_mod._PAID_TOKENS = {"test-paid-token"}
    app = create_app()
    c = TestClient(app, headers={"Authorization": "Bearer test-paid-token"})
    yield c
    _server_mod._PAID_TOKENS = set()


# ── CORS ──────────────────────────────────────────────────────────────


def test_cors_rejects_unknown_origin(client):
    resp = client.options(
        "/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    assert "evil.example.com" not in acao


def test_cors_allows_configured_origin(client):
    resp = client.get(
        "/healthz",
        headers={"Origin": "http://localhost:8080"},
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao == "http://localhost:8080"


# ── Hashcash SHA-256 ──────────────────────────────────────────────────


def test_hashcash_uses_sha256():
    """Verify that SHA-1 stamps are rejected and SHA-256 stamps work."""
    date_str = time.strftime("%y%m%d")
    counter = 0
    sha1_only_stamp = None
    while counter < 2_000_000:
        stamp = f"1:18:{date_str}:gmnap-api::sha1test:{counter}"
        sha1_digest = hashlib.sha1(stamp.encode("utf-8")).hexdigest()
        sha1_bits = bin(int(sha1_digest, 16))[2:].zfill(160)
        sha256_digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
        sha256_bits = bin(int(sha256_digest, 16))[2:].zfill(256)
        if sha1_bits[:18] == "0" * 18 and sha256_bits[:18] != "0" * 18:
            sha1_only_stamp = stamp
            break
        counter += 1

    if sha1_only_stamp:
        assert not verify_hashcash(
            sha1_only_stamp
        ), "SHA-1-valid stamp should fail SHA-256 check"

    valid = _make_hashcash()
    _used_stamps.pop(valid, None)
    assert verify_hashcash(valid), "SHA-256 valid stamp should pass"


def test_hashcash_replay_rejected():
    stamp = _make_hashcash()
    _used_stamps.pop(stamp, None)
    assert verify_hashcash(stamp) is True
    assert verify_hashcash(stamp) is False, "Replay should be rejected"


def test_hashcash_expired_rejected():
    stamp = _make_hashcash()
    _used_stamps.pop(stamp, None)
    _used_stamps[stamp] = time.time() - 600
    assert verify_hashcash(stamp) is False


# ── Security Headers ─────────────────────────────────────────────────


def test_security_headers_present(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert "nosniff" in resp.headers.get("X-Content-Type-Options", "")
    assert "DENY" in resp.headers.get("X-Frame-Options", "")
    assert "max-age=31536000" in resp.headers.get("Strict-Transport-Security", "")
    assert "default-src" in resp.headers.get("Content-Security-Policy", "")
    assert "strict-origin" in resp.headers.get("Referrer-Policy", "")
    assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")


def test_security_headers_on_error_responses(client):
    resp = client.get("/nonexistent-path-xyz")
    assert "nosniff" in resp.headers.get("X-Content-Type-Options", "")
    assert "DENY" in resp.headers.get("X-Frame-Options", "")


# ── Rate Limiting ─────────────────────────────────────────────────────


def test_rate_limit_free_tier():
    """Free tier should be rate-limited at 60 req/min."""
    _server_mod._rate_limiter = RateLimiter(free_rpm=60, paid_rpm=10_000)
    app = create_app()
    client = TestClient(app)

    statuses = []
    for _ in range(62):
        resp = client.get("/healthz")
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Expected 429 in statuses, got: {set(statuses)}"


def test_rate_limit_paid_tier_bypasses(monkeypatch):
    """Paid tier should have higher rate limit."""
    _server_mod._rate_limiter = RateLimiter(free_rpm=5, paid_rpm=10_000)
    _server_mod._PAID_TOKENS = {"secret-paid-token-abc123"}
    app = create_app()
    client = TestClient(app)

    try:
        for _ in range(10):
            resp = client.get(
                "/healthz",
                headers={"Authorization": "Bearer secret-paid-token-abc123"},
            )
            assert (
                resp.status_code == 200
            ), f"Paid tier should not be rate-limited, got {resp.status_code}"
    finally:
        _server_mod._PAID_TOKENS = set()


# ── Query Validation ──────────────────────────────────────────────────


def test_query_name_length_limit(client):
    stamp = _make_hashcash()
    long_name = "A" * 501
    resp = client.get(
        f"/api/v1/query?name={long_name}",
        headers={"X-Hashcash": stamp},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "max 500" in detail or "too long" in detail


def test_query_injection_payloads(paid_client, monkeypatch):
    """SQL, XSS, and command injection payloads should not crash the server."""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.region_code = "R0"
    mock_result.confidence = 0.5
    mock_result.detection_method = "fallback"
    mock_result.metadata = {}

    mock_mgr = MagicMock()
    mock_mgr.detect_region.return_value = mock_result
    mock_module = MagicMock()
    mock_module.RegionManager.return_value = mock_mgr

    monkeypatch.setitem(
        __import__("sys").modules,
        "src.regions.manager_optimized",
        mock_module,
    )

    payloads = [
        "'; DROP TABLE users; --",
        "<script>alert(1)</script>",
        "$(cat /etc/passwd)",
        "{{7*7}}",
        "%00%0d%0aX-Injected: true",
        "' OR '1'='1",
        "; rm -rf /",
    ]
    for payload in payloads:
        resp = paid_client.get(
            "/api/v1/query",
            params={"name": payload},
        )
        assert resp.status_code != 500, f"Injection payload crashed server: {payload}"


# ── Batch Processing ─────────────────────────────────────────────────


def test_process_batch_size_limit(paid_client):
    too_many = [{"CanonicalLatin": f"Test {i}"} for i in range(10_001)]
    resp = paid_client.post(
        "/api/v1/process",
        json={"entries": too_many, "mode": "quick"},
    )
    assert resp.status_code == 400
    assert "10,000" in resp.json()["detail"] or "10000" in resp.json()["detail"]


# ── Metrics ───────────────────────────────────────────────────────────


def test_metrics_no_sensitive_data():
    _server_mod._PAID_TOKENS = {"secret-paid-token-abc123"}
    try:
        app = create_app()
        client = TestClient(app)
        resp = client.get("/metrics")
        body = resp.text
        assert (
            "secret-paid-token-abc123" not in body
        ), "Metrics should not leak API tokens"
    finally:
        _server_mod._PAID_TOKENS = set()


# ── Error Handling ────────────────────────────────────────────────────


def test_error_no_traceback_leakage(paid_client, monkeypatch):
    """Error responses should not leak stack traces."""
    from unittest.mock import MagicMock

    # Mock RegionManager to raise an internal error
    mock_module = MagicMock()
    mock_module.RegionManager.side_effect = RuntimeError("internal boom")
    monkeypatch.setitem(
        __import__("sys").modules,
        "src.regions.manager_optimized",
        mock_module,
    )

    resp = paid_client.get("/api/v1/query?name=test")
    body = resp.text
    if resp.status_code == 500:
        assert "Traceback" not in body
        assert "internal boom" not in body
        assert "Internal server error" in body


def test_oversized_request_body(paid_client):
    """Extremely large request bodies should be handled gracefully."""
    huge_entries = [{"CanonicalLatin": "X" * 1000} for _ in range(10_001)]
    resp = paid_client.post(
        "/api/v1/process",
        json={"entries": huge_entries},
    )
    assert resp.status_code == 400


# ── API / Web UI Round-Trip ──────────────────────────────────────────


def test_query_response_includes_global_id(paid_client, monkeypatch):
    """GET /api/v1/query should return global_id in the response shape
    expected by static/app.js."""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.region_code = "A1"
    mock_result.confidence = 0.95
    mock_result.detection_method = "script"
    mock_result.metadata = {"script": "Latin"}

    mock_mgr = MagicMock()
    mock_mgr.detect_region.return_value = mock_result
    mock_module = MagicMock()
    mock_module.RegionManager.return_value = mock_mgr

    monkeypatch.setitem(
        __import__("sys").modules,
        "src.regions.manager_optimized",
        mock_module,
    )

    resp = paid_client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
    assert resp.status_code == 200

    data = resp.json()

    # Verify response shape matches what app.js expects
    assert "name" in data, "Response must include 'name'"
    assert "global_id" in data, "Response must include 'global_id'"
    assert "region_code" in data, "Response must include 'region_code'"
    assert "confidence" in data, "Response must include 'confidence'"
    assert "detection_method" in data, "Response must include 'detection_method'"
    assert "metadata" in data, "Response must include 'metadata'"

    # Verify global_id is a non-empty string
    assert isinstance(data["global_id"], str)
    assert len(data["global_id"]) >= 22, "GlobalID should be at least 22 chars"

    # Verify name round-trips correctly
    assert data["name"] == "Euler, Leonhard"
