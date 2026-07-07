# Performance characterization (R54 rewrite, 2026-07-06)

## ⚠️ Correction notice — the old "1 M in 362 s" claim was FALSE

Every version of this document before R54 (2026-07-06) claimed **"1 M
real names → 362 s (6.0 min), 2 763 entries/s, measured not projected,
via the `AsyncBatchAggregator` streaming path."** That claim was
**false**, and it is fully retracted.

What actually happened: `process_batch` switched at `>100_000` entries
to a `StreamingPipelineAdapter` that fed **16-entry microbatches
serially** into `_process_batch_internal`. Every 16-entry microbatch
hit a "fast path" (`_process_small_batch_fast`, the `≤25` branch) that
did **no region detection unless `CanonicalNative` was set** — and the
benchmark entries carried `CanonicalLatin`, not `CanonicalNative`. So
the "1 M run" was, per entry, essentially `entry.copy()`: no region
detection, no enrichment, no GDPR, no collision analytics, no writes.
The benchmark timed a **dict-copy loop** and reported its speed as
pipeline throughput.

Proof (R54, reproducible): forcing the old streaming path on 30 real
names yielded `DetectedRegion` on **0/30** entries; the real serial
path yields **30/30**. The "streaming path is ~10× faster" was ~10×
*less work*, not more speed.

R54 deleted the streaming detour and the lossy fast path. Every batch
size now runs the identical real stage sequence. Scale comes from a
real process pool (`_process_batch_parallel`), because the workload is
CPU-bound (region detection dominates) and asyncio delivers **zero**
CPU parallelism for CPU-bound work.

## TL;DR — honest current numbers

Measured on an 8-core Apple-silicon laptop, `OFFLINE=1`, real names
sampled from `data/genealogy_enrichment.json`, **clean `output/` dir**
(see the stage-9 caveat below):

| Path | N | Throughput | Region coverage |
|---|---:|---:|---:|
| serial (`GMNAP_NO_PARALLEL=1`), real names | 4 000 | 184 / s | 4000/4000 |
| serial, real names | 10 000 | 233 / s | 10000/10000 |
| parallel (process pool), real names | 4 000 | 268 / s | 4000/4000 |
| parallel, real names | 10 000 | 348 / s | 10000/10000 |
| parallel, real names — full dataset (R56) | 39 891 | 221 / s | 100 % |
| **parallel, synthetic+CC (R56) — MEASURED 1 M** | **1 000 000** | **849 / s — 19.6 min** | **1 000 000 / 1 000 000** |

- Serial and parallel outputs are **byte-identical** at 10 k
  (`tests/v7/test_parallel_path.py`).
- The ~1.5× parallel speedup at 10 k is **Amdahl-capped by the
  batch-global tail**; the per-entry fraction grows with N.

## The measured 1 M (R56, 2026-07-07)

**1 000 000 entries end-to-end in 1 178 s (19.6 min), 849 entries/s.**
RSS peak 10.3 GB (24 GB machine), on-disk output 1.4 GB (changelog DB).
Region coverage verified by querying **all 1 000 000 rows** in the
stage-9 DuckDB: 100.00 % carry a real `DetectedRegion`. The spec §7
warm-cache gate passes at measured scale (19.6 ≤ 35 min QUICK).

Two honest qualifiers:

1. **Workload shape.** The 1 M run is the synthetic benchmark corpus,
   which carries `CountryCodes` — the geo branch resolves via the CC
   fast path, so per-entry cost is lower than CC-less input. Real names
   with no CC take the full name-origin cascade and measure **221 / s on
   the complete 39 891-entry real dataset** (the largest real workload
   that exists in this repo). A CC-less 1 M-scale run projects to
   ~75 min from that anchor — that single number is a projection and is
   labeled as one.
2. **Memory.** Results are held in memory: budget ~10 GB per 1 M rows,
   or split the caller's batch on smaller machines.

### The four scale defects the campaign found (all fixed)

Getting 1 M to *complete at all* took three attempts; each found a
latent defect no test had ever exercised (nothing had genuinely run
≥ 100 k before):

