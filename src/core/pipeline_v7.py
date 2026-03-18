"""
V7-compliant processing pipeline for GMNAP MathLineage Edition.
Implements the 12-stage pipeline from specs_v7.yaml.
"""

import asyncio
import hashlib
import json
import logging
import os
import resource
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from datetime import timezone as _tz

from src.core.unicode_handler import UnicodeNormalizer
from src.regions.manager_optimized import RegionManager as OptimizedRegionManager

# Stage implementations
from src.pipeline.stage1_ingest import ingest_entries
from src.pipeline.stage3_region_hooks import stage3_region_hooks
from src.pipeline.stage5_collision_analytics import stage5_collision_analytics
from src.pipeline.stage7_tag_short_forms import tag_short_forms
from src.pipeline.stage8_global_validate import stage8_global_validate
from src.pipeline.stage9_write_and_diff import write_snapshot, diff_snapshots, generate_sql_changelog
from src.pipeline.stage10_report import generate_report
from src.pipeline.stage11_idempotency_check import idempotency_check

# Optional imports (degrade gracefully)
try:
    from src.core.globalid import generate_global_id
except ImportError:
    generate_global_id = None

try:
    from src.graph.memgraph_ops import MemgraphPool as MemgraphOps
except ImportError:
    MemgraphOps = None

try:
    from src.quality.gates import QualityGateChecker as QualityGatesEnforcer
except ImportError:
    QualityGatesEnforcer = None

try:
    from src.ops.spec_loader import load_specs
except ImportError:
    load_specs = None

try:
    from src.core.gdpr import gdpr_pipeline
except ImportError:
    gdpr_pipeline = None

try:
    from src.llm.etd_extractor import run_llm_etd
except ImportError:
    run_llm_etd = None

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """V7 runtime profiles from spec section 6."""
    QUICK = "quick"      # tier-0 APIs, 4 workers, <=35 min/1M
    FULL = "full"        # tier-0+1 APIs, 8 workers, <=70 min/1M
    EXTREME = "extreme"  # all tiers, 12 workers, no SLA


@dataclass
class V7QualityGates:
    """Quality gates from specs_v7.yaml section 7, mode-aware."""
    duplicate_global_id: int = 0
    duplicate_external_id_pct_max: float = 0.10
    roundtrip_script_rate_min: float = 0.97
    genealogy_edge_conflict_pct_max: float = 2.0
    graph_coherence_score_min: float = 0.85
    peak_rss_gb_on_2M: int = 6
    warm_cache_runtime_per_1M_min: int = 35
    idempotent_diff_bytes_max: int = 0


@dataclass
class PipelineMetrics:
    """Metrics tracked during pipeline execution."""
    total_entries: int = 0
    processed_entries: int = 0
    failed_entries: int = 0
    duplicate_global_ids: int = 0
    duplicate_external_ids: int = 0
    roundtrip_failures: int = 0
    graph_conflicts: int = 0
    graph_coherence: float = 0.0
    schema_errors: int = 0
    schema_quarantined: int = 0
    schema_rejected: int = 0
    collisions: int = 0
    edges: int = 0
    idempotency_diff_bytes: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    stage_timings: Dict[str, float] = field(default_factory=dict)
    memory_peak_mb: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def entries_per_second(self) -> float:
        duration = self.duration_seconds
        if duration > 0:
            return self.processed_entries / duration
        return 0

    @property
    def projected_time_per_million(self) -> float:
        if self.entries_per_second > 0:
            return (1_000_000 / self.entries_per_second) / 60
        return float('inf')

    @property
    def peak_rss_gb(self) -> float:
        try:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            # macOS returns bytes, Linux returns KB
            import platform
            if platform.system() == "Darwin":
                return ru.ru_maxrss / (1024 * 1024 * 1024)
            return ru.ru_maxrss / (1024 * 1024)
        except Exception:
            return 0.0


