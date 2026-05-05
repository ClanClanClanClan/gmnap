import pytest

from src.regions.manager_optimized import RegionManager

CASES = [
    ("Hartosh Singh Bal", "D1"),  # Hindi-belt
    ("Zhaosong Lu", "E1"),  # Chinese
    ("Minyoung Jeon", "E4"),  # Korean
    ("Indranil Biswas", "D3"),  # Bengali
    ("Phillip Griffiths", "A1"),  # Anglo
]


@pytest.mark.parametrize("name,expect", CASES)
def test_priority_rules_fix(name, expect):
    m = RegionManager()
    out = m.detect_region({"CanonicalLatin": name})
    assert out is not None, f"no result for {name}"
    assert out.region_code == expect, f"{name} -> {out.region_code}, expected {expect}"
    assert (
        0.60 <= out.confidence <= 0.95
    ), f"bad confidence for {name}: {out.confidence}"
    # Round-32: "surname" added to the allowed set. Korean "Jeon" now
    # gets a direct surname-exact hit before script-priority / ICU
    # ever look at it. The end region (E4) and confidence (0.95) are
    # the same; the *route* changed. Update the assertion to track
    # the routes the production detector actually emits, not the
    # historical priority-only path.
    assert out.detection_method in {
        "script-priority",
        "icu-priority",
        "surname",
    }
