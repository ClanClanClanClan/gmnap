#!/usr/bin/env python3
"""1M entry validation test for GMNAP V7 with expert streaming solution"""

import asyncio, os, time, json
from typing import List, Dict, Any
from src.quality.gates_rolling import RollingGates, GateLimits


def mk(n: int) -> List[Dict[str, Any]]:
    return [
        {"ID": f"entry{i:08d}", "CanonicalNative": "John Smith", "Region": "a1_anglo_sphere"}
        for i in range(n)
    ]


async def main():
    # Set optimal configuration
    os.environ.setdefault("GMNAP_STREAMING", "1")
    os.environ.setdefault("GMNAP_CHUNK", "2000")
    os.environ.setdefault("GMNAP_INFLIGHT", "4")
    os.environ.setdefault("GMNAP_STREAM_THRESHOLD", "10000")

    from src.core.pipeline_v7 import V7Pipeline
    from src.core.patch.pipeline_v7_integration_patch import enable_streaming_patch

    # Enable the streaming patch
    enable_streaming_patch(
        chunk=int(os.getenv("GMNAP_CHUNK")),
        inflight=int(os.getenv("GMNAP_INFLIGHT")),
        threshold=int(os.getenv("GMNAP_STREAM_THRESHOLD")),
        retries=1,
    )

    N = int(os.getenv("N", "1000000"))
    p = V7Pipeline()
    g = RollingGates(GateLimits(minutes_1m_max=35.0, min_success_rate=0.95))

    print(f"🚀 Running {N:,} entry validation with streaming patch...")

    t0 = time.perf_counter()
    out = await p.process_batch(mk(N))
    dt = time.perf_counter() - t0

    eps = N / dt if dt > 0 else 0.0
    g.ingest(out)
    dec = g.decision(eps)

    print(json.dumps({"N": N, "seconds": round(dt, 2), "eps": round(eps, 1), **dec}, indent=2))

    # Status message
    status = "✅ PASS" if dec["ok"] else "❌ FAIL"
    print(f"\n{status}: {dec['minutes_1m']:.1f} min/1M, {dec['success_rate']:.1%} success rate")


if __name__ == "__main__":
    asyncio.run(main())
