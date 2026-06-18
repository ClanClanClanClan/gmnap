#!/usr/bin/env python3
import asyncio, json, os

# Round 34: src/quality/rolling_gates.py was a near-duplicate of
# src/quality/gates_rolling.py (H5 backlog flagged ``RollingGates``).
# Consolidated to gates_rolling.py; aliasing GateLimits→RollingLimits
# keeps this call site working.
from src.ops.scale_guard_service import ScaleConfig, ScaleGuardService
from src.quality.gates_rolling import GateLimits as RollingLimits
from src.quality.gates_rolling import RollingGates


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
