# Risk–coverage curves

Measured on the 843-entry adjudicated name-origin benchmark
(`tests/fixtures/name_origin_benchmark.json`). Grid: **quick (16 points)**.


## Operating point (production default)

`GMNAP_SCORER_MIN_SCORE=0.50`, `GMNAP_SCORER_MIN_MARGIN=0.30`, `GMNAP_FASTTEXT_P1=0.50`, `GMNAP_FASTTEXT_MARGIN=0.15`.

## Pareto frontier (coverage × leaf_precision)

| scorer_score | scorer_margin | ft_p1 | ft_margin | coverage | leaf_prec | group_prec |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.30 | 0.50 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.50 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.70 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.70 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.50 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.50 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.70 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.70 | 0.20 | 0.362 | 0.728 | 0.728 |

## Full sweep (sorted by leaf_precision desc)

| scorer_score | scorer_margin | ft_p1 | ft_margin | coverage | leaf_prec | group_prec |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.30 | 0.50 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.50 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.70 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.30 | 0.70 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.50 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.50 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.70 | 0.15 | 0.362 | 0.728 | 0.728 |
| 0.60 | 0.30 | 0.70 | 0.20 | 0.362 | 0.728 | 0.728 |
| 0.50 | 0.40 | 0.50 | 0.15 | 0.361 | 0.727 | 0.727 |
| 0.50 | 0.40 | 0.50 | 0.20 | 0.361 | 0.727 | 0.727 |
| 0.50 | 0.40 | 0.70 | 0.15 | 0.361 | 0.727 | 0.727 |
| 0.50 | 0.40 | 0.70 | 0.20 | 0.361 | 0.727 | 0.727 |
| 0.60 | 0.40 | 0.50 | 0.15 | 0.361 | 0.727 | 0.727 |
| 0.60 | 0.40 | 0.50 | 0.20 | 0.361 | 0.727 | 0.727 |
| 0.60 | 0.40 | 0.70 | 0.15 | 0.361 | 0.727 | 0.727 |
| 0.60 | 0.40 | 0.70 | 0.20 | 0.361 | 0.727 | 0.727 |

## ASCII scatter

```
leaf_precision (higher is better)
  +------------------------------------------------------------+
1.0 |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                     *                                      |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
    |                                                            |
0.0 |                                                            |
  +------------------------------------------------------------+
   0.0                           1.0
              coverage (higher is better)
```

## Observations

- Across all 16 operating points, coverage varies by only **0.001** and leaf-precision by **0.001**.
  The four threshold knobs studied here are **not the dominant lever**
  on this benchmark — most abstentions happen earlier in the pipeline
  (no surname signal at all) and never reach these thresholds.

- **Actionable next step**: if you need more coverage, widen the
  signature-suffix table or relax the CJK hybrid guard. If you need
  higher precision, tighten the same-group gate rather than these
  thresholds — the gate is what prevents cross-group fastText drift.

- **Production default is already on the Pareto frontier.** Shipping
  with `GMNAP_SCORER_MIN_SCORE=0.50` and `GMNAP_SCORER_MIN_MARGIN=0.30`
  sits at the coverage-max corner of the frontier; moving either knob
  costs 0.1-0.2% leaf-precision for a similar drop in coverage.
