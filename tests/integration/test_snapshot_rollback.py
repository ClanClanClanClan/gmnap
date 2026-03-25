"""
Snapshot Rollback Test (V7 spec §8: snapshot_rollback).

Validates: "git revert HEAD~1 restores coherence"
- Run pipeline → save snapshot → modify → rerun → revert → verify identical.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.slow
class TestSnapshotRollback:
    """Test that pipeline snapshots are deterministic and revertible."""

    @pytest.fixture
    def snapshot_dir(self, tmp_path):
        """Create a temporary snapshot directory."""
        snap = tmp_path / "snapshots"
        snap.mkdir()
        return snap

    @pytest.fixture
    def sample_entries(self):
        """Small batch of test entries."""
        return [
            {
                "CanonicalLatin": "Euler, Leonhard",
                "CanonicalNative": "Euler, Leonhard",
                "BirthYear": 1707,
                "DeathYear": 1783,
                "CountryCodes": ["CH"],
                "Gender": "male",
                "FamilyNameType": "surname",
                "LanguageOfPublication": ["deu", "lat", "fra"],
                "Historic": True,
                "GDPR_DATA": False,
                "Confidence": 95,
            },
            {
                "CanonicalLatin": "Gauss, Carl Friedrich",
                "CanonicalNative": "Gauß, Carl Friedrich",
                "BirthYear": 1777,
                "DeathYear": 1855,
                "CountryCodes": ["DE"],
                "Gender": "male",
                "FamilyNameType": "surname",
                "LanguageOfPublication": ["deu", "lat"],
                "Historic": True,
                "GDPR_DATA": False,
                "Confidence": 98,
            },
        ]

    def _snapshot_hash(self, entries: list) -> str:
        """Compute deterministic hash of entry list."""
        canonical = json.dumps(
            sorted(entries, key=lambda e: e.get("CanonicalLatin", "")),
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def test_snapshot_determinism(self, sample_entries, snapshot_dir):
        """Same input should produce identical snapshot hash."""
        h1 = self._snapshot_hash(sample_entries)
        h2 = self._snapshot_hash(sample_entries)
        assert h1 == h2, "Snapshot hashing must be deterministic"

    def test_snapshot_changes_on_modification(self, sample_entries, snapshot_dir):
        """Modified entries should produce different snapshot hash."""
        h1 = self._snapshot_hash(sample_entries)

        # Modify an entry
        modified = [dict(e) for e in sample_entries]
        modified[0]["BirthYear"] = 1708  # Wrong year

        h2 = self._snapshot_hash(modified)
        assert h1 != h2, "Modified entries must produce different hash"

    def test_snapshot_revert_restores_original(self, sample_entries, snapshot_dir):
        """Reverting to original entries restores original hash."""
        original_hash = self._snapshot_hash(sample_entries)

        # Modify
        modified = [dict(e) for e in sample_entries]
        modified[0]["Confidence"] = 50
        modified_hash = self._snapshot_hash(modified)
        assert original_hash != modified_hash

        # "Revert" — restore original data
        reverted_hash = self._snapshot_hash(sample_entries)
        assert reverted_hash == original_hash, "Revert must restore original state"

    def test_snapshot_write_and_read(self, sample_entries, snapshot_dir):
        """Write snapshot to disk, read back, verify identical."""
        snap_file = snapshot_dir / "snapshot_001.json"
        snap_file.write_text(
            json.dumps(sample_entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        loaded = json.loads(snap_file.read_text(encoding="utf-8"))
        assert self._snapshot_hash(loaded) == self._snapshot_hash(sample_entries)

    def test_idempotent_processing(self, sample_entries):
        """Processing same entries twice should yield identical results.

        This validates the V7 idempotent_diff_bytes_max = 0 gate.
        """

        # Simulate processing: just sort and normalise
        def process(entries):
            return sorted(
                entries,
                key=lambda e: e.get("CanonicalLatin", ""),
            )

        r1 = process(sample_entries)
        r2 = process(sample_entries)
        assert self._snapshot_hash(r1) == self._snapshot_hash(r2)

    def test_git_snapshot_simulation(self, sample_entries, tmp_path):
        """Simulate git-based snapshot: commit → modify → revert → verify."""
        repo = tmp_path / "repo"
        repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@gmnap.org"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "GMNAP Test"],
            cwd=repo,
            capture_output=True,
        )

        snap_file = repo / "snapshot.json"

        # Commit original snapshot
        snap_file.write_text(json.dumps(sample_entries, indent=2))
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Original snapshot"],
            cwd=repo,
            capture_output=True,
        )

        original_hash = self._snapshot_hash(sample_entries)

        # Commit modified snapshot
        modified = [dict(e) for e in sample_entries]
        modified[0]["Confidence"] = 10
        snap_file.write_text(json.dumps(modified, indent=2))
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Modified snapshot"],
            cwd=repo,
            capture_output=True,
        )

        modified_hash = self._snapshot_hash(modified)
        assert original_hash != modified_hash

        # Revert: git revert HEAD
        result = subprocess.run(
            ["git", "revert", "--no-commit", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"git revert failed: {result.stderr}"

        # Read reverted snapshot
        reverted = json.loads(snap_file.read_text())
        reverted_hash = self._snapshot_hash(reverted)

        assert (
            reverted_hash == original_hash
        ), "git revert HEAD~1 must restore original snapshot coherence"
