from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

# Minimal internal aggregator (kept here for one-file import)
ProcessFunc = Callable[[List[dict]], Awaitable[List[dict]]]


@dataclass
class AggConfig:
    min_size: int = 24
    target_size: int = 96
    max_size: int = 256
    max_latency_ms: int = 20
    fastpath_threshold: int = 10
    max_concurrency: int = 1


class _AsyncAgg:
    def __init__(self, fn: ProcessFunc, cfg: AggConfig):
        self.fn = fn
        self.cfg = cfg
        self.q: asyncio.Queue[tuple[dict, asyncio.Future]] = asyncio.Queue()
        self.sem = asyncio.Semaphore(cfg.max_concurrency)
        self.worker = asyncio.create_task(self._loop())

    async def _loop(self):
        try:
            while True:
                e, fut = await self.q.get()
                batch = [e]
                futs = [fut]
                loop = asyncio.get_running_loop()
                t0 = loop.time()
                # Coalesce up to target_size within latency budget
                while len(batch) < self.cfg.target_size:
                    timeout = (self.cfg.max_latency_ms / 1000) - (loop.time() - t0)
                    if timeout <= 0:
                        break
                    try:
                        e2, f2 = await asyncio.wait_for(self.q.get(), timeout)
                        batch.append(e2)
                        futs.append(f2)
                        if len(batch) >= self.cfg.max_size:
                            break
                    except asyncio.TimeoutError:
                        break
                async with self.sem:
                    try:
                        res = await self.fn(batch)
                    except Exception as ex:
                        for f in futs:
                            if not f.done():
                                f.set_exception(ex)
                    else:
                        if not isinstance(res, list) or len(res) != len(futs):
                            res = [None] * len(futs)
                        for f, r in zip(futs, res):
                            if not f.done():
                                f.set_result(r)
        except asyncio.CancelledError:
            return

    async def submit(self, entries: List[dict]) -> List[dict]:
        if len(entries) <= self.cfg.fastpath_threshold and self.q.empty():
            async with self.sem:
                return await self.fn(entries)
        loop = asyncio.get_running_loop()
        futs = []
        for e in entries:
            fut = loop.create_future()
            futs.append(fut)
            await self.q.put((e, fut))
        return [await f for f in futs]


# ----------- Region fast-path helper ------------
def _uniform_region(entries: List[dict]) -> Optional[str]:
    if not entries:
        return None
    r0 = (
        entries[0].get("Region")
        or entries[0].get("region")
        or entries[0].get("RegionHint")
    )
    if not r0:
        return None
    for e in entries[1:]:
        if (e.get("Region") or e.get("region") or e.get("RegionHint")) != r0:
            return None
    return r0


@dataclass
class BoosterConfig:
    agg: AggConfig = field(default_factory=AggConfig)
    warmup_min_entries: int = 64
    enable_region_fastpath: bool = True


class PipelineService:
    """Holds a single V7Pipeline instance, reuses it across batches,
    applies microbatching for tiny caller batches, and skips region detection
    when a uniform Region is supplied for the entire batch.
    """

    def __init__(
        self, pipeline_ctor: Callable[[], Any], cfg: BoosterConfig | None = None
    ):
        self.cfg = cfg or BoosterConfig()
        self.pipeline = pipeline_ctor()
        # Async microbatch aggregator that targets ~20ms latency
        self.agg = _AsyncAgg(self._process_impl, self.cfg.agg)
        self._warmed = False
        self._region_cache: Dict[str, Any] = {}

    async def warmup(self):
        if self._warmed:
            return
        payload = [
            {"GlobalID": "WARMUP-0", "CanonicalNative": "김민수", "Region": "e4_korea"}
            for _ in range(self.cfg.warmup_min_entries)
        ]
        await self.pipeline.process_batch(payload)
        self._warmed = True

    async def process(self, entries: List[dict]) -> List[dict]:
        # One-shot bypass for very small batches before warmup
        if not self._warmed:
            await self.warmup()
        return await self.agg.submit(entries)

    async def _process_impl(self, entries: List[dict]) -> List[dict]:
        # Region fast-path: if uniform Region provided, pre-bind processor
        if self.cfg.enable_region_fastpath:
            uni = _uniform_region(entries)
            if uni:
                mgr = getattr(self.pipeline, "region_manager", None) or getattr(
                    self.pipeline, "regions", None
                )
                if mgr:
                    proc = self._region_cache.get(uni)
                    if proc is None:
                        proc = getattr(mgr, "get_processor", lambda r: None)(uni)
                        if proc:
                            self._region_cache[uni] = proc
                    if proc:
                        # fast path: call specialised internal method if available
                        fn = getattr(
                            self.pipeline, "process_batch_with_processor", None
                        )
                        if callable(fn):
                            return await fn(entries, proc)
        # default
        return await self.pipeline.process_batch(entries)
