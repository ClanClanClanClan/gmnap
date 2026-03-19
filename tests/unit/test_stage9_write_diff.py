"""
Unit tests for Stage 9: Write&Diff.

Tests deterministic YAML snapshot writing, HTML diff generation,
SQL changelog, and Cypher changelog.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.pipeline.stage9_write_and_diff import (
    diff_snapshots,
    generate_cypher_changelog,
    generate_sql_changelog,
    write_snapshot,
)


@pytest.fixture
def sample_entries():
    return [
        {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA", "CanonicalLatin": "Smith, John", "BirthYear": 1975},
        {"GlobalID": "BBBBBBBBBBBBBBBBBBBBBB", "CanonicalLatin": "García, José", "BirthYear": 1980},
    ]


# ── write_snapshot ───────────────────────────────────────────────────────


class TestWriteSnapshot:
    """Test snapshot writing."""

    def test_creates_snapshot_dir(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = write_snapshot(sample_entries, out_root=tmpdir)
            assert Path(snap).exists()
            assert Path(snap).is_dir()

    def test_writes_manifest(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = write_snapshot(sample_entries, out_root=tmpdir)
            manifest = Path(snap) / "MANIFEST.json"
            assert manifest.exists()
            data = json.loads(manifest.read_text())
            assert data["count"] == 2
            assert "run_hash" in data

    def test_writes_individual_yaml_files(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = write_snapshot(sample_entries, out_root=tmpdir)
            yaml_files = list(Path(snap).glob("*.yaml"))
            assert len(yaml_files) == 2

    def test_writes_entries_json(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = write_snapshot(sample_entries, out_root=tmpdir)
            entries_json = Path(snap) / "entries.json"
            assert entries_json.exists()
            data = json.loads(entries_json.read_text())
            assert len(data) == 2

    def test_deterministic_hash(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot(sample_entries, out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            # Same entries -> same hash in dir name
            hash1 = Path(snap1).name.split("-")[1]
            hash2 = Path(snap2).name.split("-")[1]
            assert hash1 == hash2

    def test_skips_entries_without_global_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [{"CanonicalLatin": "No ID"}]
            snap = write_snapshot(entries, out_root=tmpdir)
            yaml_files = list(Path(snap).glob("*.yaml"))
            assert len(yaml_files) == 0

    def test_updates_snapshot_index(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            write_snapshot(sample_entries, out_root=tmpdir)
            idx = Path(tmpdir) / "SNAPSHOT_INDEX.json"
            assert idx.exists()
            data = json.loads(idx.read_text())
            assert "latest" in data
            assert "run_hash" in data

    def test_volatile_keys_scrubbed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [{"GlobalID": "A" * 22, "ProcessedAt": "2025-01-01", "CanonicalLatin": "Test"}]
            snap = write_snapshot(entries, out_root=tmpdir)
            data = json.loads((Path(snap) / "entries.json").read_text())
            assert "ProcessedAt" not in data[0]


# ── diff_snapshots ───────────────────────────────────────────────────────


class TestDiffSnapshots:
    """Test snapshot diff generation."""

    def test_diff_added_entries(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot([sample_entries[0]], out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            summary = diff_snapshots(snap1, snap2)
            assert summary["added"] == 1
            assert summary["removed"] == 0

    def test_diff_removed_entries(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot(sample_entries, out_root=tmpdir + "/a")
            snap2 = write_snapshot([sample_entries[0]], out_root=tmpdir + "/b")
            summary = diff_snapshots(snap1, snap2)
            assert summary["removed"] == 1
            assert summary["added"] == 0

    def test_diff_identical(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot(sample_entries, out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            summary = diff_snapshots(snap1, snap2)
            assert summary["added"] == 0
            assert summary["removed"] == 0
            assert summary["modified"] == 0

    def test_diff_creates_html(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot([sample_entries[0]], out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            diff_snapshots(snap1, snap2)
            diff_dir = Path(snap2) / "diff"
            assert (diff_dir / "index.html").exists()


# ── generate_sql_changelog ───────────────────────────────────────────────


class TestSQLChangelog:
    """Test SQL changelog generation."""

    def test_generates_sql(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot([sample_entries[0]], out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            sql_path = generate_sql_changelog(snap1, snap2)
            assert Path(sql_path).exists()
            content = Path(sql_path).read_text()
            assert "INSERT INTO gmnap_changelog" in content
            assert "INSERT" in content  # New entry


# ── generate_cypher_changelog ────────────────────────────────────────────


class TestCypherChangelog:
    """Test Cypher changelog generation."""

    def test_generates_cypher(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot([sample_entries[0]], out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            cypher_path = generate_cypher_changelog(snap1, snap2)
            assert Path(cypher_path).exists()
            content = Path(cypher_path).read_text()
            assert "MERGE" in content or "MATCH" in content
            assert "Mathematician" in content

    def test_cypher_insert(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot([], out_root=tmpdir + "/a")
            snap2 = write_snapshot(sample_entries, out_root=tmpdir + "/b")
            cypher_path = generate_cypher_changelog(snap1, snap2)
            content = Path(cypher_path).read_text()
            assert "INSERT" in content

    def test_cypher_delete(self, sample_entries):
        with tempfile.TemporaryDirectory() as tmpdir:
            snap1 = write_snapshot(sample_entries, out_root=tmpdir + "/a")
            snap2 = write_snapshot([], out_root=tmpdir + "/b")
            cypher_path = generate_cypher_changelog(snap1, snap2)
            content = Path(cypher_path).read_text()
            assert "DELETE" in content
