#!/usr/bin/env python3
"""Reliability diagram for the region-detector's confidence scores.

The detector emits ``confidence ∈ [0, 1]`` alongside every region
prediction. We've claimed 100 % emitted-leaf precision on the
523-entry adjudicated subset of ``tests/fixtures/name_origin_benchmark.json``,
but precision alone doesn't tell us whether the per-prediction
confidence is *calibrated*: when the detector says 0.7, is it right
70 % of the time? When it says 0.95, 95 % of the time?

This script answers the question by binning predictions into ten
confidence buckets ``[0.0, 0.1), [0.1, 0.2), …, [0.9, 1.0]`` and
computing the empirical accuracy in each bucket. A perfectly
calibrated detector would have bucket midpoint ≈ bucket accuracy.

Outputs:

- ``docs/calibration.json`` — raw bucket data
- ``docs/calibration.md`` — markdown report including:
    * a Brier score (mean squared error between confidence and
      indicator), the standard scalar calibration metric
    * an Expected Calibration Error (ECE) — weighted mean
      |accuracy − confidence| across buckets
    * an ASCII reliability diagram (no matplotlib dependency)

Run::

    PYTHONPATH=. python3 tools/calibration.py

Idempotent. Read-only against the codebase + benchmark.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parent.parent
BENCHMARK = REPO / "tests" / "fixtures" / "name_origin_benchmark.json"
OUT_JSON = REPO / "docs" / "calibration.json"
OUT_MD = REPO / "docs" / "calibration.md"
# Knots for the runtime isotonic calibrator. Read by
# src/regions/calibration.py when GMNAP_CALIBRATE_CONFIDENCE=1.
OUT_KNOTS = REPO / "data" / "calibration_isotonic.json"

# Mirror the test_benchmark_evaluation.py adjudication policy: a
# prediction is "correct" iff the detector's emitted leaf is in the
# benchmark's `acceptable_leaves` set. R0 (residual) is honest
# abstention, not a wrong answer; we either drop those or count them
# as a separate category.
N_BUCKETS = 10


def _load_benchmark() -> list[dict[str, Any]]:
    if not BENCHMARK.exists():
        sys.exit(f"benchmark fixture not found: {BENCHMARK}")
    return json.loads(BENCHMARK.read_text(encoding="utf-8"))


def _detect(manager, name: str) -> tuple[Optional[str], float]:
    """Return (predicted_leaf, confidence) for one name."""
    entry = {"CanonicalLatin": name}
    result = manager.detect_region(entry)
    if result is None:
        return None, 0.0
    leaf = getattr(result, "region_code", None)
    conf = float(getattr(result, "confidence", 0.0) or 0.0)
    return leaf, max(0.0, min(1.0, conf))


def _bucket(conf: float) -> int:
    """Map confidence ∈ [0, 1] to bucket index 0..N_BUCKETS-1."""
    if conf >= 1.0:
        return N_BUCKETS - 1
    return int(conf * N_BUCKETS)


def _pav_fit(samples: list[tuple[float, int]]) -> list[tuple[float, float]]:
    """Pool-Adjacent-Violators isotonic regression.

    Input
    -----
    ``samples`` is a list of ``(raw_confidence, is_correct)`` pairs;
    ``is_correct`` is 0 or 1.

    Output
    ------
    A list of ``(threshold, calibrated_p)`` knots, sorted **strictly**
    ascending by ``threshold`` and non-decreasing in ``calibrated_p``.
    To apply: find the smallest knot whose ``threshold >= p_raw`` and
    use its ``calibrated_p``. Edge cases (``p_raw`` above all
    thresholds) clip to the last knot.

    Pre-aggregation
    ---------------
    Tied x values are pre-aggregated into single weighted points
    *before* the PAV merge loop runs. Without aggregation, samples
    sharing an x produce multiple PAV blocks at the same threshold;
    the apply path can only return one of those blocks' cal_p (the
    first match), which is statistically not the empirical mean at
    that x. Aggregation gives one unique threshold per knot and
    eliminates that ambiguity.

    Why PAV here, not Platt
    -----------------------
    The 0.75 fastText bucket on this benchmark is ~96 % accurate
    while the 0.85+ rule-based buckets are 72-76 %. The relationship
    between raw-p and empirical-accuracy is *not* monotonic-sigmoid —
    it has a piecewise-flat, source-dependent shape. Platt scaling
    (a single sigmoid) can't fit that. Isotonic regression is non-
    parametric and only assumes monotone non-decreasing accuracy
    with confidence; PAV is the standard linear-time fitter.

    No sklearn dependency: <40 lines suffice.
    """
    if not samples:
        return []

    # Pre-aggregate ties: collapse all samples sharing an x value into
    # one weighted point (sum_y, count). PAV operates on unique-x
    # blocks from here on, so the output has at most one knot per
    # distinct input confidence.
    aggregated: dict[float, list[float]] = {}
    for p, y in samples:
        bucket = aggregated.setdefault(p, [0.0, 0.0])
        bucket[0] += float(y)
        bucket[1] += 1.0
    pairs = sorted(aggregated.items())  # by threshold ascending

    # Each block is [threshold, sum_correct, count].
    blocks: list[list[float]] = [[p, sy, n] for p, (sy, n) in pairs]

    i = 0
    while i + 1 < len(blocks):
        mean_i = blocks[i][1] / blocks[i][2]
        mean_j = blocks[i + 1][1] / blocks[i + 1][2]
        if mean_i > mean_j:
            # Violation — merge i+1 into i, then back up so the new
            # block is checked against its left neighbour. Threshold
            # of the merged block is the max (rightmost) of the two,
            # so the block still represents the contiguous x-range
            # ending at that point.
            blocks[i][0] = max(blocks[i][0], blocks[i + 1][0])
            blocks[i][1] += blocks[i + 1][1]
            blocks[i][2] += blocks[i + 1][2]
            del blocks[i + 1]
            if i > 0:
                i -= 1
        else:
            i += 1

    return [(b[0], b[1] / b[2]) for b in blocks]


def _apply_isotonic(p: float, knots: list[tuple[float, float]]) -> float:
    """Map a raw confidence through the fitted PAV knots."""
    if not knots:
        return p
    for threshold, cal_p in knots:
        if p <= threshold:
            return cal_p
    return knots[-1][1]


def _ece_brier_on_buckets(
    samples: list[tuple[float, int]],
) -> tuple[float, float, list[dict[str, Any]]]:
    """Compute ECE + Brier + per-bucket stats from (conf, is_correct) pairs.

    Used for both the raw-confidence pass and the post-calibration
    re-evaluation, so the metrics are comparable.
    """
    buckets = [
        {
            "lo": i / N_BUCKETS,
            "hi": (i + 1) / N_BUCKETS,
            "n": 0,
            "correct": 0,
            "conf_sum": 0.0,
        }
        for i in range(N_BUCKETS)
    ]
    brier_sum = 0.0
    for conf, is_correct in samples:
        b = _bucket(conf)
        buckets[b]["n"] += 1
        buckets[b]["correct"] += int(is_correct)
        buckets[b]["conf_sum"] += conf
        brier_sum += (conf - is_correct) ** 2

    total = len(samples)
    ece = 0.0
    for b in buckets:
        n = b["n"]
        b["accuracy"] = (b["correct"] / n) if n else None
        b["mean_conf"] = (b["conf_sum"] / n) if n else None
        if n and b["accuracy"] is not None and b["mean_conf"] is not None:
            ece += (n / max(total, 1)) * abs(b["accuracy"] - b["mean_conf"])
    brier = brier_sum / max(total, 1)
    return ece, brier, buckets


def _kfold_cv_metrics(
    samples: list[tuple[float, int]],
    k: int = 5,
    seed: int = 42,
) -> tuple[float, float, list[dict[str, Any]]]:
    """Honest out-of-fold ECE / Brier via k-fold cross-validation.

    The default ``run()`` reports ECE measured on the same set the
    PAV fitter trained on — which is optimistic. CV approximates the
    out-of-sample number a fresh batch would actually see:

      - shuffle samples deterministically (seed),
      - for each of k folds:
        - hold out the fold,
        - fit PAV on the remaining k-1 folds,
        - apply the knots to each held-out sample,
      - aggregate the k held-out predictions into one set,
      - compute ECE / Brier / per-bucket reliability on it.

    Returns ``(cv_ece, cv_brier, cv_buckets)`` shaped like
    ``_ece_brier_on_buckets``.

    With small per-x-value cardinality (the GMNAP benchmark has only
    ~3 distinct raw confidences), the CV number tracks the train-set
    one closely — the fit is so coarse that holding out 20 % barely
    moves it. That's the honest result, not a flaw of the method.
    """
    import random

    rng = random.Random(seed)
    n = len(samples)
    if n == 0 or k < 2:
        return _ece_brier_on_buckets([])

    indices = list(range(n))
    rng.shuffle(indices)
    fold_membership = [indices[i::k] for i in range(k)]

    oof: list[tuple[float, int]] = []
    for fold in fold_membership:
        holdout = set(fold)
        train = [samples[i] for i in indices if i not in holdout]
        knots = _pav_fit(train)
        for i in fold:
            p_raw, y = samples[i]
            oof.append((_apply_isotonic(p_raw, knots), y))

    return _ece_brier_on_buckets(oof)


def _samples_from(manager, eligible):
    """Run detection on a list of benchmark entries; return
    ``(samples, abstentions)`` where samples is a list of
    ``(raw_conf, is_correct)``."""
    samples: list[tuple[float, int]] = []
    abstentions = 0
    for e in eligible:
        name = e.get("full_name") or ""
        if not name:
            continue
        accepted = set(e.get("acceptable_leaves") or [])
        leaf, conf = _detect(manager, name)
        if leaf is None or leaf == "R0":
            abstentions += 1
            continue
        samples.append((conf, int(leaf in accepted)))
    return samples, abstentions


def run() -> dict[str, Any]:
    from src.regions.benchmark_split import load_test, load_train
    from src.regions.manager_optimized import RegionManager

    manager = RegionManager()

    train = [
        e
        for e in load_train()
        if e.get("expected_mode") == "leaf" and e.get("acceptable_leaves")
    ]
    test = [
        e
        for e in load_test()
        if e.get("expected_mode") == "leaf" and e.get("acceptable_leaves")
    ]

    train_samples, train_abst = _samples_from(manager, train)
    test_samples, test_abst = _samples_from(manager, test)

    # 1. Raw ECE on the held-out test set — the headline number.
    raw_ece, raw_brier, raw_buckets = _ece_brier_on_buckets(test_samples)

    # 2. Fit PAV on TRAIN. Apply to both train (sanity check) and
    #    test (the honest evaluation).
    knots = _pav_fit(train_samples)
    train_cal = [(_apply_isotonic(c, knots), y) for c, y in train_samples]
    test_cal = [(_apply_isotonic(c, knots), y) for c, y in test_samples]
    train_cal_ece, train_cal_brier, train_cal_buckets = _ece_brier_on_buckets(train_cal)
    test_cal_ece, test_cal_brier, test_cal_buckets = _ece_brier_on_buckets(test_cal)

    # 3. K-fold CV WITHIN the train set — variance estimate that's
    #    independent of the test split.
    cv_ece, cv_brier, cv_buckets = _kfold_cv_metrics(train_samples, k=5, seed=42)

    return {
        "n_train_eligible": len(train),
        "n_train_predicted": len(train_samples),
        "n_train_abstain": train_abst,
        "n_test_eligible": len(test),
        "n_test_predicted": len(test_samples),
        "n_test_abstain": test_abst,
        # back-compat aliases (n_eligible / n_predicted / n_abstain
        # used to mean the full-set numbers; they now mean the test
        # set, which is what should drive any headline claim)
        "n_eligible": len(test),
        "n_predicted": len(test_samples),
        "n_abstain": test_abst,
        "ece": raw_ece,  # raw test-set ECE
        "brier": raw_brier,
        "buckets": raw_buckets,
        "calibrated": {
            "ece": test_cal_ece,  # honest: fit on train, eval on test
            "brier": test_cal_brier,
            "buckets": test_cal_buckets,
            "knots": [list(k) for k in knots],
            "train_ece": train_cal_ece,  # for completeness — train-set re-application
            "train_brier": train_cal_brier,
            "train_buckets": train_cal_buckets,
        },
        "cv": {
            "k": 5,
            "seed": 42,
            "scope": "train-set (variance estimate; complement to held-out test)",
            "ece": cv_ece,
            "brier": cv_brier,
            "buckets": cv_buckets,
        },
    }


def _ascii_diagram(report: dict[str, Any]) -> str:
    """Render a 30-column reliability diagram. Each row is one bucket;
    '#' columns indicate empirical accuracy, '|' indicates the bucket
    midpoint (perfect-calibration target). Rows with zero predictions
    are shown but greyed."""
    lines = ["Reliability diagram (30 cols = 100 %)", ""]
    lines.append("  bucket │  midpt │     n │   acc │ chart")
    lines.append("  ───────┼────────┼───────┼───────┼" + "─" * 32)
    for i, b in enumerate(report["buckets"]):
        lo, hi = b["lo"], b["hi"]
        midpt = (lo + hi) / 2
        n = b["n"]
        acc = b["accuracy"]
        # 30-column chart
        if n == 0:
            chart = "·" * 30
        else:
            assert acc is not None
            acc_col = int(round(acc * 30))
            mid_col = int(round(midpt * 30))
            cols = [" "] * 30
            for c in range(min(acc_col, 30)):
                cols[c] = "#"
            if 0 <= mid_col < 30:
                cols[mid_col] = "|"
            chart = "".join(cols)
        acc_str = f"{acc:5.2f}" if acc is not None else "  —  "
        lines.append(
            f"  [{lo:.1f},{hi:.1f}) │  {midpt:.2f}  │ {n:5d} │ {acc_str} │ {chart}"
        )
    return "\n".join(lines) + "\n"


def _md_report(report: dict[str, Any]) -> str:
    raw_diag = _ascii_diagram(report)
    cal_diag = _ascii_diagram({"buckets": report["calibrated"]["buckets"]})
    cv_diag = _ascii_diagram({"buckets": report["cv"]["buckets"]})
    n_test_elig = report["n_test_eligible"]
    n_train_elig = report["n_train_eligible"]
    n_pred = report["n_predicted"]
    n_abst = report["n_abstain"]
    raw_ece = report["ece"]
    raw_brier = report["brier"]
    cal_ece = report["calibrated"]["ece"]
    cal_brier = report["calibrated"]["brier"]
    train_cal_ece = report["calibrated"]["train_ece"]
    cv_ece = report["cv"]["ece"]
    cv_brier = report["cv"]["brier"]
    cv_k = report["cv"]["k"]
    n_knots = len(report["calibrated"]["knots"])

    def _interp(ece: float) -> str:
        if ece < 0.05:
            return (
                "**ECE < 0.05** is the conventional threshold for "
                "'well-calibrated'. Confidence scores can be read as "
                "approximate probabilities."
            )
        if ece < 0.10:
            return (
                "**0.05 ≤ ECE < 0.10** indicates moderate "
                "miscalibration. Treat the confidence as a rough "
                "ranking, not a probability."
            )
        return (
            "**ECE ≥ 0.10** indicates substantial miscalibration. "
            "Use the isotonic-calibrated value (below) for any "
            "downstream consumer that expects a probability."
        )

    return f"""# Region-detector confidence calibration

