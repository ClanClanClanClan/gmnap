"""Integration tests for V7Pipeline across different modes."""
from __future__ import annotations

import asyncio

import pytest

from src.core.pipeline_v7 import V7Pipeline, PipelineMode


def _make_entry(name: str = "Euler, Leonhard", country: str = "CH") -> dict:
    return {"CanonicalLatin": name, "CountryCodes": [country]}


@pytest.mark.asyncio
async def test_quick_mode_processes(monkeypatch, tmp_path):
    """QUICK mode processes a single entry and returns a dict with 'entries' key."""
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")
    monkeypatch.setenv("OFFLINE", "1")

    pipeline = V7Pipeline(mode=PipelineMode.QUICK, output_dir=str(tmp_path / "out"))
    result = await pipeline.process_batch([_make_entry()])
    assert isinstance(result, dict)
    assert "entries" in result
    assert len(result["entries"]) >= 1


@pytest.mark.asyncio
async def test_all_modes_produce_valid_output(monkeypatch, tmp_path):
    """All three modes produce entries with GlobalID fields."""
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")
    monkeypatch.setenv("OFFLINE", "1")

    for mode in (PipelineMode.QUICK, PipelineMode.FULL, PipelineMode.EXTREME):
        out_dir = tmp_path / f"out_{mode.value}"
        pipeline = V7Pipeline(mode=mode, output_dir=str(out_dir))
        result = await pipeline.process_batch([_make_entry()])
        entries = result["entries"]
        assert len(entries) >= 1, f"Mode {mode.value} returned no entries"
        for entry in entries:
            assert "GlobalID" in entry, (
                f"Mode {mode.value}: entry missing GlobalID: {list(entry.keys())}"
            )


@pytest.mark.asyncio
async def test_deterministic_output(monkeypatch, tmp_path):
    """Processing the same entry twice produces the same GlobalID."""
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")
    monkeypatch.setenv("OFFLINE", "1")

    entry = _make_entry()

    pipeline1 = V7Pipeline(mode=PipelineMode.QUICK, output_dir=str(tmp_path / "run1"))
    result1 = await pipeline1.process_batch([dict(entry)])

    pipeline2 = V7Pipeline(mode=PipelineMode.QUICK, output_dir=str(tmp_path / "run2"))
    result2 = await pipeline2.process_batch([dict(entry)])

    gid1 = result1["entries"][0]["GlobalID"].split("--")[0]  # Strip collision suffix
    gid2 = result2["entries"][0]["GlobalID"].split("--")[0]
    assert gid1 == gid2, f"Base GlobalIDs differ: {gid1} vs {gid2}"


@pytest.mark.asyncio
async def test_quality_gates_in_output(monkeypatch, tmp_path):
    """Result has a quality_gates dict with a passed field."""
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")
    monkeypatch.setenv("OFFLINE", "1")

    pipeline = V7Pipeline(mode=PipelineMode.QUICK, output_dir=str(tmp_path / "out"))
    result = await pipeline.process_batch([_make_entry()])
    assert "quality_gates" in result
    assert "passed" in result["quality_gates"]
    assert isinstance(result["quality_gates"]["passed"], bool)
