"""RegionDetectionResult dataclass. Moved verbatim from manager_optimized (R45)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegionDetectionResult:
    """Result of region detection."""

    region_code: str
    confidence: float
    detection_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Phase 2 fields (backward compatible -- all optional)
    geo_region: Optional[str] = None
    name_region: Optional[str] = None
    group_region: Optional[str] = None
    candidates: Optional[List[Any]] = None
    conflict: bool = False
    # Phase 3: resolution level ("leaf", "group", or "abstain")
    resolution_level: Optional[str] = None