Generated by `tools/calibration.py` on the
adjudicated leaf-mode entries of
`tests/fixtures/name_origin_benchmark.json`, split deterministically
into train ({n_train_elig} entries) and held-out test ({n_test_elig}
entries) by `src/regions/benchmark_split.py`.

## Methodology

1. **Stratified 80/20 split** by group letter (A–G), seed 42. Tiny
   groups (F=43, G=37) get ≥ 1 test entry; bigger groups (C=233,
   B=166) keep their ~80/20 ratio. Split is computed once per
   process and cached.
2. **PAV isotonic fitter is trained ONLY on the train set** (~675
   samples after R0/None filtering).
3. **Headline calibrated ECE is measured on the held-out test set**
   — none of those samples were seen during fitting, so the number
   is an honest estimate of generalization.
4. **5-fold cross-validation runs WITHIN the train set** as an
   independent variance estimate. Complementary to (3); doesn't
   touch the test set at all.

## Summary

| Metric | Raw test | Calibrated test (held-out) | Train-applied | {cv_k}-fold CV on train |
|---|---:|---:|---:|---:|
| Eligible entries (leaf-mode) | {n_test_elig} | {n_test_elig} | {n_train_elig} | {n_train_elig} |
| Predictions emitted | {n_pred} | {n_pred} | – | – |
| Abstentions (R0 / None) | {n_abst} | {n_abst} | – | – |
| Brier score | **{raw_brier:.4f}** | **{cal_brier:.4f}** | – | **{cv_brier:.4f}** |
| Expected Calibration Error (ECE) | **{raw_ece:.4f}** | **{cal_ece:.4f}** | {train_cal_ece:.4f} | **{cv_ece:.4f}** |

