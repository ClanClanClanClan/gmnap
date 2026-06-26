#!/usr/bin/env python3
import asyncio
import json
import time
from typing import Any, Dict, List

from src.diag.memdiff import MemDiff
from src.ops.streaming_executor import StreamConfig, StreamingExecutor
from src.quality.gates_streaming import StreamingGates


def mk(n: int) -> List[Dict[str, Any]]:
    return [
        {
            "GlobalID": f"rca{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
        }
        for i in range(n)
    ]


async def once(n: int):
    from src.core.pipeline_v7 import V7Pipeline

    p = V7Pipeline()
    await p.process_batch(mk(128))  # warm-up
    mem = MemDiff(top=15)
    before = mem.snapshot()
    ex = StreamingExecutor(p.process_batch, StreamConfig(chunk=1500, inflight=4))
    out, m = await ex.run(mk(n))
    after = mem.snapshot()
    memlines = mem.compare(before, after)
    g = StreamingGates()
    g.ingest(out)
    dec = g.decision(m["eps"])
    return {"n": n, "metrics": m, "gates": dec, "memdiff": memlines[:10]}


async def main():
    res10k = await once(10_000)
    res100k = await once(100_000)
    print(json.dumps({"10k": res10k, "100k": res100k}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
