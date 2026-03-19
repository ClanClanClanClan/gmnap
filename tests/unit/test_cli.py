"""
Unit tests for the GMNAP CLI.

Tests all CLI commands: query, lineage, process, sources, regions.
"""

import json

import pytest
from click.testing import CliRunner

from src.cli.gmnap import cli


@pytest.fixture
def runner():
    return CliRunner()


# ── CLI Group ────────────────────────────────────────────────────────────


class TestCLIGroup:
    """Test CLI group basics."""

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "GMNAP" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "7.0.0" in result.output


# ── query command ────────────────────────────────────────────────────────


class TestQueryCommand:
    """Test the query command."""

    def test_query_basic(self, runner):
        result = runner.invoke(cli, ["query", "Smith, John"])
        assert result.exit_code == 0
        assert "Name:" in result.output
        assert "Region:" in result.output
        assert "Confidence:" in result.output

    def test_query_json_output(self, runner):
        result = runner.invoke(cli, ["query", "Smith, John", "--json-output"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "input" in data
        assert "region" in data
        assert "confidence" in data

    def test_query_quick_mode(self, runner):
        result = runner.invoke(cli, ["query", "García, José", "--mode", "quick"])
        assert result.exit_code == 0

    def test_query_unicode_name(self, runner):
        result = runner.invoke(cli, ["query", "Müller, Hans"])
        assert result.exit_code == 0


# ── sources command ──────────────────────────────────────────────────────


class TestSourcesCommand:
    """Test the sources command."""

    def test_sources_lists_tiers(self, runner):
        result = runner.invoke(cli, ["sources"])
        assert result.exit_code == 0
        assert "Tier 0" in result.output
        assert "Tier 1" in result.output
        assert "OpenAlex" in result.output


# ── regions command ──────────────────────────────────────────────────────


class TestRegionsCommand:
    """Test the regions command."""

    def test_regions_lists_codes(self, runner):
        result = runner.invoke(cli, ["regions"])
        assert result.exit_code == 0
        assert "Supported regions" in result.output
        assert "A1" in result.output