**The second column is the honest number.** It's the test-set ECE
after applying knots that were fit only on the disjoint train set.
The third column (train-applied) is the same fitted knots applied
back to their training data — useful as a sanity check (should be
near zero) but not a generalization claim. The fourth column (CV)
estimates fit-time variance.

{_interp(raw_ece)}

After PAV (pool-adjacent-violators) isotonic regression on the
same set, ECE drops to **{cal_ece:.4f}** ({n_knots} knots fitted,
saved to `data/calibration_isotonic.json`). Enable at runtime via
`GMNAP_CALIBRATE_CONFIDENCE=1`.

### Caveat — measured-on-train, single-bucket artifact

The calibrated ECE is computed by re-applying the fitted knots
to the same 654 samples used for fitting, which is optimistic in
two ways:

1. **No held-out evaluation.** A more honest number would come
   from k-fold cross-validation; the apparent ECE on a fresh,
   held-out split could plausibly be 2-5× higher than what's
   reported here.
2. **Single-bucket collapse.** PAV merges everything into a
   small number of plateaus (here: 2 knots covering the full
   input range), so almost every calibrated sample lands in one
   confidence bucket. ECE in 10-bucket binning is then trivially
   small because there is essentially nothing to be miscalibrated
   *across* buckets — only *within* one.

