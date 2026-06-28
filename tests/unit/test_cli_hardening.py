"""Tests for CLI hardening (Phase 3 audit fixes)."""

import json
import os
import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.gmnap import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def valid_json_file(tmp_path):
    f = tmp_path / "input.json"
    f.write_text(json.dumps([{"CanonicalLatin": "Euler, Leonhard"}]))
    return str(f)


# ── Input Validation ──────────────────────────────────────────────────


def test_input_file_too_large(runner, tmp_path):
    """Files over 100 MB should be rejected."""
    big = tmp_path / "big.json"
    # Create a file just over 100 MB by writing a header then seeking
    with open(big, "wb") as fh:
        fh.seek(100 * 1024 * 1024 + 1)
        fh.write(b"x")

    result = runner.invoke(cli, ["validate", str(big)])
    assert result.exit_code != 0
    assert "too large" in result.output.lower() or "no entries" in result.output.lower()


def test_input_file_invalid_json(runner, tmp_path):
    """Malformed JSON should produce a user-friendly error."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json!!!")
    result = runner.invoke(cli, ["validate", str(bad)])
    assert result.exit_code != 0
    assert (
        "invalid json" in result.output.lower() or "no entries" in result.output.lower()
    )


def test_input_file_invalid_yaml(runner, tmp_path):
    """Malformed YAML should produce a user-friendly error."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(":\n  - :\n    invalid: [unclosed")
    result = runner.invoke(cli, ["validate", str(bad)])
    assert result.exit_code != 0


def test_input_file_not_found(runner):
    """Non-existent file should be rejected by Click."""
    result = runner.invoke(cli, ["validate", "/nonexistent/file.json"])
    assert result.exit_code != 0


def test_input_file_binary(runner, tmp_path):
    """Binary files should be rejected."""
    binf = tmp_path / "data.json"
    binf.write_bytes(
        struct.pack("4I", 0x7F454C46, 0, 0, 0)
    )  # ELF header (has null bytes)
    result = runner.invoke(cli, ["validate", str(binf)])
    assert result.exit_code != 0
    assert "binary" in result.output.lower() or "no entries" in result.output.lower()


# ── Output Path Validation ────────────────────────────────────────────


def test_output_path_traversal_blocked(runner, valid_json_file):
    """Path traversal attempts should be blocked."""
    result = runner.invoke(
        cli, ["process", valid_json_file, "--output", "../../etc/evil"]
    )
    assert result.exit_code != 0
    assert "traversal" in result.output.lower() or "escapes" in result.output.lower()


def test_output_path_absolute_blocked(runner, valid_json_file):
    """Absolute output paths should be blocked."""
    result = runner.invoke(cli, ["process", valid_json_file, "--output", "/tmp/evil"])
    assert result.exit_code != 0
    assert "relative" in result.output.lower() or "absolute" in result.output.lower()


def test_output_path_sibling_prefix_blocked(runner, valid_json_file):
    """A sibling directory whose name merely starts with the cwd's name
    must NOT pass the --output guard. Regression: the old
    str(resolved).startswith(str(cwd)) check accepted cwd=/a/proj +
    --output ../proj-evil/x (resolves to /a/proj-evil/x), escaping the
    working directory. The pipeline is mocked so a failure to block would
    surface as exit 0, not as a slow real run."""
    mock_pipeline = MagicMock()
    mock_pipeline.process_batch = AsyncMock(
        return_value={"entries": [], "quality_gates": {}}
    )
    with patch(
        "src.core.pipeline_v7.V7Pipeline", MagicMock(return_value=mock_pipeline)
    ):
        with runner.isolated_filesystem():
            cwd_name = Path(os.getcwd()).name
            evil = f"../{cwd_name}-evil/out.json"
            result = runner.invoke(cli, ["process", valid_json_file, "--output", evil])
            assert (
                result.exit_code != 0
            ), f"sibling-prefix escape was not blocked: {result.output!r}"
            assert (
                "escape" in result.output.lower()
                or "traversal" in result.output.lower()
            )
            mock_pipeline.process_batch.assert_not_called()


def test_process_actually_writes_output(runner, valid_json_file):
    """`process --output DIR` must write results.json into DIR.

    Regression: --output was validated for traversal but then only
    echoed ("Output in {dir}/") — nothing was ever written there. The
    pipeline is mocked so this test targets the writing behaviour, not
    the (separately tested) V7 pipeline.
    """
    fake_result = {
        "entries": [{"CanonicalLatin": "Euler, Leonhard", "region_code": "A1"}],
        "quality_gates": {"passed": True},
    }
    mock_pipeline = MagicMock()
    mock_pipeline.process_batch = AsyncMock(return_value=fake_result)
    mock_cls = MagicMock(return_value=mock_pipeline)

    with patch("src.core.pipeline_v7.V7Pipeline", mock_cls):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["process", valid_json_file, "--output", "myout"]
            )
            assert result.exit_code == 0, result.output
            out_file = Path("myout/results.json")
            assert out_file.exists(), "process() did not write results.json"
            data = json.loads(out_file.read_text())
            assert data[0]["CanonicalLatin"] == "Euler, Leonhard"
            assert str(out_file) in result.output


# ── Query Validation ──────────────────────────────────────────────────


def test_query_empty_name(runner):
    """Empty name should be rejected."""
    result = runner.invoke(cli, ["query", ""])
    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "must not" in result.output.lower()


# ── Informational Commands ────────────────────────────────────────────


def test_regions_lists_all_37(runner):
    """The regions command should list all 37 regions."""
    # Mock RegionManager to avoid slow Dropbox I/O and heavy imports
    mock_mgr = MagicMock()
    mock_mgr.IMPLEMENTED_REGIONS = {f"R{i}" for i in range(37)}
    mock_mgr.get_region.return_value = MagicMock(REGION_NAME="Test Region")
    mock_module = MagicMock()
    mock_module.RegionManager = lambda: mock_mgr

    with patch.dict("sys.modules", {"src.regions.manager_optimized": mock_module}):
        result = runner.invoke(cli, ["regions"])
    # Should show the count
    assert "37" in result.output or result.exit_code == 0


def test_sources_lists_tiers(runner):
    """The sources command should list all 4 tiers."""
    result = runner.invoke(cli, ["sources"])
    assert result.exit_code == 0
    assert "Tier 0" in result.output
    assert "Tier 1" in result.output
    assert "Tier 2" in result.output
    assert "Tier 3" in result.output


# ── Extreme Mode ──────────────────────────────────────────────────────


def test_extreme_mode_requires_tos(runner, valid_json_file, monkeypatch):
    """--force-extreme without YES_I_ACCEPT_GS_TOS should fail."""
    monkeypatch.delenv("YES_I_ACCEPT_GS_TOS", raising=False)
    result = runner.invoke(cli, ["process", valid_json_file, "--force-extreme"])
    assert result.exit_code != 0
    assert "YES_I_ACCEPT_GS_TOS" in result.output
