"""Runtime confidence calibration via PAV isotonic regression.

The region detector emits a raw confidence ∈ [0, 1] alongside every
prediction, but those raw values are not calibrated probabilities.
Measurement on the 843-entry adjudicated benchmark
(`tests/fixtures/name_origin_benchmark.json`) showed an Expected
Calibration Error of ~0.186 — substantial miscalibration, with the
0.85+ rules buckets only 72-76 % accurate while the 0.75 fastText
bucket is 96 %.

`tools/calibration.py` fits a Pool-Adjacent-Violators isotonic
regressor on the (raw_confidence, is_correct) pairs and saves the
resulting knots to `data/calibration_isotonic.json`. This module is
the read side: when ``GMNAP_CALIBRATE_CONFIDENCE=1`` is set, it
loads those knots once and exposes ``apply(p)`` to map raw → cal.

Default behaviour (env var unset) is identity — the caller's raw
confidence is returned unchanged. This preserves back-compat for any
test or fixture that pinned specific raw-confidence values, and lets
the calibration roll out per-deployment rather than as a forced
behaviour change.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Resolve relative to the repo root so this works in both `python -m`
# and editable-install contexts.
_KNOTS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "calibration_isotonic.json"
)

_KNOTS_CACHE: Optional[List[Tuple[float, float]]] = None
_KNOTS_LOAD_LOCK = Lock()


def _load_knots() -> Optional[List[Tuple[float, float]]]:
    """Lazy-load the PAV knots; cache on first hit, return None on
    error so the caller can fall back to raw confidence."""
    global _KNOTS_CACHE
    if _KNOTS_CACHE is not None:
        return _KNOTS_CACHE

    with _KNOTS_LOAD_LOCK:
        if _KNOTS_CACHE is not None:
            return _KNOTS_CACHE
        try:
            payload = json.loads(_KNOTS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning(
                "GMNAP_CALIBRATE_CONFIDENCE=1 set but %s is missing — "
                "run `tools/calibration.py` to fit and save the PAV "
                "knots. Falling back to raw confidence.",
                _KNOTS_PATH,
            )
            _KNOTS_CACHE = []
            return _KNOTS_CACHE
        except (OSError, ValueError) as exc:
            logger.warning(
                "Failed to load calibration knots from %s: %s. "
                "Falling back to raw confidence.",
                _KNOTS_PATH,
                exc,
            )
            _KNOTS_CACHE = []
            return _KNOTS_CACHE

        knots_raw = payload.get("knots") or []
        # Sanity-check: every entry should be a [threshold, calibrated_p]
        # pair, both in [0, 1], sorted by threshold ascending.
        knots: List[Tuple[float, float]] = []
        for k in knots_raw:
            if (
                isinstance(k, (list, tuple))
                and len(k) == 2
                and all(isinstance(x, (int, float)) for x in k)
                and 0.0 <= k[0] <= 1.0
                and 0.0 <= k[1] <= 1.0
            ):
                knots.append((float(k[0]), float(k[1])))
        _KNOTS_CACHE = knots
        return _KNOTS_CACHE


def _enabled() -> bool:
    return os.getenv("GMNAP_CALIBRATE_CONFIDENCE", "").strip() == "1"


def apply(p: float) -> float:
    """Map a raw confidence ``p`` through the fitted PAV knots.

    Returns ``p`` unchanged when:
      - ``GMNAP_CALIBRATE_CONFIDENCE`` env var is not "1"
      - the knots file is missing or unparseable
      - the fitted knots list is empty

    Otherwise returns the calibrated probability — the empirical
    accuracy in the smallest-threshold knot bucket whose threshold
    ≥ ``p``.
    """
    if not _enabled():
        return p
    knots = _load_knots()
    if not knots:
        return p
    # Clip to [0, 1] just in case a caller passes something out of
    # range — the PAV fit assumes proper probabilities.
    p = max(0.0, min(1.0, p))
    for threshold, cal_p in knots:
        if p <= threshold:
            return cal_p
    return knots[-1][1]


def reset_cache() -> None:
    """Drop the in-memory knots cache. Tests use this between
    fixtures that mutate ``data/calibration_isotonic.json``."""
    global _KNOTS_CACHE
    with _KNOTS_LOAD_LOCK:
        _KNOTS_CACHE = None
