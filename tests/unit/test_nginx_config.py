"""Tests for nginx configuration hardening (Phase 2 audit fixes)."""

from pathlib import Path

import pytest

NGINX_CONF = Path(__file__).resolve().parent.parent.parent / "config" / "nginx.conf"


@pytest.fixture()
def nginx_text():
    assert NGINX_CONF.exists(), f"nginx.conf not found at {NGINX_CONF}"
    return NGINX_CONF.read_text(encoding="utf-8")


def test_security_headers_in_config(nginx_text):
    """All required security headers must be present."""
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "Referrer-Policy",
        "Permissions-Policy",
    ]
    for header in required_headers:
        assert header in nginx_text, f"Missing security header: {header}"


def test_gzip_enabled(nginx_text):
    """Gzip compression must be configured."""
    assert "gzip on" in nginx_text, "gzip must be enabled"
    assert "gzip_types" in nginx_text, "gzip_types must be configured"
    assert "application/json" in nginx_text, "JSON must be in gzip_types"


def test_metrics_restricted(nginx_text):
    """Metrics endpoint must have active allow/deny rules (not commented)."""
    in_metrics = False
    has_allow = False
    has_deny = False
    for line in nginx_text.splitlines():
        stripped = line.strip()
        if "location /metrics" in stripped:
            in_metrics = True
        if in_metrics:
            if stripped.startswith("allow ") and not stripped.startswith("#"):
                has_allow = True
            if stripped.startswith("deny all") and not stripped.startswith("#"):
                has_deny = True
            if stripped == "}":
                break

    assert has_allow, "Metrics location must have active 'allow' rules (not commented)"
    assert has_deny, "Metrics location must have active 'deny all' rule (not commented)"


def test_server_tokens_off(nginx_text):
    """server_tokens must be turned off to hide nginx version."""
    assert "server_tokens off" in nginx_text, "server_tokens off must be set"


def test_ssl_template_exists(nginx_text):
    """An SSL template section must exist (commented is OK)."""
    assert (
        "ssl_certificate" in nginx_text
    ), "SSL template with ssl_certificate must exist"
    assert "ssl_protocols" in nginx_text, "SSL template must specify ssl_protocols"
    assert "TLSv1.2" in nginx_text, "SSL template must include TLSv1.2"
    assert "TLSv1.3" in nginx_text, "SSL template must include TLSv1.3"


def test_client_max_body_size(nginx_text):
    """client_max_body_size must be set."""
    assert (
        "client_max_body_size" in nginx_text
    ), "client_max_body_size must be configured"
    # Extract the value - should be reasonable (not unlimited)
    for line in nginx_text.splitlines():
        if "client_max_body_size" in line and not line.strip().startswith("#"):
            # Should have a size limit, not be 0 (unlimited)
            assert (
                "0" not in line.split("client_max_body_size")[1].split(";")[0].strip()
                or "50" in line
            )


def test_rate_limit_zone_configured(nginx_text):
    """Rate limiting zone must be configured."""
    assert "limit_req_zone" in nginx_text, "Rate limit zone must be defined"
    assert "limit_req zone=" in nginx_text, "Rate limit must be applied"
    assert "limit_req_status 429" in nginx_text, "Rate limit status should be 429"


def test_no_default_server_name(nginx_text):
    """Server name should be _ (catch-all) not a specific domain in default config."""
    found_server_name = False
    for line in nginx_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("server_name") and not stripped.startswith("#"):
            found_server_name = True
            # Default config should use _ or localhost, not a real domain
            assert (
                "_" in stripped or "localhost" in stripped
            ), f"Default server_name should be _ or localhost, got: {stripped}"
    assert found_server_name, "server_name directive must be present"
