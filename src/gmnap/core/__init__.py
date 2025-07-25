"""
GMNAP Core - 10-stage processing pipeline and global functionality

Implements the core GMNAP v6.1 pipeline:
Stage 0: Config - Load RegionSpecs, verify file ownership, licence checks
Stage 1: Ingest - Read YAML, Unicode normalization
Stage 2: DetectRegion - Script ranges, ICU, fastText, affiliation hints
Stage 3: RegionHooks - clean→augment→validate→order_key
Stage 4: AuthorityEnrich - External API integration 
Stage 5: CollisionAnalytics - DuckDB analysis
Stage 6: TagShortForms - Populate ShortFormClusters
Stage 7: GlobalValidate - JSON-Schema, unique IDs, round-trip
Stage 8: Write&Diff - Deterministic YAML, HTML diff, SQL changelog
Stage 9: Report - Markdown summary, metrics.json
Stage 10: IdempotencyCheck - Full rerun verification
"""

from .pipeline import GMNAPPipeline
from .globalid import generate_global_id
from .database import GMNAPDatabase

__all__ = ["GMNAPPipeline", "generate_global_id", "GMNAPDatabase"]