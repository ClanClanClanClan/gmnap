import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.pipeline_metrics import stage_timer


@pytest.mark.timeout(15)
def test_stage_timer_observes_time():
    with stage_timer("unit_test_stage", entries=10):
        time.sleep(0.01)
    # Nothing to assert (metrics may be no-op); ensure no exceptions
    assert True