| # | Defect | Impact at 1 M | Fix |
|---|---|---|---|
| 1 | Stage-5 `DuckDBAnalytics.load_entries`: `executemany` (row-wise parameter conversion, ~1.5 ms/row) + a per-row `json.dumps` payload nothing reads | **6 hours** (run killed) | temp-CSV + vectorized `read_csv` — 0.23 s / 100 k, **~370× measured**; payload dropped |
| 2 | Stage-6 fallback: `e.get("GlobalID", f"unknown_{entries.index(e)}")` — `dict.get` evaluates its default EAGERLY, so an O(n) full-dict-comparison scan ran per entry → **O(n²)** | projected **days** (run killed at 100 % CPU in `PyObject_RichCompare`) | `enumerate()` — 0.52 s at 200 k; plus k-sampled betweenness for > 10 k-node graphs |
| 3 | Stage-9 writers built monolithic strings (canonical JSON of everything; an HTML diff with **two** canonical dumps per entry) | multi-GB strings / HTML | streamed `json.dump` (byte-identical); HTML capped at `GMNAP_HTML_DIFF_MAX_ROWS` (5 000) with an announced truncation row |
| 4 | Stage-11 idempotency re-run ran its own stage 9 into the same `output/`, **overwriting the main run's artifacts** with the 20-entry sample | 1 M run left a 20-entry `stage9.yaml` | re-run skips write stages (comparison is in-memory); `tests/v7/test_stage11_no_clobber.py` |

## Where the time goes (real names)

Per-stage breakdown, serial, real names (representative):

- **Stage 2 region detection** — the dominant per-entry cost
  (~6 ms/name). This is the actual product work (classifying each name
  by linguistic origin) and is exactly what the process pool
  parallelizes across cores.
- **Stages 1, 3, 4** (unicode, region hooks, authority-offline) —
  small per-entry costs.
- **Batch-global tail** (run once in the parent, ~8-9 s at 4 k):
  - Stage 5 collision analytics (DuckDB `:memory:`) — ~2 s.
  - Stage 9 write/diff — **R54 fixed the dominant cost here.** The
    DuckDB changelog writer issued **two single-row `execute()`
    statements per entry** (an upsert + a changes-row). DuckDB is a
    columnar OLAP engine where single-row inserts are micro-
    transactions; this was ~7.5 ms/entry (~2 hours projected for 1 M
    *just to write the changelog*). Now batched into `executemany`
    inside one transaction (~5×). Output is byte-identical.
  - Stage 10 report + Stage 11 idempotency re-run — ~2 s each.

### Stage-9 caveat: wipe `output/` before benchmarking

The stage-9 changelog DB (`output/stage9.duckdb`) **persists across
runs** and always treats the batch as new INSERTs (`_previous_entries`
is empty), so it grows unboundedly. A stale multi-hundred-MB DB from
prior runs inflates stage-9 write time several-fold and will make a
benchmark look far slower than a fresh run. Always `rm -rf output/`
before measuring. (The unbounded-growth behaviour itself is a known
operational limitation, tracked separately.)

### ShortFormClusters O(k²) cap

Stage 7 emits, for each entry, the sorted GlobalID list of every other
entry sharing one of its short forms. A short form shared by *k*
entries therefore stored a *k*-length list on each of *k* members —
**O(k²)**. Pathological input (e.g. synthetic `Surname{i}, Given{i}`,
where every entry has initials "S.G.") hit **100 KB/entry**. R54 caps
the stored list at `GMNAP_SHORTFORM_CLUSTER_CAP` (default 64) and logs
when a cluster is capped. Real, diverse names rarely approach the cap;
the synthetic worst case dropped from 101 KB to 2.6 KB/entry.

## The round-28 regex-cache fix is real (and unrelated)

Separately and genuinely: `manager_optimized._wb()` (a regex helper in
the priority-rules scorer) was recompiling the same ~50-100 patterns
~4 million times per 1 k batch — most of the wall-clock was in
`re.compile`. A one-line `@functools.lru_cache(maxsize=None)` fixed it.
That fix is in place and load-bearing. It has **nothing to do** with
the retracted streaming claim — it made the *real* per-entry stages
faster; the streaming claim was about a path that skipped those stages
entirely.

## Reproduce

```bash
rm -rf output/          # stale changelog DB inflates stage 9 — always wipe
PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000 --real-names

# force serial vs parallel to compare (parallel needs N >= threshold):
GMNAP_NO_PARALLEL=1 PYTHONPATH=. python3 tools/run_benchmark.py --sizes 10000 --real-names
```

`--real-names` samples `data/genealogy_enrichment.json` (needs
`git lfs pull`). The fastText model is not bundled; without it, stage-2
falls back to rules-only detection (still classifies, just without the
ML tiebreaker) — see the model-distribution note in the README.

## Knobs

| Env | Default | Effect |
|---|---|---|
| `GMNAP_NO_PARALLEL` | unset | `=1` forces the serial path |
| `GMNAP_PARALLEL_THRESHOLD` | 20000 | batches ≥ this size use the process pool |
| `GMNAP_PARALLEL_WORKERS` | cpu_count-1 | worker processes in the pool |
| `GMNAP_SHORTFORM_CLUSTER_CAP` | 64 | max gids stored per short-form cluster |
