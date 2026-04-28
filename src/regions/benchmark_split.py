"""Deterministic train/test split for the adjudicated benchmark.

The 843-entry adjudicated name-origin benchmark
(`tests/fixtures/name_origin_benchmark.json`) was used until now for
*everything*: leaf-precision measurement, calibration fitting,
operating-point sweep in `tools/rc_curve.py`, threshold selection in
`manager_optimized.py`. That's evaluation-on-train across the board
— honest out-of-sample numbers were never reported.

This module fixes that with a stratified deterministic 80/20 split:

    train:  ~673 entries — used for fitting (calibration, thresholds)
    test:   ~170 entries — held entirely back, only for headline numbers

Stratification is by group letter (A–G), so each group keeps the
same proportions on both sides of the split. Tiny groups still get
≥ 1 test entry (we cap at floor; max(1, n*0.2)).

Determinism comes from `random.Random(SEED).shuffle(sorted(names))`:
the seed is fixed, the input is sorted into stable order before
shuffling, so the split survives reordering of the JSON file. The
assignment is computed once and cached.

Public API
----------
``load_all()``     – the original 843 entries (unchanged behaviour)
``load_train()``   – the ~673 train entries
``load_test()``    – the ~170 test entries
``assignment()``   – ``{full_name: 'train' | 'test'}`` mapping
``BENCHMARK_PATH`` – the on-disk JSON path
"""

from __future__ import annotations

import collections
import functools
import json
import random
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent.parent
BENCHMARK_PATH = REPO / "tests" / "fixtures" / "name_origin_benchmark.json"

# Don't change SEED or TEST_FRACTION without communicating it widely —
# every "test-set ECE / precision / coverage" number we publish is
# tied to this exact split. Changing them invalidates published
# numbers and forces re-running every consumer of `load_test()`.
SEED = 42
TEST_FRACTION = 0.2


@functools.lru_cache(maxsize=1)
def load_all() -> List[Dict[str, Any]]:
    """The full adjudicated benchmark, in original file order."""
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


def _group_for(entry: Dict[str, Any]) -> str:
    """First letter of the first acceptable leaf — A, B, C, …, R, Z."""
    leaves = entry.get("acceptable_leaves") or []
    if leaves and leaves[0]:
        return leaves[0][0].upper()
    expected = (entry.get("expected_leaf") or "").upper()
    return expected[0] if expected else "?"


@functools.lru_cache(maxsize=1)
def assignment() -> Dict[str, str]:
    """Return ``{full_name: 'train' | 'test'}`` for every benchmark entry.

    Stratified per-group with a fixed seed; min(1, …) cap on test
    size keeps even tiny groups (G=37, F=43) represented in the
    held-out set.
    """
    data = load_all()
    by_group: Dict[str, List[str]] = collections.defaultdict(list)
    for e in data:
        name = e.get("full_name")
        if not name:
            continue
        by_group[_group_for(e)].append(name)

    out: Dict[str, str] = {}
    rng = random.Random(SEED)
    for group in sorted(by_group):  # iterate groups in deterministic order
        names = sorted(by_group[group])  # deterministic input order
        rng.shuffle(names)
        n_test = max(1, int(round(len(names) * TEST_FRACTION)))
        for n in names[:n_test]:
            out[n] = "test"
        for n in names[n_test:]:
            out[n] = "train"
    return out


def load_train() -> List[Dict[str, Any]]:
    """Train-set subset of the benchmark (~80 %, stratified by group).

    Use this for fitting calibration knots, picking operating-point
    thresholds, or any other parameter that's tuned on the data.
    """
    a = assignment()
    return [e for e in load_all() if a.get(e.get("full_name", "")) == "train"]


def load_test() -> List[Dict[str, Any]]:
    """Test-set subset of the benchmark (~20 %, held out).

    Use this only for final headline numbers. Don't tune thresholds
    on it; the whole point is that those tunings already happened on
    the train side and we want an unbiased estimate of generalization.
    """
    a = assignment()
    return [e for e in load_all() if a.get(e.get("full_name", "")) == "test"]
