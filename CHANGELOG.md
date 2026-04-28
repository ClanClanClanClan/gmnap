# Changelog

All notable changes to this project go here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [SemVer](https://semver.org/) once a tagged release lands.

## [Unreleased] — 2026-04-28 (Tier 1 — honest evaluation methodology)

The post-audit follow-up: a proposed Tier 1 list of three items
intended to fix the ship-readiness gaps that round-4's "still flag"
list left open. All three landed in this batch.

### Removed (Tier 1.3)

- **9-file dead-code cluster in `src/core/`** (4368 lines, b4a9de1).
  Trace via the import graph:
  `end_to_end_orchestration` (orphan) →
  `pipeline_stage_implementation`, `authority_source_integration`
  (only consumer was the orphan); `v7_quality_gates` was alive only
  by way of 3 other orphans (`real_compliance_tracker`,
  `performance_benchmarker`, `v7_orchestrator`); `pipeline_v7_hotfix`
  patched in an attribute (`_force_immediate_processing`) that's now
  baked into `pipeline_v7.py:366`, so the hotfix and its sole
  consumer (`tools/apply_hotfixes.py`) are obsolete. Sole external
  claimant `tests/paranoid/test_v7_spec_ultra_compliance.py`
  (754 lines) didn't even collect (`NameError: pytest`); moved to
  `docs/orphaned_tests/`.

### Added (Tier 1.2)

- **`pytest-cov` instrumentation in CI** (adcaf16). Both `Core
  tests` and `Property tests` pytest invocations now pass
  `--cov=src --cov-append`. New `Coverage summary` step parses
  `coverage.xml`, prints line + branch %, asserts a `--cov-fail-
  under` floor (currently 0; will ratchet up after the first green
  run reveals the actual number). New `Upload coverage artifact`
  step keeps coverage.xml retrievable from the GHA UI for 14 days.
  `pytest-cov>=4.0` added to `requirements-dev.txt` for local devs.

### Added (Tier 1.1)

- **Stratified 80/20 train/test split for the benchmark.** Until
  now, `tests/fixtures/name_origin_benchmark.json` was both the
  training set for calibration / threshold tuning AND the test set
  for headline-precision claims. Every published number was
  in-sample. New module `src/regions/benchmark_split.py` does a
  group-stratified deterministic split (seed 42, ~80/20 per group);
  `load_train()` / `load_test()` for consumers. 7 unit tests pin
  the invariants (determinism, no overlap, group representation,
  per-group fraction bounds, sentinel on the seed value).

### Changed (Tier 1.1)

- **`tools/calibration.py` now fits PAV on TRAIN, evaluates on TEST.**
  The headline calibrated ECE drops from "in-sample artefact-perfect"
  (round-3 reported 0.0009 → fixed-PAV showed 0.0000) to **honest
  out-of-sample 0.0390** on the 168 held-out entries. Still under
  the 0.05 well-calibrated threshold but no longer gamed. The
  markdown report shows four columns side-by-side: raw test, calibrated
  test (the headline), train-applied (sanity check), and 5-fold CV
  on train (variance estimate). All four reliability diagrams are
  rendered.

  The runtime knots in `data/calibration_isotonic.json` are now
  fitted on the train set only; calling `apply()` from
  `src/regions/calibration.py` with `GMNAP_CALIBRATE_CONFIDENCE=1`
  uses these honest knots.

  Numbers on the GMNAP benchmark:

  | Metric | Raw test | Calibrated test (held-out) | CV on train |
  |---|---:|---:|---:|
  | ECE   | 0.1881 | **0.0390** | 0.0018 |
  | Brier | 0.139  | 0.114      | 0.115  |

### Known follow-ups

- `tools/rc_curve.py` (operating-point sweep) still runs against
  the full benchmark via embedded subprocess source. Refactoring it
  to use the train/test split would require restructuring the
  template; out of scope for this Tier 1 batch but flagged for
  a follow-up.
- Coverage floor in CI is `0` — the first green run will reveal the
  baseline; a follow-up commit will ratchet to that minus 1 pp.

## [Unreleased] — 2026-04-28 (audit-pass round 4)

Round-3's audit listed four "still flagged" items that hadn't been
fixed yet. Round 4 fixes all four.

### Added (round 4)

- **Per-process Fetcher pool** in `src/authority/manager_tier01.py`.
  Each `(module_path, class_name)` pair instantiates exactly one
  `AuthorityFetcher` and reuses it across calls. Previously every
  `_fetch_*` invocation built a fresh instance, paying ~1 ms of
  `aiohttp.ClientSession` setup AND resetting per-instance rate-limit
  state — so a 10k-entry batch that wanted 10 RPS got hit at full
  executor speed. Pool drains via `_close_fetcher_pool()` (tests + an
  atexit hook). Locked test confirms 20 sequential calls produce
  exactly 1 `__init__` invocation; `_close_fetcher_pool()` makes the
  next call rebuild.
- **5-fold cross-validated ECE / Brier in the calibration report.**
  `tools/calibration.py:_kfold_cv_metrics()` shuffles deterministically
  (seed=42), holds out one fold of 5, fits PAV on the remaining 4,
  applies the knots to the held-out fold, and aggregates the OOF
  predictions for one final 10-bucket ECE. Honest out-of-sample
  number, not measured-on-train. Result on the 654-sample GMNAP
  benchmark: train-set calibrated ECE = 0.0000 (the artefact-prone
  measure that round 3 flagged), **5-fold CV ECE = 0.0039** (well
  under the 0.05 well-calibrated threshold). Both numbers + a third
  reliability diagram are now shown in `docs/calibration.md`.
- **5 new k-fold CV unit tests** in `tests/unit/test_pav_fitter.py`:
  empty-input behaviour, seed determinism, holdout-count
  preservation, near-perfect input giving low ECE, no-input-mutation
  invariant.
- **2 new pool-semantics tests** in
  `tests/unit/test_canonical_fetcher_delegation.py`: instance-reuse-
  across-20-calls, close-then-rebuild.
- **2 new Crossref_Thesis legacy-shape tests**: success path includes
  `match=True / works>=1`, miss path keeps `match=False / works=0`.

### Fixed (round 4)

- **Crossref_Thesis success shape mismatched legacy contract.** The
  cached/OFFLINE/empty-name paths returned `{hit, match, works}`
  while the new live-fetch path (`_call_canonical_fetcher`) returned
  only `{hit, source_id, ...}`. Downstream tests in
  `test_authority_manager.TestCrossrefThesis::test_cached_result`
  asserted on `match`/`works`. Post-process the live result to add
  `match = bool(hit)` and `works = 1 if hit else 0` (or pull from
  upstream metadata when available). All four code paths now expose
  the same key set.

## [Unreleased] — 2026-04-28 (audit-pass round 2 + 3)

Self-audit after the round-1 audit caught more rot. Two threads:
deeper authority-stack consolidation (round 2) and a paranoid review
that surfaced a real bug + missing test coverage (round 3).

### Fixed (2026-04-28)

- **PAV isotonic fitter was statistically wrong on tied input.**
  Self-audit: passing `samples = [(0.5, 1), (0.5, 0), (0.5, 1),
  (0.5, 1)]` should give one knot with `cal_p = 0.75` (3/4 correct).
  Old fitter produced 3 knots all at threshold 0.5 with cal_ps
  `[0.5, 1.0, 1.0]`, and the apply path returns the FIRST match
  → `0.5`. Fix: pre-aggregate ties into single weighted (sum_y,
  count) blocks before the merge loop, so PAV's output now has at
  most one knot per unique input confidence. Re-fit on the GMNAP
  benchmark: 7 redundant knots → 2 clean knots; calibrated values
  for tied inputs now match the empirical mean.

### Added (2026-04-28)

- **Unit tests for the PAV fitter** —
  `tests/unit/test_pav_fitter.py` (16 tests). Covers empty input,
  single sample, all-correct, all-wrong, monotonic input,
  single/chain violations, **tie aggregation** (the bug above),
  apply edge-clipping, fit-then-apply roundtrip monotonicity, and
  GMNAP-shaped benchmark data. The fitter previously had only an
  end-to-end integration test via `tools/calibration.py`.
- **Unit tests for `_call_canonical_fetcher`** —
  `tests/unit/test_canonical_fetcher_delegation.py` (9 tests). Pins
  the contract between the V7 tier orchestrator and the canonical
  `src/authorities/tier{0,1}/X.Fetcher` classes: successful
  translation, cache-hit short-circuit, OFFLINE-skip, exception
  containment, missing-fetcher graceful degradation, empty-name
  guard, tier-1 sources, and a mixed-outcome batch where one source
  blows up but the others survive.
- **Calibration report honesty disclaimer.** `docs/calibration.md`
  now flags two artefacts that make the post-cal ECE = 0.0000 look
  better than it is: (1) the metric is computed measured-on-train
  with no held-out evaluation, (2) PAV collapses everything into one
  10-bucket bin so ECE is trivially small *across* buckets even
  though within-bucket spread persists. The calibrator is doing
  real work (correctly pulls 0.95 → 0.87) but the headline number
  isn't probabilistic-grade calibration.

## [Unreleased] — 2026-04-27 (audit-pass round 2)

Round-2 sweep: deleted the entire dead duplicate authority module
plus made the stubs that survived actually call live HTTP.

### Added (round 2)

- **`_call_canonical_fetcher(module_path, class_name, source_name,
  name)` helper** in `src/authority/manager_tier01.py`. Lazily imports
  a `src/authorities/tierN/X.Fetcher` class, instantiates it with
  empty config, awaits its `fetch(name)` wrapped in
  `retry_with_backoff` (2 retries × 0.5 s exp backoff), translates
  `FetchResult` → flat tier01 dict shape. All 8 tier-0/1 `_fetch_*`
  shims (OpenAlex, Crossref, ORCID_ETD, Crossref_Thesis, zbMATH,
  GND, HAL, OAI_University) now delegate through this helper when
  `OFFLINE=0`. Until this commit they all silently returned
  `{hit: False}` regardless of OFFLINE, so the live HTTP path was
  unreachable from `pipeline_v7.py`'s enrichment stage.
- **PAV-isotonic confidence calibrator (opt-in via
  `GMNAP_CALIBRATE_CONFIDENCE=1`).** `tools/calibration.py` now
  fits a Pool-Adjacent-Violators isotonic regressor on the
  843-entry adjudicated benchmark and writes the knots to
  `data/calibration_isotonic.json`. `src/regions/calibration.py`
  is the runtime read side: lazy-loads the knots, exposes
  `apply(p) -> float`. Wired into
  `RegionManager.detect_region` via `dataclasses.replace` so
  cached results carry the calibrated value. Identity (no-op) when
  the env var is unset, preserving back-compat for any test or
  fixture that pinned a specific raw confidence. ECE on the
  benchmark: 0.1860 → 0.0009 (with the round-3 honesty caveat
  above; calibrator successfully pulls overconfident raw 0.95 down
  to ~0.87).
- **Backward-chain in the web UI.** `static/app.js` learns a
  `<select id="tree-direction">` next to the depth selector;
  Ancestors (default) / Descendants. Threads `direction=` to
  `/api/v1/lineage/{id}?direction=...`, flips the panel title
  ("Advisor Tree" ↔ "Student Tree"), direction-aware empty/error
  copy. CSS shares the existing `.tree-depth-label` styling via
  a comma'd selector. 31/31 browser-smoke scenarios green.
- **`gmnap lineage --direction` CLI flag.** Mirror of the API
  parameter; default `ancestors`. Local-YAML walker is
  forward-only by construction, so `descendants` skips it and
  goes straight to `GenealogyLookup.traverse_lineage(...,
  direction=...)`.
- **Pre-commit hook tracked in repo + install script.**
  `.git/hooks/pre-commit` (which validated E4 Korea + 37-region
  load time) was clone-local; new clones had no validation. Moved
  to `scripts/git_hooks/pre-commit`; added
  `scripts/install_hooks.sh` (worktree-aware via `git rev-parse
  --git-common-dir`, idempotent, env-var skip). Wired into `make
  setup` and a new `make install-hooks` target. README
  "Contributing" section explains the hook + the `--no-verify`
  escape hatch.

### Removed (round 2)

- **13 confirmed-dead files in `src/authority/`** (544 LoC).
  `manager.py` (orchestrator never called), `policy.py`,
  `merge_authority_data.py`, `manager_policy_hook.py`, plus 9
  `*_adapter.py` files (only ever referenced by the dead
  `manager.py`). Inbound call graph traced via the Explore agent;
  no production caller, no surviving test caller, no string-based
  references. Only `manager_tier01.py` and `common.py` remain in
  the singular package — the full canonical authority stack lives
  in `src/authorities/` (plural).
- **`tests/unit/test_crossref_adapter.py`** moved to
  `docs/orphaned_tests/` — was the sole consumer of the deleted
  `src/authority/crossref_adapter.py`. Dropped from CI's Core
  tests step. Canonical Crossref Fetcher
  (`src/authorities/tier0/crossref.py:CrossrefFetcher`) is
  exercised by integration tests rather than a narrow unit test.

### Changed (round 2)

- **CLAUDE.md authority claims.** "9 adapters with real HTTP
  calls" was technically true but pointed at the deleted
  `src/authority/*_adapter.py` files. Rewrote the section to
  reflect the actual canonical path through
  `manager_tier01._fetch_* → _call_canonical_fetcher →
  src/authorities/tierN/X.Fetcher.fetch()`, plus the per-source
  table now lists the canonical Fetcher class for each source.

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
