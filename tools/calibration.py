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


def run() -> dict[str, Any]:
    from src.regions.manager_optimized import RegionManager

    manager = RegionManager()

    benchmark = _load_benchmark()
    # Skip entries the adjudicators flagged as "expected_mode: group" —
    # those are designed to test the abstain-to-group path, not leaf
    # confidence calibration. Same for entries with no acceptable_leaves.
    eligible = [
        e
        for e in benchmark
        if e.get("expected_mode") == "leaf" and e.get("acceptable_leaves")
    ]

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

    abstentions = 0  # detector returned None or R0
    total = 0
    brier_sum = 0.0  # for Brier score on abstain==False

    for e in eligible:
        name = e.get("full_name") or ""
        if not name:
            continue
        accepted = set(e.get("acceptable_leaves") or [])
        leaf, conf = _detect(manager, name)
        if leaf is None or leaf == "R0":
            abstentions += 1
            continue
        total += 1
        is_correct = leaf in accepted
        b = _bucket(conf)
        buckets[b]["n"] += 1
        buckets[b]["correct"] += int(is_correct)
        buckets[b]["conf_sum"] += conf
        # Brier: (conf - 1)^2 if correct, conf^2 if wrong
        brier_sum += (conf - (1.0 if is_correct else 0.0)) ** 2

    # Compute per-bucket calibration + ECE
    ece = 0.0
    for b in buckets:
        n = b["n"]
        b["accuracy"] = (b["correct"] / n) if n else None
        b["mean_conf"] = (b["conf_sum"] / n) if n else None
        if n and b["accuracy"] is not None and b["mean_conf"] is not None:
            ece += (n / max(total, 1)) * abs(b["accuracy"] - b["mean_conf"])

    brier = brier_sum / max(total, 1)

    return {
        "n_eligible": len(eligible),
        "n_predicted": total,
        "n_abstain": abstentions,
        "ece": ece,
        "brier": brier,
        "buckets": buckets,
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
    diag = _ascii_diagram(report)
    n_eligible = report["n_eligible"]
    n_pred = report["n_predicted"]
    n_abst = report["n_abstain"]
    ece = report["ece"]
    brier = report["brier"]

    interp = []
    if ece < 0.05:
        interp.append(
            "**ECE < 0.05** is the conventional threshold for "
            "'well-calibrated'. Confidence scores can be read as "
            "approximate probabilities."
        )
    elif ece < 0.10:
        interp.append(
            "**0.05 ≤ ECE < 0.10** indicates moderate miscalibration. "
            "Treat the confidence as a rough ranking, not a probability."
        )
    else:
        interp.append(
            "**ECE ≥ 0.10** indicates substantial miscalibration. "
            "Consider Platt scaling or isotonic regression on a held-"
            "out set before exposing the score to downstream consumers."
        )

    return f"""# Region-detector confidence calibration

Generated by `tools/calibration.py` on the
{n_eligible} adjudicated leaf-mode entries of
`tests/fixtures/name_origin_benchmark.json`.

## Summary

| Metric | Value | Interpretation |
|---|---:|---|
| Eligible entries (leaf-mode) | {n_eligible} | adjudicated subset |
| Predictions emitted | {n_pred} | non-R0, non-None |
| Abstentions (R0 / None) | {n_abst} | honest "I don't know" |
| **Brier score** | **{brier:.4f}** | mean squared error vs the indicator |
| **Expected Calibration Error (ECE)** | **{ece:.4f}** | weighted mean \\|accuracy − confidence\\| |

{interp[0]}

## Reliability diagram

```
{diag}```

Each row is a confidence bucket. Column count of `#` is empirical
accuracy in that bucket, scaled to 30 columns. The `|` marks the
bucket midpoint — a perfectly calibrated detector has `#` ending
right at the `|` for every populated row.

## Reproduce

```bash
PYTHONPATH=. python3 tools/calibration.py
```

Outputs both this file and `docs/calibration.json`.
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

    # Echo the diagram to stdout so a caller can see results immediately.
    print(_ascii_diagram(report))
    print(f"ECE   = {report['ece']:.4f}")
    print(f"Brier = {report['brier']:.4f}")
    print(f"\nwrote {OUT_JSON.relative_to(REPO)}")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
