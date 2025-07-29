# GMNAP V7 Architecture Guide

## Overview

This document describes the finalized GMNAP v7 architecture after the comprehensive reorganization completed on 2025-07-28. The structure now fully complies with the v7 specifications outlined in `implementation_plan.md`.

## Directory Structure

```
gmnap/
├── src/gmnap/                    # Single unified source tree
│   ├── __init__.py
│   ├── core/                     # Core pipeline and utilities
│   │   ├── __init__.py
│   │   ├── pipeline.py           # Main 10-stage pipeline with pattern detection
│   │   ├── pipeline_v6.py        # Legacy v6 pipeline
│   │   ├── streaming_pipeline.py # Streaming variant
│   │   ├── config.py             # Configuration management
│   │   ├── database.py           # DuckDB/SQLite interface
│   │   ├── errors.py             # Custom exceptions
│   │   ├── globalid.py           # SHA-256 ID generation
│   │   ├── monitoring.py         # Performance monitoring
│   │   └── unicode_handler.py    # NFC→NFKD→custom→NFC chain
│   │
│   ├── regions/                  # Regional processing modules
│   │   ├── __init__.py
│   │   ├── manager.py            # Regional processor manager
│   │   ├── a_groups/             # Western regions
│   │   │   ├── a1_anglo_sphere.py
│   │   │   └── a2_western_europe.py
│   │   ├── b_groups/             # Slavic regions
│   │   │   ├── b1_east_slavic.py
│   │   │   └── b2_south_slavic_central.py
│   │   ├── c_groups/             # Middle East/Caucasus
│   │   │   ├── c2_persian_tajik.py
│   │   │   ├── c3_arabic_levant_nile.py
│   │   │   └── c4_arabic_gulf.py
│   │   ├── d_groups/             # South Asia (not implemented)
│   │   ├── e_groups/             # East Asia
│   │   │   ├── e1_sinophone_mainland.py
│   │   │   ├── e3_japan.py
│   │   │   └── e4_korea/        # Korean converter subsystem
│   │   └── g_groups/             # Latin America/Iberian
│   │
│   ├── authorities/              # External API integrations
│   │   ├── __init__.py
│   │   ├── base.py               # Authority fetcher base class
│   │   ├── cache.py              # Caching layer
│   │   ├── tier0/                # Free APIs
│   │   │   ├── __init__.py
│   │   │   ├── dblp.py
│   │   │   ├── google_scholar.py
│   │   │   ├── orcid.py
│   │   │   └── wikidata.py
│   │   ├── tier1/                # Premium APIs (future)
│   │   └── tier2/                # Experimental (future)
│   │
│   ├── linguistic/               # Language processing
│   │   ├── __init__.py
│   │   ├── rules.py              # 34 linguistic rules
│   │   └── transliteration.py   # Script conversion
│   │
│   ├── validation/               # Quality assurance
│   │   ├── __init__.py
│   │   ├── quality_gates.py      # Performance metrics
│   │   └── roundtrip.py          # Script round-trip tests
│   │
│   ├── utils/                    # Utility modules
│   │   ├── __init__.py
│   │   ├── async_utils.py        # Async helpers
│   │   ├── cache.py              # Zstandard caching
│   │   └── database.py           # Database utilities
│   │
│   └── v7_compat.py              # V7 compatibility layer
│
├── config/                       # Configuration files
│   ├── regional/                 # Per-region configurations
│   └── [config files TBD]
│
├── data/                         # Data files
│   ├── corp/                     # Corporate data
│   ├── fixtures/                 # Test fixtures
│   ├── korean/                   # Korean-specific data
│   └── region_index/             # ISO territory mappings
│
├── docs/                         # Documentation
│   ├── architecture/             # System design docs
│   │   ├── V7_ARCHITECTURE_GUIDE.md (this file)
│   │   └── [legacy docs]
│   ├── korean/                   # Korean converter docs
│   ├── session_reports/          # Development session reports
│   └── api/                      # API documentation
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   │   └── korean/               # Korean-specific tests
│   ├── integration/              # Integration tests
│   ├── quality_gates/            # Quality gate tests
│   ├── property/                 # Property-based tests
│   ├── security/                 # Security tests
│   ├── stress/                   # Stress tests
│   ├── memory/                   # Memory tests
│   ├── hardcore/                 # Hardcore tests
│   ├── v5_tests/                 # Legacy v5 tests
│   ├── mock_api/                 # Mock API tests
│   ├── sea_roundtrip/            # SEA script tests
│   ├── concurrency/              # Concurrency tests
│   ├── memory_peak/              # Peak memory tests
│   ├── msc_provenance/           # MSC provenance tests
│   ├── fake_api/                 # Fake API tests
│   └── secret_scan/              # Secret scanning
│
├── scripts/                      # Executable scripts
│   ├── fixes/                    # Bug fix scripts
│   ├── analysis/                 # Analysis scripts
│   └── korean/                   # Korean-specific scripts
│
├── tools/                        # Development tools
│   ├── dictionaries/             # Dictionary tools
│   ├── cli/                      # CLI tools
│   └── [utility scripts]
│
├── cache/                        # Runtime caches
│   ├── authority_cache/          # API response cache
│   ├── bad_json/                 # Invalid payloads
│   ├── config/                   # Config cache
│   ├── gs/                       # Google Scholar cache
│   └── output/                   # Output cache
│
├── archive/                      # Historical code
│   ├── old_src_structure_20250728/  # Pre-v7 src
│   ├── session_work_20250728/       # Cleanup work
│   ├── korean_backups/              # Korean backups
│   └── [other archives]
│
├── logs/                         # Log files
├── reports/                      # Generated reports
├── analysis/                     # Analysis outputs
├── charts/                       # Chart templates
├── cron/                         # Cron scripts
└── debug_tools/                  # Debug utilities
```

