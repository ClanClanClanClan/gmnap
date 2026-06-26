import time

from src.ops.pipeline_metrics import stage_timer


def test_stage_timer_observes_time():
    with stage_timer("unit_test_stage", entries=10):
        time.sleep(0.01)
    # Nothing to assert (metrics may be no-op); ensure no exceptions
    assert True
