# Changelog

All notable changes to this project go here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [SemVer](https://semver.org/) once a tagged release lands.

## [Unreleased] — 2026-04-27

The "ship-readiness" arc continued: reproducibility gates, calibration
honesty, backward-chain lineage queries, Git LFS for the genealogy
JSON, and a no-shortcuts restoration of 8 ex-RED test files.

### Added (2026-04-27 audit pass)

- **Confidence calibration analysis** (`tools/calibration.py`,
  `docs/calibration.md`, `docs/calibration.json`). Runs RegionManager
  against the 843-entry adjudicated benchmark, bins predictions into
  10 confidence buckets, computes Brier score + Expected Calibration
  Error (ECE = 0.186 — substantial miscalibration documented
  honestly with reliability diagram + remediation notes), emits an
  ASCII reliability diagram. The 0.75 fastText bucket is 96 % accurate
  while 0.85+ rules buckets are 72–76 % accurate — system over-reports
  confidence on "easy" cases.
- **Backward-chain lineage queries** — `query_lineage()` and
  `traverse_lineage()` now accept `direction="ancestors"` (default,
  follows `-[:DOCTORAL_ADVISOR]->`) or `direction="descendants"`
  (follows `<-[:DOCTORAL_ADVISOR]-`). Wired into the API as
  `/api/v1/lineage/{id}?direction=descendants`. `GenealogyLookup`
  builds a reverse-adjacency cache lazily for the JSON fallback path.
  CLI gets the matching `--direction` flag.
- **Git LFS pin** for `data/genealogy_enrichment.json` (~6 MB, 20 598
  records). `.gitattributes` registers the filter; fresh clones
  require `git lfs install && git lfs pull` to materialise the file
  (the README and DEMO call this out).
- **`requirements.lock` reproducibility gate** — `make lock`
  regenerates the pinned-transitive-deps lockfile via `pip-compile
  --strip-extras`. CI's lint job re-runs the same command and diffs
  against the committed copy (filtered through `grep -v '^#'` so the
  pip-compile-baked output filename in the header doesn't trip the
  gate). Drift fails the build with a "run make lock" pointer.
- **`docs/grafana_dashboard.json`** — drop-in 9-panel Grafana
  dashboard targeting the existing `/metrics` Prometheus exporter.
  Covers uptime, throughput, latency p50/p95/p99 by endpoint,
  pipeline duration, schema-error rate, authority-source hits by
  tier. Imports cleanly via the Grafana UI.
- **`retry_with_backoff` (already shipped, now actually wired)** —
  `_fetch_wikidata_p184`'s QID-search and SPARQL legs are now wrapped
  via inner closures so transient `aiohttp.ClientError` /
  `httpx.NetworkError` / `OSError` / `asyncio.TimeoutError` get
  retried up to 2× with 0.5 s × 2^n backoff. The retry helper had
  6 unit tests for months but no production caller — this commit is
  the wire-up.
- **`docs/orphaned_tests/` + README** — 13 untracked test files that
  were sitting in `tests/unit/` (30/107 green, 69 fail, 7 collection
  errors). Parked outside the pytest testpaths with per-file
  pass-rate, common failure patterns, and a revival recipe.

### Fixed (2026-04-27 audit pass)

- **8 RED tests properly restored — no shortcuts** (40 + 38 + 6 +
  17 + 24 + 5 + 34 + 0 = 164 tests). Earlier work had documented
  them as "modernise-later" stubs in `docs/test_followups.md`;
  reverted that bandaid and rebuilt the production APIs the tests
  actually need:
  `src/core/gdpr.py` (`PERSONAL_DATA_FIELDS`, cohort-aware
  `apply_birth_year_privacy`, `scrub_sources`, ShadowNode conversion
  via deterministic 16-char SHA-256 hash, `gdpr_pipeline`
  end-to-end orchestrator);
  `src/quality/gates.py` (`QualityGateChecker` with mode-aware
  thresholds, Sørensen-Dice bigram `dice()` helper);
  `src/authority/common.py` (`retry_with_backoff` async helper,
  see *Added* above for its eventual wiring);
  `src/authority/manager_tier01.py` (tiered `TIER_HANDLERS = {0:[…],
  1:[…], 2:[…], 3:[…]}` orchestrator, `enrich_by_tiers()` with
  parallel `asyncio.gather`, live Wikidata P184 SPARQL path);
  `src/pipeline/stage5_collision_analytics.py` (in-batch +
  cross-batch dedup via `--N` suffix, persisted JSON registry,
  `_emit_edges_csv` audit trail; `ensure_unique_global_ids`
  preserved as back-compat);
  `src/pipeline/stage9_write_and_diff.py` (deterministic
  `write_snapshot`, `generate_sql_changelog`,
  `generate_cypher_changelog`, honours `SOURCE_DATE_EPOCH`);
  `src/regions/base.py` (`load_yaml_config()` + `_YAML_CACHE` for
  per-region YAML extension points).
- **`stage9_write_and_diff` jinja2 import** lazy — module top-level
  `from jinja2 import …` was breaking import on environments without
  jinja2. Moved into `_render_html_diff` (the only function that
  needs it).
- **CI lockfile-sync false positive** — pip-compile bakes its
  `--output-file` argument into the generated header, so even a
  cosmetically-identical regenerated lockfile diffed against the
  committed copy. Strip leading-`#` lines from both before comparing.
- **DEMO.md output snippets re-grounded** in real CLI / API output —
  CanonicalLatin → Name, BirthYear → Born, fictitious indented
  lineage tree → real JSON, Ramanujan D2 → D1, Tao "diaspora
  conflict" claim moved from CLI (where it doesn't surface) to API
  (where it does). Added the `git lfs install && git lfs pull` step
  the new LFS pin requires.
- **CSP `style-src 'unsafe-inline'` removed** — the d3 tree renderer
  uses `.attr("transform", …)` not inline `.style`, so the inline-
  styles allowance was unused. Tightened to
  `default-src 'self'; script-src 'self'; style-src 'self'`.

### Removed (2026-04-27 audit pass)

- **`ensure_yaml_loaded()` + `_apply_yaml_overrides()`** in
  `RegionSpec` — the auto-merge machinery had no production caller
  (no `config/regions/` directory has ever shipped). Replaced with
  the explicit `load_yaml_config()` extension point and a
  `_YAML_CACHE` for repeat reads. CLAUDE.md was claiming "37/37 YAML
  config files auto-loaded"; that was always a fiction.
- **`docs/test_followups.md`** — the "modernise-later" stub for the
  8 RED tests. Deleted along with the bandaid.

---

## [Unreleased] — 2026-04-24

The "ship-readiness" arc: tree visualization in the web UI, adversarial
test infrastructure, a live Memgraph integration, and a wholesale
rehabilitation of the test suite that CI was silently skipping.

### Added

- **Genealogy tree visualization in the web UI.** d3 v7 vendored
  locally (no CDN dependency for offline demos). Profile view now
  shows a top-down ancestor tree with depth selector (3 / 5 / 8),
  pan + zoom, click-to-navigate, and graceful empty-state messaging.
- **Adversarial Playwright browser harness** (`tools/browser_smoke.py`,
  31 scenarios) covering happy-path, XSS, Unicode (jp/ru/ar/gr/
  diacritics/emoji), edge inputs, responsive viewports, keyboard
  shortcuts, correction form, tree-depth navigation, server-500
  mid-flight, and rapid-fire load. Wired into CI as a dedicated
  `browser-test` job that uploads screenshots + a markdown audit
  report as artefacts on every push.
- **Live Memgraph integration** — `tools/load_memgraph_from_enrichment.py`
  loads `data/genealogy_enrichment.json` into Memgraph 2.12 (idempotent,
  MERGE-based), and `src/genealogy/query.py` reads it back via Bolt for
  the `/api/v1/lineage/{id}` endpoint. New `memgraph-test` CI job
  using GHA `services:` block runs four e2e tests against a real
  Memgraph container on every push.
- **`/readyz` Bolt probe** — the readiness handler now performs a real
  `verify_connectivity()` via `src.genealogy.query._driver`, replacing
  the earlier raw-TCP-socket check that returned 200 even when
  Memgraph was alive but auth was broken.
- **`ARCHITECTURE.md`** — reviewer-facing one-pager covering split
  geo / name-origin design, three-tier suffix system, same-group gate,
  honest abstention policy, operating-point selection.
- **`DEMO.md`** — 10-minute reviewer walkthrough with CLI + web UI
  screenshots + API curl examples.
- **`tools/triage_tests.py`** + `docs/test_triage.md` — single-shot
  classifier of every `tests/unit/` file by collectibility (GREEN /
  GREEN-untracked / YELLOW / RED) plus actual pass/fail count, used
  to triage the silenced-test backlog.
- **Genealogy coverage** expanded from 6 172 → 20 598 mathematicians
  via OpenAlex affiliations merge (15 120 author records, 14 432 of
  them new). Institution coverage 4.3 ×, Country coverage 4.3 ×.
- **Vendored ISO-3166 alpha-2 → English country-name map** in
  `tools/build_genealogy_enrichment.py` covering ≈ 95 % of OpenAlex's
  118 country codes.
- **`tools/capture_screenshots.py`** — 8 canonical demo shots
  (landing, search, profile, tree depth-5, multi-advisor tree,
  correction dialog, mobile viewport, unknown-name) for `DEMO.md`.
- **`tools/rc_curve.py`** — risk-coverage threshold sweep across
  scorer-margin × fastText-p1 × fastText-margin combinations,
  exposed via env vars. Result documented in `docs/risk_coverage.md`.
- **23 + 18 + 11 + 4 = 56 new unit tests** (genealogy lookup, query,
  fastText worker, duckdb shape regressions).
- **CI: 24 silenced test files rehabilitated** — coverage rose from
  17 / 62 tracked files (~140 tests) to 41 files (≈ 2 020 tests).
  Includes the entire `tests/unit/korean/` directory plus
  `test_a3_nordic_baltic`, `test_a4_oceania`, `test_cjk_roundtrip`,
  and 5 GREEN-untracked files now committed for the first time.
- **CI: `docker-build` job** smoke-tests the production image on every
  push, including a `/healthz` + `/readyz` boot check.

### Changed

- **FastText CLI tiebreaker is now a persistent worker**
  (`FastTextCLIWorker`, singleton per process). Replaces the
  fork+exec+model-load-per-query pattern. Measured: **~60 ×** per-call
  speedup (43 q/s → ≈ 2 700 q/s) and **~2.3 ×** end-to-end on the
  synthetic full-pipeline benchmark (190 → 430 entries/s).
- **Hashcash mining** in the browser batches 256 SHA-256 digests per
  `Promise.all`. Amortizes microtask overhead across many hashes;
  18-bit mining drops from 10 + s to ~ 1 s on a modern CPU.
- **`traverse_lineage` edge endpoints** are now canonical display
  names (`"Bernoulli, Johann"`) instead of opaque GlobalIDs. The web
  UI tree label is now human-readable.
- **`/api/v1/lineage` Memgraph fallback gate** now triggers on
  `result.get("root_name")`, not on `result.get("edges")`. Prevents
  silently returning stale YAML / JSON for graph-resident leaves
  (mathematicians the graph knows have no advisors).
- **`gmnap process` rejected-output-path error** now includes the
  bad path, a copy-pasteable suggestion, and an explanation —
  reviewer following `DEMO.md` no longer bounces off the guard.
- **`src/genealogy/__init__.py`** uses lazy `__getattr__` (PEP 562)
  so `from src.genealogy.query import …` doesn't pull `requests`,
  which the Docker image deliberately omits.

### Fixed

- **A2 Western Europe casefold bug** — `apply_unicode_fold_exceptions`
  was calling `text.casefold()` on every name, lowercasing
  `"Euler, Leonhard"` to `"euler, leonhard"` on response. Limited to
  ß/ẞ → ss/SS expansion only; case is preserved.
- **`[hidden] { display: none !important }` CSS rule** — the
  `.loading { display: flex }` author rule was overriding the UA
  stylesheet's hidden-attribute behaviour, leaving the spinner
  visible after `el.hidden = true`. Now overridden globally.
- **Debounce race that hid the profile after navigation** — the
  300 ms debounced search from `searchInput.fill()` fired AFTER the
  user pressed Enter or clicked a result, calling `showView("results")`
  and ripping the open profile out from under the user. Added
  `.cancel()` to the debounce helper, called from Enter and from
  `renderProfile()`. Browser harness run-time dropped 195 s → 78 s
  (this race was the cause of the flakiness).
- **`DuckDBAnalytics.suffix_duplicates` empty-list return shape** —
  the `self.skipped` fallback returned a bare `[]` for empty-list
  inputs, breaking pipeline Stage 5's `entries, n = …` unpack with
  `ValueError`. XSS payloads that Stage 2 security-rejected emptied
  the list and crashed the whole `/api/v1/process` request with a
  500. Now always returns `(entries, 0)` when entries are passed.
- **XSS browser-harness scenarios were vacuous** — the original
  payloads didn't call `alert()`, so the dialog-fired check was
  trivially satisfied. Hardened: payloads now use `alert(1)`,
  added `xss:svg`, and the assertion snapshots `<script>/<img>/<svg>`
  counts before/after to detect any payload that gets parsed as HTML
  instead of escaped. Proven by neutering `escapeHtml`: 3/6 scenarios
  now fail (was 0/5).
- **`FastTextCLIWorker.predict()` AttributeError under `python -O`** —
  `assert self._proc and …` was stripped by the optimizer, then
  `.write()` hit None. Replaced with a runtime check inside the
  io_lock; widened `except` to include `AttributeError` + `ValueError`.
- **`FastTextCLIWorker.shutdown()` race with `predict()`** — shutdown
  now acquires `_io_lock` before nulling `_proc`, so concurrent
  predicts can't observe the half-torn-down state.
- **`FastTextCLIWorker` deadlock on huge input** — input is now
  capped to 4096 characters before `stdin.write`. Without this, a
  64 KB+ input would block the flush forever (the readline that
  would drain the response is behind the same lock).
- **`FastTextCLIWorker.get()` duplicate-spawn on path aliases** —
  keys on `realpath(expanduser(...))`, so tilde-form and symlinked
  paths share a single subprocess instead of spawning duplicates.
- **`/api/v1/lineage` Memgraph fallback gate (CRITICAL)** — see
  *Changed* above; legitimate graph leaves were silently falling
  through to stale YAML.
- **`init_memgraph.cypher` schema mismatch (CRITICAL)** — see
  *Removed*. The init file was creating a separate
  `:Mathematician` subgraph the lineage code never read.
- **`/readyz` returned 200 against broken Memgraph** — see
  *Changed*. Now performs a real Bolt handshake.

### Removed

- **`init_memgraph.cypher`** — used `:Mathematician` while the
  loader uses `:Person`; pre-seeded sample nodes that disagreed
  with the loaded data; defined `:GraphMetadata`, `:QueryTemplates`,
  `:QualityGates` nodes that no code reads. The loader is now the
  single source of schema truth.
- **`docker-compose.yml --init-file=…` + the volume mount** for
  the cypher file. The loader is idempotent.
- **`src/regions/a_groups/a2_western_europe.py`** — legacy flat
  duplicate of the package version, contained the casefold bug
  even after the package version was fixed. Confirmed dead via
  `python -c 'from src.regions.a_groups.a2_western_europe import …'`
  loading the package, not the flat module.

### CI

- **`test`** job: 17 → 41 test files (≈ 2 020 tests, up from ~ 140).
- **New jobs**: `browser-test` (Chromium + Playwright + 31 scenarios),
  `memgraph-test` (live Memgraph 2.12 services-block + 4 e2e tests),
  `docker-build` (image build + boot-check on `/readyz`+`/healthz`).
- **`GMNAP_FREE_RPM`** env override on the rate limiter so the
  browser harness's rapid-fire scenario can hit the API at full
  speed in CI without 429s.

### Repo hygiene

- **Untracked `tests/.pytest_cache/`** removed from git tracking
  (was committed before `.gitignore` caught it; churned with every
  pytest run). `tests/.pytest_cache/` and
  `docs/screenshots/browser_audit/` (per-run generated screenshots)
  added to `.gitignore`.
