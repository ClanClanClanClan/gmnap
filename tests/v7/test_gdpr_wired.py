"""GDPR must actually run in the live pipeline (spec §10).

src/core/gdpr.py was complete and unit-tested but had ZERO live callers —
the pipeline never marked, scrubbed, masked, or honored --drop-personal
(MASTERPLAN §3.1). R47 wires gdpr_pipeline into process_batch after
enrichment, before the stage-9 write. GMNAP_DISABLE_GDPR=1 is the
kill-switch; GMNAP_DROP_PERSONAL=1 (set by the CLI's --drop-personal)
collapses to ShadowNodes.
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _batch():
    # 1 person born 1987 in a cohort of ONE -> decade masking must fire
    return [
        {
            "CanonicalLatin": "Kowalski, Jan",
            "BirthYear": 1987,
            "_sources": ["GoogleScholar", "OpenAlex"],
            "AuthoritySources": [
                {"source": "ProQuest", "id": "p1"},
                {"source": "OpenAlex", "id": "o1"},
            ],
        }
    ]


def _run(entries):
    return asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(entries))


@pytest.mark.timeout(60)
def test_gdpr_marks_scrubs_and_masks_in_live_pipeline():
    e = _run(_batch())[0]
    assert e.get("GDPR_DATA") is True, "GDPR_DATA marking did not run"
    assert e.get("BirthYear") == "1980s", "cohort<5 decade masking did not run"
    assert "GoogleScholar" not in e.get("_sources", []), "_sources not scrubbed"
    assert "ProQuest" not in [
        s.get("source") for s in e.get("AuthoritySources", [])
    ], "AuthoritySources dict-shape not scrubbed"
    assert any(
        s.get("source") == "OpenAlex" for s in e.get("AuthoritySources", [])
    ), "non-scrubbed sources must survive"


@pytest.mark.timeout(60)
def test_drop_personal_env_collapses_to_shadow_nodes(monkeypatch):
    """The CLI sets GMNAP_DROP_PERSONAL=1 for --drop-personal; the pipeline
    must honor it (the flag had been plumbed but dropped on the floor)."""
    monkeypatch.setenv("GMNAP_DROP_PERSONAL", "1")
    e = _run(_batch())[0]
    assert e.get("ShadowNode") is True
    assert "CanonicalLatin" not in e, "personal fields must be dropped"
    assert "BirthYear" not in e
    assert "GlobalID" in e and "ShadowHash" in e


@pytest.mark.timeout(60)
def test_gdpr_kill_switch(monkeypatch):
    monkeypatch.setenv("GMNAP_DISABLE_GDPR", "1")
    e = _run(_batch())[0]
    assert "GDPR_DATA" not in e
    assert e.get("BirthYear") == 1987  # unmasked when disabled
