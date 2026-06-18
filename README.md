# MathLineage — Global Mathematician Name Authority

## What this is

MathLineage disambiguates mathematician names by linguistic origin
and academic genealogy. Given a name like `Erdős, Pál` or
`Hilbert, David`, it returns the regional naming convention
(family-first vs given-first, particle handling, transliteration),
canonical form, advisor chain, institution, and a stable global ID
deterministically derived from the canonical form.

## Who it's for

Researchers and tools that need to **deduplicate mathematician
records across sources** — bibliometric tooling, prosopography
projects, mathematics-genealogy maintainers, citation graphs that
need to merge `Erdős, Pál`, `Erdos, P.`, `Paul Erdős`, and `P.
Erdős` into one entity with verifiable provenance.

## Why it matters

Naming-convention disagreement is the dominant source of
deduplication errors in cross-source academic data. Generic
name-matching libraries don't know that Hungarian writes family-
first, that Tamil names are patronymic-not-surname, or that
`van der Waerden` is one particle-and-surname not three tokens.
This project encodes those 37 region-specific rules + a vetted
genealogy of ~39,500 mathematicians (MGP seed + Wikidata SPARQL +
OpenAlex affiliations).

## Quick Start

```bash
# One-time setup (pip install + compile fasttext CLI; ~30 seconds)
make setup

# Query a name (region + genealogy + institution)
gmnap query "Euler, Leonhard"

# Start the API server
gmnap serve --port 8080

# Open the web UI
open http://localhost:8080
```

`make setup` is the recommended path. For a minimal install without the
fasttext tiebreaker (rules-based detection only) run
`pip install -r requirements.txt` instead; the CLI and API still work,
just with lower name-origin accuracy on hard cases.

For a reproducible install matching exactly the dependency graph CI
runs against, use `pip install -r requirements.lock` (transitive
versions pinned by `make lock` / `pip-compile`).

