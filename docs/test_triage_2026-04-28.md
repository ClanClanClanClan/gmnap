# Non-CI test triage (Tier 2.2, 2026-04-28)

The repo has 13+ test directories outside CI's `Core tests` list.
Tier-2 audit item 2.2 was to triage them: find what passes,
promote it into CI, document the rest.

## Method

For each non-CI directory under `tests/`, run pytest with
`--timeout=30 -p no:cacheprovider` and record the headline result.
Anything dependent on `OFFLINE=0` or external services is naturally
gated by environment (most fail "no network" or skip).

## Results

| Directory | Result | Decision |
|---|---|---|
| `tests/authority/` | 1 passed | **Added to CI** |
| `tests/cjk/` | 8 passed | **Added to CI** |
| `tests/coherence/` | 12 failed | Skip (broken assertions on a removed module) |
| `tests/compliance/` | 2 passed / 5 failed | Skip (mixed; needs per-file work) |
| `tests/concurrency/` | 0 collected | Empty |
| `tests/db/` | 3 passed | **Added to CI** |
| `tests/error_recovery/` | 1 passed / 1 failed | Skip (one broken test) |
| `tests/extreme/` | 5 skipped | Skip (all are `pytest.skip` for OFFLINE=1) |
| `tests/genealogy/` | 2 passed / 28 errors | Skip (collection errors, broken imports) |
| `tests/hardcore/` | not triaged | Out of scope this round |
| `tests/idempotency/` | 2 passed / 2 failed / 9 errors | Skip (collection errors) |
| `tests/live/` | not run | Skip (`@pytest.mark.live` — needs network) |
| `tests/memory/` | 14 passed / 3 failed | Skip (3 flaky perf-style assertions) |
| `tests/mock_api/` | 11 passed / 2 failed | Skip (2 broken; could fix per file later) |
| `tests/paranoid/` | not triaged | Out of scope (some files moved to `docs/orphaned_tests/` already) |
| `tests/performance/` | not triaged | Naturally gated (perf assertions) |
| `tests/production/` | not triaged | Out of scope |
| `tests/property/` | 1/2 collected (other has ImportError) | Skip the broken one |
| `tests/v7/` | 7 passed | **Added to CI** |

**Net delta**: +19 tests in the CI Core-tests step, sourced from
4 previously-untouched directories. The added test files:

```
tests/authority/test_manager_offline.py
tests/cjk/test_v7_cjk_roundtrip.py
tests/db/test_changelog_edges.py
tests/db/test_pool_tx.py
tests/v7/test_v7_basic.py
tests/v7/test_v7_complete.py
tests/v7/test_v7_complete_integration.py
tests/v7/test_v7_full_pipeline.py
tests/v7/test_v7_imports.py
```

## Why not just add every "mostly passing" file

The user's mandate is "no failures of any kind". Adding a 14/17
file means the 3 failures gate every PR. Each of those 3 needs
fixing first — that's a separate per-file investigation, not a
bulk operation.

The 4 directories above are 100 % pass on triage. They go straight
into CI without per-file work.

## Follow-ups

- Per-file fix-up for `tests/coherence/`, `tests/compliance/`,
  `tests/idempotency/`, `tests/genealogy/` — each is a separate
  diagnosis (broken imports, schema drift, removed dependency).
- Move clearly-orphaned test files to `docs/orphaned_tests/`
  alongside the existing 14.
- `tests/hardcore/`, `tests/paranoid/`, `tests/performance/`,
  `tests/production/` — bigger directories that need their own
  triage pass.
