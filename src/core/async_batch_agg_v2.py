from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Tuple

ProcessFunc = Callable[[List[dict]], Awaitable[List[dict]]]


@dataclass
class AggConfig:
    min_size: int = 24
    target_size: int = 96
    max_size: int = 256
    max_latency_ms: int = 20
    fastpath_threshold: int = 10
    max_concurrency: int = 1


class AsyncBatchAggregatorV2:
    def __init__(self, fn: ProcessFunc, cfg: AggConfig | None = None):
        self.fn = fn
        self.cfg = cfg or AggConfig()
        self.q: asyncio.Queue[Tuple[dict, asyncio.Future]] = asyncio.Queue()
        self.sem = asyncio.Semaphore(self.cfg.max_concurrency)
        self._closed = False
        self._worker = asyncio.create_task(
            self._loop(), name="AsyncBatchAggregatorV2._loop"
        )

    async def _loop(self):
        try:
            while True:
                e, fut = await self.q.get()
                batch = [e]
                futs = [fut]
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
            # Drain queue and fail outstanding futures
            while not self.q.empty():
                _, fut = self.q.get_nowait()
                if not fut.done():
                    fut.set_exception(asyncio.CancelledError())
            return

    async def submit(self, entries: List[dict]) -> List[dict]:
        if self._closed:
            raise RuntimeError("Aggregator is closed")
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

    async def aclose(self):
        if self._closed:
            return
        self._closed = True
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
        return False
