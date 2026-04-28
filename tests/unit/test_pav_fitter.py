"""Unit tests for the PAV (Pool-Adjacent-Violators) isotonic fitter.

The fitter lives in `tools/calibration.py` because it's a one-shot
training utility, not production runtime code. The runtime *apply*
path is in `src/regions/calibration.py` and tested separately by
`tests/unit/test_calibration.py`. These tests pin the fitter's
mathematical correctness.
"""

from __future__ import annotations

import pytest

from tools.calibration import _apply_isotonic, _kfold_cv_metrics, _pav_fit


def _means_monotone_nondecreasing(knots):
    """Invariant PAV must always satisfy."""
    for i in range(len(knots) - 1):
        assert (
            knots[i][1] <= knots[i + 1][1] + 1e-12
        ), f"non-monotone at index {i}: {knots[i]} → {knots[i + 1]}"


def _thresholds_strictly_increasing(knots):
    """Post-aggregation PAV should produce one knot per unique x."""
    for i in range(len(knots) - 1):
        assert (
            knots[i][0] < knots[i + 1][0]
        ), f"duplicate threshold at index {i}: {knots[i]} == {knots[i + 1]}"


# ── Empty / trivial inputs ──────────────────────────────────────────


def test_empty_input_returns_empty():
    assert _pav_fit([]) == []


def test_single_sample():
    assert _pav_fit([(0.5, 1)]) == [(0.5, 1.0)]
    assert _pav_fit([(0.5, 0)]) == [(0.5, 0.0)]


# ── All-correct / all-wrong (degenerate) ───────────────────────────


def test_all_correct_all_ones():
    knots = _pav_fit([(0.3, 1), (0.5, 1), (0.9, 1)])
    assert len(knots) == 3
    assert all(k[1] == 1.0 for k in knots)
    _thresholds_strictly_increasing(knots)


def test_all_wrong_all_zeros():
    knots = _pav_fit([(0.3, 0), (0.5, 0), (0.9, 0)])
    assert len(knots) == 3
    assert all(k[1] == 0.0 for k in knots)


# ── Already-monotonic input (no merge needed) ──────────────────────


def test_monotonic_input_no_merge():
    knots = _pav_fit([(0.1, 0), (0.5, 0), (0.9, 1), (0.95, 1)])
    assert len(knots) == 4
    _means_monotone_nondecreasing(knots)


# ── Single violation triggers correct merge ────────────────────────


def test_single_violation_merges_correctly():
    # Means 0, 1, 0 — middle and last violate; PAV should merge them.
    samples = [(0.2, 0), (0.5, 1), (0.8, 0)]
    knots = _pav_fit(samples)
    _means_monotone_nondecreasing(knots)
    # The (0.5, 1) and (0.8, 0) blocks merge to (0.8, 0.5).
    assert knots == [(0.2, 0.0), (0.8, 0.5)]


def test_chain_violation_merges_left():
    # Each block independently violates → PAV should pool them.
    samples = [(0.2, 0), (0.4, 1), (0.6, 1), (0.8, 0), (0.9, 1)]
    knots = _pav_fit(samples)
    _means_monotone_nondecreasing(knots)
    # Trace:
    #   Aggregated unique-x means: 0, 1, 1, 0, 1
    #   i=2: (0.6, mean 1) vs (0.8, mean 0) — violation. Merge to (0.8, 1/2).
    #   i=1: (0.4, mean 1) vs (0.8, mean 0.5) — violation. Merge to (0.8, 2/3).
    #   i=0: (0.2, mean 0) vs (0.8, mean 2/3) — OK.
    #   i=1: (0.8, mean 2/3) vs (0.9, mean 1.0) — OK.
    # Final: [(0.2, 0.0), (0.8, 2/3), (0.9, 1.0)]
    assert len(knots) == 3
    assert knots[0] == (0.2, 0.0)
    assert knots[1][0] == 0.8
    assert abs(knots[1][1] - 2 / 3) < 1e-9
    assert knots[2] == (0.9, 1.0)


# ── Tie aggregation (the bug this test caught) ────────────────────


def test_ties_at_same_x_aggregate_to_empirical_mean():
    # 4 samples all at x=0.5: 3 correct, 1 wrong → empirical 0.75.
    # Pre-aggregation PAV would have produced multiple same-threshold
    # blocks; the apply path would return the leftmost block's value
    # (0.5), which is statistically wrong. Post-aggregation gives one
    # clean knot at the true empirical mean.
    samples = [(0.5, 1), (0.5, 0), (0.5, 1), (0.5, 1)]
    knots = _pav_fit(samples)
    assert len(knots) == 1, "ties must collapse to one knot per unique x"
    assert knots[0] == (0.5, 0.75)
    assert _apply_isotonic(0.5, knots) == 0.75


def test_ties_with_violation_combined():
    # Mix ties with PAV violations: at x=0.4 we have 2 correct, 0 wrong;
    # at x=0.6 we have 0 correct, 1 wrong (single sample).
    # Aggregated means: (0.4, 1.0), (0.6, 0.0) — violates.
    # After merge: (0.6, 2/3 ≈ 0.667).
    samples = [(0.4, 1), (0.4, 1), (0.6, 0)]
    knots = _pav_fit(samples)
    assert len(knots) == 1
    assert knots[0][0] == 0.6
    assert abs(knots[0][1] - 2 / 3) < 1e-9


# ── Apply path: monotone, edge-clipping ────────────────────────────


def test_apply_below_first_threshold_returns_first_cal_p():
    knots = [(0.5, 0.3), (0.9, 0.8)]
    # p=0.1 ≤ 0.5 → returns the first knot's cal_p.
    assert _apply_isotonic(0.1, knots) == 0.3


