#!/usr/bin/env python3
import asyncio, json, sys
from src.core.pipeline_guard_service import PipelineGuardService, GuardConfig
from src.diag.flight_recorder import FlightRecorder


async def main():
    from src.core.pipeline_v7 import V7Pipeline

    svc = PipelineGuardService(
        lambda: V7Pipeline(), GuardConfig(), FlightRecorder("flight_canary.jsonl")
    )
    await svc.warmup()
    entry = {
        "ID": "entry00000001",
        "CanonicalNative": "John Smith",
        "Region": "a1_anglo_sphere",
        "SourceDatabase": "test",
        "Year": 2020,
    }
    out = await svc.process([entry])
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
