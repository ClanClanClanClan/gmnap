"""R58 adversarial pins: names the fastText model is CONFIDENTLY WRONG about.

Measured against the 271-name multi-agent adjudicated pilot ground truth,
raw fastText promotion (no group anchor) tops out at 77-81% verifiable-leaf
precision even at prob >= 0.99 — and the model asserts wrong leaves at
probability 1.0. These pins guarantee the wrong leaf is NEVER emitted for
the flagship counterexamples, at any future threshold or tier change.

The allowed outcomes are deliberately broad: R0 (abstention), a correct
group-level claim, or the ADJUDICATED leaf (later rounds legitimately
convert several of these via the dictionary supplement). Only the model's
known-wrong leaf is forbidden.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.regions.manager_optimized import RegionManager

_MODEL = Path("data/ml_training/ft_name_classifier.ftz")

# (name, model's confidently-wrong leaf, adjudicated leaf-or-group)
_PINS = [
    ("N. Touzi", "A1", "C3"),  # ft A1@0.983
    ("U. Cetin", "A1", "C1"),  # ft A1@1.00
    ("U. Çetin", "A1", "C1"),
    ("R. S. Hazra", "A1", "D3"),  # ft A1@1.00
    ("L. C. Yeung", "A1", "E1"),  # ft A1@0.999
    ("J. Cvitanic", "A1", "B2"),  # ft A1@0.995
    ("J. Cvitanić", "A1", "B2"),
    ("L. Tangpi", "E1", "F-group"),  # ft E1@0.85; adjudicated F GROUP_ONLY
    ("B. Büke", "A1", "C1"),
    # Short-homograph class: given-name-driven ANGLO hint + ft's A1 bias
    # correlate on a 3-char Chinese-Singaporean surname. The unconditional
    # >=4-char surname guard on ft emissions keeps this abstained.
    ("Timothy L. H. Wee", "A1", "E1"),
]


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


@pytest.mark.skipif(not _MODEL.exists(), reason="fastText model not built")
@pytest.mark.parametrize("name,wrong_leaf,adjudicated", _PINS)
def test_confidently_wrong_model_leaf_is_never_emitted(
    manager, name, wrong_leaf, adjudicated
):
    r = manager.detect_region({"CanonicalLatin": name})
    assert r.region_code != wrong_leaf, (
        f"{name!r} emitted the model's confidently-wrong leaf {wrong_leaf} "
        f"(adjudicated: {adjudicated}) via {r.detection_method} "
        f"conf={r.confidence} — raw fastText promotion has been reinstated "
        f"somewhere. It must never be. See docs/calibration.md (R58)."
    )