def test_apply_above_last_threshold_clips_to_last_cal_p():
    knots = [(0.5, 0.3), (0.9, 0.8)]
    # p=1.0 > all thresholds → clip to last cal_p.
    assert _apply_isotonic(1.0, knots) == 0.8


def test_apply_at_threshold_inclusive():
    knots = [(0.5, 0.3), (0.9, 0.8)]
    # p=0.5 ≤ 0.5 → first match.
    assert _apply_isotonic(0.5, knots) == 0.3
    # p=0.9 ≤ 0.9 → second match.
    assert _apply_isotonic(0.9, knots) == 0.8


def test_apply_between_thresholds_returns_higher_knot():
    # Step-function semantics: smallest threshold ≥ p.
    knots = [(0.5, 0.3), (0.9, 0.8)]
    assert _apply_isotonic(0.7, knots) == 0.8


def test_apply_empty_knots_is_identity():
    assert _apply_isotonic(0.42, []) == 0.42


# ── Roundtrip: fit then apply preserves monotonicity ───────────────


def test_fit_apply_roundtrip_is_monotone():
    """Apply must be monotone non-decreasing in p, regardless of
    how the PAV fitter merged the input."""
    samples = [
        (0.1, 0),
        (0.2, 1),
        (0.3, 0),
        (0.4, 1),
        (0.5, 1),
        (0.6, 0),
        (0.7, 1),
        (0.8, 1),
        (0.9, 0),
        (0.95, 1),
    ]
    knots = _pav_fit(samples)
    _means_monotone_nondecreasing(knots)
    last = -1.0
    for p in [0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92, 1.0]:
        cal = _apply_isotonic(p, knots)
        assert cal >= last - 1e-12, f"non-monotone apply: p={p} gave {cal} < {last}"
        last = cal


# ── Realistic GMNAP-shaped data ────────────────────────────────────


def test_gmnap_shaped_data_two_clean_knots():
    """The actual GMNAP benchmark produces ~3 unique confidences
    (rule-based 0.85/0.95, fastText-derived ~0.715). With ties
    aggregated, PAV should end up with at most 2-3 knots — not the 7
    redundant knots the pre-fix fitter produced."""
    # Mimic the real bucket distribution: many samples at three unique
    # confidences, with the 0.85/0.95 buckets having lower accuracy
    # than the 0.715 bucket — the textbook violation case.
    samples: list[tuple[float, int]] = []
    samples += [(0.715, 1)] * 365  # 96 % of 380
    samples += [(0.715, 0)] * 15
    samples += [(0.85, 1)] * 143  # 72 % of 199
    samples += [(0.85, 0)] * 56
    samples += [(0.95, 1)] * 55  # 76 % of 72
    samples += [(0.95, 0)] * 17

    knots = _pav_fit(samples)
    assert len(knots) <= 3, (
        f"GMNAP-shaped data should produce ≤ 3 knots after tie "
        f"aggregation; got {len(knots)}: {knots}"
    )
    _thresholds_strictly_increasing(knots)
    _means_monotone_nondecreasing(knots)


# ── K-fold CV metrics ──────────────────────────────────────────────


def test_kfold_cv_empty_input_returns_zeroed_metrics():
    ece, brier, buckets = _kfold_cv_metrics([], k=5)
    assert ece == 0.0
    assert brier == 0.0
    assert all(b["n"] == 0 for b in buckets)


def test_kfold_cv_is_deterministic_under_seed():
    """Same seed → same result. Different seed → different shuffle →
    *possibly* different bucket distribution but the same overall
    ECE up to a small float-precision delta."""
    samples = [(0.5, i % 2) for i in range(100)]
    a = _kfold_cv_metrics(samples, k=5, seed=42)
    b = _kfold_cv_metrics(samples, k=5, seed=42)
    assert a[0] == b[0]
    assert a[1] == b[1]


def test_kfold_cv_preserves_total_holdout_count():
    """Every sample appears in exactly one held-out fold; the sum of
    bucket n's should equal the input size."""
    samples = [(0.7, 1)] * 60 + [(0.9, 0)] * 40
    _, _, buckets = _kfold_cv_metrics(samples, k=5, seed=0)
    assert sum(b["n"] for b in buckets) == 100


def test_kfold_cv_on_perfect_calibrator_input_gives_low_ece():
    """If raw confidence = empirical accuracy (the textbook
    well-calibrated case), CV ECE should stay small — held-out
    predictions land near the diagonal up to bernoulli sampling
    noise. With 1000 samples per x, the per-fold accuracy estimate
    for the held-out 200 is tight enough that CV ECE stays under
    the conventional 0.05 'well-calibrated' threshold."""
    # 90 % of samples at p=0.9 are correct, 50 % at p=0.5, 10 % at p=0.1.
    # Use 1000 each so 5-fold holdouts have 200 samples — bernoulli SE
    # of the per-fold accuracy is sqrt(0.5*0.5/200) ≈ 0.035.
    samples: list[tuple[float, int]] = []
    samples += [(0.9, 1)] * 900 + [(0.9, 0)] * 100
    samples += [(0.5, 1)] * 500 + [(0.5, 0)] * 500
    samples += [(0.1, 1)] * 100 + [(0.1, 0)] * 900
    ece, _, _ = _kfold_cv_metrics(samples, k=5, seed=42)
    assert ece < 0.05, f"Expected near-perfect input to give CV ECE < 0.05, got {ece}"


def test_kfold_cv_does_not_modify_input():
    """The CV runner should not mutate its samples argument — callers
    might re-use it for other measurements."""
    samples = [(0.5, 1), (0.6, 0), (0.7, 1)]
    snapshot = list(samples)
    _kfold_cv_metrics(samples, k=2, seed=1)
    assert samples == snapshot
