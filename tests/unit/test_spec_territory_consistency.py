"""Spec §2 iso_territories <-> code territory map: the ruled cases (R51).

The 2026-07-06 §14 amendment reconciled spec and code (LT->C9 Baltic,
HU->A2, SS->F2 only, Norway quoted so it stops parsing as boolean False).
This guard keeps the two from drifting apart again on those territories.
"""

from pathlib import Path

import pytest
import yaml

from src.regions.base import get_region_for_territory

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.timeout(30)
def test_ruled_territories_match_spec():
    spec = yaml.safe_load((REPO / "docs" / "specs_v7_clean.yaml").read_text())
    spec_map = {}
    for group in spec["region_groups"]:
        for cc in group.get("iso_territories") or []:
            assert cc is not False, "unquoted 'NO' regressed to YAML boolean"
            spec_map[cc] = group["code"]
    for cc in ("LT", "HU", "SS", "NO", "LV", "EE"):
        assert spec_map.get(cc) == get_region_for_territory(cc), cc
    # each territory maps to exactly one group (SS was in two)
    assert spec_map["SS"] == "F2"