**Git LFS.** `data/genealogy_enrichment.json` (~6 MB) is tracked via
Git LFS. After cloning, run `git lfs install && git lfs pull` once
to materialise the file (a fresh clone retrieves the LFS pointer by
default and you'll see a 130-byte stub instead of the real JSON).

For a step-by-step reviewer walkthrough (CLI + web UI + API, with
screenshots), see **[DEMO.md](DEMO.md)**. For the architecture
one-pager covering the five design decisions an evaluator asks about,
see **[ARCHITECTURE.md](ARCHITECTURE.md)**. For the running list of
changes, see **[CHANGELOG.md](CHANGELOG.md)**.

For contributing, see **[CONTRIBUTING.md](CONTRIBUTING.md)** (pre-commit
hook, audit battery, CI gates). For security policy and how to report
a vulnerability, see **[SECURITY.md](SECURITY.md)**. For the licensing
status of the bundled data (`data/genealogy_enrichment.json`) — which
is a derivative of Wikidata + OpenAlex + curated MGP entries, each with
its own provenance — see **[DATA_SOURCES.md](DATA_SOURCES.md)**.

## Features

- **37 Regions**: Full linguistic processing (clean/augment/validate/order_key) for Anglo, Germanic, Slavic, Arabic, CJK, South Asian, African, and more
- **9 Authority Sources**: OpenAlex, Crossref, ORCID, HAL, GND, Wikidata, zbMATH, OAI, Crossref Thesis
- **12-Stage Pipeline**: Unicode normalization → region detection → authority enrichment → collision analytics → schema validation → output
- **Genealogy Enrichment**: ~39,500 mathematicians with advisor chains, birth years, and institutions (seeded from MGP + Wikidata SPARQL)
- **Web Interface**: Dark-themed SPA at localhost:8080
- **API**: REST endpoints with rate limiting, hashcash PoW, Prometheus metrics
- **GDPR Compliant**: ShadowNode conversion, birth year masking

### Measured Performance (OFFLINE mode, Apple M1, rounds 28–30)

**1 M real names processed in 362 s (6.0 min) — measured, not
projected.** Headline read: **2 763 entries/s at 1 M scale**.
See `docs/perf_characterization.md` for methodology, profile dumps
and the round-28 / round-30 trajectory.

| Path | Batch size | Throughput | Wall clock | RSS peak |
|---|---:|---:|---:|---:|
| `RegionManager.detect_region` (stage 2 only, warm) | — | ~780 / s | — | 230 MB |
| `V7Pipeline.process_batch` (synthetic) | 1 000 | 273 / s | 3.7 s | 355 MB |
| `V7Pipeline.process_batch` (synthetic) | 10 000 | 192 / s | 52.1 s | 450 MB |
| `V7Pipeline.process_batch` (real, `--real-names`) | 1 000 | 153 / s | 6.6 s | 379 MB |
| `V7Pipeline.process_batch` (real) | 10 000 | 135 / s | 74.1 s | 496 MB |
| `V7Pipeline.process_batch` (real) | 100 000 | 295 / s | 339.6 s | 812 MB |
| **`V7Pipeline.process_batch` (real) — production** | **1 000 000** | **2 763 / s** | **362.0 s (6.0 min)** | **769 MB** |

The 100 k → 1 M jump (~9.4×) is real and structural:
`process_batch` switches at > 100 k entries to the
`AsyncBatchAggregator` streaming path, which coalesces 1 000-entry
chunks dispatched concurrently under `max_concurrency`. RSS at 1 M
is *lower* than at 100 k because streaming releases each chunk's
intermediate state as the sink consumes it.

Round-28's `@functools.lru_cache(maxsize=None)` on
`manager_optimized._wb()` was the unlock. cProfile showed the
priority-rules scorer was recompiling the same ~50–100 regex
patterns ~4 million times per 1 k batch — 357 s of a 379 s run
burned in `re.compile`. Single-line fix → 22× speedup on the real-
name 10 k benchmark. Earlier "fastText subprocess is the bottleneck"
hypothesis was wrong. Single-run numbers; ±15 % run-to-run variance
is normal on a laptop.

Reproduce:
- Synthetic: `make bench-real` → no, that's real. Synthetic is
  `PYTHONPATH=. python3 tools/run_benchmark.py --sizes 1000,10000`
- Real names: `make bench-real` (samples from
  `data/genealogy_enrichment.json` so this needs `git lfs pull`
  to have run).

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness probe |
| `/readyz` | GET | Readiness probe |
| `/api/v1/query?name=...` | GET | Single name lookup |
| `/api/v1/lineage/{id}` | GET | Academic genealogy |
| `/api/v1/process` | POST | Batch processing |
| `/metrics` | GET | Prometheus metrics |

## CLI Commands

```bash
gmnap query "Name"           # Region detection
gmnap process input.json     # Batch pipeline
gmnap validate input.json    # Schema validation
gmnap serve --port 8080      # Start API server
gmnap sources                # List authority sources
gmnap regions                # List 37 regions
gmnap lineage --id GID       # Academic genealogy
```

## Docker

```bash
cp .env.example .env         # Configure environment
docker compose up -d          # Start all services
curl localhost/healthz        # Verify via nginx
curl localhost:8080/healthz   # Verify direct
```

## Configuration

Copy `.env.example` to `.env` and configure. Key variables:
- `OFFLINE=1` — cache-only mode (default, no network needed)
- `PIPELINE_MODE=quick` — quick/full/extreme
- `GMNAP_API_TOKENS=token1,token2` — paid tier Bearer tokens

## Testing

```bash
PYTHONPATH=. pytest tests/unit/ -q --timeout=120
```

**~2,376 tests collected** across the unit / authority / cjk / db / v7 / regions directories CI runs — covering region detection accuracy, 500-entry golden dataset, 843-entry adjudicated name-origin benchmark, end-to-end workflows, API security, CLI hardening, web interface, and nginx config. Plus 32-scenario adversarial Playwright browser-test job and live Memgraph integration. Coverage gated at `--cov-fail-under=20` with explicit floors at line ≥ 22 % / branch ≥ 18 % (current 23.93 % / 19.41 %).

## Region Detection

Split geo/name-origin architecture validated by external onomastics expert:
- **100% emitted-leaf precision** on the full 523-entry adjudicated benchmark *(in-sample)*; held-out test-set numbers are reported separately by `tests/unit/test_benchmark_evaluation.py` and pinned at the same level on the 168-entry test split (see `src/regions/benchmark_split.py`)
- **100% CC-based accuracy** across 216 territories
- Three-tier suffix system + fastText CLI tiebreaker + same-group gate
- Honest abstention: returns R0 + group hint when uncertain, never forces a wrong leaf
- Confidence calibration: PAV isotonic fit on 675-entry train, **held-out test ECE = 0.039** (raw 0.188; full report in `docs/calibration.md`). Enable runtime via `GMNAP_CALIBRATE_CONFIDENCE=1`

## Genealogy Enrichment

`data/genealogy_enrichment.json` (~39,500 mathematicians) backs the
Advisors / Institution / BirthYear fields in CLI and API responses.
Sources, in order of priority:

1. `data/mgp_validation_data.json` — 15 canonical demo entries from the
   Math Genealogy Project.
2. Hand-curated stubs in `tools/build_genealogy_enrichment.py` for
   transitive advisors like Johann Bernoulli and Pfaff.
3. `data/wikidata_genealogy.json` — 4,385 mathematicians fetched from
   Wikidata SPARQL (`P184` doctoral advisor, `P569` birth date, `P69`
   institution). Fetched with `scripts/data/fetch_wikidata_genealogy.py`.
4. `data/ml_training/openalex_10k_mathematicians.json` — 15,120
   OpenAlex author records giving `Institution` + `Country` coverage
   for working mathematicians the Wikidata P184 query misses
   (people without a formally-recorded doctoral advisor).

Name matching is diacritic-insensitive (`Erdős` ↔ `Erdos`) and handles
given-name order, parenthetical aliases, hyphenated compounds, and
Dutch/German particles (`von Neumann` ↔ `Neumann … von`). Unknown names
pass through without fake data.

The lineage endpoint accepts either a GlobalID or a canonical name:

```bash
curl "localhost:8080/api/v1/lineage/name:Euler,%20Leonhard?depth=3"
# Returns Euler → Johann Bernoulli → Jacob Bernoulli
```

Rebuild after editing sources:

```bash
python3 scripts/data/fetch_wikidata_genealogy.py   # optional, hits Wikidata SPARQL
PYTHONPATH=. python3 tools/build_genealogy_enrichment.py
```

## Contributing

`make setup` installs a git pre-commit hook from
`scripts/git_hooks/pre-commit` into your local `.git/hooks/`. The
hook runs two fast smoke checks (E4 Korea region loads, all 37
regions load under 2 s) and blocks commits that break either.

If you skipped `make setup` or set up a fresh worktree:

```bash
make install-hooks    # or: bash scripts/install_hooks.sh
```

To bypass on a one-off (e.g. emergency revert), `git commit
--no-verify`. The hook is informational, not authoritative — CI
runs the full lint + test matrix on every push regardless.

## License

**Code**: MIT (see [LICENSE](LICENSE)).

**Bundled data** (`data/genealogy_enrichment.json` + region YAML
configs + adjudicated benchmarks): a mix of CC0 (Wikidata,
OpenAlex), CC-BY (HAL, OAI-PMH harvests, zbMATH Open metadata),
and curated entries (Mathematics Genealogy Project seed + manual
adjudication). Per-source provenance + attribution requirements
are spelled out in **[DATA_SOURCES.md](DATA_SOURCES.md)**.