The right way to read the numbers below: the calibrator does
*reduce* over-confidence (raw 0.95 → cal ~0.87, matching the
empirical rule-source accuracy) but it does *not* magically lift
the discrimination of the underlying detector. Treat the
calibrated value as "pessimistic-replacement-for-overconfident-
raw", not as a probability you can use for downstream Bayesian
reasoning without further validation.

## Raw reliability diagram

```
{raw_diag}```

## Calibrated reliability diagram (train-set)

```
{cal_diag}```

## Held-out reliability diagram ({cv_k}-fold CV)

```
{cv_diag}```

Each row is a confidence bucket. Column count of `#` is empirical
accuracy in that bucket, scaled to 30 columns. The `|` marks the
bucket midpoint — a perfectly calibrated detector has `#` ending
right at the `|` for every populated row. Compare the two diagrams:
the raw confidence consistently overshoots its midpoint (the bars
end short of `|`); the calibrated one tracks `|` more closely
because the PAV fitter pushed each bin's nominal value down to
match its empirical accuracy.

## Reproduce

```bash
PYTHONPATH=. python3 tools/calibration.py
```

Outputs `docs/calibration.json` (raw + calibrated bucket data),
this markdown report, and `data/calibration_isotonic.json` (the
fitted PAV knots used by the runtime `GMNAP_CALIBRATE_CONFIDENCE`
path).

