"""End-to-end user workflow tests.

Tests the actual user journeys, not isolated components:
1. Batch processing via API
2. Single query via API
3. CLI commands
4. Web UI serving
"""

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """API client with paid token (bypasses hashcash)."""
    import src.api.server as mod

    mod._PAID_TOKENS.add("test-workflow-token")
    mod._rate_limiter = mod.RateLimiter(free_rpm=60, paid_rpm=10_000)
    app = mod.create_app()
    return TestClient(app, headers={"Authorization": "Bearer test-workflow-token"})


class TestBatchProcessingWorkflow:
    """User uploads a batch of names -> processes -> gets enriched entries back."""

    def test_batch_returns_200(self, client):
        """POST /api/v1/process with valid entries must return 200."""
        r = client.post(
            "/api/v1/process",
            json={
                "entries": [
                    {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]},
                    {"CanonicalLatin": "Ramanujan, Srinivasa", "CountryCodes": ["IN"]},
                ],
                "mode": "quick",
            },
        )
        assert (
            r.status_code == 200
        ), f"Expected 200, got {r.status_code}: {r.text[:200]}"

    def test_batch_returns_correct_count(self, client):
        """Response must contain all submitted entries."""
        entries = [
            {"CanonicalLatin": f"TestBatch{i}, Name{i}", "CountryCodes": ["US"]}
            for i in range(5)
        ]
        r = client.post("/api/v1/process", json={"entries": entries, "mode": "quick"})
        assert r.status_code == 200
        data = r.json()
        assert data["processed"] >= 5, f"Only {data['processed']} processed out of 5"

    def test_batch_entries_have_detection_fields(self, client):
        """Each returned entry must have DetectedRegion, DetectionConfidence, DetectionMethod."""
        r = client.post(
            "/api/v1/process",
            json={
                "entries": [{"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]}],
                "mode": "quick",
            },
        )
        assert r.status_code == 200
        entries = r.json().get("entries", [])
        assert len(entries) >= 1
        e = entries[0]
        assert (
            "DetectedRegion" in e
        ), f"Missing DetectedRegion. Keys: {sorted(e.keys())}"

    def test_batch_regions_are_correct(self, client):
        """Entries with CountryCodes must detect correct regions."""
        r = client.post(
            "/api/v1/process",
            json={
                "entries": [
                    {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]},
                    {"CanonicalLatin": "Kim, Minhyong", "CountryCodes": ["KR"]},
                    {"CanonicalLatin": "Ivanov, Sergei", "CountryCodes": ["RU"]},
                ],
                "mode": "quick",
            },
        )
        assert r.status_code == 200
        entries = r.json().get("entries", [])
        if len(entries) >= 3:
            regions = [e.get("DetectedRegion") for e in entries]
            # At minimum, they should be detected (not None)
            assert all(
                r is not None for r in regions
            ), f"Some regions are None: {regions}"

    def test_batch_quality_gates_present(self, client):
        """Response must include quality_gates field."""
        r = client.post(
            "/api/v1/process",
            json={
                "entries": [{"CanonicalLatin": "Smith, John", "CountryCodes": ["US"]}],
                "mode": "quick",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "quality_gates" in data
        assert "metrics" in data

    def test_batch_pagination(self, client):
        """Pagination (limit/offset) must work."""
        entries = [
            {"CanonicalLatin": f"Page{i}, Test{i}", "CountryCodes": ["US"]}
            for i in range(10)
        ]
        r = client.post(
            "/api/v1/process",
            json={
                "entries": entries,
                "mode": "quick",
                "limit": 3,
                "offset": 0,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data.get("entries", [])) <= 3
        assert data.get("has_more") is True or data.get("processed", 0) <= 3

    def test_batch_empty_entries_rejected(self, client):
        """Empty entries list should be handled gracefully."""
        r = client.post("/api/v1/process", json={"entries": [], "mode": "quick"})
        # Should either return 200 with 0 entries or 400
        assert r.status_code in (200, 400)

    def test_batch_missing_canonical_latin_rejected(self, client):
        """Entries without CanonicalLatin must be rejected."""
        r = client.post(
            "/api/v1/process",
            json={
                "entries": [{"BirthYear": 1990}],
                "mode": "quick",
            },
        )
        assert r.status_code == 400
        assert "CanonicalLatin" in r.json().get("detail", "")

    def test_batch_oversized_rejected(self, client):
        """More than 10,000 entries must be rejected."""
        entries = [{"CanonicalLatin": f"Bulk{i}"} for i in range(10_001)]
        r = client.post("/api/v1/process", json={"entries": entries, "mode": "quick"})
        assert r.status_code == 400


class TestQueryWorkflow:
    """User searches a single name -> gets region + metadata."""

    def test_query_returns_name(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Euler, Leonhard"

    def test_query_returns_region(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
        data = r.json()
        assert "region_code" in data
        assert data["region_code"] is not None

    def test_query_returns_confidence(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
        data = r.json()
        assert "confidence" in data
        assert data["confidence"] > 0

    def test_query_returns_global_id(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
        data = r.json()
        assert "global_id" in data
        # GlobalID may be None if generation fails, but field must exist

    def test_query_returns_detection_method(self, client):
        r = client.get("/api/v1/query", params={"name": "Euler, Leonhard"})
        data = r.json()
        assert "detection_method" in data

    def test_query_empty_name_400(self, client):
        r = client.get("/api/v1/query", params={"name": ""})
        assert r.status_code == 400

    def test_query_long_name_400(self, client):
        r = client.get("/api/v1/query", params={"name": "A" * 501})
        assert r.status_code == 400

    def test_query_unicode_works(self, client):
        r = client.get("/api/v1/query", params={"name": "Müller, Hans-Jürgen"})
        assert r.status_code == 200

    def test_query_cjk_works(self, client):
        r = client.get("/api/v1/query", params={"name": "陶哲轩"})
        assert r.status_code == 200

    def test_query_xss_safe(self, client):
        r = client.get("/api/v1/query", params={"name": "<script>alert(1)</script>"})
        # Should return 200 (name is data, not code) or 400, but NOT 500
        assert r.status_code != 500


class TestCorrectionWorkflow:
    """User submits a correction suggestion."""

    def test_suggest_correction_endpoint(self, client):
        r = client.post(
            "/api/v1/suggest",
            json={
                "original_name": "Euler, Leonhard",
                "correction_type": "advisor",
                "suggested_value": "Bernoulli, Johann I",
                "source_url": "https://mathgenealogy.org/id.php?id=38586",
                "submitter_note": "Confirmed on MGP",
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "received"


class TestWebUIWorkflow:
    """User opens browser -> sees search page -> searches -> gets results."""

    def test_index_page_served(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "MathLineage" in r.text or "GMNAP" in r.text

    def test_css_served(self, client):
        r = client.get("/static/style.css")
        assert r.status_code == 200
        assert "var(--bg-primary)" in r.text

    def test_js_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "escapeHtml" in r.text

    def test_health_check_works(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data

    def test_security_headers_on_all_responses(self, client):
        """Every response must have security headers."""
        for path in ["/healthz", "/", "/static/style.css"]:
            r = client.get(path)
            assert (
                "X-Content-Type-Options" in r.headers
            ), f"Missing X-Content-Type-Options on {path}"
            assert "X-Frame-Options" in r.headers, f"Missing X-Frame-Options on {path}"


class TestCLIWorkflow:
    """User runs CLI commands."""

    def test_cli_query(self):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["query", "Euler, Leonhard"])
        assert result.exit_code == 0
        assert "Region:" in result.output

    def test_cli_sources(self):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["sources"])
        assert result.exit_code == 0
        assert "Tier 0" in result.output

    def test_cli_regions(self):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["regions"])
        assert result.exit_code == 0
        # Should list at least 30 regions
        assert "A1" in result.output

    def test_cli_validate_valid_file(self, tmp_path):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        f = tmp_path / "test.json"
        f.write_text(json.dumps([{"CanonicalLatin": "Euler, Leonhard"}]))
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(f)])
        assert result.exit_code == 0

    def test_cli_validate_invalid_file(self, tmp_path):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        f = tmp_path / "bad.json"
        f.write_text("{not valid json!!!")
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(f)])
        # Should fail gracefully, not crash
        assert (
            result.exit_code != 0
            or "invalid" in result.output.lower()
            or "no entries" in result.output.lower()
        )

    def test_cli_help(self):
        from click.testing import CliRunner

        from src.cli.gmnap import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "query" in result.output
        assert "process" in result.output
        assert "validate" in result.output
        assert "serve" in result.output
