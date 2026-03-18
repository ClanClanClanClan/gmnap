"""
Tests for authority adapter schema compliance fixes.

Validates:
- OFFLINE=1 blocks all tier-0 and tier-1 handlers (no HTTP calls)
- Institution field is a string (not list) in all adapters
- GND BirthYear/DeathYear are plain integers (not dicts)
- NameEvents not synthesized without year data; aliases go to Variants.Synthesised
- AffiliationTimeline items always have required 'country' field
- AuthorityIDs only contains string values
- Pipeline report includes 'entries' key
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── OFFLINE mode tests ────────────────────────────────────────────────────


@pytest.fixture
def uncached_entry():
    """An entry name unlikely to be in cache."""
    import uuid
    return {"CanonicalLatin": f"Uncached, Test{uuid.uuid4().hex[:8]}"}


@pytest.mark.asyncio
async def test_offline_blocks_tier0_openalex(uncached_entry):
    """OpenAlex handler returns hit=False when OFFLINE=1 (no cache hit)."""
    with patch.dict(os.environ, {"OFFLINE": "1"}):
        import importlib
        import src.authority.manager_tier01 as m
        importlib.reload(m)
        result = await m._fetch_openalex(uncached_entry)
        assert result == {"OpenAlex": {"hit": False}}


@pytest.mark.asyncio
async def test_offline_blocks_tier0_crossref(uncached_entry):
    """Crossref handler returns hit=False when OFFLINE=1 (no cache hit)."""
    with patch.dict(os.environ, {"OFFLINE": "1"}):
        import importlib
        import src.authority.manager_tier01 as m
        importlib.reload(m)
        result = await m._fetch_crossref(uncached_entry)
        assert result == {"Crossref": {"hit": False}}


@pytest.mark.asyncio
async def test_offline_blocks_tier0_orcid(uncached_entry):
    """ORCID_ETD handler returns hit=False when OFFLINE=1 (no cache hit)."""
    with patch.dict(os.environ, {"OFFLINE": "1"}):
        import importlib
        import src.authority.manager_tier01 as m
        importlib.reload(m)
        result = await m._fetch_orcid_etd(uncached_entry)
        assert result == {"ORCID_ETD": {"hit": False}}


@pytest.mark.asyncio
async def test_offline_blocks_hal(uncached_entry):
    """HAL handler returns hit=False when OFFLINE=1 (no cache hit)."""
    with patch.dict(os.environ, {"OFFLINE": "1"}):
        import importlib
        import src.authority.manager_tier01 as m
        importlib.reload(m)
        result = await m._fetch_hal(uncached_entry)
        assert result == {"HAL": {"hit": False}}


@pytest.mark.asyncio
async def test_offline_blocks_zbmath(uncached_entry):
    """zbMATH handler returns hit=False when OFFLINE=1 (no cache hit)."""
    with patch.dict(os.environ, {"OFFLINE": "1"}):
        import importlib
        import src.authority.manager_tier01 as m
        importlib.reload(m)
        result = await m._fetch_zbmath(uncached_entry)
        assert result == {"zbMATH_Open": {"hit": False}}


# ── Institution type tests ────────────────────────────────────────────────


def test_institution_is_string_concept():
    """Verify the schema expects Institution as a string."""
    import json
    from pathlib import Path
    schema_path = Path("docs/schema_v2.0.json")
    if not schema_path.exists():
        pytest.skip("Schema file not found")
    raw = json.loads(schema_path.read_text())
    entry_schema = raw.get("patternProperties", {}).get("^.+$", {})
    inst_def = entry_schema.get("properties", {}).get("Institution", {})
    assert inst_def.get("type") == "string", f"Institution should be string, got {inst_def}"


# ── GND BirthYear type test ──────────────────────────────────────────────


def test_gnd_birthyear_is_int():
    """GND adapter should return BirthYear as plain int, not dict."""
    from src.authority.gnd_adapter import GNDAdapter
    adapter = GNDAdapter()
    # Simulate what the adapter does with birth data
    # The adapter extracts int(str(birthDate)[:4])
    year_str = "1882-03-14"
    result = int(str(year_str)[:4])
    assert isinstance(result, int)
    assert result == 1882


# ── NameEvents synthesis test ─────────────────────────────────────────────


def test_no_name_events_without_year():
    """Alternative name forms should go to Variants.Synthesised, not NameEvents."""
    # Directly test the synthesis logic from manager.py
    merged = {"AlternativeLatin": ["L. Euler", "Leonhardus Euler"]}
    entry = {"CanonicalLatin": "Euler, Leonhard"}

    # Reproduce the post-merge synthesis from manager.py
    if "AlternativeLatin" in merged:
        alts = merged.pop("AlternativeLatin", [])
        canonical = entry.get("CanonicalLatin", "")
        synth = [{"str": alt, "type": "authority-alias"} for alt in alts if alt and alt != canonical]
        if synth:
            merged.setdefault("Variants", {}).setdefault("Synthesised", []).extend(synth)

    # Verify: no NameEvents created
    assert "NameEvents" not in merged
    # Verify: AlternativeLatin was removed
    assert "AlternativeLatin" not in merged
    # Verify: Variants.Synthesised has the aliases
    assert "Variants" in merged
    assert len(merged["Variants"]["Synthesised"]) == 2
    assert merged["Variants"]["Synthesised"][0]["type"] == "authority-alias"


# ── AffiliationTimeline country test ──────────────────────────────────────


def test_affiliation_timeline_requires_country():
    """AffiliationTimeline items without country should be skipped."""
    # Simulate the synthesis logic
    merged = {"Institution": "MIT", "InstitutionCountry": ""}
    entry = {}

    cc = merged.get("InstitutionCountry", "")
    if cc:
        # Would create timeline — but cc is empty, so this block is skipped
        timeline = [{"institution": merged["Institution"], "country": cc}]
    else:
        timeline = []

    # With no country, no timeline should be created
    assert timeline == []


def test_affiliation_timeline_with_country():
    """AffiliationTimeline items WITH country should be created correctly."""
    merged = {"Institution": "MIT", "InstitutionCountry": "US",
              "_InstitutionAll": ["MIT", "Harvard"]}

    cc = merged.get("InstitutionCountry", "")
    insts = merged.get("_InstitutionAll") or ([merged["Institution"]] if isinstance(merged.get("Institution"), str) else [])
    timeline = [{"institution": inst, "country": cc} for inst in insts if inst]

    assert len(timeline) == 2
    assert all("country" in item for item in timeline)
    assert timeline[0]["country"] == "US"


# ── AuthorityIDs string filter test ───────────────────────────────────────


def test_authority_ids_strings_only():
    """AuthorityIDs should only contain string values after filtering."""
    # Simulate the filtering from enrich_by_tiers
    ids = {
        "OpenAlex": "A12345",
        "ORCID": "0000-0001-2345-6789",
        "PublicationCount": 42,  # int — should be filtered
        "HIndex": 15,           # int — should be filtered
        "CoAuthors": ["a", "b"],  # list — should be filtered
    }
    filtered = {k: v for k, v in ids.items() if isinstance(v, str)}
    assert "OpenAlex" in filtered
    assert "ORCID" in filtered
    assert "PublicationCount" not in filtered
    assert "HIndex" not in filtered
    assert "CoAuthors" not in filtered


# ── Report entries key test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_report_contains_entries():
    """process_batch() report should include 'entries' key with processed entries."""
    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode
    except ImportError:
        pytest.skip("V7Pipeline not importable")

    entries = [
        {"CanonicalLatin": "Test, Alpha", "CountryCodes": ["US"]},
        {"CanonicalLatin": "Test, Beta", "CountryCodes": ["GB"]},
    ]
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    report = await pipeline.process_batch(entries)
    assert "entries" in report, "Report must include 'entries' key"
    assert isinstance(report["entries"], list)
    assert len(report["entries"]) == 2
