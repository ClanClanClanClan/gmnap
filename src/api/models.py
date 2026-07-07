"""Pydantic request/response models for the GMNAP API (R46 split from server.py)."""

from typing import Any, Dict, List

from pydantic import BaseModel

from src import __version__


class ProcessRequest(BaseModel):
    entries: List[Dict[str, Any]]
    mode: str = "quick"
    schema_strict: int = 0
    limit: int = 100  # max entries to return per page (1-10000)
    offset: int = 0  # skip first N results

    @property
    def pipeline_mode(self) -> str:
        """Validated mode string."""
        return self.mode if self.mode in ("quick", "full", "extreme") else "quick"


class HealthResponse(BaseModel):
    status: str
    # The SOFTWARE release version (single source: src.__version__) — R55.
    # This used to be a hardcoded "7.0", which is the SPEC generation, not
    # the release; the two had drifted apart across five surfaces.
    version: str = __version__
    uptime_seconds: float = 0.0


class CorrectionSuggestion(BaseModel):
    original_name: str
    correction_type: str  # advisor, institution, year, name, country, other
    suggested_value: str
    source_url: str = ""
    submitter_note: str = ""
