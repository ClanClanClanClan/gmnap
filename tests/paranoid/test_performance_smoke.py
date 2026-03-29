import pytest
import time, pytest


@pytest.mark.perf
@pytest.mark.timeout(15)
def test_small_throughput_smoke(pipeline_process):
    batch = [
        {
            "GlobalID": f"P{i}",
            "CanonicalLatin": "Test",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
        }
        for i in range(5000)
    ]
    t0 = time.perf_counter()
    out = pipeline_process(batch)
    dt = time.perf_counter() - t0
    eps = len(out) / dt if dt > 0 else float("inf")
    assert eps > 1000, f"Throughput too low: {eps:.1f} entries/s"
