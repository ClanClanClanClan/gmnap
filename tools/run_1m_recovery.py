#!/usr/bin/env python3
import asyncio
import json
import math
import os
import statistics
import time
from typing import Any, Dict, List

from src.ops.scale_guard_service import ScaleConfig, ScaleGuardService


def mk_entries(n: int) -> List[Dict[str, Any]]:
    return [
        {
            "ID": f"entry{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
            "SourceDatabase": "test",
        }
        for i in range(n)
    ]


async def run_1m(chunk: int = 1500, inflight: int = 4, N: int = 1_000_000):
    from src.core.pipeline_v7 import V7Pipeline

    svc = ScaleGuardService(
        lambda: V7Pipeline(), ScaleConfig(stream_chunk=chunk, inflight_chunks=inflight)
    )
    await svc.warmup()
    t0 = time.perf_counter()
    ok = 0
    err = 0
    # stream through the service using its internal streaming
    out = await svc.process(mk_entries(N))
    for r in out:
        if isinstance(r, dict):
            if r.get("status") == "processing_error" or r.get("Status") == "failed":
                err += 1
            else:
                ok += 1
        else:
            # Handle string results as errors
            err += 1
    dt = time.perf_counter() - t0
    eps = N / dt if dt > 0 else 0.0
    return {
        "processed": N,
        "ok": ok,
        "err": err,
        "eps": eps,
        "minutes_1m": (1_000_000 / eps) / 60.0 if eps > 0 else math.inf,
        "seconds": dt,
        "chunk": chunk,
        "inflight": inflight,
    }


async def main():
    chunk = int(os.getenv("CHUNK", "1500"))
    inflight = int(os.getenv("INFLIGHT", "4"))
    N = int(os.getenv("N", "1000000"))
    res = await run_1m(chunk, inflight, N)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
