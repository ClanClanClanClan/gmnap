"""SQLiteAnalytics — the drop-in stage-5 collision-analytics fallback that IS
the live path in any environment without duckdb — previously had zero tests
(MASTERPLAN §2b.4, R49).
"""

import pytest

from src.analytics.sqlite_analytics import SQLiteAnalytics


def _entry(gid, latin, native=None):
    return {
        "GlobalID": gid,
        "CanonicalLatin": latin,
        "CanonicalNative": native or latin,
    }


@pytest.mark.timeout(30)
def test_collision_analysis_detects_duplicates():
    entries = [
        _entry("g1", "Euler, Leonhard"),
        _entry("g2", "Euler, Leonhard"),  # same latin, different person-id
        _entry("g3", "Gauss, Carl Friedrich"),
    ]
    with SQLiteAnalytics() as a:
        report = a.analyze_collisions(entries)
    assert report["total_entries"] == 3
    assert report["total_collisions"] >= 1
    assert report["collision_types"]["canonical_latin_collision"] >= 1
    assert 0.0 < report["collision_rate"] <= 100.0


@pytest.mark.timeout(30)
def test_no_collisions_on_distinct_entries():
    entries = [
        _entry("g1", "Euler, Leonhard"),
        _entry("g2", "Gauss, Carl Friedrich"),
        _entry("g3", "Noether, Emmy"),
    ]
    with SQLiteAnalytics() as a:
        report = a.analyze_collisions(entries)
    assert report["total_collisions"] == 0
    assert report["collision_rate"] == 0.0


@pytest.mark.timeout(30)
def test_collision_rate_never_exceeds_100_pct():
    """Regression for the historical over-count: an entry colliding on
    latin+native+hash at once must count ONCE, keeping the rate <= 100%."""
    entries = [
        _entry("g1", "Same, Person", "Same, Person"),
        _entry("g2", "Same, Person", "Same, Person"),
        _entry("g3", "Same, Person", "Same, Person"),
    ]
    with SQLiteAnalytics() as a:
        report = a.analyze_collisions(entries)
    assert report["collision_rate"] <= 100.0
    assert report["total_collisions"] <= report["total_entries"]
