import gc
import time

import pytest

try:
    import psutil
except Exception:
    psutil = None


@pytest.mark.slow
@pytest.mark.timeout(15)
def test_memory_trend_smoke(pipeline_process, tiny_dataset):
    if psutil is None:
        pytest.skip("psutil not available")
    proc = psutil.Process()
    readings = []
    for _ in range(30):
        pipeline_process(list(tiny_dataset))
        gc.collect()
        readings.append(proc.memory_info().rss / (1024 * 1024))
        time.sleep(0.01)
    assert (max(readings) - min(readings)) < 300, "Memory increased too much"
