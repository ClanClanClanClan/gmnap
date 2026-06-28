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


# Generous upper bound on the costs file size. The real file is a few
# hundred bytes (one float per source). 1 MiB is ~6 orders of magnitude
# of headroom and bounds a single os.read().
_MAX_COSTS_BYTES = 1024 * 1024


def _parse_costs(raw: str) -> Dict[str, float]:
    """Parse the JSON body, degrading to ``{}`` on any malformation."""
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("cost-tracker: malformed costs JSON (%s) — starting fresh", exc)
        return {}
    return data if isinstance(data, dict) else {}


def _load() -> Dict[str, float]:
    """Read the costs file under a SHARED lock.

    The shared lock means a concurrent ``record()`` (which holds the
    EXCLUSIVE lock across its whole read-modify-write) can never expose
    a half-written / truncated file to a reader. Returns ``{}`` if the
    file is absent or unreadable.
    """
    p = _costs_path()
    if not p.exists():
        return {}
    try:
        fd = os.open(p, os.O_RDONLY)
    except OSError as exc:
        logger.warning("cost-tracker: failed to open %s (%s) — starting fresh", p, exc)
        return {}
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        try:
            raw = os.read(fd, _MAX_COSTS_BYTES).decode("utf-8", errors="replace")
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return _parse_costs(raw)


def record(source: str, calls: int = 1, override_chf: float | None = None) -> None:
    """Record N live API calls to a given source.

    ``override_chf`` is for sources whose price isn't a simple
    per-call rate (e.g. monthly subscription chunks). When set, the
    full charge in CHF is added directly without scaling by ``calls``.

    Concurrency: the EXCLUSIVE ``flock`` is acquired BEFORE the file is
    read so the entire read-modify-write is atomic across processes.
    The earlier implementation read (via ``_load``) *before* locking and
    then opened the file in ``"w"`` mode, which (a) truncated the file
    before the lock was held — a concurrent reader could observe an
    empty file and lose all prior spend — and (b) left a lost-update
    race: two workers could both read the old total, both add their
    cost, and the second write would clobber the first. Locking first
    and reading the live bytes under the lock closes both holes.
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
        # O_RDWR | O_CREAT — open without truncating; create if absent.
        fd = os.open(p, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                raw = os.read(fd, _MAX_COSTS_BYTES).decode("utf-8", errors="replace")
                data = _parse_costs(raw)
                data[source] = round(float(data.get(source, 0.0)) + cost, 6)
                payload = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
                os.lseek(fd, 0, os.SEEK_SET)
                os.ftruncate(fd, 0)
                os.write(fd, payload)
                os.fsync(fd)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def total() -> float:
    """Sum across all sources, in CHF. Used by CI's cost-guard job."""
    return sum(_load().values())


def reset() -> None:
    """Test-fixture helper — wipe the costs file."""
    p = _costs_path()
    if p.exists():
        p.unlink()