## Key Architecture Decisions

### 1. Single Source Tree
- All source code under `src/gmnap/` - no duplicate structures
- Clear module hierarchy matching v7 specifications
- Proper Python package structure with `__init__.py` files

### 2. Regional Processing Architecture
- Each region group (a-h) has its own subdirectory
- Korean (e4) has extended structure due to FST complexity
- Regional processors inherit from common base classes

### 3. Authority Integration
- Tiered structure (tier0/1/2) for API management
- Tier0: Free APIs (implemented)
- Tier1: Premium APIs (future)
- Tier2: Experimental (future)

### 4. Test Organization
- Comprehensive test categories matching v7 specs
- Korean tests integrated into main suite
- Quality gates for continuous validation

### 5. Documentation Structure
- Centralized under `docs/`
- Architecture, API, and regional subdirectories
- Korean-specific documentation preserved

## Import Examples

With the v7 structure, imports are clean and consistent:

```python
# Core imports
from gmnap.core.pipeline import Pipeline
from gmnap.core.config import Config
from gmnap.core.unicode_handler import UnicodeHandler

# Regional imports
from gmnap.regions.e_groups.e4_korea.converter import KoreanConverter
from gmnap.regions.manager import RegionalProcessorManager

# Authority imports
from gmnap.authorities.tier0.wikidata import WikidataFetcher
from gmnap.authorities.cache import AuthorityCache

# Utility imports
from gmnap.utils.database import DatabaseManager
from gmnap.validation.quality_gates import QualityGates
```

## Migration Notes

### From Old Structure
- `src/core/*` → `src/gmnap/core/*`
- `src/authorities/*` → `src/gmnap/authorities/*`
- `src/linguistic/*` → `src/gmnap/linguistic/*`
- Korean tests → `tests/unit/korean/`
- Documentation → `docs/`

### Preserved Components
- Korean converter structure in e4_korea/
- Pre-commit hooks remain functional
- Git tracking maintained for critical files

### Archived Components
- Old src structure → `archive/old_src_structure_20250728/`
- Cleanup work → `archive/session_work_20250728/`
- Test results → `archive/test_results/`

## Development Workflow

### 1. Regional Development
- Work in `src/gmnap/regions/{group}/{region}.py`
- Tests in `tests/unit/{region}/`
- Docs in `docs/regional/{region}/`

### 2. Pipeline Development
- Core pipeline: `src/gmnap/core/pipeline.py`
- Pattern detection integrated
- Quality gates via pre-commit

### 3. Testing
```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/quality_gates/

# Run Korean validation
cd src/gmnap/regions/e_groups/e4_korea
python scripts/validate.py
```

### 4. Pre-commit Hooks
The pre-commit hook validates:
- Korean mathematician dataset (733 tests)
- Korean diverse dataset (200 tests)
Both must pass before commits are allowed.

## Current Status

### Implemented
- ✅ Complete v7 directory structure
- ✅ Core pipeline with pattern detection (88.3% accuracy)
- ✅ Korean converter (84.45% mathematician, 71% diverse)
- ✅ Authority tier0 implementations
- ✅ Regional processors for A1, A2, B1, B2, C3, E1, E3, E4, G1

### Not Implemented
- ❌ D-group regions (architectural gap)
- ❌ Authority tier1/tier2
- ❌ Full linguistic module
- ❌ Some v7 test categories

## Next Steps

1. Implement D-group regional processors
2. Complete linguistic module implementation
3. Add tier1/tier2 authority integrations
4. Achieve 85%+ accuracy on all test suites
5. Complete v7 test coverage

## Maintenance

### Adding New Regions
1. Create module in appropriate group directory
2. Inherit from regional base class
3. Add tests in `tests/unit/{region}/`
4. Document in `docs/regional/{region}/`

### Updating Pipeline
1. Modify `src/gmnap/core/pipeline.py`
2. Update pattern databases as needed
3. Run quality gates to ensure no regression
4. Document changes in commit message

### Managing Dependencies
- Core dependencies in `requirements.txt`
- Regional dependencies documented per module
- Version constraints for stability