"""R58: icu-priority weak-evidence gate + weak-group fastText routing.

Pilot root cause: for Latin input, ``_detect_by_icu`` re-ran the priority
scorer on ICU-normalized (i.e. identical) text WITHOUT the Fix-4
weak-evidence gate ``_detect_by_script`` applies — resurrecting, at
0.76-0.81 confidence, exactly the single-suffix (best_score 1.2-1.9) hits
the script path had just rejected. 'Francis Lörler' (German) emitted as
B3/Greek that way.

The weak signal is not discarded: it rides as a ``weak_group`` anchor that
the same-group fastText gate may refine WITHIN ('Kratsios' weak-HELLENIC +
ft B3 -> B3), while cross-group ft verdicts let it die ('Lörler'
weak-HELLENIC + ft A2 -> R0, no group claimed).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.regions.manager_optimized import RegionManager

_MODEL = Path("data/ml_training/ft_name_classifier.ftz")


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


def _detect(manager, name):
    return manager.detect_region({"CanonicalLatin": name})


@pytest.mark.parametrize(
    "name",
    [
        "Francis Lörler",  # German; was B3@0.76 via icu-priority
        "A. Matoussi",  # Tunisian; was B3 via icu-priority
    ],
)
def test_weak_single_suffix_hits_no_longer_emit_via_icu(manager, name):
    r = _detect(manager, name)
    assert r.region_code != "B3", (
        f"{name!r} -> B3 again: the icu-priority weak-evidence resurrection "
        f"is back (method={r.detection_method}, conf={r.confidence})"
    )
    # And whatever the outcome, it must not be an icu-priority emission
    # built on a sub-2.0 score.
    assert r.detection_method != "icu-priority" or (
        r.metadata and r.metadata.get("best_score", 0) >= 2.0
    )


def test_terminal_r0_carries_no_group_from_weak_evidence(manager):
    """A dead weak hint must not surface a group claim on the abstention
    (the 100% group-or-better KPI counts group claims as commitments)."""
    r = _detect(manager, "Francis Lörler")
    if r.region_code == "R0":
        assert not (r.metadata or {}).get("group"), (
            "terminal R0 claims a group from a sub-2.0 single-suffix hit: "
            f"{r.metadata}"
        )


@pytest.mark.skipif(not _MODEL.exists(), reason="fastText model not built")
def test_weak_anchor_plus_ft_agreement_recovers_greek(manager):
    r = _detect(manager, "Anastasis Kratsios")
    assert r.region_code == "B3"
    assert (r.metadata or {}).get("gated") == "same_group_weak"
