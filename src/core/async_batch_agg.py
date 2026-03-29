from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, List

ProcessFunc = Callable[[List[dict]], Awaitable[List[dict]]]


@dataclass
class AggConfig:
    min_size: int = 32  # flush immediately if queue >= min_size
    target_size: int = 128  # try to coalesce to this size within latency budget
    max_size: int = 512  # hard cap per microbatch
    max_latency_ms: int = 30  # latency budget to reach target_size
    emergency_flush_ms: int = 100  # upper bound under continuous trickle
    max_concurrency: int = 1  # concurrent process_func calls
    fastpath_threshold: int = (
        10  # if submitted list <= this and queue empty -> direct call bypass
    )


@dataclass
class _Item:
    payload: dict
    fut: asyncio.Future


class AsyncBatchAggregator:
    """Concurrent micro‑batch aggregator with latency bound and adaptive coalescing.

    Usage:
        agg = AsyncBatchAggregator(process_func)
        results = await agg.add_batch(entries)  # preserves order
    """

    def __init__(self, process_func: ProcessFunc, cfg: AggConfig | None = None) -> None:
        self.process_func = process_func
        self.cfg = cfg or AggConfig()
        self._q: asyncio.Queue[_Item] | None = None
        self._closed = False
        self._workers: list[asyncio.Task] = []
        self._sem: asyncio.Semaphore | None = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Initialize async components when we're in an async context."""
        if not self._initialized:
            self._q = asyncio.Queue()
            self._sem = asyncio.Semaphore(self.cfg.max_concurrency)
            # Start one coalescer loop (additional loops don't help because we need global coalescing)
            self._workers.append(asyncio.create_task(self._coalesce_loop()))
            self._initialized = True

    async def add_batch(self, entries: List[dict]) -> List[dict]:
        """Submit a *caller batch* of entries; returns results in same order."""
        await self._ensure_initialized()
        if self._closed:
            raise RuntimeError("Aggregator closed")
        # Fast path: tiny batch and queue empty -> bypass queue/coalescer to avoid the extra hop
        if len(entries) <= self.cfg.fastpath_threshold and self._q.empty():
            async with self._sem:
                return await self.process_func(entries)

        futs: List[asyncio.Future] = []
        for e in entries:
            fut = asyncio.get_running_loop().create_future()
            await self._q.put(_Item(e, fut))
            futs.append(fut)
        # Await in the same order
        return [await f for f in futs]

    async def drain(self) -> None:
        """Wait until queue is empty and all tasks flushed."""
        if not self._initialized:
            return  # Nothing to drain if not initialized
        while not self._q.empty():
            await asyncio.sleep(0.005)
        # wait other in-flight workers
        for _ in range(self.cfg.max_concurrency):
            await asyncio.sleep(0)

    async def close(self) -> None:
        self._closed = True
        if self._initialized:
            for w in self._workers:
                w.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)

    async def _coalesce_loop(self) -> None:
        """Single loop that coalesces items under latency bounds and dispatches to process_func."""
        try:
            while True:
                item = await self._q.get()
                batch = [item.payload]
                futs = [item.fut]
                loop = asyncio.get_running_loop()
                t0 = loop.time()
                # Try to reach target_size within max_latency_ms
                while len(batch) < self.cfg.target_size:
                    timeout = (self.cfg.max_latency_ms / 1000) - (loop.time() - t0)
                    if timeout <= 0:
                        break
                    try:
                        nxt = await asyncio.wait_for(self._q.get(), timeout=timeout)
                        batch.append(nxt.payload)
                        futs.append(nxt.fut)
                        if len(batch) >= self.cfg.max_size:
                            break
                    except asyncio.TimeoutError:
                        break

                # Emergency trickle flush safeguard
                elapsed_ms = (loop.time() - t0) * 1000
                if (
                    len(batch) < self.cfg.min_size
                    and elapsed_ms < self.cfg.emergency_flush_ms
                ):
                    # try one more quick wait to grab any stragglers
                    timeout = max(
                        0.0, (self.cfg.emergency_flush_ms - elapsed_ms) / 1000
                    )
                    try:
                        while len(batch) < self.cfg.min_size:
                            nxt = await asyncio.wait_for(self._q.get(), timeout=timeout)
                            batch.append(nxt.payload)
                            futs.append(nxt.fut)
                            if len(batch) >= self.cfg.max_size:
                                break
                    except asyncio.TimeoutError:
                        pass

                # Process
                async with self._sem:
                    try:
                        results = await self.process_func(batch)
                    except Exception as e:
                        for f in futs:
                            if not f.done():
                                f.set_exception(e)
                    else:
                        # Map results 1:1; if misaligned, fill Nones
                        if not isinstance(results, list) or len(results) != len(futs):
                            results = [None] * len(futs)
                        for f, r in zip(futs, results):
                            if not f.done():
                                f.set_result(r)
        except asyncio.CancelledError:
            return
