"""
Unit tests for Stage 5: CollisionAnalytics.

Tests in-batch dedup, cross-batch collision tracking,
GlobalID suffixing, and edge CSV generation.
"""

import tempfile
from pathlib import Path


from src.pipeline.stage5_collision_analytics import (
    _load_registry,
    _save_registry,
    stage5_collision_analytics,
)


# ── In-Batch Dedup ───────────────────────────────────────────────────────


class TestInBatchDedup:
    """Test duplicate detection within a single batch."""

    def test_no_duplicates(self):
        entries = [
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
            {"GlobalID": "B" * 22, "CanonicalLatin": "Jones, Mary", "BirthYear": 1980},
        ]
        with tempfile.TemporaryDirectory() as workdir:
            out, metrics = stage5_collision_analytics(entries, workdir=workdir)
        assert len(out) == 2
        assert metrics["collisions"] == 0

    def test_with_duplicates(self):
        entries = [
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
        ]
        with tempfile.TemporaryDirectory() as workdir:
            out, metrics = stage5_collision_analytics(entries, workdir=workdir)
        assert len(out) == 2
        assert metrics["collisions"] >= 1
        # One should have suffix
        ids = [e["GlobalID"] for e in out]
        assert any("--" in gid for gid in ids)

    def test_suffix_format(self):
        entries = [
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
        ]
        with tempfile.TemporaryDirectory() as workdir:
            out, _ = stage5_collision_analytics(entries, workdir=workdir)
        suffixed = [e["GlobalID"] for e in out if "--" in e["GlobalID"]]
        for s in suffixed:
            assert s.startswith("A" * 22 + "--")


# ── Cross-Batch Collision ────────────────────────────────────────────────


class TestCrossBatchCollision:
    """Test cross-batch GlobalID collision detection."""

    def test_registry_persists(self):
        with tempfile.TemporaryDirectory() as workdir:
            ids = {"A" * 22, "B" * 22}
            _save_registry(workdir, ids)
            loaded = _load_registry(workdir)
            assert loaded == ids

    def test_empty_registry(self):
        with tempfile.TemporaryDirectory() as workdir:
            loaded = _load_registry(workdir)
            assert loaded == set()

    def test_cross_batch_detects_collision(self):
        with tempfile.TemporaryDirectory() as workdir:
            # First batch
            entries1 = [
                {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John", "BirthYear": 1975},
            ]
            out1, _ = stage5_collision_analytics(entries1, workdir=workdir)
            assert out1[0]["GlobalID"] == "A" * 22

            # Second batch with same GlobalID
            entries2 = [
                {"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John Jr", "BirthYear": 1975},
            ]
            out2, metrics2 = stage5_collision_analytics(entries2, workdir=workdir)
            # Should have been suffixed
            assert out2[0]["GlobalID"] != "A" * 22
            assert "--" in out2[0]["GlobalID"]


# ── Edge CSV ─────────────────────────────────────────────────────────────


class TestEdgeCSV:
    """Test genealogy edge CSV generation."""

    def test_edges_csv_created(self):
        entries = [
            {
                "GlobalID": "A" * 22,
                "CanonicalLatin": "Smith",
                "BirthYear": 1975,
                "Advisors": ["B" * 22],
            },
        ]
        with tempfile.TemporaryDirectory() as workdir:
            _, metrics = stage5_collision_analytics(entries, workdir=workdir)
            assert metrics["edges"] == 1
            csv = Path(workdir) / "stage5_edges.csv"
            assert csv.exists()
            lines = csv.read_text().splitlines()
            assert len(lines) == 2  # header + 1 edge

    def test_no_edges(self):
        entries = [
            {"GlobalID": "A" * 22, "CanonicalLatin": "Smith", "BirthYear": 1975},
        ]
        with tempfile.TemporaryDirectory() as workdir:
            _, metrics = stage5_collision_analytics(entries, workdir=workdir)
            assert metrics["edges"] == 0
