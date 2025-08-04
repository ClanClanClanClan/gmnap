# GMNAP V7 Architecture Reorganization Plan

## Executive Summary

This plan outlines the reorganization of the GMNAP codebase to fully comply with v7 specifications as defined in `implementation_plan.md`. The current structure has evolved organically and needs consolidation, cleanup, and proper architectural alignment.

## Current vs Target Architecture Analysis

### 🔴 Major Discrepancies Found

1. **Duplicate src/ structures**:
   - `/src/` (old structure with archive/, authorities/, core/, etc.)
   - `/src/gmnap/` (v7 structure but incomplete)
   - Need to merge and consolidate into single `/src/gmnap/`

2. **Missing v7 components**:
   - `/src/gmnap/linguistic/` - Not implemented
   - `/src/gmnap/validation/` - Not implemented  
   - `/src/gmnap/utils/` - Not implemented
   - `/src/gmnap/authorities/tier1/` - Empty
   - `/src/gmnap/authorities/tier2/` - Missing

3. **Misplaced components**:
   - `/src/authorities/` should be `/src/gmnap/authorities/`
   - `/src/core/` duplicates `/src/gmnap/core/`
   - `/src/linguistic/`, `/src/utils/`, `/src/validation/` at wrong level

4. **Scattered test infrastructure**:
   - `/tests/` has proper subdirectories but missing some v7 tests
   - Korean tests in `/src/gmnap/regions/e_groups/e4_korea/tests/`
   - Test scripts scattered in `/cleanup_work/test_scripts/`

5. **Documentation chaos**:
   - `/docs/` exists but only has architecture/ subdirectory
   - `/documentation/` created during cleanup
   - Korean docs in `/src/gmnap/regions/e_groups/e4_korea/docs/`
   - Many docs still in root after cleanup

## Reorganization Actions

### Phase 1: Core Structure Consolidation

```bash
# 1. Merge duplicate src structures
mv src/authorities/* src/gmnap/authorities/
mv src/core/* src/gmnap/core/  # Careful - merge with existing
mv src/linguistic src/gmnap/
mv src/utils src/gmnap/
mv src/validation src/gmnap/

# 2. Remove old src/ directories
rm -rf src/archive/  # Move to /archive/src_archive/
rm -rf src/authorities/
rm -rf src/core/

# 3. Create missing tier directories
mkdir -p src/gmnap/authorities/tier1/
mkdir -p src/gmnap/authorities/tier2/
```

### Phase 2: Test Infrastructure Unification

```bash
# 1. Move Korean tests to main test suite
mv src/gmnap/regions/e_groups/e4_korea/tests/* tests/unit/korean/

# 2. Move scattered test scripts
mv cleanup_work/test_scripts/test_*.py tests/integration/
mv cleanup_work/test_scripts/comprehensive_*.py tests/quality_gates/

# 3. Create missing v7 test directories
mkdir -p tests/sea_roundtrip/
mkdir -p tests/concurrency/
mkdir -p tests/memory_peak/
mkdir -p tests/msc_provenance/
mkdir -p tests/fake_api/
mkdir -p tests/secret_scan/
```

### Phase 3: Documentation Consolidation

```bash
# 1. Merge documentation directories
mv documentation/* docs/
rmdir documentation/

# 2. Move Korean docs to central location
mv src/gmnap/regions/e_groups/e4_korea/docs/* docs/korean/

# 3. Create v7 doc structure
mkdir -p docs/api/
mkdir -p docs/regional/
mkdir -p docs/linguistic/
```

### Phase 4: Data & Config Organization

```bash
# 1. Consolidate data directories
mkdir -p data/fixtures/
mkdir -p data/region_index/
mv src/gmnap/regions/e_groups/e4_korea/data/* data/korean/

# 2. Create proper config structure
mkdir -p config/regional/
# Move weights.yaml, diaspora.yaml, source_manifest.json from cleanup
```

### Phase 5: Tools & Scripts Cleanup

