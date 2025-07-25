# GMNAP Comprehensive Audit and Reorganization Plan

## Executive Summary

The Global Mathematician-Name Authority Project (GMNAP) is a world-scale, script-aware knowledge base covering 43 region groups across all continents. The current implementation shows Korean converter development has dominated the repository structure, creating confusion and inefficiency. This audit provides a complete analysis and reorganization plan aligned with GMNAP v6.1 specifications.

## Current State Analysis

### 1. Scripts Directory (57 files, 90% Korean-focused)

**Korean-Specific Scripts (48 files - TO BE MOVED)**
- `analyze_korean_components.py`, `build_v4_mappings.py`, `complete_korean_mappings.py`
- `test_*_converter.py` (12 files), `debug_*_converter.py` (5 files)
- `evaluate_roundtrip*.py`, `validate_v5_system.py`
- **Issue**: Hardcoded paths to `/Users/dylanpossamai/` in 20+ scripts

**GMNAP Core Scripts (9 files - TO BE KEPT)**
- `generate_stats.py` - Project-wide statistics
- `generate_test_report.py` - Global test reporting
- `organize_project.py` - Project organization
- `setup_dev.sh`, `setup_environment.py` - Development setup
- `refresh_corpus.py` - Corpus management
- `performance_optimization.py` - Global performance

### 2. Data Directory (304MB total, 299MB in corp/)

**Korean-Specific Data (TO BE MOVED)**
- `corp/c4_ko_sample.txt` (299MB) - Korean corpus
- `corp/korean_mathematicians.txt`, `corp/kowiki.*`
- All romanization tables: `*_romanization.csv`, `*_table.csv`
- Korean FST files: `korean_*.fst`, `v4_*.fst`
- Korean mappings: `v4_*mappings*.json`, `korean_*.json`

**GMNAP Core Data (TO BE KEPT)**
- `gmnap.db` - Main database
- `classifier_params.json` - Global classifier

### 3. Source Code Structure

**Current Issues:**
- `/src/v5/` - Entire directory is Korean-specific
- `/src/regions/e_groups/e4_korea.py` AND `e4_korea_v5.py` - Duplicate implementations
- Missing implementations for 35/43 region groups
- No clear separation between core pipeline and regional processors

### 4. Documentation (30 MD files)

**Korean-Specific (19 files - TO BE ARCHIVED)**
- All `KOREAN_V5_*.md`, `V5_*.md` files
- Korean implementation plans and audits

**GMNAP Core (11 files - TO BE KEPT/UPDATED)**
- `README.md`, `docs/specs v6.md`, `docs/specs v6.yaml`
- `docs/architecture/GMNAP_V7_ARCHITECTURE.md`
- Core audit and implementation roadmaps

### 5. Large Files and Binary Data

**Problematic Files:**
- `cache/config/lid.176.bin` (125MB) - Language detection model
- `data/corp/c4_ko_sample.txt` (299MB) - Korean corpus
- Multiple FST binaries that should be generated, not stored

## Reorganization Plan (Aligned with GMNAP v6.1 Specs)

### Phase 1: Create Clean Directory Structure

```bash
gmnap/
├── README.md                          # Project overview
├── ARCHITECTURE.md                    # System architecture
├── CHANGELOG.md                       # Version history
├── LICENSE                            # MIT License
├── requirements/                      # Dependency management
│   ├── base.txt                      # Core dependencies
│   ├── dev.txt                       # Development tools
│   └── regional/                     # Region-specific deps
│       ├── e4_korea.txt              
│       └── ...
│
├── docs/                             # Specifications and guides
│   ├── specs/
│   │   ├── v6.1.yaml                # Current spec
│   │   └── v6.1.md                  
│   ├── api/                         # API documentation
│   ├── deployment/                  # Deployment guides
│   └── development/                 # Dev guides
│
├── src/
│   ├── gmnap/                       # Core GMNAP package
│   │   ├── __init__.py
│   │   ├── core/                    # Core functionality
│   │   │   ├── pipeline.py         # 10-stage pipeline
│   │   │   ├── globalid.py         # GlobalID generation
│   │   │   ├── database.py         # Database operations
│   │   │   ├── schema.py           # YAML schema v1.5
│   │   │   └── monitoring.py       # Performance monitoring
│   │   │
│   │   ├── authorities/            # External API integrations
│   │   │   ├── base.py            # Base authority class
│   │   │   ├── tier0/             # Free APIs
│   │   │   │   ├── openalex.py
│   │   │   │   ├── crossref.py
│   │   │   │   ├── orcid.py
│   │   │   │   └── zbmath.py
│   │   │   ├── tier1/             # Premium APIs
│   │   │   └── tier2/             # Scraping (--force-extreme)
│   │   │
│   │   ├── regions/               # Regional processors (43 groups)
│   │   │   ├── __init__.py       # Region manager
│   │   │   ├── base.py           # Base region class
│   │   │   ├── a_groups/         # Anglo-sphere (A1-A5)
│   │   │   │   ├── a1_anglo_core.py
│   │   │   │   ├── a2_western_europe.py
│   │   │   │   └── ...
│   │   │   ├── e_groups/         # East Asian (E1-E7)
│   │   │   │   ├── e4_korea/     # Korean module
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── converter.py
│   │   │   │   │   └── resources/
│   │   │   │   └── ...
│   │   │   └── ...
│   │   │
│   │   ├── linguistic/           # Language processing
│   │   │   ├── unicode_handler.py
│   │   │   ├── rules_engine.py
│   │   │   └── variant_generator.py
│   │   │
│   │   └── utils/               # Utilities
│   │       ├── cache.py
│   │       ├── config.py
│   │       └── logging.py
│   │
│   └── cli/                     # Command-line interface
│       ├── gmnap.py            # Main CLI
│       └── commands/
│           ├── query.py
│           ├── diff.py
│           └── pipeline.py
│
├── data/                        # Permanent data assets
│   ├── schemas/                # Schema definitions
│   ├── weights/                # Confidence weights
│   └── region_index.csv       # ISO→Region mapping
│
├── resources/                  # Generated resources
│   ├── databases/             # SQLite/DuckDB files
│   ├── models/                # ML models
│   └── regional/              # Region-specific resources
│       └── e4_korea/
│           ├── fst/          # Generated FST files
│           ├── mappings/     # Name mappings
│           └── tables/       # Romanization tables
│
├── tests/                     # Test suites
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── regional/             # Region-specific tests
│   │   └── e4_korea/
│   └── fixtures/             # Test data
│
├── scripts/                  # Maintenance scripts
│   ├── core/                # Core scripts
│   │   ├── setup_dev.sh
│   │   ├── generate_stats.py
│   │   └── refresh_authorities.py
│   └── regional/            # Region-specific scripts
│       └── e4_korea/
│           └── build_fst.py
│
├── deployment/              # Deployment configs
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
│
└── archive/                # Historical versions
    ├── v5_korean/          # Complete v5 Korean implementation
    └── legacy_scripts/     # Old scripts for reference
```

