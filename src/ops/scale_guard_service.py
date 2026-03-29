from __future__ import annotations
import asyncio, os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

# ---- Minimal recorder (time/RSS only; no external deps) ----
try:
    import resource, psutil

    def _rss_mb() -> float:
        try:
            return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        except Exception:
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

except Exception:
    import resource

    def _rss_mb() -> float:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


@dataclass
class AggConfig:
    min_size: int = 24
    target_size: int = 96
    max_size: int = 256
    max_latency_ms: int = 20
    fastpath_threshold: int = 10
    max_concurrency: int = 1


class AsyncBatchAggregator:
    def __init__(self, fn, cfg: AggConfig):
        self.fn = fn
        self.cfg = cfg
        self.q: asyncio.Queue[Tuple[dict, asyncio.Future]] = asyncio.Queue()
        self.sem = asyncio.Semaphore(cfg.max_concurrency)
        self._closed = False
        self._worker = asyncio.create_task(self._loop(), name="ScaleAgg._loop")

    async def _loop(self):
        try:
            while True:
                e, f = await self.q.get()
                batch = [e]
                futs = [f]
                loop = asyncio.get_running_loop()
                t0 = loop.time()
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
                        for fu in futs:
                            if not fu.done():
                                fu.set_exception(ex)
                    else:
                        if not isinstance(res, list) or len(res) != len(futs):
                            res = [None] * len(futs)
                        for fu, r in zip(futs, res):
                            if not fu.done():
                                fu.set_result(r)
        except asyncio.CancelledError:
            while not self.q.empty():
                _, fu = self.q.get_nowait()
                if not fu.done():
                    fu.set_exception(asyncio.CancelledError())
            return

    async def submit(self, entries: List[dict]) -> List[dict]:
        if self._closed:
            raise RuntimeError("closed")
        if len(entries) <= self.cfg.fastpath_threshold and self.q.empty():
            async with self.sem:
                return await self.fn(entries)
        loop = asyncio.get_running_loop()
        futs = []
        for e in entries:
            fu = loop.create_future()
            futs.append(fu)
            await self.q.put((e, fu))
        return [await fu for fu in futs]

    async def aclose(self):
        if self._closed:
            return
        self._closed = True
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass


# ---- Preflight normalisation ----
_REGION_ALIAS = {"A1": "a1_anglo_sphere", "E4": "e4_korea"}


def sanitise_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    if "GlobalID" not in e and "ID" in e:
        e["GlobalID"] = e["ID"]
    if "Region" in e and e["Region"] in _REGION_ALIAS:
        e["Region"] = _REGION_ALIAS[e["Region"]]
    return e


@dataclass
class ScaleConfig:
    warmup_entries: int = 128
    micro: AggConfig = field(default_factory=AggConfig)
    uniform_region_fastpath: bool = True
    stream_chunk: int = 1500
    inflight_chunks: int = 4


class ScaleGuardService:
    """Self-contained wrapper that reuses one pipeline instance, micro-batches
    tiny inputs, fast-paths uniform-region batches, and streams very large inputs.
    """

    def __init__(
        self, pipeline_ctor: Callable[[], Any], cfg: ScaleConfig | None = None
    ):
        self.cfg = cfg or ScaleConfig()
        self.pipeline = pipeline_ctor()
        self.agg = AsyncBatchAggregator(self._process_impl, self.cfg.micro)
        self._warmed = False
        self._region_cache: Dict[str, Any] = {}

    async def warmup(self):
        if self._warmed:
            return
        warm = [
            {"GlobalID": f"W-{i}", "CanonicalNative": "김민수", "Region": "e4_korea"}
            for i in range(self.cfg.warmup_entries)
        ]
        await self.pipeline.process_batch(warm)
        self._warmed = True

    async def process(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._warmed:
            await self.warmup()
        entries = [sanitise_entry(dict(e)) for e in entries]
        if len(entries) >= 150_000:  # stream at scale to avoid cliffs
            return await self._stream(entries)
        return await self.agg.submit(entries)

    async def _stream(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        sem = asyncio.Semaphore(self.cfg.inflight_chunks)

        async def run(part: List[Dict[str, Any]]):
            async with sem:
                res = await self._process_impl(part)
                out.extend(res)

        tasks = [
            asyncio.create_task(run(entries[i : i + self.cfg.stream_chunk]))
            for i in range(0, len(entries), self.cfg.stream_chunk)
        ]
        await asyncio.gather(*tasks)
        return out

    async def _process_impl(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # uniform-region fast path
        if (
            self.cfg.uniform_region_fastpath
            and entries
            and all(e.get("Region") == entries[0].get("Region") for e in entries)
        ):
            r = entries[0].get("Region")
            mgr = getattr(self.pipeline, "region_manager", None) or getattr(
                self.pipeline, "regions", None
            )
            if mgr:
                proc = self._region_cache.get(r)
                if proc is None:
                    proc = getattr(mgr, "get_processor", lambda _r: None)(r)
                    if proc:
                        self._region_cache[r] = proc
                fast = getattr(self.pipeline, "process_batch_with_processor", None)
                if proc and callable(fast):
                    return await fast(entries, proc)
        # default
        try:
            return await self.pipeline.process_batch(entries)
        except Exception as ex:
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
