#!/usr/bin/env python3
import asyncio, time, json, statistics, os
from typing import List, Dict
from src.core.pipeline_guard_service import PipelineGuardService, GuardConfig

SIZES = [
    int(x)
    for x in os.getenv(
        "SIZES",
        "10,25,50,75,100,150,200,250,300,400,500,750,1000,1500,2000,2500,3000,4000,5000,7500,10000,15000,20000,25000,30000,40000,50000,75000,100000",
    ).split(",")
]
ROUNDS = int(os.getenv("ROUNDS", "3"))


def mk(n: int) -> List[Dict]:
    return [
        {"ID": f"entry{i:08d}", "CanonicalNative": "John Smith", "Region": "a1_anglo_sphere"}
        for i in range(n)
    ]


async def once(svc, n: int) -> float:
    t0 = time.perf_counter()
    await svc.process(mk(n))
    return n / (time.perf_counter() - t0)


async def main():
    from src.core.pipeline_v7 import V7Pipeline

    svc = PipelineGuardService(lambda: V7Pipeline())
    await svc.warmup()
    results = {}
    for n in SIZES:
        vals = []
        for _ in range(ROUNDS):
            vals.append(await once(svc, n))
        results[n] = {
            "median_eps": statistics.median(vals),
            "p90_eps": statistics.quantiles(vals, n=10)[8],
            "runs": vals,
        }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
