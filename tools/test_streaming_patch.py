#!/usr/bin/env python3
"""Quick streaming patch smoke test (1k→50k)"""
import asyncio, os, time, json
from typing import List, Dict, Any


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
    )

    p = V7Pipeline()

    # Warmup
    await p.process_batch(mk(128))

    print("🔥 Streaming Patch Smoke Test")
    print("=" * 40)

    for n in [1000, 5000, 10000, 50000]:
        print(f"Testing {n:>5,} entries... ", end="", flush=True)

        t0 = time.perf_counter()
        out = await p.process_batch(mk(n))
        dt = time.perf_counter() - t0

        eps = n / dt if dt > 0 else 0.0
        ok = sum(1 for r in out if r.get("status") != "processing_error")
        minutes_1m = (1_000_000 / eps) / 60.0 if eps > 0 else None

        status = "✅" if eps >= 400 else "⚠️" if eps >= 200 else "❌"
        print(f"{status} {eps:>6.0f} e/s ({minutes_1m:>4.1f}min/1M)")


if __name__ == "__main__":
    asyncio.run(main())
