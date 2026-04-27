"""Tests for stage 9 write-and-diff functions."""

from __future__ import annotations

import json
import pathlib

from src.pipeline.stage9_write_and_diff import (
    generate_cypher_changelog,
    generate_sql_changelog,
    write_snapshot,
)


def _make_entries(count: int = 1) -> list[dict]:
    entries = []
    for i in range(count):
        entries.append(
            {
                "GlobalID": f"GID-{i:04d}",
                "CanonicalLatin": f"Author-{i}, Test",
                "UpdatedAt": "2026-01-15T00:00:00Z",
            }
        )
    return entries


class TestWriteSnapshot:
    def test_write_snapshot_creates_files(self, tmp_path, monkeypatch):
        """write_snapshot creates a directory with YAML files for each entry."""
        monkeypatch.setenv("OFFLINE", "1")
        monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

        entries = _make_entries(2)
        snap_dir = write_snapshot(entries, out_root=str(tmp_path / "yaml"))
        snap_path = pathlib.Path(snap_dir)

        assert snap_path.exists()
        yaml_files = list(snap_path.glob("*.yaml"))
        assert len(yaml_files) == 2, f"Expected 2 YAML files, found {len(yaml_files)}"

    def test_write_snapshot_creates_manifest(self, tmp_path, monkeypatch):
        """write_snapshot creates a MANIFEST.json containing run_hash."""
        monkeypatch.setenv("OFFLINE", "1")
        monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

        entries = _make_entries(1)
        snap_dir = write_snapshot(entries, out_root=str(tmp_path / "yaml"))
        manifest_path = pathlib.Path(snap_dir) / "MANIFEST.json"

        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "run_hash" in manifest
        assert isinstance(manifest["run_hash"], str)
        assert len(manifest["run_hash"]) > 0

    def test_snapshot_is_deterministic(self, tmp_path, monkeypatch):
        """Writing the same entries twice produces snapshots with the same content hash."""
        monkeypatch.setenv("OFFLINE", "1")
        monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

        entries = _make_entries(2)

        snap1 = write_snapshot(list(entries), out_root=str(tmp_path / "yaml"))
        snap2 = write_snapshot(list(entries), out_root=str(tmp_path / "yaml2"))

        # Both snapshots should use the same run_hash since entries are identical
        m1 = json.loads((pathlib.Path(snap1) / "MANIFEST.json").read_text())
        m2 = json.loads((pathlib.Path(snap2) / "MANIFEST.json").read_text())
        assert m1["run_hash"] == m2["run_hash"]

        # entries.json content should match
        e1 = (pathlib.Path(snap1) / "entries.json").read_text(encoding="utf-8")
        e2 = (pathlib.Path(snap2) / "entries.json").read_text(encoding="utf-8")
        assert e1 == e2


class TestChangelogs:
    def test_sql_changelog_produces_inserts(self, tmp_path, monkeypatch):
        """SQL changelog for new entries contains INSERT statements."""
        monkeypatch.setenv("OFFLINE", "1")
        monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

        # Write an empty previous snapshot, then a snapshot with one entry
        prev_dir = write_snapshot([], out_root=str(tmp_path / "prev"))
        curr_dir = write_snapshot(_make_entries(1), out_root=str(tmp_path / "curr"))

        sql_path = generate_sql_changelog(
            prev_dir,
            curr_dir,
            out_path=str(tmp_path / "changelog.sql"),
        )
        sql_content = pathlib.Path(sql_path).read_text(encoding="utf-8")
        assert (
            "INSERT" in sql_content
        ), f"Expected INSERT in SQL changelog:\n{sql_content}"

    def test_cypher_changelog_produces_merges(self, tmp_path, monkeypatch):
        """Cypher changelog for new entries contains MERGE statements."""
        monkeypatch.setenv("OFFLINE", "1")
        monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

        prev_dir = write_snapshot([], out_root=str(tmp_path / "prev"))
        curr_dir = write_snapshot(_make_entries(1), out_root=str(tmp_path / "curr"))

        cypher_path = generate_cypher_changelog(
            prev_dir,
            curr_dir,
            out_path=str(tmp_path / "changelog.cypher"),
        )
        cypher_content = pathlib.Path(cypher_path).read_text(encoding="utf-8")
        assert (
            "MERGE" in cypher_content
        ), f"Expected MERGE in Cypher changelog:\n{cypher_content}"
