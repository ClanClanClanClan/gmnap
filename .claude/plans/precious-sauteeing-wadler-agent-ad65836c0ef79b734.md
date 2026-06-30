# GMNAP Comprehensive Audit Plan

## Validated Findings (Corrections from Initial Exploration)

Several claims from the initial exploration were verified as **incorrect**:

- **"19 of 37 regions fail to load"** -- FALSE. All 37 region class names in `manager_optimized.py` exactly match the classes exported by their modules. Every region loads correctly.
- **"Hardcoded DB password in global_deployment.py:538"** -- FALSE. The file `src/infrastructure/global_deployment.py` does not exist in this codebase.
- **"28 bare except clauses"** -- OVERSTATED. There is exactly **1 true bare `except:`** (in `src/regions/e_groups/e4_korea/scripts/git_integration.py:104`). However, there are **~20 `except Exception:` without `as e`** that silently swallow with `pass` -- a real but less severe issue.
- **"Missing script_switch.yaml"** -- FALSE. It exists at `config/script_switch.yaml`.
- **"Duplicate module paths for c5_arabic_maghreb"** -- FALSE. Only `c5_arabic_maghreb.py` exists; no subdirectory variant.
- **"jsonschema dependency unpinned"** -- FALSE. It is pinned to `==4.21.1` in `requirements.txt` (though `pyproject.toml` uses `>=4.21` which is standard for library-style packaging).

## Confirmed Issues (Prioritized)

---

### GROUP 1: Dead Code Cleanup -- `manager.py` vs `manager_optimized.py`
**Priority: HIGH | Effort: 1 hour | Parallelizable: Yes**

**Problem:** Two RegionManager implementations coexist:
- `src/regions/manager.py` (1,701 lines) -- old, only maps 14 regions, has stale import `e4_korea_processor`/`E4_Korea`, does `import fasttext` at top level (crashes if not installed)
- `src/regions/manager_optimized.py` (2,101 lines) -- current, maps all 37 regions, has graceful `try/except ImportError` for fasttext

**Who uses what:**
- Production CLI (`src/cli/gmnap.py`) uses `manager_optimized`
- Pipeline v7 (`src/core/pipeline_v7.py`) uses `manager_optimized`
- Pipeline v6 (`src/core/pipeline_v6.py`) uses old `manager`
- Several test files (`tests/hardcore/`, `tests/quality_gates/`) use old `manager`
- `analysis/comprehensive_audit.py`, `quick_performance_test.py` use old `manager`

**Also stale:** `src/regions/e_groups/e4_korea_processor.py` (10,670 bytes) -- only referenced by old `manager.py`. The real Korean processor is at `src/regions/e_groups/e4_korea/processor_lightweight.py`.

**Action:**
1. Audit every import of `src.regions.manager` (see list above) -- migrate to `manager_optimized` or confirm these are legacy-only paths
2. If `pipeline_v6.py` is no longer the production pipeline (Makefile confirms v7 is canonical), mark it and `manager.py` as deprecated
3. Consider deleting `e4_korea_processor.py` if no other code imports it
4. Update tests that import from old `manager` to use `manager_optimized`

**Verification:**
- `grep -rn "from src.regions.manager import" src/ tests/` should return zero results (or only deprecated files)
- All 976 tests still pass
- `make run-quick` still works

---

### GROUP 2: Silent Exception Swallowing in Authority Adapters
**Priority: HIGH | Effort: 2-3 hours | Parallelizable: Yes**

**Problem:** At least 8 authority adapter files have `except Exception: pass` patterns that silently hide failures. When an authority source fails, the pipeline silently continues without that data -- no logging, no metrics, no way to detect degradation.