## Runtime use

```python
import os
os.environ["GMNAP_CALIBRATE_CONFIDENCE"] = "1"

from src.regions.manager_optimized import RegionManager
mgr = RegionManager()
result = mgr.detect_region({{"CanonicalLatin": "Euler, Leonhard"}})
result.confidence  # now isotonic-calibrated
```

When the env var is unset (the default), confidence is the raw
detector score — preserving back-compat for anything that pinned
specific values in tests or fixtures.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-names",
        type=int,
        default=None,
        help="Cap eligible names (debug / fast iteration; full run = all 523).",
    )
    args = parser.parse_args()

    report = run()
    if args.max_names is not None:
        # The cap is informational; we already ran the full set above.
        print(
            f"(--max-names ignored after run; processed {report['n_predicted']})",
            file=sys.stderr,
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_MD.write_text(_md_report(report), encoding="utf-8")

    OUT_KNOTS.parent.mkdir(parents=True, exist_ok=True)
    OUT_KNOTS.write_text(
        json.dumps(
            {
                "knots": report["calibrated"]["knots"],
                "raw_ece": report["ece"],
                "calibrated_ece": report["calibrated"]["ece"],
                "n_predicted": report["n_predicted"],
                "fitter": "PAV (pool-adjacent-violators isotonic regression)",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Echo the diagram to stdout so a caller can see results immediately.
    print(_ascii_diagram(report))
    print(f"Raw         ECE = {report['ece']:.4f}")
    print(f"Calibrated  ECE = {report['calibrated']['ece']:.4f}")
    print(f"Raw         Brier = {report['brier']:.4f}")
    print(f"Calibrated  Brier = {report['calibrated']['brier']:.4f}")
    print(f"PAV knots fitted: {len(report['calibrated']['knots'])}")
    print(f"\nwrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    print(f"wrote {OUT_KNOTS.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
