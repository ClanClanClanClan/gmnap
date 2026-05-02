# MathLineage — Global Mathematician Name Authority

## What It Does

Processes mathematician names across 37 linguistic regions, detecting geographic origin, normalizing naming conventions, and enriching with authority data from 9 sources.

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

## Features

- **37 Regions**: Full linguistic processing (clean/augment/validate/order_key) for Anglo, Germanic, Slavic, Arabic, CJK, South Asian, African, and more
- **9 Authority Sources**: OpenAlex, Crossref, ORCID, HAL, GND, Wikidata, zbMATH, OAI, Crossref Thesis
- **12-Stage Pipeline**: Unicode normalization → region detection → authority enrichment → collision analytics → schema validation → output
- **Genealogy Enrichment**: ~39,500 mathematicians with advisor chains, birth years, and institutions (seeded from MGP + Wikidata SPARQL)
- **Web Interface**: Dark-themed SPA at localhost:8080
- **API**: REST endpoints with rate limiting, hashcash PoW, Prometheus metrics
- **GDPR Compliant**: ShadowNode conversion, birth year masking

### Measured Performance (OFFLINE mode, Apple M1, 2026-04-28)

Three distinct measurements — see `docs/perf_characterization.md`
for methodology and reproducibility. **The real-name 10 k row is
the production-relevant headline number.**

| Path | Batch size | Throughput | 1M projection |
|---|---:|---:|---:|
| `RegionManager.detect_region` (stage 2 only, warm) | — | ~780 / s | ~21 min |
| `V7Pipeline.process_batch` (synthetic) | 1 000 | 21 / s | 803 min |
| `V7Pipeline.process_batch` (synthetic) | 10 000 | 29 / s | 583 min (~9.7 h) |
| `V7Pipeline.process_batch` (real names, `--real-names`) | 1 000 | 5 / s | 3 462 min |
| **`V7Pipeline.process_batch` (real names) — production** | **10 000** | **7 / s** | **2 489 min (~41 h)** |

Real names are ~4× **slower** than synthetic at every scale —
real entries trigger more work in stage 4 (authority cache lookups),
stage 6 (Bayesian solver iterates on actual advisor edges), and
stages 7-8 (more populated metadata). The earlier README projection
of "real expected 2-5× faster than synthetic" was wrong;
`docs/perf_characterization.md` documents the gap analysis.

Honest production read: **~7 entries/s sustained, ~41 h/1M real
names**. Typical batches of < 100 k entries finish in 2-4 hours
end-to-end, acceptable for offline batch processing. RSS scales
sub-linearly: 460 MB at 1 k → 628 MB at 10 k → projected ~1-1.5
GB at 100 k.

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

**~2,376 tests collected** across the unit / authority / cjk / db / v7 directories CI runs — covering region detection accuracy, 500-entry golden dataset, 843-entry adjudicated name-origin benchmark, end-to-end workflows, API security, CLI hardening, web interface, and nginx config. Plus 32-scenario adversarial Playwright browser-test job and live Memgraph integration. Coverage gated at `--cov-fail-under=15` (line + branch combined; line-only is 17.96 %, branch is 12.4 %).

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

MIT
