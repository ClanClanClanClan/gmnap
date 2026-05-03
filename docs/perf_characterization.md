# Performance characterization (Tier 2.3, 2026-04-28; round-30 update 2026-05-03)

Tier-2 audit item 2.3: replace projection numbers in the README's
performance table with measurements at the largest practical scale,
and document the methodology so the numbers are reproducible.

## TL;DR (current production numbers)

**1 M real names → 362 s (6.0 min) on Apple M1, OFFLINE, single
process.** 2 763 entries/s, 769 MB peak RSS — measured, not
projected. Skip to "What 1M actually looks like" for the table and
the round-28 regex-cache + round-30 streaming-path explanation. The
pre-round-28 tables earlier in this doc are kept for historical
context; they're slow because of the `_wb()` cache bug, not because
the pipeline is slow.

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
|   1 000 |  207.8 s |   5 entries/s | 3 462 min (~58 h) | 460 MB |
|  10 000 | 1 493.6 s |   7 entries/s | 2 489 min (~41.5 h) | 628 MB |

The earlier ROUND-2 prediction "real names expected 2-5× faster than
synthetic" was **wrong**: real names are consistently ~4× **slower**
than synthetic at every batch size we measured (5-7/s real vs 21-
29/s synthetic). The intuition that real names skip stage-2 rule
fallback was right; what we missed is the cost we pay *elsewhere*:

- **Stage 4 authority enrichment**, even OFFLINE: real names cause
  the manager_tier01 fetchers to do their cache-key compute and
  per-source hit/miss accounting per entry, whereas synthetic names
  short-circuit on the empty-name guard or get cached negative
  responses faster.
- **Stage 6 graph coherence**: the Bayesian joint-probability solver
  iterates more on entries that *actually have* advisor edges in
  the enrichment JSON. Synthetic entries have no advisor data, so
  stage 6 short-circuits.
- **Stage 7 short-form tagging** + **stage 8 quality gates**: both
  iterate over more populated metadata for real entries.

Honest engineering read for production workloads (post round-28
`_wb` cache fix, **post round-30 actual 1 M measurement**):

**1 M real names processed in 362 seconds (6.0 min) — measured, not
projected.** Apple M1, OFFLINE, single process. Peak RSS 769 MB.

Round 30 verified the projection by running the full 1 M end-to-end:

| Size | Wall clock | Throughput | RSS peak |
|-----:|-----------:|-----------:|---------:|
| 10 k |  65.7 s   |  152 /s    |  492 MB  |
| 100 k| 339.6 s   |  295 /s    |  812 MB  |
| 1 M  | **362.0 s**| **2 763 /s**| 769 MB |

The 100 k → 1 M jump is real and structural: ``process_batch``
switches at >100 k entries to the ``AsyncBatchAggregator`` streaming
path, which coalesces 16-entry buffers into 1 000-entry chunks
dispatched concurrently under ``max_concurrency``. Three downstream
effects:

  1. **Throughput up ~10×** because chunks run in parallel.
  2. **RSS *lower* at 1 M than at 100 k** because streaming
     releases each chunk's intermediate state as the sink consumes
     it; serial path holds the full result list in memory.
  3. **Sub-100 k batches don't benefit** — they use the direct
     ``_process_batch_internal`` path, which serializes chunks.

Production guidance: batch sizes ≥ 100 001 hit the streaming path
and run dramatically faster per entry. Below that threshold,
throughput is bounded by serial chunk processing.

Round-30 → 1 M was a real measurement, not an extrapolation. The
earlier "~1.8 h" projection (linear scaling from 10 k) was off by
**18×** in the wrong direction — production is much faster than
the small-batch numbers suggest.

### Round-28 finding: the original 7/s was a regex-cache bug

cProfile on a 1 k real-name benchmark surfaced that
`manager_optimized._wb()` (a small regex helper used by the
priority-rules scorer) was being called ~4 million times during 1 k
entries — each call recompiling the same ~50-100 patterns from
scratch (Python's regex cache misses on this access pattern). 357 s
of the 379 s benchmark was burned in `re.compile` re-work.

Fix: one-line `@functools.lru_cache(maxsize=None)` decorator on
`_wb()`. The pattern set is bounded (priority lexicons are static
at module load), so an unbounded LRU is correct + cheap (~50-100
cached entries × ~200 bytes each).

Round-13 → round-28 trajectory on the real-name 10 k benchmark:

|       | entries/s | 1 M projection |
|-------|----------:|---------------:|
| Rd 13 |       7   | ~41 h          |
| Rd 28 | **152**   | **~1.8 h**     |

The "fastText subprocess is the bottleneck" hypothesis (which
motivated round 26's deferred in-process-fastText proposal) was
wrong. Round 26's deferral was right (fastText isn't the
bottleneck), but for the wrong reason — the actual bottleneck was
regex re-compilation in the rules scorer.

Reproduce + profile:

```bash
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000 --real-names
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000 --real-names --profile
# → docs/perf_profile_1000_real.txt
```

RSS scales sub-linearly: 460 MB at 1 k → 628 MB at 10 k → projected
~1-1.5 GB at 100 k. Memory is not the bottleneck.

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

A real-name batch (where rules fire on most entries) skips both
extra costs. Round 28 closed the regex-cache bug that dominated
the synthetic numbers; round 30 verified production throughput on
1 M real names end-to-end (see "What 1M actually looks like" below).
The synthetic-batch tables above are kept for trajectory context;
they're not the production number.

## What 1M actually looks like

**Round-30 measurement: 362 s (6.0 min) for 1 M real names.**
2 763 entries/s, 769 MB peak RSS, single Apple M1 process,
OFFLINE=1. The number is measured end-to-end through
`tools/run_benchmark.py --sizes 1000000 --real-names`, not
extrapolated.

Two pre-round-30 projections were both wrong:

1. **The pre-round-28 "~41 h/1M" projection** (linear extrapolation
   from the 7 entries/s 10 k benchmark) was wrong because the round-28
   `@functools.lru_cache(maxsize=None)` decorator on
   `manager_optimized._wb()` collapsed regex re-compilation overhead.
   See "Round-28 finding" above.
2. **The post-round-28 "~1.8 h/1M" projection** (linear extrapolation
   from 152 entries/s on real-name 10 k) was also wrong — by 18× in
   the *favourable* direction. It missed the streaming path that
   `process_batch` switches to at >100 k entries: chunks dispatched
   concurrently under `max_concurrency` give a near-10× boost the
   serial path doesn't deliver.

Production guidance: batch sizes ≥ 100 001 entries trigger the
streaming `AsyncBatchAggregator` path and run dramatically faster
per entry (2 763/s at 1 M). Below that threshold, throughput is
bounded by serial chunk processing (130-300/s).

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
- **Real-name benchmark.** Done in rounds 28 and 30 — see the
  round-30 table above for the headline 1 M number.
