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
                {
                    "GlobalID": "A" * 22,
                    "CanonicalLatin": "Smith, John",
                    "BirthYear": 1975,
                },
            ]
            out1, _ = stage5_collision_analytics(entries1, workdir=workdir)
            assert out1[0]["GlobalID"] == "A" * 22

            # Second batch with same GlobalID
            entries2 = [
                {
                    "GlobalID": "A" * 22,
                    "CanonicalLatin": "Smith, John Jr",
                    "BirthYear": 1975,
                },
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


class TestSQLiteAnalyticsCollisionRate:
    """SQLiteAnalytics is the DuckDB-fallback drop-in used by the V7
    pipeline. Its reported collision_rate must be a real fraction."""

    def test_exact_duplicate_rate_not_over_100pct(self):
        """An exact duplicate trips the latin + native + hash checks, but
        the reported collision_rate must count it ONCE and stay <=100%.

        Regression (R38 audit): total_collisions = sum(collision_types)
        triple-counted each exact duplicate, so collision_rate could
        exceed 100% (e.g. 150% for two identical entries).
        """
        from src.analytics.sqlite_analytics import SQLiteAnalytics

        a = SQLiteAnalytics()
        e1 = {
            "GlobalID": "g1",
            "CanonicalLatin": "Euler, Leonhard",
            "CanonicalNative": "Euler, Leonhard",
        }
        e2 = {
            "GlobalID": "g2",
            "CanonicalLatin": "Euler, Leonhard",
            "CanonicalNative": "Euler, Leonhard",
        }
        res = a.analyze_collisions([e1, e2])
        assert res["total_entries"] == 2
        assert res["collision_rate"] <= 100.0
        assert res["total_collisions"] == 1  # the one duplicate, counted once
        # The per-dimension breakdown still records every event.
        assert res["collision_types"]["canonical_latin_collision"] == 1
        assert res["collision_types"]["hash_collision"] == 1

    def test_no_duplicates_zero_rate(self):
        from src.analytics.sqlite_analytics import SQLiteAnalytics

        a = SQLiteAnalytics()
        res = a.analyze_collisions(
            [
                {
                    "GlobalID": "g1",
                    "CanonicalLatin": "Euler, Leonhard",
                    "CanonicalNative": "Euler, Leonhard",
                },
                {
                    "GlobalID": "g2",
                    "CanonicalLatin": "Gauss, Carl",
                    "CanonicalNative": "Gauss, Carl",
                },
            ]
        )
        assert res["collision_rate"] == 0
        assert res["total_collisions"] == 0
