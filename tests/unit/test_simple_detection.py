"""Region detection smoke test (V7 manager, no pipeline).

Migrated 2026-05-01 from V6 (`src.core.pipeline_v6.GMNAPPipeline` with
`pipeline.region_manager`) to V7 (`src.regions.manager_optimized
.RegionManager`). The V6 pipeline imports were the last live caller
of `pipeline_v6.py`; with this migration plus the others in round 18,
the legacy pipeline can be deleted.
"""

import pytest

from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_simple_detection() -> None:
    """Smoke test: every test entry resolves to *some* region."""
    manager = RegionManager()

    test_entries = {
        "Newton, Isaac": {"CanonicalLatin": "Newton, Isaac"},
        "Wang, Xiaoming": {"CanonicalLatin": "Wang, Xiaoming"},
        "Chebyshev, Pafnuty": {"CanonicalLatin": "Chebyshev, Pafnuty"},
        "Gauss, Carl Friedrich": {"CanonicalLatin": "Gauss, Carl Friedrich"},
    }

    for name, entry in test_entries.items():
        result = manager.detect_region(entry)
        assert result.region_code, f"empty region_code for {name}"
        assert isinstance(result.confidence, float)
        assert isinstance(result.detection_method, str)
        assert isinstance(result.metadata, dict)
