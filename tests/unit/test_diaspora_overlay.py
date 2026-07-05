"""Spec §3 diaspora overlay: era-scoped CC→region geo overrides (R49 §3.5).

config/diaspora.yaml loaded into _diaspora_config since Phase 2 but was never
READ — _detect_by_diaspora was a stub returning None. Now the geo branch
consults it first: the committed config maps TH pre-2015 → E6 and 2016- → A1.
Also guards the cache-key fix: geo is now ERA-dependent, so BirthYear must
participate in the detection cache key (era-distinct entries used to collide
in one slot and share a wrong geo).
"""

from pathlib import Path

import pytest

from src.regions.manager_optimized import RegionManager


def _detect(m, year):
    e = {"CanonicalLatin": "Suwannarat, Somchai", "CountryCodes": ["TH"]}
    if year is not None:
        e["BirthYear"] = year
    r = m.detect_region(e)
    return r if isinstance(r, dict) else r.__dict__


@pytest.mark.timeout(30)
def test_overlay_era_rules_drive_geo_axis():
    m = RegionManager(Path("./config"))
    assert _detect(m, 2010)["geo_region"] == "E6"  # "-2015" rule
    assert _detect(m, 2020)["geo_region"] == "A1"  # "2016-" rule


@pytest.mark.timeout(30)
def test_overlay_conflict_flag_when_geo_diverges_from_name():
    m = RegionManager(Path("./config"))
    d = _detect(m, 2020)
    assert d["geo_region"] == "A1"
    assert d["conflict"] is True  # name axis stays Thai (E6)


@pytest.mark.timeout(30)
def test_no_birthyear_falls_through_to_static_mapping():
    m = RegionManager(Path("./config"))
    d = _detect(m, None)
    assert d["geo_region"] == "E6"  # static TH territory mapping


@pytest.mark.timeout(30)
def test_cache_key_is_era_aware():
    """One shared manager, same name+CC, different eras — results must NOT
    collide in the detection cache (the key previously omitted BirthYear)."""
    m = RegionManager(Path("./config"))
    first = _detect(m, 2010)["geo_region"]
    second = _detect(m, 2020)["geo_region"]
    assert (first, second) == ("E6", "A1")


@pytest.mark.timeout(30)
def test_range_syntax_variants():
    contains = RegionManager._diaspora_range_contains
    assert contains("-2015", 2010) and not contains("-2015", 2016)
    assert contains("2016-", 2020) and not contains("2016-", 2015)
    assert contains("1980..2000", 1990)
    assert not contains("1980..2000", 2001)
    assert contains("..2015", 2015)  # inclusive bound, spec dot-syntax
