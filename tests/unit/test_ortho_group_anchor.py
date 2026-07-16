"""R58: orthographic group-anchor module — trap pins from the adversarial judge.

Every case here is a named counterexample from the design round; a failure
means a trap the judges explicitly closed has reopened.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("OFFLINE", "1")

from src.regions.detection.orthography import detect_ortho_group_anchor
from src.regions.manager_optimized import RegionManager

_MODEL = Path("data/ml_training/ft_name_classifier.ftz")


# ---------- pure-function table pins ----------


def test_tier1_slavic_signature():
    a = detect_ortho_group_anchor("Zdzisław Brzeźniak")
    assert a and a.kind == "group" and a.payload == "SLAVIC_CENTRAL" and a.tier == 1


def test_vietnamese_context_suppresses_slavic():
    """Judge mod (a): 'Đinh, Tiến Cường' must NOT get a Slavic anchor —
    đ + hook/horn vowels are Vietnamese (E5 is a real group)."""
    assert detect_ortho_group_anchor("Đinh, Tiến Cường") is None
    assert detect_ortho_group_anchor("Đỗ, Đức Thái") is None


def test_albanian_c_cedilla_is_not_tier1_turkic():
    """Judge mod (b): Ç-initial alone must not be a veto-immune anchor."""
    a = detect_ortho_group_anchor("Arben Çela")
    assert a is None or a.tier == 2  # never tier-1


def test_dotless_i_and_g_breve_stay_tier1_turkic():
    a = detect_ortho_group_anchor("Ayşe Sarıoğlu")
    assert a and a.payload == "TURKIC" and a.tier == 1


def test_marks_read_from_surname_token_only():
    """'Irène Marcovici': è in the GIVEN name must not anchor; the surname
    is Romanian."""
    a = detect_ortho_group_anchor("Irène Marcovici")
    assert a is None or a.payload != "GERMANIC_WESTERN"


def test_bare_acutes_and_hungarian_blocked():
    assert detect_ortho_group_anchor("G. Bérczi") is None  # Hungarian zs/gy... é
    assert detect_ortho_group_anchor("José Fernández") is None  # Spanish straddle


def test_macron_exclusion_japanese():
    assert detect_ortho_group_anchor("Satō, Kenji") is None  # Hepburn macron


def test_umlaut_alone_anchors_nothing():
    assert detect_ortho_group_anchor("Mehmet Ömer") is None


def test_u_umlaut_plus_germanic_pattern():
    a = detect_ortho_group_anchor("Peter Grünwald")
    assert a and a.payload == "GERMANIC_WESTERN"


def test_o_umlaut_plus_pattern_is_permitted_set():
    a = detect_ortho_group_anchor("Anna Sjöberg")
    assert a and a.kind == "permitted"
    assert a.payload == frozenset({"GERMANIC_WESTERN", "NORDIC_BALTIC"})


def test_french_marks_without_suffix_are_group_cap():
    """Benaïm guard (judge mod c): ï without the French/Italian suffix
    whitelist licenses at most a group claim, never a leaf."""
    a = detect_ortho_group_anchor("Michel Benaïm")
    assert a and a.kind == "group_cap" and a.payload == "GERMANIC_WESTERN"


def test_french_marks_with_suffix_license_group():
    a = detect_ortho_group_anchor("Julien Brémont")
    assert a and a.kind == "group" and a.payload == "GERMANIC_WESTERN"


def test_s_caron_class_is_permitted_slavic_baltic():
    a = detect_ortho_group_anchor("D. Kršek")
    assert a and a.kind == "permitted"
    assert "SLAVIC_CENTRAL" in a.payload and "BALTIC" in a.payload


# ---------- end-to-end pins (need the model for the veto/refinement) ----------


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


@pytest.mark.skipif(not _MODEL.exists(), reason="fastText model not built")
def test_aid_veto_maghrebi_french(manager):
    """'René Aïd': ï is transliteration orthography, not French origin — the
    confident cross-group ft verdict (C3) vetoes the Tier-2 anchor; no
    GERMANIC group claim may survive on the abstention."""
    r = manager.detect_region({"CanonicalLatin": "René Aïd"})
    assert r.region_code != "A2"
    if r.region_code == "R0":
        assert (r.metadata or {}).get("group") != "GERMANIC_WESTERN"


@pytest.mark.skipif(not _MODEL.exists(), reason="fastText model not built")
def test_benaim_never_gets_a2_leaf(manager):
    r = manager.detect_region({"CanonicalLatin": "Michel Benaïm"})
    assert r.region_code != "A2", (
        "Benaïm got an A2 LEAF — the group_cap guard regressed (anchor+ft "
        "agreement is correlated evidence, capped at group level)"
    )


@pytest.mark.skipif(not _MODEL.exists(), reason="fastText model not built")
def test_dinh_never_slavic(manager):
    r = manager.detect_region({"CanonicalLatin": "Đinh, Tiến Cường"})
    assert r.region_code not in ("B1", "B2", "B3")
