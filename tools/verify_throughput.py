#!/usr/bin/env python3
import asyncio, json, os
from src.quality.rolling_gates import RollingGates, RollingLimits
from src.ops.scale_guard_service import ScaleGuardService, ScaleConfig


def mk(n):
    return [
        {
            "ID": f"entry{i:08d}",
            "CanonicalNative": "John Smith",
            "Region": "a1_anglo_sphere",
        }
        for i in range(n)
    ]


async def main():
    from src.core.pipeline_v7 import V7Pipeline

    chunk = int(os.getenv("CHUNK", "1500"))
    inflight = int(os.getenv("INFLIGHT", "4"))
    testN = int(os.getenv("TESTN", "100000"))
    svc = ScaleGuardService(
        lambda: V7Pipeline(), ScaleConfig(stream_chunk=chunk, inflight_chunks=inflight)
    )
    await svc.warmup()
    gates = RollingGates(RollingLimits(minutes_1m_max=35.0, min_success_rate=0.95))
    out = await svc.process(mk(testN))
    gates.ingest(out)
    eps = testN / max(
        1, float(os.getenv("SECONDS_OVERRIDE", "0")) or 1.0
    )  # place-holder if you time externally
    print(json.dumps(gates.decision(eps), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
