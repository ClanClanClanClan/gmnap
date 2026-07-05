"""Stage 2 must copy the split geo/name-origin + diaspora fields onto entries.

Spec §2/§3: every record carries both axes (geo_region / name_region), the
group, the resolution level, and the diaspora conflict flag — not just the
collapsed region_code. RegionDetectionResult computed all of these, but the
stage-2 boundary dropped them (only DetectedRegion/Confidence/Method were
copied). Regression for MASTERPLAN §3.4 (R47).
"""

import asyncio

import pytest

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


def _run(entries):
    return asyncio.run(V7Pipeline(mode=PipelineMode.QUICK).process_batch(entries))


@pytest.mark.timeout(60)
def test_entries_carry_split_detection_fields():
    out = _run([{"CanonicalLatin": "Kowalski, Jan"}])
    e = out[0]
    # name-only entry: name axis populated, no geo signal -> no GeoRegion field
    assert e["DetectedRegion"] == "B2"
    assert e["NameRegion"] == "B2"
    assert e["GroupRegion"] == "SLAVIC_CENTRAL"
    assert e["ResolutionLevel"] == "leaf"
    assert e["RegionConflict"] is False
    assert "GeoRegion" not in e  # optional axis omitted when absent


@pytest.mark.timeout(60)
def test_diaspora_conflict_flag_tao_case():
    """The canonical diaspora case (ARCHITECTURE.md §1): Terence Tao —
    geo says Australia (A1), the name string says Chinese (E1), and the
    conflict flag must surface that divergence instead of hiding it."""
    out = _run([{"CanonicalLatin": "Tao, Terence", "CountryCodes": ["AU"]}])
    e = out[0]
    assert e["GeoRegion"] == "A1"
    assert e["NameRegion"] == "E1"
    assert e["RegionConflict"] is True


@pytest.mark.timeout(60)
def test_split_fields_are_deterministic():
    entries = [
        {"CanonicalLatin": "Kowalski, Jan"},
        {"CanonicalLatin": "Tao, Terence", "CountryCodes": ["AU"]},
        {"CanonicalLatin": "Müller, Hans", "CountryCodes": ["DE"]},
    ]
    fields = (
        "DetectedRegion",
        "GeoRegion",
        "NameRegion",
        "GroupRegion",
        "ResolutionLevel",
        "RegionConflict",
        "RegionCandidates",
    )
    a = [{k: e.get(k) for k in fields} for e in _run([dict(x) for x in entries])]
    b = [{k: e.get(k) for k in fields} for e in _run([dict(x) for x in entries])]
    assert a == b
