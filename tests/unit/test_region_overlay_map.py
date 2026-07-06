"""Spec §2a region overlay map — R55 wiring guard.

The spec defines 10 sub-national overlay codes (CH-FR, IN-WB, LK-TA, …)
that resolve to a MORE specific region than the country-level CC. Until
R55 the map existed only in docs/specs_v7_clean.yaml with zero code
references: the geo branch fed "IN-WB" to get_region_for_territory, got
R0 back, and silently dropped the geo signal.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.regions.base import REGION_OVERLAY_MAP, get_region_for_overlay
from src.regions.manager_optimized import RegionManager

# The full §2a contract, verbatim from docs/specs_v7_clean.yaml.
_SPEC_2A = {
    "CH-FR": "A2",
    "RU-NC": "C9",
    "AZ-IR": "C9",
    "IN-HN": "D1",
    "IN-SOUTH": "D2",
    "IN-WB": "D3",
    "LK-TA": "D2",
    "LK-SI": "D5",
    "TR-TRP": "D3",
    "AS-ASM": "D3",
}


def test_overlay_map_matches_spec_2a_exactly():
    assert REGION_OVERLAY_MAP == _SPEC_2A


def test_overlay_lookup_normalises():
    assert get_region_for_overlay("in-wb ") == "D3"
    assert get_region_for_overlay("XX-YY") is None


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


@pytest.mark.parametrize(
    "codes,want",
    [
        (["IN-WB"], "D3"),  # West Bengal -> Bengali, not the IN default D1
        (["IN-SOUTH"], "D2"),  # Dravidian south
        (["LK-TA"], "D2"),  # Sri Lanka Tamil, not the LK default D5
        (["RU-NC"], "C9"),  # North Caucasus, not the RU default B1
        (["IN", "IN-WB"], "D3"),  # overlay beats the bare CC in a mixed list
    ],
)
def test_overlay_codes_drive_geo_region(manager, codes, want):
    r = manager.detect_region({"CanonicalLatin": "Test, Person", "CountryCodes": codes})
    geo = getattr(r, "geo_region", None) or r.region_code
    assert geo == want, f"{codes} -> {geo}, wanted {want} ({r.detection_method})"


@pytest.mark.parametrize("codes,want", [(["IN"], "D1"), (["LK"], "D5")])
def test_plain_country_codes_unchanged(manager, codes, want):
    r = manager.detect_region({"CanonicalLatin": "Test, Person", "CountryCodes": codes})
    geo = getattr(r, "geo_region", None) or r.region_code
    assert geo == want
