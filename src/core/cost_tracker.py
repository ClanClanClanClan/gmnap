"""Per-source live-API cost tracking.

Round 34 phase 3. CI's ``cost-guard`` job previously read
``cache/api_costs.json`` against a CHF 120/month budget, but nothing
in the codebase ever wrote to that file — every CI run reinitialized
it to ``{}`` and the budget enforcement was theatre. This module is
the writer side: tier-0/tier-1 authority fetchers call ``record(...)``
on each live request; CI reads the running total.

Pricing table (CHF / 1 000 calls, rounded up to be conservative):

  OpenAlex          0.00   free, polite-pool email
  Crossref          0.00   free, no key required
  Wikidata          0.00   free, SPARQL endpoint
  ORCID             0.00   free
  GND               0.00   free, DNB API
  HAL               0.00   free, OAI-PMH
  OAI_University    0.00   free, OAI-PMH
  zbMATH_Open       0.00   free, OAI-PMH
  Crossref_Thesis   0.00   free
  Scopus            5.00   metered above 20k/month — placeholder
  Dimensions        5.00   metered — placeholder
  MathSciNet        0.00   subscription seat — sunk cost
  ProQuest         10.00   per-call metered — placeholder
  GoogleScholar     0.00   ToS-gated; never priced

All tier-0/tier-1 sources are free at the volumes we hit. The
metered tier-2/tier-3 placeholders exist so the CI guard catches a
prod misconfiguration that opens the floodgates on a paid source —
e.g. ``OFFLINE=0`` with a Scopus key wired in and an accidental
1 M-entry batch.

Single-process-safe (locks per file write). Multi-process aggregation
is by-file (the json file is the source of truth); concurrent writers
use a fcntl exclusive lock.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import threading
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# CHF per 1 000 calls; defaults are zero for free APIs. Real numbers
# only for the metered sources. Update when subscriptions change.
_DEFAULT_PRICING_CHF_PER_1K: Dict[str, float] = {
    "OpenAlex": 0.0,
    "Crossref": 0.0,
    "Wikidata": 0.0,
    "Wikidata_P184": 0.0,
    "ORCID": 0.0,
    "ORCID_ETD": 0.0,
    "GND": 0.0,
    "HAL": 0.0,
    "OAI_University": 0.0,
    "zbMATH_Open": 0.0,
    "Crossref_Thesis": 0.0,
    "Scopus": 5.0,
    "Dimensions": 5.0,
    "MathSciNet": 0.0,
    "ProQuest": 10.0,
    "GoogleScholar": 0.0,
}

_LOCK = threading.Lock()


def _costs_path() -> Path:
    """Resolve cache/api_costs.json relative to the process CWD.

    CI's cost-guard step reads from the same path; matching it means
    a single canonical writer + reader. Operators wanting persistence
    across container restarts should mount the cache/ directory as a
    volume (the docker-compose.yml already does).
    """
    base = Path(os.getenv("GMNAP_COSTS_PATH", "cache/api_costs.json"))
    base.parent.mkdir(parents=True, exist_ok=True)
    return base


def _load() -> Dict[str, float]:
    p = _costs_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("cost-tracker: failed to read %s (%s) — starting fresh", p, exc)
        return {}


def record(source: str, calls: int = 1, override_chf: float | None = None) -> None:
    """Record N live API calls to a given source.

    ``override_chf`` is for sources whose price isn't a simple
    per-call rate (e.g. monthly subscription chunks). When set, the
    full charge in CHF is added directly without scaling by ``calls``.
    """
    if calls <= 0:
        return
    pricing = _DEFAULT_PRICING_CHF_PER_1K.get(source, 0.0)
    if override_chf is not None:
        cost = float(override_chf)
    else:
        cost = (pricing * calls) / 1000.0

    if cost == 0.0:
        # Skip the file I/O for the common free-source path.
        return

    with _LOCK:
        p = _costs_path()
        data = _load()
        data[source] = round(data.get(source, 0.0) + cost, 6)
        # fcntl lock against concurrent writers from other processes
        # (e.g. a parallel uvicorn worker hitting the same source).
        with open(p, "w", encoding="utf-8") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX)
                json.dump(data, fh, indent=2, sort_keys=True)
            finally:
                try:
                    fcntl.flock(fh, fcntl.LOCK_UN)
                except OSError:
                    pass


def total() -> float:
    """Sum across all sources, in CHF. Used by CI's cost-guard job."""
    return sum(_load().values())


def reset() -> None:
    """Test-fixture helper — wipe the costs file."""
    p = _costs_path()
    if p.exists():
        p.unlink()
