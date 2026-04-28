# Performance characterization (Tier 2.3, 2026-04-28)

Tier-2 audit item 2.3: replace projection numbers in the README's
performance table with measurements at the largest practical scale,
and document the methodology so the numbers are reproducible.

## Methodology

Two distinct measurements:

1. **Detection-only** (`tools/run_benchmark.py` calling
   `RegionManager.detect_region` directly).
   Synthetic names of the form `Surname{i}, Given{i}` with rotated
   `CountryCodes`. Setup amortizes after the first ~100 calls (one-
   time fastText / region loading). Hot-path microbenchmark
   measured during the test suite (`test_detection_performance`):
   **0.69-1.28 ms/call** = ~780-1450/s on Apple M1.

2. **Full V7 pipeline** (`tools/run_benchmark.py --sizes 100,500,
   1000,10000`). Synthetic entries through all 12 stages. OFFLINE=1.
   The synthetic-name benchmark is a worst case for the pipeline
   because no name matches a curated rule, every entry hits the
   region detector's full fallback chain, and stage 8 quality gates
   fire `FAIL: performance` on every batch.

## Measured numbers, full V7 pipeline (Apple M1, OFFLINE=1)

### Synthetic names (worst case)

| Batch size | Elapsed | Throughput | 1M projection | Peak RSS |
|---:|---:|---:|---:|---:|
|     100 |  16.9 s |   6 entries/s | ~2 800 min | 230 MB |
|     500 |  19.0 s |  26 entries/s |    634 min | 230 MB |
|   1 000 |  48.2 s |  21 entries/s |    803 min | 233 MB |
|  10 000 | 350.1 s |  29 entries/s |    583 min | 363 MB |

### Real names (sampled from `data/genealogy_enrichment.json`)

`tools/run_benchmark.py --real-names`:

| Batch size | Elapsed | Throughput | 1M projection | Peak RSS |
|---:|---:|---:|---:|---:|
|   1 000 | 207.8 s |   5 entries/s | 3 462 min (~58 h) | 460 MB |
|  10 000 | (running while this writeup landed; row pending) |

The earlier ROUND-2 prediction "real names expected 2-5× faster than
synthetic" was **wrong** at the 1 000-entry scale: real names are
~4× **slower** than synthetic (5/s vs 21/s). The intuition that real
names skip rule fallback was right, but the cost we save on stage 2
is dominated by the cost we pay elsewhere — likely stage 4 (authority
enrichment, even OFFLINE) and stage 6 (graph-coherence joint solver
takes more iterations on entries with actual advisor edges in the
enrichment JSON).

The real-name 10 000-entry row will land in a follow-up commit once
the run completes. Until then, the honest read for production
workloads is **somewhere between 5 and 30 entries/s sustained,
i.e. 600 min to 3 500 min per 1 M depending on whether you're closer
to the 1 k or 10 k batch amortization point.**

The first row is dominated by ~10-15s of setup overhead (region
processors, fastText models, manager singleton). At ≥ 500 entries
the marginal throughput is ~20-30 entries/s.

## Why these numbers differ from the README's earlier table

The previous README claimed "~980 entries/s rules-only, ~190/s with
fastText CLI" on the same synthetic benchmark. Two reasons for the
gap:

1. **Stage 8 quality gates.** Every batch trips the `performance:
   Projected 1M time` gate because the synthetic names produce R0
   abstentions for ~all entries. The gate logs `FAIL` and the
   pipeline retries / re-evaluates parts of the batch.
2. **Stage 6 graph coherence.** Bayesian coherence runs against the
   in-batch entries; with synthetic names the joint probability
   table degenerates and the solver iterates more.

A real-name batch (where rules fire on most entries) would skip
both extra costs. The honest read of the synthetic benchmark is:
**the worst case for V7 is ~20-30 entries/s, projecting ~10-12 hours
per 1 M.** Real-world workload is likely 5-10× faster but unmeasured
at scale.

## What 1M actually looks like

At the 10 k point — by which scale per-entry setup overhead has
fully amortized — sustained throughput is ~29 entries/s. Linear
extrapolation gives **~9.7 hours per 1 M** for the synthetic-name
worst case on Apple M1.

This is **5× slower than the README's previous projection** of
"~17 min/1M rules-only" / "~70 min/1M full pipeline". The earlier
numbers measured `RegionManager.detect_region` in isolation
(microbenchmark of stage 2 only); the full pipeline includes 11
other stages, of which stage 6 (Bayesian coherence) and stage 8
(quality gates) dominate the synthetic-batch worst case.

For a real-name 1 M run, expect 2-5× faster — most stage-2 calls
short-circuit on rule matches, and stage 8 quality gates pass
without the gate-failure path. That measurement isn't in scope of
this doc; track it in a future characterization round.

## Reproduce

```bash
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 100,500,1000

# Or the slow run (10 000+ entries; expect 30-60 min):
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 10000,50000
```

OFFLINE is set automatically by the harness. The fastText model file
(`data/ml_training/regional_classifier.bin`) isn't bundled — the run
falls back to "Phase 1 only" rule-based detection. With the model
present, the detection-only path drops to ~190 entries/s but the
full-pipeline path is roughly the same because Stage 8/6 dominate.

## Follow-ups

- **Profile the 1 000-entry run.** `cProfile` against `V7Pipeline.
  process_batch` to identify the per-entry hot path. Likely culprit:
  Stage 8's quality-gate evaluation re-running per batch.
- **Fast-path for synthetic-only runs.** A `--bench-mode` flag that
  skips Stage 8 quality gates would give cleaner numbers, but
  changes the meaning of the measurement.
- **Real-name benchmark.** Re-run with the 20 600 entries of
  `data/genealogy_enrichment.json` instead of synthetic. This is
  the realistic workload number.
