from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from src.core.compat.normalize_result import normalize_result


@dataclass
class StreamConfig:
    chunk: int = 2000
    inflight: int = 4
    soft_timeout_s: float = 120.0
    max_retries: int = 1
    retry_base_s: float = 0.25
    retry_jitter_s: float = 0.25


class StreamingExecutor:
    def __init__(
        self, fn: Callable[[List[dict]], Any], cfg: StreamConfig | None = None
    ):
        self.fn = fn
        self.cfg = cfg or StreamConfig()

    async def _call_once(self, chunk: List[dict]) -> List[dict]:
        try:
            res = self.fn(chunk)
            if asyncio.iscoroutine(res):
                res = await asyncio.wait_for(res, timeout=self.cfg.soft_timeout_s)
        except Exception as ex:
            return [
                {
                    "GlobalID": e.get("GlobalID"),
                    "status": "processing_error",
                    "error": str(ex),
                }
                for e in chunk
            ]
        rows, _ = normalize_result(res)
        return rows

    async def _call_with_retry(self, chunk: List[dict]) -> List[dict]:
        out = await self._call_once(chunk)
        if self.cfg.max_retries <= 0:
            return out
        fails = [e for e in out if e.get("status") == "processing_error"]
        if not fails:
            return out
        await asyncio.sleep(
            self.cfg.retry_base_s + random.random() * self.cfg.retry_jitter_s
        )
        retry_out = await self._call_once(fails)
        ridx = 0
        merged = []
        for e in out:
            if e.get("status") == "processing_error":
                r = retry_out[ridx] if ridx < len(retry_out) else e
                ridx += 1
                merged.append(r if r.get("status") != "processing_error" else e)
            else:
                merged.append(e)
        return merged

    async def run(self, entries: List[dict]) -> Tuple[List[dict], Dict[str, float]]:
        sem = asyncio.Semaphore(self.cfg.inflight)
        out = []
        t0 = time.perf_counter()

        async def worker(chunk):
            async with sem:
                out.extend(await self._call_with_retry(chunk))

        tasks = [
            asyncio.create_task(worker(entries[i : i + self.cfg.chunk]))
            for i in range(0, len(entries), self.cfg.chunk)
        ]
        await asyncio.gather(*tasks)
        dt = time.perf_counter() - t0
        eps = (len(entries) / dt) if dt > 0 else 0.0
        return out, {"seconds": dt, "eps": eps}
