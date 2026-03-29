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
    assert 0.60 <= out.confidence <= 0.95, f"bad confidence for {name}: {out.confidence}"
    assert out.detection_method in {"script-priority", "icu-priority"}  # ICU no longer hard-wins
