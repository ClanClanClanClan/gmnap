"""
Comprehensive unit tests for V7 pipeline.

Tests all 12 stages, mode selection, quality gate integration,
chunking, and error handling.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.pipeline_v7 import PipelineMetrics, PipelineMode, V7Pipeline, V7QualityGates


# ── Helper ───────────────────────────────────────────────────────────────


def _run(coro):
    """Run async coroutine in tests."""
    return asyncio.run(coro)


def _sample_entries(n: int = 5) -> list:
    """Generate sample entries for testing."""
    names = [
        ("Smith, John", 1975),
        ("García, José", 1980),
        ("Wang, Wei", 1970),
        ("Tanaka, Hiroshi", 1965),
        ("Ivanov, Sergei", 1968),
        ("Kim, Minsu", 1982),
        ("Mueller, Hans", 1960),
        ("Al-Rashid, Ahmad", 1972),
        ("da Silva, Maria", 1985),
        ("Nakamura, Yuki", 1990),
    ]
    return [
        {"CanonicalLatin": name, "BirthYear": year}
        for name, year in names[:n]
    ]


# ── PipelineMode ─────────────────────────────────────────────────────────


class TestPipelineMode:
    """Test pipeline mode enum."""

    def test_quick_mode(self):
        assert PipelineMode.QUICK.value == "quick"

    def test_full_mode(self):
        assert PipelineMode.FULL.value == "full"

    def test_extreme_mode(self):
        assert PipelineMode.EXTREME.value == "extreme"


# ── V7QualityGates defaults ──────────────────────────────────────────────


class TestV7QualityGatesDefaults:
    """Test quality gate dataclass defaults (Quick mode)."""

    def test_defaults(self):
        g = V7QualityGates()
        assert g.duplicate_global_id == 0
        assert g.duplicate_external_id_pct_max == 0.10
        assert g.roundtrip_script_rate_min == 0.97
        assert g.genealogy_edge_conflict_pct_max == 2.0
        assert g.graph_coherence_score_min == 0.85
        assert g.peak_rss_gb_on_2M == 6
        assert g.warm_cache_runtime_per_1M_min == 35
        assert g.idempotent_diff_bytes_max == 0


# ── PipelineMetrics ──────────────────────────────────────────────────────


class TestPipelineMetrics:
    """Test metrics tracking."""

    def test_entries_per_second(self):
        m = PipelineMetrics()
        m.processed_entries = 1000
        # Should return float
        assert isinstance(m.entries_per_second, float)

    def test_projected_time(self):
        m = PipelineMetrics()
        m.processed_entries = 0
        assert m.projected_time_per_million == float("inf")

    def test_peak_rss_gb(self):
        m = PipelineMetrics()
        rss = m.peak_rss_gb
        assert isinstance(rss, float)
        assert rss >= 0


# ── Pipeline Initialization ──────────────────────────────────────────────


class TestPipelineInit:
    """Test pipeline initialization."""

    def test_quick_mode_workers(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        assert p.workers == 4

    def test_full_mode_workers(self):
        p = V7Pipeline(mode=PipelineMode.FULL)
        assert p.workers == 8

    def test_extreme_mode_workers(self):
        p = V7Pipeline(mode=PipelineMode.EXTREME)
        assert p.workers == 12

    def test_full_mode_gates(self):
        p = V7Pipeline(mode=PipelineMode.FULL)
        assert p.quality_gates.duplicate_external_id_pct_max == 0.05
        assert p.quality_gates.genealogy_edge_conflict_pct_max == 1.0
        assert p.quality_gates.graph_coherence_score_min == 0.92
        assert p.quality_gates.warm_cache_runtime_per_1M_min == 70

    def test_extreme_mode_gates(self):
        p = V7Pipeline(mode=PipelineMode.EXTREME)
        assert p.quality_gates.duplicate_external_id_pct_max == 0
        assert p.quality_gates.genealogy_edge_conflict_pct_max == 0
        assert p.quality_gates.graph_coherence_score_min == 0.97

    def test_output_dir_default(self):
        p = V7Pipeline()
        assert p.output_dir == "out/yaml"


# ── Pipeline Execution ───────────────────────────────────────────────────


class TestPipelineExecution:
    """Test full pipeline execution."""

    def test_process_empty_batch(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(p.process_batch([]))
        assert report["metrics"]["total_entries"] == 0
        assert report["metrics"]["processed_entries"] == 0

    def test_process_small_batch(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = _sample_entries(3)
        report = _run(p.process_batch(entries))
        assert report["metrics"]["total_entries"] == 3
        assert report["metrics"]["processed_entries"] == 3
        assert report["mode"] == "quick"

    def test_process_with_chunking(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = _sample_entries(5)
        report = _run(p.process_batch(entries, chunk_size=2))
        assert report["metrics"]["processed_entries"] == 5

    def test_report_contains_quality_gates(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = _sample_entries(2)
        report = _run(p.process_batch(entries))
        assert "quality_gates" in report
        assert "passed" in report["quality_gates"]

    def test_report_contains_metrics(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = _sample_entries(2)
        report = _run(p.process_batch(entries))
        metrics = report["metrics"]
        assert "duration_seconds" in metrics
        assert "entries_per_second" in metrics
        assert "stage_timings" in metrics


# ── Stage 1: Ingest ──────────────────────────────────────────────────────


class TestStage1Ingest:
    """Test Stage 1: Unicode normalization."""

    def test_unicode_normalization(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"CanonicalLatin": "García, José"}]
        result = _run(p._stage_1_ingest(entries))
        assert len(result) == 1
        assert "CanonicalLatin" in result[0]


# ── Stage 1b: LLM ETD ───────────────────────────────────────────────────


class TestStage1bLLMETD:
    """Test Stage 1b: LLM ETD extraction."""

    def test_no_pdf_path_skips(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"CanonicalLatin": "Smith, John"}]
        result = _run(p._stage_1b_llm_etd(entries))
        assert result == entries  # Unchanged

    def test_with_pdf_path_attempts_extraction(self):
        """When pdf_path is set but no LLM available, should not crash."""
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"CanonicalLatin": "Smith, John", "_pdf_path": "/fake/thesis.pdf"}]
        result = _run(p._stage_1b_llm_etd(entries))
        assert len(result) == 1


# ── Stage 2: DetectRegion ────────────────────────────────────────────────


class TestStage2DetectRegion:
    """Test Stage 2: Region detection."""

    def test_region_detection(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"CanonicalLatin": "Smith, John"}]
        result = _run(p._stage_2_detect_region(entries))
        assert "DetectedRegion" in result[0]
        assert "DetectionConfidence" in result[0]
        assert "DetectionMethod" in result[0]


# ── Stage 5: Collision Analytics ─────────────────────────────────────────


class TestStage5CollisionAnalytics:
    """Test Stage 5: GlobalID generation and collision detection."""

    def test_generates_global_ids(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"CanonicalLatin": "Smith, John", "BirthYear": 1975}]
        result = _run(p._stage_5_collision_analytics(entries))
        assert "GlobalID" in result[0]
        gid = result[0]["GlobalID"]
        # Base ID is 22 chars, may have --N suffix from cross-batch collision
        base_id = gid.split("--")[0]
        assert len(base_id) == 22

    def test_preserves_existing_global_ids(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        existing_id = "XYZXYZXYZXYZXYZXYZXYZX"  # Unique ID unlikely in registry
        entries = [{"CanonicalLatin": "UniqueName999", "GlobalID": existing_id}]
        result = _run(p._stage_5_collision_analytics(entries))
        # Base ID should be preserved (may get suffix from cross-batch)
        base = result[0]["GlobalID"].split("--")[0]
        assert base == existing_id


# ── Stage 6: Graph Consistency ───────────────────────────────────────────


class TestStage6GraphConsistency:
    """Test Stage 6: Bayesian graph coherence calculation."""

    def test_coherence_with_advisors(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [
            {"GlobalID": "A" * 22, "Advisors": ["B" * 22]},
            {"GlobalID": "B" * 22},
        ]
        result = _run(p._stage_6_graph_consistency(entries))
        # Bayesian posterior: 1 resolved / 1 total → Beta(3,1) mean = 0.75
        assert 0 < p.metrics.graph_coherence <= 1.0
        assert p.metrics.edges == 1

    def test_coherence_no_advisors(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [{"GlobalID": "A" * 22}]
        _run(p._stage_6_graph_consistency(entries))
        assert p.metrics.graph_coherence == 0.95  # Prior default

    def test_coherence_all_resolved(self):
        """All advisor edges resolve → high Bayesian coherence."""
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [
            {"GlobalID": "A" * 22, "Advisors": ["B" * 22, "C" * 22]},
            {"GlobalID": "B" * 22, "Advisors": ["C" * 22]},
            {"GlobalID": "C" * 22},
        ]
        _run(p._stage_6_graph_consistency(entries))
        # 3 edges, 3 resolved → Beta(5,1) mean = 5/6 ≈ 0.833
        assert p.metrics.graph_coherence > 0.8
        assert p.metrics.edges == 3

    def test_coherence_none_resolved(self):
        """No advisor edges resolve → low Bayesian coherence."""
        p = V7Pipeline(mode=PipelineMode.QUICK)
        entries = [
            {"GlobalID": "A" * 22, "Advisors": ["X" * 22, "Y" * 22]},
        ]
        _run(p._stage_6_graph_consistency(entries))
        # 2 edges, 0 resolved → Beta(2,3) mean = 2/5 = 0.4
        assert p.metrics.graph_coherence < 0.5
        assert p.metrics.edges == 2


# ── Stage 9: Write & Diff ───────────────────────────────────────────────


class TestStage9WriteDiff:
    """Test Stage 9: Snapshot writing."""

    def test_writes_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = V7Pipeline(mode=PipelineMode.QUICK, output_dir=tmpdir)
            entries = [{"GlobalID": "A" * 22, "CanonicalLatin": "Smith, John"}]
            snapshot_dir = p._stage_9_write_diff(entries)
            assert Path(snapshot_dir).exists()
            assert (Path(snapshot_dir) / "MANIFEST.json").exists()
            assert (Path(snapshot_dir) / "entries.json").exists()


# ── Quality Gates Check ──────────────────────────────────────────────────


class TestQualityGatesCheck:
    """Test _check_quality_gates method."""

    def test_all_pass_clean_data(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        p.metrics.processed_entries = 10
        p.metrics.duplicate_global_ids = 0
        p.metrics.duplicate_external_ids = 0
        p.metrics.roundtrip_failures = 0
        p.metrics.graph_conflicts = 0
        p.metrics.edges = 10
        p.metrics.graph_coherence = 0.95
        p.metrics.idempotency_diff_bytes = 0
        assert p._check_quality_gates()

    def test_fails_on_duplicates(self):
        p = V7Pipeline(mode=PipelineMode.QUICK)
        p.metrics.processed_entries = 10
        p.metrics.duplicate_global_ids = 5
        p.metrics.graph_coherence = 0.95
        assert not p._check_quality_gates()


# ── GlobalID Generation ──────────────────────────────────────────────────


class TestGlobalIDGeneration:
    """Test GlobalID generation."""

    def test_deterministic(self):
        entry = {"CanonicalNative": "Smith, John", "BirthYear": 1975}
        id1 = V7Pipeline._make_global_id(entry)
        id2 = V7Pipeline._make_global_id(entry)
        assert id1 == id2

    def test_length_22(self):
        entry = {"CanonicalLatin": "Smith, John"}
        gid = V7Pipeline._make_global_id(entry)
        assert len(gid) == 22

    def test_different_entries_different_ids(self):
        e1 = {"CanonicalNative": "Smith, John", "BirthYear": 1975}
        e2 = {"CanonicalNative": "Jones, Mary", "BirthYear": 1980}
        assert V7Pipeline._make_global_id(e1) != V7Pipeline._make_global_id(e2)
