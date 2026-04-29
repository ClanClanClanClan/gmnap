# Orphaned tests

These 15 files are parked here as the destination for orphaned
test code we don't want to lose but can't run as-is. The original
batch was 13 files sitting **untracked** in `tests/unit/` after a
previous round of test-suite work — never committed, never imported,
never run by CI. Two more landed later from round-2 / round-4
dead-code cleanups (`test_crossref_adapter.py` was the only
consumer of the deleted `src/authority/crossref_adapter.py`;
`test_v7_spec_ultra_compliance.py` referenced the 9-file
`src/core/end_to_end_orchestration` cluster that was deleted in
round 4). Rather than silently lose the work or pollute the
active `tests/unit/` namespace with broken imports, they're
parked here for triage.

## Why they're not in CI

Per-file pass rate when run in isolation against `main` at parking
time:

| File | Pass / Fail / Errors |
|---|---|
| `test_all_regions_fixtures.py`     | 0 / 1 / 7  — missing fixture file |
| `test_authority_schema_fixes.py`   | 7 / 4 / 0 |
| `test_crossref_thesis_adapter.py`  | 1 / 3 / 0 |
| `test_genealogy.py`                | 1 / 6 / 0 |
| `test_gnd_adapter.py`              | 0 / 3 / 0 |
| `test_hal_adapter.py`              | 0 / 3 / 0 |
| `test_llm_extractor.py`            | 3 / 12 / 0 |
| `test_oai_university_adapter.py`   | 1 / 3 / 0 |
| `test_openalex_adapter.py`         | 2 / 4 / 0 |
| `test_orcid_etd_adapter.py`        | 1 / 3 / 0 |
| `test_pipeline_v7.py`              | 13 / 21 / 0 |
| `test_wikidata_p184_adapter.py`    | 1 / 3 / 0 |
| `test_zbmath_adapter.py`           | 0 / 3 / 0 |
| `test_crossref_adapter.py`         | tests-dead-code (production `CrossrefAdapter` deleted 2026-04-27) |
| **Total**                          | **30 / 69 / 7** |

`test_crossref_adapter.py` was moved here on 2026-04-27 alongside
the deletion of `src/authority/crossref_adapter.py` (plus 12 other
confirmed-dead files in the singular `src/authority/` package). The
test itself was passing, but it was the only remaining caller of
the dead adapter — so the test was dead-code-testing-dead-code.
The canonical Crossref implementation lives at
`src/authorities/tier0/crossref.py:CrossrefFetcher` and is
exercised by the live-pipeline integration tests rather than by a
narrow unit test.

`test_v7_spec_ultra_compliance.py` was moved here on 2026-04-28 along
with the deletion of a 9-file dead cluster in `src/core/`
(`end_to_end_orchestration`, `pipeline_stage_implementation`,
`authority_source_integration`, `v7_quality_gates`,
`real_compliance_tracker`, `performance_benchmarker`,
`v7_orchestrator`, `pipeline_v7_hotfix`, plus
`tools/apply_hotfixes.py`). It was the only file that imported every
member of the cluster, didn't even collect (`NameError: pytest is
not defined`), wasn't in CI, and last-modified a month before the
cluster's siblings became orphaned. The file is preserved here in
case any of the cluster comes back, but realistically the
assertions inside reference an architecture that hasn't existed
since v7's first cleanup pass.

Every file is **less than 50 % green**. Adding any of them to CI as-is
would either fail the pipeline (most) or silently mask regressions
(the partial-pass ones).

## Common failure patterns

Spot-checking the failures:

1. **Schema drift.** Most adapter tests assert on response shapes
   that pre-date the V7 schema. Example: `test_gnd_adapter.py`
   expects `{"hits": [...]}` but the current adapter returns
   `{"GND": {"hit": False, "edges": []}}`.
2. **Stale module paths.** `test_genealogy.py` imports
   `src.genealogy.lookup` (singular) while the actual module is at
   `src.core.genealogy_lookup`.
3. **Missing fixtures.** `test_all_regions_fixtures.py` reads from
   `tests/fixtures/all_regions.json` which doesn't exist in the repo.
4. **OFFLINE handling regressions.** Some `test_*_adapter.py` tests
   assume the adapters call out to the live API even with `OFFLINE=1`,
   which contradicts the V7 OFFLINE-default rule.

## How to revive

Pick a file. For each failing test:

1. Read what the test asserts. Decide if the contract is still
   correct in V7.
2. If yes — fix the test (update the import path or the expected
   shape) until it goes green.
3. If no — delete the test (with a one-line note in the commit).
4. Once a file is 100 % green, `git mv docs/orphaned_tests/<file>
   tests/unit/` and add it to the `Core tests` step in
   `.github/workflows/ci.yml`.

## Why not just delete them

These files contain real assertions a previous contributor wrote.
Schema changes happen; the assertions might still encode useful
edge cases that the surviving CI doesn't cover. Easier to keep them
as a backlog than to lose the work entirely.

If a file proves to be entirely obsolete (every test asserts on a
contract that no longer exists), `git rm` it and note the deletion
in `CHANGELOG.md`.