**Affected files (core pipeline path):**
- `src/authority/oai_university_adapter.py:79` -- `except Exception: pass`
- `src/authority/crossref_adapter.py:85` -- `except Exception: pass`
- `src/authority/crossref_thesis_adapter.py:74` -- `except Exception: pass`
- `src/authority/orcid_etd_adapter.py:87,89` -- `except Exception: pass`
- `src/authority/wikidata_p184_adapter.py:95` -- `except Exception: pass`
- `src/authority/openalex_adapter.py:81` -- `except Exception: pass`
- `src/authority/hal_adapter.py` -- similar pattern
- `src/authority/gnd_adapter.py` -- similar pattern

**Also affected (less critical, in scripts):**
- `src/regions/e_groups/e4_korea/scripts/git_integration.py:104` -- sole bare `except: pass`
- Various Korea scripts with `except Exception:` followed by silent continues

**Action:**
1. In each authority adapter, replace `except Exception: pass` with `except Exception as e: logger.warning(f"... failed: {e}")` 
2. Add a counter metric so Prometheus can track adapter failure rates
3. The bare `except: pass` in `git_integration.py:104` should become `except Exception as e: logger.debug(...)`
4. In `src/core/pipeline_v7.py:380`, the catch `except (ImportError, Exception) as e` is redundant -- `Exception` already covers `ImportError`. Clean up to just `except Exception as e`.

**Verification:**
- Run test suite; no regressions
- Check that authority failures during pipeline runs now appear in logs
- Prometheus `/metrics` endpoint should show new counters

---

### GROUP 3: Silent Optional Dependency Degradation
**Priority: MEDIUM | Effort: 1-2 hours | Parallelizable: Yes**

**Problem:** `src/core/pipeline_v7.py` lines 39-67 silently set 6 optional modules to `None` when imports fail. If any of these are expected in production, the pipeline silently skips entire stages.

**Modules silently disabled:**
1. `src.core.globalid.generate_global_id` (GlobalID generation)
2. `src.graph.memgraph_ops.MemgraphPool` (graph database)
3. `src.quality.gates.QualityGateChecker` (quality gates)
4. `src.ops.spec_loader.load_specs` (spec loading)
5. `src.core.gdpr.gdpr_pipeline` (GDPR compliance)
6. `src.llm.etd_extractor.run_llm_etd` (LLM extraction)

**Similar patterns in:**
- `src/api/server.py:28,71` -- FastAPI/ASGI imports
- `src/utils/cache.py:21` -- cache backend
- `src/utils/database.py:20` -- DB driver
- `src/core/memgraph_client.py:17` -- neo4j driver

**Action:**
1. Add `logger.warning()` calls to each `except ImportError` block that sets a module to `None`
2. Add a startup summary log that lists which optional modules loaded and which are missing
3. For truly required modules (e.g., GlobalID generation in FULL/EXTREME modes), raise an error instead of silently degrading

**Verification:**
- Start pipeline with intentionally missing optional deps; confirm warnings appear in logs
- No regressions in test suite

---

### GROUP 4: TODO/FIXME Audit
**Priority: MEDIUM | Effort: 1-2 hours | Parallelizable: Yes**

**Confirmed TODOs in production code:**
1. `src/core/streaming_pipeline.py:448` -- "TODO: Implement streaming report generation"
2. `src/core/streaming_pipeline.py:454` -- "TODO: Implement streaming idempotency verification"
3. `src/core/pipeline_v6.py:318` -- "TODO: Re-enable after debugging" (Unicode normalization disabled!)
4. `src/core/pipeline_v6.py:1092` -- "TODO: Track actual changes"
5. `src/core/pipeline_v6.py:1664` -- "TODO: Add remaining tier-1 authority fetchers"

**Action:**
1. **Item 3 is the most concerning** -- linguistic normalization is disabled in pipeline_v6 "for debugging" but never re-enabled. Since v7 is canonical, verify v7 does not have this issue.
2. For each TODO, either resolve it or convert to a tracked issue with a reference number
3. Remove stale TODOs that are no longer relevant (e.g., pipeline_v6 if deprecated)

