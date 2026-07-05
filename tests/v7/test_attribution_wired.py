"""ATTRIBUTION.txt generation is wired + the spec actually loads (R48 §3.6).

Three stacked pre-existing breaks: (1) spec_loader searched only
non-existent root paths (specs_v7.yaml / v7.0.yaml) so every consumer
raised SpecError; (2) docs/specs_v7_clean.yaml itself did not PARSE as
YAML (5 prose lines with unquoted inner colons — mechanically quoted, no
semantic change); (3) attribution's CC-BY SPDX key/values carry U+2011
non-breaking hyphens — lookups are now normalised. Stage 10 writes
output/ATTRIBUTION.txt on every run (spec §10).
"""

import asyncio
from pathlib import Path

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.ops.attribution import generate_attribution_text
from src.ops.spec_loader import load_specs


@pytest.mark.timeout(30)
def test_spec_loads_and_is_the_v7_spec():
    specs = load_specs()
    assert str(specs.get("schema_version", "")).startswith("7")
    assert len(specs.get("authority_sources", [])) == 14


@pytest.mark.timeout(30)
def test_attribution_resolves_all_spdx_licences():
    text = generate_attribution_text()
    # every spec'd source appears, and the U+2011 CC‑BY values resolve
    assert text.count("CC0-1.0") == 5
    assert text.count("CC-BY-4.0") == 3
    assert "OpenAlex" in text and "HAL" in text and "zbMATH" in text
    assert "(SPDX: CC‑BY)" not in text  # no unresolved non-breaking-hyphen keys


@pytest.mark.timeout(60)
def test_stage_10_writes_attribution_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # spec_loader resolves relative to cwd; point it at the repo spec
    repo = Path(__file__).resolve().parents[2]
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "specs_v7_clean.yaml").write_text(
        (repo / "docs" / "specs_v7_clean.yaml").read_text()
    )
    asyncio.run(
        V7Pipeline(mode=PipelineMode.QUICK).process_batch(
            [{"CanonicalLatin": "Euler, Leonhard"}]
        )
    )
    out = tmp_path / "output" / "ATTRIBUTION.txt"
    assert out.exists()
    assert "ATTRIBUTION" in out.read_text()
