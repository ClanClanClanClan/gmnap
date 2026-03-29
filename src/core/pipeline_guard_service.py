from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from src.diag.flight_recorder import FlightRecorder

from .async_batch_agg_v2 import AggConfig, AsyncBatchAggregatorV2
from .preflight_sanitiser import sanitise_entry


@dataclass
class GuardConfig:
    min_size: int = 24
    target_size: int = 96
    max_latency_ms: int = 20
    warmup_entries: int = 64
    enable_region_fastpath: bool = True
    chunk_size_large: int = 2500  # autotuned sweet spot from your data
    inflight_chunks: int = 4  # streaming level for huge batches


class PipelineGuardService:
    def __init__(
        self,
        pipeline_ctor: Callable[[], Any],
        cfg: GuardConfig | None = None,
        recorder: FlightRecorder | None = None,
    ):
        self.cfg = cfg or GuardConfig()
        self.pipeline = pipeline_ctor()
        self.rec = recorder or FlightRecorder()
        self.agg = AsyncBatchAggregatorV2(
            self._process_impl,
            AggConfig(
                min_size=self.cfg.min_size,
                target_size=self.cfg.target_size,
                max_latency_ms=self.cfg.max_latency_ms,
            ),
        )
        self._warmed = False
        self._region_cache: Dict[str, Any] = {}

    async def warmup(self):
        if self._warmed:
            return
        warm = [
            {"GlobalID": f"W-{i}", "CanonicalNative": "김민수", "Region": "e4_korea"}
            for i in range(self.cfg.warmup_entries)
        ]
        async with self.rec.stage("warmup"):
            await self.pipeline.process_batch(warm)
        self._warmed = True

    async def process(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._warmed:
            await self.warmup()
        entries = [sanitise_entry(e.copy()) for e in entries]
        # Very large inputs: process via streaming chunks to avoid timeouts and memory cliffs
        if len(entries) >= 150_000:
            return await self._stream_large(entries)
        return await self.agg.submit(entries)

    async def _stream_large(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        chunk = self.cfg.chunk_size_large
        sem = asyncio.Semaphore(self.cfg.inflight_chunks)

        async def _run(part: List[Dict[str, Any]]):
            async with sem:
                res = await self._process_impl(part)
                out.extend(res)

        tasks = [
            asyncio.create_task(_run(entries[i : i + chunk]))
            for i in range(0, len(entries), chunk)
        ]
        await asyncio.gather(*tasks)
        return out

    async def _process_impl(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # Optional region fast-path
        if (
            self.cfg.enable_region_fastpath
            and entries
            and all(e.get("Region") == entries[0].get("Region") for e in entries)
        ):
            region = entries[0].get("Region")
            mgr = getattr(self.pipeline, "region_manager", None) or getattr(
                self.pipeline, "regions", None
            )
            if mgr:
                proc = self._region_cache.get(region)
                if proc is None:
                    proc = getattr(mgr, "get_processor", lambda r: None)(region)
                    if proc:
                        self._region_cache[region] = proc
                fn = getattr(self.pipeline, "process_batch_with_processor", None)
                if proc and callable(fn):
                    async with self.rec.stage(f"process_with_{region}"):
                        return await fn(entries, proc)

        # Default pipeline path with stage recorder
        async with self.rec.stage("process_batch"):
            try:
                res = await self.pipeline.process_batch(entries)
                return res
            except Exception as ex:
                # Convert hard crash into structured error entries for 0% success triage
                return [
                    {
                        "GlobalID": e.get("GlobalID"),
                        "status": "processing_error",
                        "error": str(ex),
                    }
                    for e in entries
                ]

    async def aclose(self):
        await self.agg.aclose()
