import multiprocessing as mp
import threading
import time

import pytest


class SharedRegionStub:
    def __init__(self):
        self._cache = {}

    def process(self, entry):
        self._cache[entry["GlobalID"]] = time.time()
        return entry


@pytest.mark.slow
@pytest.mark.timeout(15)
def test_threaded_shared_state_smoke():
    region = SharedRegionStub()

    def worker(idx):
        for i in range(2000):
            region.process({"GlobalID": f"W{idx}-{i}"})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(region._cache) == 20 * 2000


def _proc_work(pipeline, items):
    return pipeline(items)


@pytest.mark.slow
@pytest.mark.timeout(15)
def test_multiprocess_pipeline_smoke(pipeline_process):
    items = [
        {
            "GlobalID": f"P{i}",
            "CanonicalLatin": "Test",
            "Field": "Mathematics",
            "Source": "Manual",
            "LastUpdated": "2024-01-01",
            "ValidationStatus": "verified",
        }
        for i in range(500)
    ]
    with mp.Pool(4) as pool:
        chunks = [items[i : i + 125] for i in range(0, len(items), 125)]
        results = pool.starmap(_proc_work, [(pipeline_process, c) for c in chunks])
    assert sum(len(r) for r in results) == 500
