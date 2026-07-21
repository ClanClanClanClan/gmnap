"""R58: curated surname_exact YAML supplements (config/regions/<code>.yaml).

Exact-only entries at the surname tier's direct-match position, derived from
the adjudicated pilot ground truth. These tests pin the three safety
properties the adversarial judge demanded and a few flagship recoveries.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.regions.manager_optimized import RegionManager


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


def _detect(manager, name):
    return manager.detect_region({"CanonicalLatin": name})


@pytest.mark.parametrize(
    "name,leaf",
    [
        ("A. Réveillac", "A2"),
        ("D. Kršek", "B2"),
        ("N. Touzi", "C5"),  # Maghrebi (R58.7 taxonomy fix); ft wrong (A1@0.983)
        ("U. Cetin", "C1"),  # ft wrong at prob 1.00
        ("R. S. Hazra", "D3"),  # ft wrong at prob 1.00
        ("M. Nabil Kazi-Tani", "C5"),  # Algerian (R58.7); hyphenated cleaned form
        ("G. Bérczi", "A2"),  # Hungarian -> A2 (R58.7; H1 is "Historical")
        ("T. Furuya", "E3"),
    ],
)
def test_supplement_recovers_adjudicated_leaves(manager, name, leaf):
    r = _detect(manager, name)
    assert (r.region_code, r.detection_method) == (leaf, "surname"), (
        f"{name!r} -> {r.region_code} via {r.detection_method}; "
        f"adjudicated {leaf} via yaml supplement"
    )
    assert r.confidence >= 0.95


@pytest.mark.parametrize(
    "name,forbidden",
    [
        # Turkish given name 'Taha' must not fire c3.yaml's 'taha'
        # (Diaaeldin Taha) from the FIRST-token position.
        ("T. Güneş", "C3"),
        # Persian given name 'Mitra' must not fire d3.yaml's 'mitra'
        # (Siddharth Mitra) from the first-token position.
        ("Mitra Fatemi", "D3"),
    ],
)
def test_position_guard_blocks_given_name_misfires(manager, name, forbidden):
    r = _detect(manager, name)
    assert r.region_code != forbidden, (
        f"{name!r} -> {forbidden}: the supplement matched a GIVEN name at "
        f"parts[0] — the non-CJK position guard regressed"
    )


def test_pang_deliberately_excluded(manager):
    """'pang' is a common Korean surname; e1.yaml must not claim it."""
    r = _detect(manager, "Pang, Min-su")
    assert r.region_code != "E1"


def test_supplement_entries_are_exact_only(manager):
    """A supplement entry must never prefix/substring-fire: 'kuan' is in
    e1.yaml; a 'Kuang'-adjacent LONGER surname not in any list must not
    resolve via a partial match against the supplement."""
    r = _detect(manager, "Robert Kuanberg")
    assert not (
        r.detection_method == "surname"
        and r.region_code == "E1"
        and r.confidence < 0.95
    ), f"partial-match fired from a supplement entry: {r}"


def test_a2_particle_override_still_live(manager):
    """The R58 loader refactor must not break the pre-existing A2 particle
    merge (the first live YAML override, R53)."""
    from src.regions.base import load_region_yaml

    cfg = load_region_yaml("A2")
    assert "vom" in (cfg.get("germanic_particles") or []), (
        "a2.yaml germanic_particles no longer load — the load_region_yaml "
        "refactor broke the processor override path"
    )
    assert "surname_exact" in cfg  # both keys coexist in one file