```bash
# 1. Organize tools
mkdir -p tools/dictionaries/
mkdir -p tools/cli/
mv cleanup_work/utilities/* tools/

# 2. Consolidate scripts  
mv cleanup_work/fixes/*.py scripts/fixes/
mv cleanup_work/analysis/*.py scripts/analysis/
mv src/gmnap/regions/e_groups/e4_korea/scripts/* scripts/korean/
```

### Phase 6: Archive Old Work

```bash
# 1. Archive cleanup work
mv cleanup_work/ archive/session_work_20250728/

# 2. Archive old results
mv cleanup_work/results/* archive/test_results/

# 3. Clean Korean backups
mv src/gmnap/regions/e_groups/e4_korea/backups/* archive/korean_backups/
```

## Final V7-Compliant Structure

```
gmnap/
├── src/gmnap/              # Single source tree
│   ├── core/               # Pipeline, config, globalid, unicode
│   ├── regions/            # All regional modules (a-h groups)
│   ├── authorities/        # Tier 0/1/2 API integrations
│   ├── linguistic/         # Rules, transliteration, variants
│   ├── validation/         # Schema, quality gates, roundtrip
│   └── utils/              # Cache, database, async helpers
├── config/                 # All configuration files
│   ├── weights.yaml
│   ├── diaspora.yaml
│   ├── source_manifest.json
│   └── regional/           # Per-region configs
├── data/                   # All data files
│   ├── region_index.csv
│   ├── fixtures/           # Test data
│   └── korean/             # Korean-specific data
├── docs/                   # All documentation
│   ├── architecture/       # System design docs
│   ├── api/                # API documentation
│   ├── regional/           # Regional implementation docs
│   ├── korean/             # Korean-specific docs
│   └── schema.json         # YAML schema v1.5
├── tests/                  # Comprehensive test suite
│   ├── unit/
│   ├── integration/
│   ├── quality_gates/
│   ├── property/
│   ├── stress/
│   ├── security/
│   └── [other v7 tests]
├── scripts/                # All executable scripts
│   ├── setup_dev.sh
│   ├── get_fasttext.sh
│   ├── fixes/              # Fix scripts
│   ├── analysis/           # Analysis scripts
│   └── korean/             # Korean-specific scripts
├── tools/                  # Development tools
│   ├── dictionaries/
│   └── cli/
├── cache/                  # Runtime caches only
│   ├── gs/
│   └── bad_json/
├── archive/                # Historical/old code
│   ├── src_archive/        # Old src structures
│   ├── korean_backups/
│   └── session_work_20250728/
└── [root files]            # Only essential files
    ├── README.md
    ├── requirements.txt
    ├── Makefile
    ├── pytest.ini
    ├── docker-compose.yml
    ├── Dockerfile
    └── .gitignore
```

## Implementation Priority

1. **Critical** - Fix duplicate src/ structures (prevents import conflicts)
2. **High** - Consolidate tests (enables proper quality gates)
3. **High** - Unify documentation (improves maintainability)
4. **Medium** - Organize data/config (cleaner structure)
5. **Low** - Archive old work (cleanup)

## Risk Mitigation

1. **Before any moves**: Create full backup
2. **Test imports**: After each phase, run `python -m pytest tests/unit/test_imports.py`
3. **Git tracking**: Commit after each successful phase
4. **Rollback plan**: Keep archive of original structure

## Expected Benefits

1. **Clean imports**: `from gmnap.core.pipeline import Pipeline`
2. **No duplicates**: Single source of truth for each component
3. **V7 compliance**: Matches implementation_plan.md exactly
4. **Test coverage**: All tests in standard locations
5. **Documentation**: Single docs/ directory with clear structure
6. **Maintainability**: Clear separation of concerns

## Next Steps

1. Review and approve this plan
2. Create backup of current state
3. Execute Phase 1 (most critical)
4. Validate imports still work
5. Continue with remaining phases