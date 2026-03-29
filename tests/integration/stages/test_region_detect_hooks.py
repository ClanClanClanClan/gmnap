import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.pipeline.stage2_detect_region import stage2_detect_region

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage3_region_hooks import stage3_region_hooks


@pytest.mark.timeout(15)
def test_detect_a1_and_clean():
    batch = [{"CanonicalLatin": "Emmy Noether"}]
    b2 = stage2_detect_region(batch)
    assert b2[0]["DetectedRegion"] == "A1"
    b3 = stage3_region_hooks(b2)
    assert b3[0]["CanonicalLatin"].startswith("Noether, ")


@pytest.mark.timeout(15)
def test_detect_e1_pass_through():
    batch = [{"CanonicalNative": "陈景润", "CanonicalLatin": "Chen Jingrun"}]
    b2 = stage2_detect_region(batch)
    assert b2[0]["DetectedRegion"] == "E1"
    b3 = stage3_region_hooks(b2)
    assert b3[0]["CanonicalLatin"] == "Chen Jingrun"