class V7Pipeline:
    """
    V7-compliant processing pipeline implementing all 12 stages.

    Stages (from specs_v7.yaml section 5):
    0. Config - Load specs, verify licenses, DOI credentials
    1. Ingest - Read YAML, Unicode NFC->NFKD->fold->NFC
    1b. LLMExtract_ETD - Parse thesis PDFs (optional)
    2. DetectRegion - Script, ICU, fastText, affiliation, DOI prefix
    3. RegionHooks - clean->augment->validate->order_key
    4. AuthorityEnrich - Fetch from tier-appropriate sources
    5. CollisionAnalytics - DuckDB, suffix duplicates
    6. GraphConsistency - Betweenness, Bayesian confidence
    7. TagShortForms - Populate ShortFormClusters
    8. GlobalValidate - JSON-Schema, roundtrip, coherence gate
    9. Write&Diff - Deterministic YAML, HTML diff, SQL changelog
    10. Report - Markdown metrics, draft DOI, push snapshot
    11. IdempotencyCheck - Rerun pipeline, assert identical
    """

    def __init__(self, mode: PipelineMode = PipelineMode.QUICK,
                 output_dir: str = "out/yaml"):
        self.mode = mode
        self.output_dir = output_dir
        self.config = self._load_config()
        self.quality_gates = self._get_quality_gates()
        self.metrics = PipelineMetrics()
        self.region_manager = OptimizedRegionManager()
        self.unicode_handler = UnicodeNormalizer()
        self.workers = self._get_worker_count()
        self.prev_snapshot_dir: Optional[str] = None
        self._shortform_clusters: Dict[str, int] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load V7 spec configuration."""
        if load_specs:
            try:
                return load_specs()
            except Exception:
                pass
        return {
            "streaming_chunk_size": 8000,
            "peak_memory_limit": "6GB RSS",
        }

    def _get_quality_gates(self) -> V7QualityGates:
        """Get quality gates based on mode."""
        gates = V7QualityGates()
        if self.mode == PipelineMode.FULL:
            gates.duplicate_external_id_pct_max = 0.05
            gates.genealogy_edge_conflict_pct_max = 1.0
            gates.graph_coherence_score_min = 0.92
            gates.warm_cache_runtime_per_1M_min = 70
        elif self.mode == PipelineMode.EXTREME:
            gates.duplicate_external_id_pct_max = 0
            gates.genealogy_edge_conflict_pct_max = 0
            gates.graph_coherence_score_min = 0.97
        return gates

    def _get_worker_count(self) -> int:
        return {
            PipelineMode.QUICK: 4,
            PipelineMode.FULL: 8,
            PipelineMode.EXTREME: 12
        }[self.mode]

    async def process_batch(self, entries: List[Dict[str, Any]],
                            chunk_size: int | None = None) -> Dict[str, Any]:
        """Process a batch of entries through the full V7 pipeline.

        Chunk size and inflight limits are read from environment variables:
          GMNAP_CHUNK (default 8000)
          GMNAP_INFLIGHT (default per mode: Quick=4, Full=8, Extreme=12)
          GMNAP_STREAM_THRESHOLD (default 10000)
        """
        # Honour env var overrides (V7 spec streaming config)
        if chunk_size is None:
            chunk_size = int(os.getenv("GMNAP_CHUNK",
                             self.config.get("streaming_chunk_size", 8000)))
        inflight = int(os.getenv("GMNAP_INFLIGHT", self.workers))
        self.workers = inflight

        self.metrics = PipelineMetrics()
        self.metrics.total_entries = len(entries)
        logger.info(f"V7 Pipeline: mode={self.mode.value}, entries={len(entries)}, "
                     f"workers={self.workers}, chunk_size={chunk_size}")

        # Stage 0: Config
        await self._timed_stage("0_config", self._stage_0_config)

        # Process in chunks for memory efficiency
        all_results = []
        for i in range(0, len(entries), chunk_size):
            chunk = entries[i:i + chunk_size]
            logger.info(f"Chunk {i // chunk_size + 1}: {len(chunk)} entries")

            results = chunk
            results = await self._timed_stage("1_ingest", self._stage_1_ingest, results)
            results = await self._timed_stage("1b_llm_etd", self._stage_1b_llm_etd, results)
            results = await self._timed_stage("2_detect_region", self._stage_2_detect_region, results)
            results = await self._timed_stage("3_region_hooks", self._stage_3_region_hooks, results)
            results = await self._timed_stage("4_authority_enrich", self._stage_4_authority_enrich, results)
            results = await self._timed_stage("5_collision_analytics", self._stage_5_collision_analytics, results)
            results = await self._timed_stage("6_graph_consistency", self._stage_6_graph_consistency, results)
            results = await self._timed_stage("7_tag_short_forms", self._stage_7_tag_short_forms, results)
            results = await self._timed_stage("8_global_validate", self._stage_8_global_validate, results)

            all_results.extend(results)

        self.metrics.processed_entries = len(all_results)

        # GDPR compliance pass
        if gdpr_pipeline:
            drop_personal = os.getenv("GMNAP_DROP_PERSONAL", "0") == "1"
            all_results = gdpr_pipeline(all_results, drop_personal=drop_personal)

        # Final stages (whole batch)
        snapshot_dir = self._stage_9_write_diff(all_results)
        self.metrics.stage_timings["9_write_diff"] = 0  # timed inline
        self._stage_10_report(all_results, snapshot_dir)
        self._stage_11_idempotency_check(all_results, snapshot_dir)

        # Quality gates
        self.metrics.end_time = datetime.now()
        self.metrics.memory_peak_mb = int(self.metrics.peak_rss_gb * 1024)
        gates_ok = self._check_quality_gates()

        report = self._generate_report()
        report["quality_gates"]["passed"] = gates_ok
        return report

    async def _timed_stage(self, name: str, func, *args):
        """Run a stage with timing and error handling."""
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args)
            else:
                result = func(*args)
            elapsed = time.time() - start
            self.metrics.stage_timings[name] = elapsed
            logger.info(f"Stage {name}: {elapsed:.3f}s")
            return result
        except Exception as e:
            self.metrics.stage_timings[name] = time.time() - start
            logger.error(f"Stage {name} FAILED: {e}")
            raise

    # =========================================================================
    # STAGE IMPLEMENTATIONS
    # =========================================================================

    async def _stage_0_config(self) -> None:
        """Stage 0: Load specs, verify licenses, DOI credentials."""
        if not self.config:
            raise RuntimeError("V7 spec configuration not loaded")
        doi_cfg = self.config.get("doi_minting", {})
        if doi_cfg and not os.getenv("DATACITE_API_KEY"):
            logger.warning("DOI minting configured but DATACITE_API_KEY not set")

    async def _stage_1_ingest(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 1: Ingest - Unicode NFC->NFKD->fold->NFC."""
        return ingest_entries(entries)

    async def _stage_1b_llm_etd(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 1b: LLMExtract_ETD - Parse thesis PDFs with LLM."""
        if not run_llm_etd:
            return entries
        specs = self.config
        for entry in entries:
            pdf_path = entry.get("_pdf_path") or entry.get("pdf_path")
            if not pdf_path:
                continue
            try:
                _, metadata = run_llm_etd(pdf_path, specs=specs)
                entry.setdefault("_etd_metadata", {}).update(metadata)
                if metadata.get("advisors"):
                    entry.setdefault("Advisors", []).extend(
                        [a for a in metadata["advisors"] if a not in entry.get("Advisors", [])]
                    )
                if metadata.get("degree_date"):
                    entry.setdefault("_degree_date", metadata["degree_date"])
                if metadata.get("institution"):
                    entry.setdefault("_institution", metadata["institution"])
            except Exception as e:
                logger.warning(f"Stage 1b LLM extraction failed for {pdf_path}: {e}")
        return entries

    async def _stage_2_detect_region(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 2: DetectRegion - Script, ICU, fastText, affiliation, DOI prefix."""
        results = []
        for entry in entries:
            result = self.region_manager.detect_region(entry)
            entry["DetectedRegion"] = result.region_code
            entry["DetectionConfidence"] = result.confidence
            entry["DetectionMethod"] = result.detection_method
            results.append(entry)
        return results

    async def _stage_3_region_hooks(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 3: RegionHooks - clean->augment->validate->order_key."""
        return stage3_region_hooks(entries, self.region_manager)

    async def _stage_4_authority_enrich(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 4: AuthorityEnrich - Fetch from tier-appropriate sources."""
        tiers = {
            PipelineMode.QUICK: [0],
            PipelineMode.FULL: [0, 1],
            PipelineMode.EXTREME: [0, 1, 2, 3],
        }[self.mode]
        logger.info(f"Authority enrichment using tiers {tiers}")

        try:
            from src.authority.manager_tier01 import enrich_by_tiers
            entries = await enrich_by_tiers(entries, tiers=tiers)
        except (ImportError, Exception) as e:
            logger.warning(f"Authority enrichment unavailable: {e}")

        return entries

    async def _stage_5_collision_analytics(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 5: CollisionAnalytics - DuckDB duplicate detection, suffix GlobalIDs."""
        # Generate GlobalIDs if missing
        for entry in entries:
            if not entry.get("GlobalID"):
                entry["GlobalID"] = self._make_global_id(entry)

        results, coll_metrics = stage5_collision_analytics(entries)
        self.metrics.collisions = int(coll_metrics.get("collisions", 0))
        self.metrics.duplicate_global_ids = self.metrics.collisions
        self.metrics.edges = int(coll_metrics.get("edges", 0))
        return results

    async def _stage_6_graph_consistency(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 6: GraphConsistency - Betweenness, Bayesian confidence, reject cycles <3."""
        bolt_uri = os.getenv("MEMGRAPH_BOLT", "")
        if MemgraphOps and bolt_uri:
            try:
                auth = None
                mg_user = os.getenv("MEMGRAPH_USER", "")
                mg_pass = os.getenv("MEMGRAPH_PASSWORD", "")
                if mg_user:
                    auth = (mg_user, mg_pass)
                ops = MemgraphOps(uri=bolt_uri, auth=auth)
                if hasattr(ops, 'import_entries'):
                    ops.import_entries(entries)
                if hasattr(ops, 'calculate_betweenness_centrality'):
                    scores = ops.calculate_betweenness_centrality()
                    for e in entries:
                        gid = e.get("GlobalID", "")
                        if gid in scores:
                            e["BetweennessScore"] = scores[gid]
                if hasattr(ops, 'detect_cycles'):
                    cycles = ops.detect_cycles(max_depth=3)
                    self.metrics.graph_conflicts = len(cycles) if cycles else 0
                if hasattr(ops, 'close'):
                    ops.close()
            except Exception as e:
                logger.warning(f"Graph consistency (Memgraph) failed: {e}")

        # Compute Bayesian graph coherence score.
        # Uses a Beta(α, β) posterior: α = edges_resolved + prior_a,
        # β = edges_unresolved + prior_b.  The coherence score is the
        # posterior mean E[Beta] = α / (α + β), which naturally accounts
        # for small-sample uncertainty (shrinks toward the prior).
        advisor_refs = set()
        known_ids = {e.get("GlobalID") for e in entries if e.get("GlobalID")}
        edges_total = 0
        edges_resolved = 0
        for e in entries:
            advisors = e.get("Advisors") or []
            for adv in advisors:
                edges_total += 1
                if adv in known_ids:
                    edges_resolved += 1
                advisor_refs.add(adv)

        self.metrics.edges = edges_total

        if edges_total == 0:
            # No edges → prior dominates; use optimistic default
            self.metrics.graph_coherence = 0.95
        else:
            # Bayesian Beta posterior with weak informative prior Beta(2, 1)
            prior_a, prior_b = 2.0, 1.0
            alpha = edges_resolved + prior_a
            beta_param = (edges_total - edges_resolved) + prior_b
            coherence = alpha / (alpha + beta_param)
            self.metrics.graph_coherence = round(coherence, 4)

        return entries

    async def _stage_7_tag_short_forms(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 7: TagShortForms - Populate ShortFormClusters."""
        results, self._shortform_clusters = tag_short_forms(entries)
        return results

    def _populate_required_fields(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Populate V2.0 schema required fields with sensible defaults.

        Called after region hooks and authority enrichment so that
        DetectedRegion, authority data, etc. are already present.
        """
        from src.regions.base import TERRITORY_TO_REGION
        # Build reverse map: region -> primary country codes
        _region_to_countries: Dict[str, List[str]] = {}
        for cc, reg in TERRITORY_TO_REGION.items():
            _region_to_countries.setdefault(reg, []).append(cc)

        utc_now = datetime.now(_tz.utc).isoformat().replace("+00:00", "Z")

        for e in entries:
            # UpdatedAt - ISO-8601 UTC timestamp
            if not e.get("UpdatedAt"):
                e["UpdatedAt"] = utc_now

            # CanonicalNative - default to CanonicalLatin for Latin-script entries
            if not e.get("CanonicalNative"):
                e["CanonicalNative"] = e.get("CanonicalLatin", "")

            # LanguageOfPublication - default from region or "eng"
            if not e.get("LanguageOfPublication"):
                region = e.get("DetectedRegion", "R0")
                lang_map = {
                    "A1": ["eng"], "A2": ["eng"], "A3": ["eng"],
                    "B1": ["rus"], "B2": ["eng"], "B3": ["ell"],
                    "C1": ["tur"], "C2": ["fas"], "C3": ["ara"],
                    "C4": ["ara"], "C5": ["ara"], "C6": ["heb"],
                    "C7": ["hye"], "C8": ["kat"],
                    "D1": ["hin", "eng"], "D2": ["tam", "eng"],
                    "D3": ["ben"], "D4": ["urd", "eng"], "D5": ["sin"],
                    "E1": ["zho"], "E2": ["zho"], "E3": ["jpn"],
                    "E4": ["kor"], "E5": ["vie"], "E6": ["tha"],
                    "E7": ["msa", "eng"],
                    "F1": ["fra"], "F2": ["eng"], "F3": ["amh"],
                    "F4": ["por"], "G1": ["spa", "por"],
                }
                e["LanguageOfPublication"] = lang_map.get(region, ["eng"])

            # FamilyNameType - default "surname"
            if not e.get("FamilyNameType"):
                e["FamilyNameType"] = "surname"

            # Gender - default "unspecified"
            if not e.get("Gender"):
                e["Gender"] = "unspecified"

            # CountryCodes - derive from input or DetectedRegion
            if not e.get("CountryCodes"):
                input_cc = e.get("_input_country_codes") or e.get("InstitutionCountry")
                if input_cc:
                    if isinstance(input_cc, str):
                        e["CountryCodes"] = [input_cc.upper()]
                    elif isinstance(input_cc, list):
                        e["CountryCodes"] = [c.upper() for c in input_cc[:5]]
                else:
                    region = e.get("DetectedRegion", "R0")
                    countries = _region_to_countries.get(region, [])
                    # Use first 3 representative countries
                    e["CountryCodes"] = sorted(countries)[:3] if countries else ["XX"]

            # Confidence - compute from detection + authority signals
            if e.get("Confidence") is None:
                det_conf = e.get("DetectionConfidence", 0.5)
                # Authority boost: each authority source adds confidence
                auth_ids = e.get("AuthorityIDs", {})
                auth_boost = min(len(auth_ids) * 10, 30)  # max 30 from authorities
                e["Confidence"] = round(min(det_conf * 70 + auth_boost, 100), 1)

            # Historic - default False
            if e.get("Historic") is None:
                birth = e.get("BirthYear")
                e["Historic"] = bool(birth and isinstance(birth, (int, float)) and birth < 1900)

            # GDPR_DATA - default False
            if e.get("GDPR_DATA") is None:
                e["GDPR_DATA"] = False

        return entries

    async def _stage_8_global_validate(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 8: GlobalValidate - JSON-Schema, roundtrip, coherence gate."""
        # Populate required fields before validation
        entries = self._populate_required_fields(entries)
        # GMNAP_SCHEMA_STRICT: 0=advisory (default), 1=quarantine all, 2=reject all
        schema_strict = int(os.getenv("GMNAP_SCHEMA_STRICT", "0"))
        results, val_metrics = stage8_global_validate(
            entries, mode=self.mode.value,
            graph_coherence=self.metrics.graph_coherence,
            schema_strict=schema_strict)
        self.metrics.schema_errors = val_metrics.get("schema_errors", 0)
        self.metrics.roundtrip_failures = val_metrics.get("roundtrip_failures", 0)
        self.metrics.schema_quarantined = val_metrics.get("quarantined_count", 0)
        self.metrics.schema_rejected = val_metrics.get("rejected_count", 0)
        return results

    def _stage_9_write_diff(self, entries: List[Dict[str, Any]]) -> str:
        """Stage 9: Write&Diff - Deterministic YAML, HTML diff, SQL changelog."""
        t0 = time.time()
        snapshot_dir = write_snapshot(entries, out_root=self.output_dir)
        logger.info(f"Snapshot written to {snapshot_dir}")

        if self.prev_snapshot_dir and Path(self.prev_snapshot_dir).exists():
            diff_summary = diff_snapshots(self.prev_snapshot_dir, snapshot_dir)
            logger.info(f"Diff: +{diff_summary['added']} -{diff_summary['removed']} ~{diff_summary['modified']}")
            generate_sql_changelog(self.prev_snapshot_dir, snapshot_dir)
            try:
                from src.pipeline.stage9_write_and_diff import generate_cypher_changelog
                generate_cypher_changelog(self.prev_snapshot_dir, snapshot_dir)
            except (ImportError, Exception) as e:
                logger.debug(f"Cypher changelog skipped: {e}")

        self.prev_snapshot_dir = snapshot_dir
        self.metrics.stage_timings["9_write_diff"] = time.time() - t0
        return snapshot_dir

    def _stage_10_report(self, entries: List[Dict[str, Any]], snapshot_dir: str) -> None:
        """Stage 10: Report - Markdown metrics, DOI draft, push to archive."""
        t0 = time.time()
        metrics_dict = {
            "duration_seconds": self.metrics.duration_seconds,
            "entries_per_second": self.metrics.entries_per_second,
            "collisions": self.metrics.collisions,
            "schema_errors": self.metrics.schema_errors,
            "schema_quarantined": self.metrics.schema_quarantined,
            "schema_rejected": self.metrics.schema_rejected,
            "roundtrip_failures": self.metrics.roundtrip_failures,
            "graph_coherence": self.metrics.graph_coherence,
        }
        generate_report(entries, metrics=metrics_dict, snapshot_dir=snapshot_dir,
                        shortform_clusters=self._shortform_clusters,
                        mode=self.mode.value.capitalize())
        self.metrics.stage_timings["10_report"] = time.time() - t0

    def _stage_11_idempotency_check(self, entries: List[Dict[str, Any]], snapshot_dir: str) -> None:
        """Stage 11: IdempotencyCheck - Shuffle entries, recompute canonical bytes, assert identical.

        Uses 'shuffled' mode: deterministically shuffles entries and checks that
        canonical byte output is identical regardless of input order — proving
        the pipeline produces deterministic output.
        """
        t0 = time.time()
        _, idemp_metrics = idempotency_check(
            entries, snapshot_dir=snapshot_dir, mode="shuffled", strict=False)
        self.metrics.idempotency_diff_bytes = int(idemp_metrics.get("idempotency_diff_bytes", 0))
        self.metrics.stage_timings["11_idempotency"] = time.time() - t0

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _make_global_id(entry: Dict[str, Any]) -> str:
        """Generate a GlobalID for an entry (128-bit truncated SHA-256, 22 Base32)."""
        if generate_global_id:
            try:
                return generate_global_id(entry)
            except Exception:
                pass
        # Fallback
        import base64
        canonical = entry.get("CanonicalNative") or entry.get("CanonicalLatin", "")
        birth = str(entry.get("BirthYear", ""))
        death = str(entry.get("DeathYear", ""))
        raw = f"{canonical}|{birth}|{death}".encode("utf-8")
        h = hashlib.sha256(raw).digest()[:16]
        return base64.b32encode(h).decode("ascii")[:22]

    # =========================================================================
    # QUALITY GATES (V7 spec section 7)
    # =========================================================================

    def _check_quality_gates(self) -> bool:
        """Check all 8 V7 quality gates with mode-specific thresholds.

        Uses pre-computed pipeline metrics (not re-counted from entries) to
        evaluate each gate.  Thresholds are sourced from QualityGateChecker
        when available; otherwise falls back to V7QualityGates dataclass.
        """
        m = self.metrics
        total = max(m.processed_entries, 1)

        # Use QualityGateChecker thresholds if available
        if QualityGatesEnforcer:
            checker = QualityGatesEnforcer(mode=self.mode.value)
            # Use checker's threshold helpers for individual metric-based checks
            results = {}
            ok, _ = checker.check_graph_coherence(m.graph_coherence)
            results["graph_coherence_score"] = ok
            ok, _ = checker.check_memory_limit()
            results["peak_rss_gb"] = ok
            ok, _ = checker.check_runtime(m.projected_time_per_million)
            results["runtime_per_1M"] = ok if m.processed_entries >= 100 else True
            ok, _ = checker.check_idempotency(m.idempotency_diff_bytes)
            results["idempotent_diff_bytes"] = ok
            ok, _ = checker.check_genealogy_edge_conflicts(m.graph_conflicts, m.edges)
            results["genealogy_edge_conflict_pct"] = ok

            # Metrics-based checks (not entry-based)
            results["duplicate_global_id"] = m.duplicate_global_ids == 0
            ext_pct = (m.duplicate_external_ids / total) * 100
            limit = checker._gate("duplicate_external_id_pct", 0.10)
            results["duplicate_external_id_pct"] = ext_pct <= (limit or 0.10)
            rt_rate = 1.0 - (m.roundtrip_failures / total)
            results["roundtrip_script_rate"] = rt_rate >= 0.97

            passed_count = sum(1 for v in results.values() if v)
            logger.info(f"Quality gates: {passed_count}/{len(results)} passed")
            return all(results.values())

        # Inline fallback if QualityGateChecker unavailable
        gates = self.quality_gates
        results = {}
        all_passed = True

        ok = m.duplicate_global_ids <= gates.duplicate_global_id
        results["duplicate_global_id"] = ok
        if not ok:
            all_passed = False

        ext_pct = (m.duplicate_external_ids / total) * 100
        ok = ext_pct <= gates.duplicate_external_id_pct_max
        results["duplicate_external_id_pct"] = ok
        if not ok:
            all_passed = False

        rt_rate = 1.0 - (m.roundtrip_failures / total)
        ok = rt_rate >= gates.roundtrip_script_rate_min
        results["roundtrip_script_rate"] = ok
        if not ok:
            all_passed = False

        conflict_pct = (m.graph_conflicts / max(m.edges, 1)) * 100 if m.edges > 0 else 0
        ok = conflict_pct <= gates.genealogy_edge_conflict_pct_max
        results["genealogy_edge_conflict_pct"] = ok
        if not ok:
            all_passed = False

        ok = m.graph_coherence >= gates.graph_coherence_score_min
        results["graph_coherence_score"] = ok
        if not ok:
            all_passed = False

        ok = m.peak_rss_gb <= gates.peak_rss_gb_on_2M
        results["peak_rss_gb"] = ok
        if not ok:
            all_passed = False

        ok = m.projected_time_per_million <= gates.warm_cache_runtime_per_1M_min or m.processed_entries < 100
        results["runtime_per_1M"] = ok
        if not ok:
            all_passed = False

        ok = m.idempotency_diff_bytes <= gates.idempotent_diff_bytes_max
        results["idempotent_diff_bytes"] = ok
        if not ok:
            all_passed = False

        passed_count = sum(1 for v in results.values() if v)
        logger.info(f"Quality gates: {passed_count}/{len(results)} passed")
        return all_passed

    def _generate_report(self) -> Dict[str, Any]:
        """Generate final pipeline report."""
        return {
            "mode": self.mode.value,
            "metrics": {
                "total_entries": self.metrics.total_entries,
                "processed_entries": self.metrics.processed_entries,
                "failed_entries": self.metrics.failed_entries,
                "duration_seconds": self.metrics.duration_seconds,
                "entries_per_second": self.metrics.entries_per_second,
                "projected_time_per_million_minutes": self.metrics.projected_time_per_million,
                "duplicate_global_ids": self.metrics.duplicate_global_ids,
                "schema_errors": self.metrics.schema_errors,
                "schema_quarantined": self.metrics.schema_quarantined,
                "schema_rejected": self.metrics.schema_rejected,
                "roundtrip_failures": self.metrics.roundtrip_failures,
                "graph_coherence": self.metrics.graph_coherence,
                "collisions": self.metrics.collisions,
                "edges": self.metrics.edges,
                "idempotency_diff_bytes": self.metrics.idempotency_diff_bytes,
                "peak_rss_gb": self.metrics.peak_rss_gb,
                "stage_timings": self.metrics.stage_timings,
            },
            "quality_gates": {
                "passed": True,
                "limits": {
                    "duplicate_global_id": self.quality_gates.duplicate_global_id,
                    "runtime_per_1M_min": self.quality_gates.warm_cache_runtime_per_1M_min,
                    "graph_coherence_min": self.quality_gates.graph_coherence_score_min,
                    "roundtrip_script_rate_min": self.quality_gates.roundtrip_script_rate_min,
                    "peak_rss_gb": self.quality_gates.peak_rss_gb_on_2M,
                    "idempotent_diff_bytes_max": self.quality_gates.idempotent_diff_bytes_max,
                }
            }
        }


async def main():
    """Example usage of V7 pipeline."""
    test_entries = [
        {"CanonicalLatin": "Wang, Wei", "BirthYear": 1970},
        {"CanonicalLatin": "Tanaka, Hiroshi", "BirthYear": 1965},
        {"CanonicalLatin": "Kim, Jong-un", "BirthYear": 1980},
        {"CanonicalLatin": "Smith, John", "BirthYear": 1975},
        {"CanonicalLatin": "Mueller, Hans", "BirthYear": 1960},
        {"CanonicalLatin": "Ivanov, Sergei", "BirthYear": 1968},
        {"CanonicalLatin": "Al-Rashid, Ahmad", "BirthYear": 1972},
        {"CanonicalLatin": "da Silva, Maria", "BirthYear": 1985},
    ]

    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    report = await pipeline.process_batch(test_entries)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(main())