### Phase 2: Immediate Actions

1. **Create Migration Script**
   ```bash
   scripts/core/migrate_to_v7_structure.py
   ```

2. **Move Korean-Specific Components**
   - All Korean scripts → `scripts/regional/e4_korea/`
   - Korean data → `resources/regional/e4_korea/`
   - Korean docs → `archive/v5_korean/docs/`

3. **Clean Root Directory**
   - Remove all loose YAML/JSON files
   - Move test results to `archive/test_results/`
   - Delete duplicate files

4. **Fix Hardcoded Paths**
   - Replace all `/Users/dylanpossamai/` with relative paths
   - Use environment variables for user-specific paths

### Phase 3: Core Infrastructure

1. **Implement Missing Core Components**
   - Region detector for all 43 groups
   - Authority tier-1/tier-2 integrations
   - GDPR compliance module
   - CLI tools

2. **Standardize Regional Modules**
   - Create template for new regions
   - Document region implementation guide
   - Add region-specific tests

3. **Database Schema Migration**
   - Implement v1.5 schema validation
   - Add migration scripts
   - Create backup procedures

### Phase 4: Documentation and Testing

1. **Update Documentation**
   - Main README focused on GMNAP, not Korean
   - Region implementation guides
   - API documentation

2. **Reorganize Tests**
   - Separate core vs regional tests
   - Add missing region tests
   - Create integration test suite

## Recommendations

### Immediate (Week 1)
1. **Backup Everything**: Create `gmnap_backup_20250724/`
2. **Run Migration Script**: Automated reorganization
3. **Remove Large Files**: Move corpora to external storage
4. **Fix Critical Paths**: Update hardcoded paths

### Short-term (Month 1)
1. **Implement Core Pipeline**: Focus on multi-region support
2. **Add 5 More Regions**: A2, B2, C1, D2, G1
3. **Setup CI/CD**: Automated testing and deployment
4. **Create Region Templates**: Standardize implementation

### Long-term (Quarter 1)
1. **Complete 20 Regions**: Priority on high-volume regions
2. **Add Tier-1 APIs**: Premium data sources
3. **GDPR Compliance**: Full implementation
4. **Performance Optimization**: Global caching strategy

## File Disposition Summary

### DELETE (Redundant/Temporary)
- All files in `test_results/` (move to archive)
- Duplicate Korean converters
- Generated FST files (regenerate on demand)
- Temporary JSON files in root

### ARCHIVE (Historical Reference)
- All v5 Korean implementation
- Old test results
- Legacy scripts
- Implementation plans/audits

### MOVE (Reorganize)
- Korean components → `src/gmnap/regions/e_groups/e4_korea/`
- Core scripts → `scripts/core/`
- Documentation → Appropriate `docs/` subdirectory

### KEEP (Core GMNAP)
- Pipeline implementation
- Authority integrations
- Database schemas
- Core documentation

## Conclusion

The current repository structure reflects organic growth focused on Korean implementation. The proposed reorganization aligns with GMNAP's true scope as a global mathematician authority system covering 43 regions. Korean (E4) becomes one module among many, with clear separation between core infrastructure and regional implementations.

This structure supports:
- Adding new regions without disrupting existing ones
- Clear ownership and maintenance boundaries  
- Efficient testing and deployment
- Compliance with v6.1 specifications
- Future scaling to all 43 regions

The reorganization can be completed in phases, maintaining operational continuity while building toward the complete GMNAP vision.