**Verification:**
- `grep -rn "TODO\|FIXME" src/` should show only tracked items

---

### GROUP 5: Memgraph Client Default Credentials
**Priority: MEDIUM | Effort: 30 minutes | Parallelizable: Yes**

**Problem:** `src/core/memgraph_client.py:70` has default parameters:
```python
def __init__(self, host="localhost", port=7687, username="gmnap", password="")
```

While credentials are overridden by env vars (line 83: `os.getenv("MEMGRAPH_PASSWORD", self.password)`), the empty-string default password and hardcoded username "gmnap" are still concerning for production.

**Action:**
1. Change defaults to require explicit configuration or env vars
2. Add a warning if the default empty password is used in non-test environments
3. Review Docker Compose files for credential management

**Verification:**
- Pipeline startup should warn if using default credentials
- Docker deployment still works

---

### GROUP 6: Linting and Code Quality
**Priority: LOW | Effort: 2-3 hours | Parallelizable: Yes**

**Problem:** Unused imports and variables across the codebase. The CI `ruff` step runs but `continue-on-error: true` is not set for it, so these likely already pass. Need to verify current ruff config.

**Action:**
1. Run `ruff check src/ --select F401,F841` to get current count
2. Fix unused imports (F401) in batches by directory
3. Fix unused variables (F841) -- may require more care
4. Ensure ruff config in `pyproject.toml` enables these rules

**Verification:**
- `ruff check src/ --select F401,F841` returns zero violations
- All tests pass

---

### GROUP 7: Exception Handler Redundancy
**Priority: LOW | Effort: 1 hour | Parallelizable: Yes (with Group 2)**

**Problem:** Pattern `except (ImportError, AttributeError, Exception) as e:` appears in both `manager.py:1698` and `manager_optimized.py:2098`. `Exception` already covers both `ImportError` and `AttributeError`, making the first two redundant. This pattern appears in several other files too.

**Action:**
1. Clean up redundant exception type lists across the codebase
2. Where the intent is to catch specific types differently, restructure into multiple except blocks

**Verification:**
- No behavioral change; purely cosmetic

---

## What NOT to Fix (Acceptable Technical Debt)

1. **`except Exception as e: logger.error(...)` patterns** -- These are valid defensive programming for a pipeline that should not crash on individual record failures. The 254 occurrences across 90 files are largely appropriate.

2. **`pyproject.toml` uses `>=` for dependencies** -- This is correct for a distributable package. The `requirements.txt` has exact pins for reproducible installs. Both are needed.

3. **Magic numbers in region processors** -- These are typically Unicode codepoints, transliteration weights, or algorithm-specific thresholds documented in the GMNAP spec. Extracting them to constants would reduce readability.

4. **Import-time side effects** -- The FastText model loading uses a singleton pattern with lazy loading. This is already optimized and intentional.

5. **Multiple pipeline versions (v6, v7)** -- v7 is canonical per Makefile, but v6 may be needed for backward compatibility. Deprecate but don't delete yet.

6. **Korea-specific backup files** (`src/regions/e_groups/e4_korea/backups/`) -- These are clearly marked as backups and don't affect production.

---

## Execution Order and Parallelism

```
Phase 1 (can run in parallel):
  ├── Group 1: Dead code cleanup (manager.py, e4_korea_processor.py)
  ├── Group 2: Exception swallowing in authority adapters
  └── Group 5: Memgraph default credentials

Phase 2 (can run in parallel, after Phase 1):
  ├── Group 3: Optional dependency warnings
  ├── Group 4: TODO/FIXME audit
  └── Group 7: Exception redundancy cleanup

Phase 3 (final):
  └── Group 6: Linting cleanup (run last -- other changes may introduce/fix lint issues)
```

**Total estimated effort: 8-12 hours**

**Critical gate:** After each phase, run `pytest tests/ -v --timeout=300` to verify no regressions.
