"""End-to-end integration test: run full V7 pipeline on fixture data."""
import asyncio
import json
import os
import pytest
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "region_test_data.json"


@pytest.fixture(autouse=True)
def offline_mode(monkeypatch):
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("PIPELINE_MODE", "quick")
    monkeypatch.setenv("GMNAP_SCHEMA_STRICT", "0")


def _load_sample_entries(n_per_region=2):
    """Load a small sample from each region for fast testing."""
    if not FIXTURE_PATH.exists():
        pytest.skip(f"Fixture file not found: {FIXTURE_PATH}")
    with open(FIXTURE_PATH) as f:
        data = json.load(f)
    entries = []
    for key, region_data in data.items():
        if key.startswith("_"):
            continue
        region_entries = region_data.get("entries", [])
        entries.extend(region_entries[:n_per_region])
    return entries


class TestE2EPipeline:
    def test_full_pipeline_on_fixtures(self):
        """Run the full V7 pipeline on sample fixture data and validate output."""
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        entries = _load_sample_entries(n_per_region=2)
        assert len(entries) >= 10, f"Expected at least 10 entries, got {len(entries)}"

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = asyncio.run(pipeline.process_batch(entries))

        # Report structure
        assert "entries" in report, "Report must contain 'entries' key"
        assert "metrics" in report, "Report must contain 'metrics' key"
        assert "quality_gates" in report, "Report must contain 'quality_gates' key"

        processed = report["entries"]
        assert len(processed) > 0, "Pipeline produced zero entries"

        # Every entry must have required fields
        for e in processed:
            assert "GlobalID" in e, f"Missing GlobalID in entry: {e.get('CanonicalLatin')}"
            assert "CanonicalLatin" in e, "Missing CanonicalLatin"
            assert "DetectedRegion" in e or "RegionCode" in e, "Missing region"

        # Metrics
        metrics = report["metrics"]
        assert metrics.get("schema_errors", 999) < len(processed), \
            "Too many schema errors"

    def test_pipeline_handles_single_entry(self):
        """Pipeline works with just one entry."""
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        entries = [{"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]}]
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = asyncio.run(pipeline.process_batch(entries))
        assert len(report["entries"]) == 1
        assert report["entries"][0]["CanonicalLatin"] == "Euler, Leonhard"

    def test_pipeline_handles_empty_batch(self):
        """Pipeline gracefully handles empty input."""
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        report = asyncio.run(pipeline.process_batch([]))
        assert report["entries"] == []
