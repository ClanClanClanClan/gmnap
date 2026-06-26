from __future__ import annotations

from typing import Any, Callable, Dict, List

from src.core.sb_booster import BoosterAggConfig, BoosterConfig, PipelineService


def build_small_batch_service(
    pipeline_ctor: Callable[[], Any],
    *,
    min_size=24,
    target_size=96,
    max_latency_ms=20,
    warmup_min_entries=64,
    enable_region_fastpath=True,
) -> PipelineService:
    svc = PipelineService(
        pipeline_ctor,
        BoosterConfig(
            agg=BoosterAggConfig(
                min_size=min_size,
                target_size=target_size,
                max_latency_ms=max_latency_ms,
            ),
            warmup_min_entries=warmup_min_entries,
            enable_region_fastpath=enable_region_fastpath,
        ),
    )
    return svc


async def process_with_booster(
    service: PipelineService, entries: List[Dict]
) -> List[Dict]:
    return await service.process(entries)
