#!/usr/bin/env python3
import asyncio
import json
import os
import time
from typing import Dict, List

from src.core.pipeline_guard_service import GuardConfig, PipelineGuardService


def mk(n: int) -> List[Dict]:
    return [
        {
            "ID": f"entry{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
        }
        for i in range(n)
    ]


async def run(n: int):
    from src.core.pipeline_v7 import V7Pipeline

    svc = PipelineGuardService(lambda: V7Pipeline())
    await svc.warmup()
    t0 = time.perf_counter()
    out = await svc.process(mk(n))
    dt = time.perf_counter() - t0
    print(
        json.dumps(
            {
                "size": n,
                "eps": n / dt,
                "seconds": dt,
                "ok": sum(1 for r in out if r.get("status") != "processing_error"),
                "err": sum(1 for r in out if r.get("status") == "processing_error"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    import sys

    asyncio.run(run(int(sys.argv[1] if len(sys.argv) > 1 else 150000)))
