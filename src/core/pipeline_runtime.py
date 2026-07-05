"""Pipeline runtime support types, split out of pipeline_v7 (R45).

``get_cached_component`` + ``BatchAggregator`` (micro-batch coalescer and its
module singleton), ``PipelineMode`` (the spec §6 runtime profiles),
``V7QualityGates`` thresholds, and ``PipelineMetrics``. The orchestrator class
``V7Pipeline`` deliberately stays in ``src.core.pipeline_v7`` — it is one
cohesive 12-stage class, and CI tests monkeypatch its module globals
(e.g. ``genealogy_enrich_batch``), a contract a class move would break.
``pipeline_v7`` re-exports these names, so existing imports are unchanged.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.deterministic_mode import get_deterministic_mode

logger = logging.getLogger(__name__)


# Global cache for expensive initializations
_initialization_cache = {
    "region_manager": None,
    "unicode_normalizer": None,
    "schema_validator": None,
    "analytics": None,
}


def get_cached_component(component_name: str, factory_func):
    """Get or create cached component."""
    global _initialization_cache
    if _initialization_cache[component_name] is None:
        _initialization_cache[component_name] = factory_func()
    return _initialization_cache[component_name]


class BatchAggregator:
    """Aggregate small batches to improve performance."""

    def __init__(self, min_batch_size: int = 50):
        self.min_batch_size = min_batch_size
        self.pending_entries = []
        self.pending_futures = []
        self.aggregation_delay = 0.005  # 5ms delay to collect more entries (reduced for better responsiveness)
        self.accumulated_results = []
        self.accumulated_metrics = {
            "total_entries": 0,
            "processing_time": 0.0,
            "entries_per_second": 0.0,
        }

    async def add_batch(
        self, entries: List[Dict[str, Any]], process_func
    ) -> Dict[str, Any]:
        """Add entries to aggregator and process when threshold reached."""
        self.pending_entries.extend(entries)

        if len(self.pending_entries) >= self.min_batch_size:
            # Process immediately if we have enough
            batch = self.pending_entries[: self.min_batch_size]
            self.pending_entries = self.pending_entries[self.min_batch_size :]
            result = await process_func(batch)
            return self._handle_dict_result(result, len(entries))
        else:
            # Wait a bit for more entries
            await asyncio.sleep(self.aggregation_delay)
            if self.pending_entries:
                batch = self.pending_entries
                self.pending_entries = []
                result = await process_func(batch)
                return self._handle_dict_result(result, len(entries))
        # Return empty result structure if no processing happened
        return {
            "results": [],
            "metrics": {
                "total_entries": 0,
                "processing_time": 0,
                "entries_per_second": 0,
            },
        }

    def _handle_dict_result(
        self, result: Any, original_batch_size: int
    ) -> Dict[str, Any]:
        """Handle both dict and list return types from process_func."""
        if isinstance(result, dict):
            # Already in correct format
            return result
        elif isinstance(result, list):
            # Convert list to dict format
            return {
                "results": result[
                    :original_batch_size
                ],  # Return only the requested entries
                "metrics": {
                    "total_entries": len(result),
                    "processing_time": 0,
                    "entries_per_second": 0,
                },
            }
        else:
            # Unexpected type, return empty result
            logger.warning(f"Unexpected result type from process_func: {type(result)}")
            return {
                "results": [],
                "metrics": {
                    "total_entries": 0,
                    "processing_time": 0,
                    "entries_per_second": 0,
                },
            }


_batch_aggregator = BatchAggregator()


class PipelineMode(Enum):
    """V7 runtime profiles from spec."""

    QUICK = "quick"  # tier-0 APIs, 4 workers, ≤35 min/1M
    FULL = "full"  # tier-0+1 APIs, 8 workers, ≤70 min/1M
    EXTREME = "extreme"  # all tiers, 12 workers, no SLA


@dataclass
class V7QualityGates:
    """Quality gates from specs_v7.yaml section 7."""

    duplicate_global_id: int = 0
    duplicate_external_id_pct_max: float = 0.10  # Quick mode
    roundtrip_script_rate_min: float = 0.97
    genealogy_edge_conflict_pct_max: float = 2.0  # Quick mode
    graph_coherence_score_min: float = 0.85  # Quick mode
    peak_rss_gb_on_2M: int = 6
    warm_cache_runtime_per_1M_min: int = 35  # Quick mode minutes
    idempotent_diff_bytes_max: int = 0


class PipelineMetrics:
    """Metrics tracked during pipeline execution."""

    def __init__(self):
        self.total_entries: int = 0
        self.processed_entries: int = 0
        self.failed_entries: int = 0
        self.duplicate_global_ids: int = 0
        self.duplicate_external_ids: int = 0
        self.roundtrip_failures: int = 0
        self.graph_conflicts: int = 0
        # Stage-6 Bayesian/graph coherence score for the batch. None
        # until stage 6 runs. _check_quality_gates reads this; before it
        # was declared here, the gate's hasattr() check was always False
        # so the stage-6 threshold was never enforced (vacuous pass).
        self.stage6_score: Optional[float] = None
        self.memory_peak_mb: int = 0
        # R48 §3.3: stage-5 GenealogyRelation extraction + stage-6 cycle
        # rejection counts (feed the §7 genealogy_edge_conflict gate).
        self.genealogy_edges: int = 0
        self.genealogy_edge_conflicts: int = 0
        self.end_time: Optional[datetime] = None
        self.start_time: datetime = (
            get_deterministic_mode().get_timestamp()
            if get_deterministic_mode()
            and hasattr(get_deterministic_mode(), "get_timestamp")
            else datetime.now()
        )
        self.stage_timings: Dict[str, float] = {}

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of processed entries."""
        if self.total_entries == 0:
            return 0.0
        successful = self.processed_entries - self.failed_entries
        return (successful / self.total_entries) * 100.0  # Return as percentage

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        from datetime import datetime

        from src.core.deterministic_mode import get_deterministic_mode

        det_mode = get_deterministic_mode()
        current_time = det_mode.get_timestamp() if det_mode else datetime.now()
        return (current_time - self.start_time).total_seconds()

    @property
    def entries_per_second(self) -> float:
        duration = self.duration_seconds
        if duration > 0:
            return self.processed_entries / duration
        return 0

    @property
    def projected_time_per_million(self) -> float:
        """Project time to process 1M entries in minutes."""
        if self.entries_per_second > 0:
            return (1_000_000 / self.entries_per_second) / 60
        return float("inf")
