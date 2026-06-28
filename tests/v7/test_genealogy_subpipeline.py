"""Regression guard: the in-batch genealogy sub-pipeline is importable
and is a genuine opt-in (not an accidental silent disable).

It was DEAD (R39): src/pipeline/stage4_authority_enrich.py imported
`AuthorityEnricher` (the class is `GenealogyAuthorityEnricher`), and
src/genealogy/authority_enricher.py hard-imported the absent `dateutil`.
Either failure made the pipeline's lazy genealogy import raise, so
_GENEALOGY_AVAILABLE was permanently False and the advisor-edge /
graph-populate block never ran — though docs claimed it did.
"""

import asyncio

import pytest


def test_genealogy_subpipeline_is_importable():
    import src.core.pipeline_v7 as pv
    from src.pipeline.stage4_authority_enrich import (  # noqa: F401
        GenealogyAuthorityEnricher,
        enrich_batch,
    )

    assert pv._GENEALOGY_AVAILABLE is True


@pytest.mark.timeout(60)
def test_genealogy_graph_block_is_opt_in(monkeypatch):
    """The genealogy graph block runs ONLY when GMNAP_GENEALOGY_GRAPH=1
    (default off keeps the 1M path lean / avoids Memgraph in default
    deploys)."""
    import src.core.pipeline_v7 as pv

    calls = {"n": 0}

    async def _fake_enrich(entries, offline=True):
        calls["n"] += 1
        return entries

    monkeypatch.setattr(pv, "genealogy_enrich_batch", _fake_enrich)

    entries = [
        {"CanonicalNative": f"Name{i}", "CanonicalLatin": f"Name{i}"}
        for i in range(30)  # >25 -> serial path that reaches the block
    ]

    # Default: flag unset -> block skipped.
    monkeypatch.delenv("GMNAP_GENEALOGY_GRAPH", raising=False)
    asyncio.run(
        pv.V7Pipeline(mode=pv.PipelineMode.QUICK).process_batch(
            [dict(e) for e in entries]
        )
    )
    assert calls["n"] == 0, "genealogy block ran without the opt-in flag"

    # Opt-in: flag on -> block runs (degrades gracefully without Memgraph).
    monkeypatch.setenv("GMNAP_GENEALOGY_GRAPH", "1")
    asyncio.run(
        pv.V7Pipeline(mode=pv.PipelineMode.QUICK).process_batch(
            [dict(e) for e in entries]
        )
    )
    assert calls["n"] >= 1, "genealogy block did not run with the opt-in flag"
