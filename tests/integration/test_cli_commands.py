"""Integration tests for the GMNAP V7 CLI commands.

Exercises query, regions, sources, and validate commands via Click's CliRunner.
All tests run with GMNAP_NO_NETWORK=1 to prevent external calls.
"""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.cli.gmnap import cli


@pytest.fixture
def runner():
    """Provide a CliRunner with network blocked via env."""
    return CliRunner(env={"GMNAP_NO_NETWORK": "1", "OFFLINE": "1"})


# ---------------------------------------------------------------------------
# query command
# ---------------------------------------------------------------------------


class TestQueryCommand:
    def test_query_command(self, runner):
        result = runner.invoke(cli, ["query", "Euler, Leonhard"])
        assert result.exit_code == 0
        # Output should include region detection information
        assert "Region:" in result.output or "region" in result.output.lower()

    def test_query_json_output(self, runner):
        result = runner.invoke(cli, ["query", "Euler, Leonhard", "--json-output"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "region" in data
        assert "confidence" in data


# ---------------------------------------------------------------------------
# regions command
# ---------------------------------------------------------------------------


class TestRegionsCommand:
    def test_regions_command(self, runner):
        result = runner.invoke(cli, ["regions"])
        assert result.exit_code == 0
        # Should list region codes — at least A1 is always present
        assert "A1" in result.output or "region" in result.output.lower()


# ---------------------------------------------------------------------------
# sources command
# ---------------------------------------------------------------------------


class TestSourcesCommand:
    def test_sources_command(self, runner):
        result = runner.invoke(cli, ["sources"])
        assert result.exit_code == 0
        # Should mention authority sources by tier
        assert "Tier" in result.output or "OpenAlex" in result.output


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_validate_valid_entry(self, runner):
        """A minimal valid entry should pass validation."""
        entry = [
            {
                "CanonicalLatin": "Euler, Leonhard",
                "GlobalID": "mgp:euler-leonhard",
                "FamilyName": "Euler",
                "GivenName": "Leonhard",
                "RegionCode": "A2",
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(entry, f)
            f.flush()
            tmp = f.name

        try:
            result = runner.invoke(cli, ["validate", tmp])
            assert result.exit_code == 0
            assert "Validated" in result.output or "Valid" in result.output
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_validate_invalid_entry(self, runner):
        """An entry missing required fields should produce errors."""
        entry = [{"Foo": "bar"}]  # no CanonicalLatin or other required fields
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(entry, f)
            f.flush()
            tmp = f.name

        try:
            # With schema_strict >= 1, exit code should be 1 when errors exist
            result = runner.invoke(cli, ["validate", tmp, "--schema-strict", "1"])
            # Either exit_code 1 or error info in output
            has_errors = (
                result.exit_code != 0 or "Invalid" in result.output or "Error" in result.output
            )
            assert has_errors, (
                f"Expected validation failure for invalid entry. "
                f"exit_code={result.exit_code}, output={result.output}"
            )
        finally:
            Path(tmp).unlink(missing_ok=True)
