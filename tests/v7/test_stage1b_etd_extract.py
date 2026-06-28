"""Stage 1b (ETD/thesis extraction) is a tested OPT-IN activation (R39).

It was dormant: the class in src/pipeline/stage_1b_llm_extract.py was
non-importable (it imported a non-existent AIIntelligence /
ExtractionError) and was never wired into the literal stage loop.

The activation routes through the working, deterministic regex extractor
src.llm.stage1b_llmextract_etd.extract_from_text, runs ONCE before
chunking (so the >100k streaming 1:1 contract holds), is off by default,
and lets stage 1 assign canonical SHA-256 GlobalIDs to the new records
(no salted hash()).
"""

import asyncio
import re

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline

THESIS = (
    "title: On Prime Gaps\n"
    "author: Bernhard Riemann\n"
    "advisor: Carl Gauss\n"
    "institution: University of Gottingen\n"
    "degree date: 1851\n"
)


def _batch():
    return [
        {"CanonicalNative": "Euler, Leonhard", "CanonicalLatin": "Euler, Leonhard"},
        {"CanonicalNative": "Doc", "CanonicalLatin": "Doc", "ThesisText": THESIS},
    ]


@pytest.mark.timeout(60)
def test_stage1b_inert_by_default(monkeypatch):
    monkeypatch.delenv("GMNAP_ENABLE_LLM_EXTRACT", raising=False)
    out = asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(_batch()))
    assert len(out) == 2  # no extraction
    assert not any(e.get("Source") == "stage1b_etd_extract" for e in out)


@pytest.mark.timeout(60)
def test_stage1b_extracts_etd_record_when_enabled(monkeypatch):
    monkeypatch.setenv("GMNAP_ENABLE_LLM_EXTRACT", "1")
    out = asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(_batch()))
    assert len(out) == 3  # original 2 + 1 extracted ETD record
    etd = [e for e in out if e.get("Source") == "stage1b_etd_extract"]
    assert len(etd) == 1
    rec = etd[0]
    assert "Riemann" in rec["CanonicalLatin"]
    assert rec.get("Institution") == "University of Gottingen"
    # Canonical deterministic GID assigned by stage 1 — NOT the old
    # hash()-based gmnap_/etd_ synthetic id.
    assert re.match(r"[A-Z2-7]{22}(--\d+)?$", rec["GlobalID"])
    assert not rec["GlobalID"].startswith(("gmnap_", "etd_"))


@pytest.mark.timeout(60)
def test_stage1b_is_deterministic(monkeypatch):
    monkeypatch.setenv("GMNAP_ENABLE_LLM_EXTRACT", "1")
    a = asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(_batch()))
    b = asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(_batch()))
    assert [e["GlobalID"] for e in a] == [e["GlobalID"] for e in b]
