import pytest

from src.core.pipeline_v7 import V7Pipeline


@pytest.mark.asyncio
async def test_pipeline_detects_romanised_asian():
    p = V7Pipeline()
    rows = [
        {"GlobalID": "T1", "CanonicalNative": "Hartosh Singh Bal"},
        {"GlobalID": "T2", "CanonicalNative": "Zhaosong Lu"},
        {"GlobalID": "T3", "CanonicalNative": "P. Griffiths"},
    ]
    out = await p.process_batch(rows)
    got = {r["GlobalID"]: r.get("DetectedRegion") for r in out}
    assert got["T1"].startswith("D1"), got
    assert got["T2"].startswith("E1"), got
    assert got["T3"].startswith("A1"), got
