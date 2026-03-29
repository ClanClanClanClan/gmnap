from __future__ import annotations

import os
from typing import Any, Dict, List

from src.core.compat.normalize_result import normalize_result
from src.core.preflight_sanitiser import sanitise_entry
from src.ops.streaming_executor import StreamConfig, StreamingExecutor


def enable_streaming_patch(
    *, chunk: int = 1500, inflight: int = 4, threshold: int = 10_000, retries: int = 1
) -> None:
    """Enable streaming patch for V7Pipeline to force optimal performance"""
    from src.core.pipeline_v7 import V7Pipeline

    if getattr(V7Pipeline, "_gmnap_stream_patch_applied", False):
        return

    orig_process_batch = V7Pipeline.process_batch

    async def _stream_call(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        execu = StreamingExecutor(
            orig_process_batch.__get__(self, self.__class__),
            StreamConfig(chunk=chunk, inflight=inflight, max_retries=retries),
        )
        entries = [sanitise_entry(dict(e)) for e in entries]
        out, _ = await execu.run(entries)
        return out

    async def process_batch_patched(
        self, entries: List[Dict[str, Any]], *args, **kwargs
    ) -> List[Dict[str, Any]]:
        force = os.getenv("GMNAP_STREAMING", "0") == "1"
        n = len(entries) if hasattr(entries, "__len__") else 0

        if force or n >= threshold:
            return await _stream_call(self, entries)

        res = await orig_process_batch(self, entries, *args, **kwargs)
        norm, _ = normalize_result(res)
        return norm

    V7Pipeline.process_batch = process_batch_patched  # type: ignore
    V7Pipeline._gmnap_stream_patch_applied = True

    async def process_stream(self, entries: List[Dict[str, Any]]):
        return await _stream_call(self, entries)

    V7Pipeline.process_stream = process_stream  # type: ignore
