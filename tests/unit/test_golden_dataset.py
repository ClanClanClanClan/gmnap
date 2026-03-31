"""Golden dataset validation -- 500 real mathematicians with verified ground truth."""

import json
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "golden_mathematicians.json"


@pytest.fixture(scope="module")
def golden_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manager():
    sys.path.insert(0, ".")
    from src.regions.manager_optimized import RegionManager

    return RegionManager()


def test_golden_dataset_has_500_entries(golden_data):
    assert len(golden_data) >= 500


def test_golden_dataset_covers_all_regions(golden_data):
    regions = {e["ExpectedRegion"] for e in golden_data}
    # At least 30 regions (some like H1/R0/Z0 may not have territory mappings)
    assert len(regions) >= 30, f"Only {len(regions)} regions: {sorted(regions)}"


@pytest.mark.parametrize("idx", range(500))
def test_golden_entry_detection(manager, golden_data, idx):
    if idx >= len(golden_data):
        pytest.skip("Not enough entries")
    entry = golden_data[idx]
    result = manager.detect_region(
        {
            "CanonicalLatin": entry["CanonicalLatin"],
            "CountryCodes": entry.get("CountryCodes", []),
        }
    )
    expected = entry["ExpectedRegion"]
    assert result.region_code == expected, (
        f'{entry["CanonicalLatin"]} (CC={entry.get("CountryCodes", ["?"])[0]}): '
        f"expected {expected}, got {result.region_code}"
    )


def test_golden_accuracy_gate(manager, golden_data):
    correct = 0
    for entry in golden_data:
        result = manager.detect_region(
            {
                "CanonicalLatin": entry["CanonicalLatin"],
                "CountryCodes": entry.get("CountryCodes", []),
            }
        )
        if result.region_code == entry["ExpectedRegion"]:
            correct += 1
    accuracy = correct / len(golden_data)
    assert (
        accuracy >= 0.99
    ), f"Golden accuracy {accuracy:.1%} < 99% ({correct}/{len(golden_data)})"
