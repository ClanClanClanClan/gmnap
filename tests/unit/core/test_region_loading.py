"""Region loader smoke test (V7 manager, no pipeline).

Migrated 2026-05-01 from V6 (`src.core.pipeline_v6.GMNAPPipeline` with
`pipeline.region_manager`) to V7 (`src.regions.manager_optimized
.RegionManager`).
"""

import pytest

from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_region_loading() -> None:
    """All 37 regions load via the V7 manager."""
    manager = RegionManager()
    manager._ensure_regions_loaded()

    assert (
        len(manager._regions) == 37
    ), f"expected 37 regions, got {len(manager._regions)}"
    # Spot-check a representative selection across groups.
    for code in ("A1", "B1", "C2", "D1", "E1", "E4", "F2", "G1", "H1", "Z0"):
        assert code in manager._regions, f"missing region {code}"
        processor = manager._regions[code]
        assert hasattr(processor, "code") and processor.code == code
