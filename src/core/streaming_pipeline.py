from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterable, Awaitable, Callable, Dict, Iterable, List

from .async_batch_agg import AggConfig, AsyncBatchAggregator

AsyncBatch = AsyncIterable[List[dict]]
ProcessBatchFunc = Callable[[List[dict]], Awaitable[List[dict]]]
SinkFunc = Callable[[List[dict]], Awaitable[None]]


class StreamingPipelineAdapter:
    """Adapts an existing batch processor to stream arbitrarily large inputs with bounded memory.

    - Reads from an async iterator of entries (or wraps a sync iterator).
    - Uses AsyncBatchAggregator to micro-batch with latency cap.
    - Applies backpressure via a semaphore on in-flight microbatches.
    - Flushes partial results to a sink callback to keep memory flat.
    """

    def __init__(
        self,
        process_batch: ProcessBatchFunc,
        *,
        micro_cfg: AggConfig | None = None,
        inflight_limit: int = 4,
    ):
        self.process_batch = process_batch
        self.agg = AsyncBatchAggregator(process_batch, micro_cfg or AggConfig())
        self._sem = asyncio.Semaphore(inflight_limit)

    async def run_stream(
        self,
        it: Iterable[Dict[str, Any]] | AsyncIterable[Dict[str, Any]],
        sink: SinkFunc,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        processed = 0

        async def _submit_and_flush(buf: List[dict]):
            async with self._sem:
                res = await self.agg.add_batch(buf)
                await sink(res)

        # Support both sync and async iterables
        buf: List[dict] = []

        async def _aiter():
            if hasattr(it, "__aiter__"):
                async for x in it:
                    yield x
            else:
                for x in it:
                    yield x

        async for entry in _aiter():
            buf.append(entry)
            processed += 1
            if len(buf) >= 16:  # small handoff to aggregator; it will coalesce
                await _submit_and_flush(buf)
                buf = []
        if buf:
            await _submit_and_flush(buf)
        await self.agg.drain()
        elapsed = time.perf_counter() - start
        eps = processed / elapsed if elapsed > 0 else 0.0
        return {"processed": processed, "seconds": elapsed, "eps": eps}
