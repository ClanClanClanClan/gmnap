"""
Integration tests for the full V7 pipeline.

Tests end-to-end processing through all 12 stages with realistic data.
"""

import asyncio
import json

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return loop.run_until_complete(coro)
    return asyncio.run(coro)


# ── Full Pipeline Integration ────────────────────────────────────────────


class TestFullPipelineIntegration:
    """Test full pipeline execution end-to-end."""

    def _sample_entries(self):
        return [
            {"CanonicalLatin": "Smith, John", "BirthYear": 1975},
            {"CanonicalLatin": "García, José María", "BirthYear": 1980},
            {"CanonicalLatin": "Wang, Wei", "BirthYear": 1970},
            {"CanonicalLatin": "Tanaka, Hiroshi", "BirthYear": 1965},
            {"CanonicalLatin": "Ivanov, Sergei Petrovich", "BirthYear": 1968},
        ]

    def test_quick_mode_end_to_end(self):
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(self._sample_entries()))
        assert report["mode"] == "quick"
        assert report["metrics"]["processed_entries"] == 5
        assert report["metrics"]["total_entries"] == 5
        assert "stage_timings" in report["metrics"]

    def test_full_mode_end_to_end(self):
        pipeline = V7Pipeline(mode=PipelineMode.FULL)
        report = _run(pipeline.process_batch(self._sample_entries()))
        assert report["mode"] == "full"
        assert report["metrics"]["processed_entries"] == 5

    def test_stage_timings_recorded(self):
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(self._sample_entries()))
        timings = report["metrics"]["stage_timings"]
        assert "1_ingest" in timings
        assert "1b_llm_etd" in timings
        assert "2_detect_region" in timings
        assert "3_region_hooks" in timings

    def test_quality_gates_in_report(self):
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(self._sample_entries()))
        qg = report["quality_gates"]
        assert "passed" in qg
        assert "limits" in qg

    def test_single_entry(self):
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch([{"CanonicalLatin": "Smith, John"}]))
        assert report["metrics"]["processed_entries"] == 1

    def test_empty_batch(self):
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch([]))
        assert report["metrics"]["processed_entries"] == 0

    def test_unicode_names(self):
        entries = [
            {"CanonicalLatin": "Müller, Hans-Jürgen"},
            {"CanonicalLatin": "Ñoño, María del Carmen"},
            {"CanonicalLatin": "O'Brien-Smith, Mary-Jane"},
        ]
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(entries))
        assert report["metrics"]["processed_entries"] == 3

    def test_chunked_processing(self):
        entries = [{"CanonicalLatin": f"Author-{i}, Test"} for i in range(20)]
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(entries, chunk_size=5))
        assert report["metrics"]["processed_entries"] == 20


# ── Multi-Region Integration ────────────────────────────────────────────


class TestMultiRegionIntegration:
    """Test pipeline with entries from many regions."""

    def test_mixed_regions(self):
        entries = [
            {"CanonicalLatin": "Smith, John"},
            {"CanonicalLatin": "Müller, Hans"},
            {"CanonicalLatin": "García, José"},
            {"CanonicalLatin": "Иванов, Иван"},
            {"CanonicalLatin": "田中, 太郎"},
            {"CanonicalLatin": "김, 철수"},
            {"CanonicalLatin": "Al-Rashid, Ahmad"},
            {"CanonicalLatin": "da Silva, Maria"},
        ]
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(entries))
        assert report["metrics"]["processed_entries"] == len(entries)
        assert report["metrics"]["failed_entries"] == 0


# ── GDPR Integration ────────────────────────────────────────────────────


class TestGDPRIntegration:
    """Test GDPR compliance in pipeline."""

    def test_gdpr_flag_set(self):
        import os

        os.environ["GMNAP_DROP_PERSONAL"] = "0"
        entries = [{"CanonicalLatin": "Smith, John", "BirthYear": 1975}]
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = _run(pipeline.process_batch(entries))
        assert report["metrics"]["processed_entries"] == 1
        os.environ.pop("GMNAP_DROP_PERSONAL", None)
