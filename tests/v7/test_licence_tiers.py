"""Spec §10 licence_tiers (R50 — MASTERPLAN §5 'BUILD MISSING').

Every record with source provenance gets tagged with the MOST RESTRICTIVE
tier among its contributing sources: public_cc0 / redistributable_cc-by /
non-redistributable. Provenance = ``_sources_hit`` (sources that actually
returned data — newly tracked in enrich_by_tiers) or the legacy
``AuthoritySources`` dicts; the ``_sources`` queried-audit trail is NOT
used (it lists every attempted source and would over-restrict everything).
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline
from src.ops.licence_tiers import tier_for_source


def _run(batch):
    return asyncio.run(
        V7Pipeline(mode=PipelineMode.QUICK).process_batch([dict(e) for e in batch])
    )


@pytest.mark.timeout(30)
def test_spec_source_tier_mapping():
    assert tier_for_source("OpenAlex") == "public_cc0"  # CC0
    assert tier_for_source("HAL") == "redistributable_cc-by"  # CC-BY (U+2011)
    assert tier_for_source("zbMATH_Open") == "redistributable_cc-by"  # NBSP name
    assert tier_for_source("ProQuest_ETD") == "non-redistributable"  # Commercial
    assert tier_for_source("NeverHeardOfIt") == "non-redistributable"  # conservative


@pytest.mark.timeout(60)
def test_records_tagged_with_most_restrictive_contributing_tier():
    out = _run(
        [
            {"CanonicalLatin": "A, One", "_sources_hit": ["OpenAlex", "Crossref"]},
            {"CanonicalLatin": "B, Two", "_sources_hit": ["OpenAlex", "HAL"]},
            {
                "CanonicalLatin": "C, Three",
                "AuthoritySources": [{"source": "MathSciNet_HTML"}],
            },
            {"CanonicalLatin": "D, Four"},  # no provenance -> no tag
        ]
    )
    tiers = {e["CanonicalLatin"]: e.get("LicenceTier") for e in out}
    assert tiers["A, One"] == "public_cc0"
    assert tiers["B, Two"] == "redistributable_cc-by"
    assert tiers["C, Three"] == "non-redistributable"
    assert tiers["D, Four"] is None


@pytest.mark.timeout(60)
def test_queried_audit_trail_does_not_taint_tier():
    """_sources (queried, regardless of hit) must NOT drive the tier —
    an OFFLINE run queries all 9 live sources but none contribute."""
    out = _run(
        [{"CanonicalLatin": "E, Five", "_sources": ["MathSciNet_HTML", "OpenAlex"]}]
    )
    assert out[0].get("LicenceTier") is None
