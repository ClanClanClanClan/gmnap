# GMNAP Comprehensive Testing Strategy

## Overview

This document outlines the extensive testing strategy for the Global Mathematician Name Authority Project (GMNAP). The testing approach covers unit tests, integration tests, property-based tests, performance tests, and compliance tests.

## Test Categories and Coverage

### 1. Unit Tests

#### 1.1 Core Module Tests

**test_globalid.py**
```python
# Test cases:
- test_generate_basic_id() - Basic ID generation
- test_collision_handling() - Verify --1, --2 suffixes
- test_deterministic_generation() - Same input → same ID
- test_invalid_inputs() - Missing fields, null values
- test_special_birth_years() - "1970s", "-500", "c1150", "1150/1160"
- test_base32_format() - Verify 22 chars, valid Base32
- test_unicode_names() - Non-ASCII canonical names
```

**test_unicode_handler_complete.py**
```python
# Test cases:
- test_normalization_chain() - NFC→NFKD→custom→NFC
- test_ligature_decomposition() - æ→ae, œ→oe, ß→ss
- test_sharp_s_variants() - ß/ẞ handling
- test_greek_tonos_mapping() - tonos = oxia
- test_script_detection() - Identify primary script
- test_mixed_script_detection() - Multi-script threshold
- test_reversibility() - Validate normalization can be reversed
```

**test_config_enhanced.py**
```python
# Test cases:
- test_load_weights_yaml() - Load and validate weights
- test_weights_normalization() - Sum to 1.0
- test_source_manifest_loading() - Load API configs
- test_environment_override() - GMNAP_* env vars
- test_missing_config_defaults() - Default values
- test_invalid_config_rejection() - Bad values
- test_config_persistence() - Save and reload
```

#### 1.2 Region Module Tests

**test_region_base.py**
```python
# Test cases:
- test_region_spec_interface() - Abstract methods
- test_mandatory_hooks() - clean, augment, validate, order_key
- test_pure_order_key() - Deterministic sorting
- test_region_codes() - A1-H1, R0, Z0 validity
- test_territory_mapping() - ISO codes → regions
```

**test_region_a1_anglo_sphere.py**
```python
# Test cases:
- test_title_removal() - Dr., Prof., etc.
- test_generational_suffixes() - Jr., Sr., III
- test_middle_initial_handling() - J.C. → J.
- test_punctuation_normalization() - Proper spacing
- test_particle_handling() - von, van, de
- test_ascii_variant_generation() - José → Jose
- test_order_key_generation() - Sorting consistency
- test_extended_latin_validation() - É, ñ, etc.
```

**test_region_detection.py**
```python
# Test cases:
- test_script_based_detection() - Unicode script analysis
- test_language_detection() - FastText integration
- test_affiliation_detection() - Country codes
- test_doi_prefix_detection() - Publisher mapping
- test_diaspora_overlay() - Date-based rules
- test_detection_priority() - script > affiliation > DOI > lang
- test_low_confidence_quarantine() - Z0 routing
- test_fallback_to_r0() - Unmapped territories
```

#### 1.3 Authority Module Tests

**test_authority_base.py**
```python
# Test cases:
- test_quota_management() - Daily limits
- test_quota_reset() - Date rollover
- test_rate_limiting() - Request spacing
- test_tier_prioritization() - 0 > 1 > 2
- test_batch_fetching() - Multiple queries
- test_personal_data_scrubbing() - GDPR compliance
- test_confidence_calculation() - Score generation
```

**test_openalex_fetcher.py**
```python
# Test cases:
- test_name_search() - Query by name
- test_id_lookup() - Direct A* ID lookup
- test_response_parsing() - Extract all fields
- test_affiliation_extraction() - Institution data
- test_orcid_extraction() - ORCID IDs
- test_rate_limit_handling() - 429 responses
- test_not_found_handling() - 404 responses
- test_network_error_handling() - Timeouts
```

#### 1.4 Cache Module Tests

**test_cache_zstandard.py**
```python
# Test cases:
- test_compression_decompression() - Round-trip data
- test_cache_key_generation() - Deterministic keys
- test_ttl_enforcement() - 30-day expiry
- test_size_limit_eviction() - 20GB limit
- test_google_scholar_isolation() - gs/ directory
- test_bad_json_quarantine() - Corrupted data
- test_atomic_writes() - .tmp file usage
- test_cache_stats() - Hit/miss tracking
```

#### 1.5 Validation Module Tests

**test_schema_v15.py**
```python
# Test cases:
- test_required_fields() - GlobalID, UpdatedAt, etc.
- test_globalid_format() - Base32 + collision suffix
- test_birth_death_consistency() - Death > Birth
- test_msc_code_format() - DDaDD pattern
- test_orcid_validation() - Checksum digit
- test_proprietary_licenses() - Scopus, WoS fields
- test_language_code_validation() - ISO 639-3
- test_country_code_validation() - ISO 3166-1
- test_confidence_range() - 0-100
- test_name_event_chronology() - Sorted years
- test_advisor_references() - Valid GlobalIDs
```

### 2. Integration Tests

**test_pipeline_integration.py**
```python
# Test cases:
- test_full_pipeline_quick_mode() - End-to-end quick
- test_full_pipeline_full_mode() - End-to-end full
- test_stage_sequencing() - 0→1→...→10
- test_error_propagation() - Failed stages
- test_checkpoint_resume() - Restart from checkpoint
- test_memory_within_limits() - <2GB RSS
- test_idempotency_verification() - Stage 10 check
- test_yaml_roundtrip() - Read→Process→Write
```

**test_region_pipeline_integration.py**
```python
# Test cases:
- test_multi_region_batch() - Mixed regions
- test_region_fallback_z0() - Failed detection
- test_batch_enrichment() - Regional batching
- test_order_key_sorting() - Multi-region sort
```

**test_authority_pipeline_integration.py**
```python
# Test cases:
- test_tier0_enrichment() - OpenAlex + mock APIs
- test_quota_exhaustion() - Handle limits
- test_multi_source_merge() - Combine data
- test_confidence_aggregation() - Score updates
```

### 3. Property-Based Tests (Hypothesis)

**test_unicode_properties.py**
```python
@given(st.text())
def test_normalization_idempotent(text):
    # Normalize(Normalize(x)) == Normalize(x)
    
@given(st.text(alphabet=string.ascii_letters))
def test_ascii_preserved(text):
    # ASCII characters unchanged
    
@given(st.text())
def test_no_data_loss(text):
    # All characters accounted for
```

**test_globalid_properties.py**
```python
@given(
    name=st.text(min_size=1),
    birth=st.one_of(st.none(), st.integers(1800, 2024)),
    death=st.one_of(st.none(), st.integers(1800, 2024))
)
def test_globalid_deterministic(name, birth, death):
    # Same input always produces same ID
```

### 4. Performance Tests

**test_performance_memory.py**
```python
# Test cases:
- test_2million_entries_memory() - Peak RSS ≤ 2GB
- test_streaming_chunks() - 8000 entry chunks
- test_duckdb_fallback() - SQLite on memory pressure
- test_cache_size_limits() - 20GB enforcement
```

**test_performance_speed.py**
```python
# Test cases:
- test_quick_mode_speed() - ≤30min/1M entries
- test_full_mode_speed() - ≤60min/1M entries  
- test_unicode_normalization_speed() - <1ms/entry
- test_region_detection_speed() - <0.5ms/entry
```

### 5. Round-Trip Tests

**test_sea_roundtrip.py**
```python
# Test cases:
- test_thai_roundtrip() - Thai ↔ RTGS
- test_khmer_roundtrip() - Khmer ↔ UNGEGN
- test_lao_roundtrip() - Lao ↔ MOICT
- test_cjk_roundtrip() - Hanzi/Kanji/Hangul
- test_accuracy_97_percent() - Quality gate
```

### 6. Stress Tests

**test_stress_concurrent.py**
```python
# Test cases:
- test_8_process_stress() - Parallel processing
- test_sigint_graceful() - Clean shutdown
- test_memory_peak_2m_entries() - Large dataset
- test_api_timeout_handling() - Network issues
```

### 7. Mock API Tests

**test_fake_api_server.py**
```python
# Mock implementations for:
- OpenAlex API
- Crossref API
- ORCID API
- MathSciNet HTML
- zbMATH API

# Test offline mode with OFFLINE=1
```

### 8. Quality Gate Tests

**test_quality_gates.py**
```python
# Test cases:
- test_no_duplicate_globalids() - 0 duplicates
- test_no_duplicate_external_ids() - 0 duplicates
- test_roundtrip_accuracy() - ≥97% CJK/SEA
- test_missing_tier0_threshold() - ≤40% quick
- test_deterministic_order_keys() - ≤0.1% variance
- test_memory_limit() - ≤2GB RSS
- test_runtime_limits() - Within targets
```

### 9. Compliance Tests

**test_gdpr_compliance.py**
```python
# Test cases:
- test_personal_data_marking() - GDPR_DATA flags
- test_email_scrubbing() - Remove from cache
- test_birth_year_granularity() - Decade for <5
- test_drop_personal_flag() - --drop-personal
```

**test_license_compliance.py**
```python
# Test cases:
- test_proprietary_license_fields() - Scopus, etc.
- test_attribution_generation() - ATTRIBUTION.txt
- test_license_restrictions() - LICENSE_RESTRICTIONS.md
```

### 10. Fixtures and Test Data

**fixtures/**
```
├── entries/
│   ├── a1_anglo_sphere.yaml      # 50 entries
│   ├── e1_chinese.yaml           # 50 entries
│   ├── c3_arabic.yaml            # 50 entries
│   └── ... (all regions)
├── api_responses/
│   ├── openalex/                 # Mock responses
│   ├── crossref/
│   └── orcid/
├── edge_cases/
│   ├── unicode_torture.yaml      # Extreme Unicode
│   ├── collisions.yaml           # ID collisions
│   └── malformed.yaml            # Invalid data
└── performance/
    ├── 10k_entries.yaml          # Medium dataset
    └── 100k_entries.yaml         # Large dataset
```

## Test Execution Strategy

### 1. Continuous Integration

```yaml
# .github/workflows/test.yml
name: GMNAP Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    steps:
      - name: Run unit tests
        run: pytest tests/unit -v --cov

  integration-tests:
    runs-on: ubuntu-22.04
    steps:
      - name: Run integration tests
        run: pytest tests/integration -v

  property-tests:
    runs-on: ubuntu-22.04
    steps:
      - name: Run property tests
        run: pytest tests/property -v --hypothesis-profile=ci

  performance-tests:
    runs-on: ubuntu-22.04
    steps:
      - name: Run performance tests
        run: pytest tests/performance -v --benchmark-only

  quality-gates:
    runs-on: ubuntu-22.04
    steps:
      - name: Check quality gates
        run: pytest tests/quality_gates -v
```

### 2. Local Development

```bash
# Run all tests
make test

# Run specific category
make test-unit
make test-integration
make test-performance

# Run with coverage
make test-coverage

# Run specific test
pytest tests/unit/test_globalid.py::test_collision_handling -v
```

### 3. Test Environments

1. **Unit Tests**: Mock all external dependencies
2. **Integration Tests**: Use Docker containers for services
3. **Performance Tests**: Dedicated hardware specs
4. **Stress Tests**: High-memory instances

### 4. Test Data Generation

```python
# scripts/generate_test_data.py
def generate_fixture_entries(region: str, count: int):
    """Generate realistic test entries for a region."""
    
def generate_collision_cases():
    """Generate entries that will collide."""
    
def generate_unicode_edge_cases():
    """Generate Unicode torture test cases."""
```

## Monitoring and Reporting

### 1. Coverage Requirements

- Unit tests: ≥90% coverage
- Integration tests: ≥80% coverage
- Overall: ≥85% coverage

### 2. Performance Baselines

- Unicode normalization: <1ms per entry
- Region detection: <0.5ms per entry
- GlobalID generation: <0.1ms per entry
- Full pipeline: <30min per 1M entries (quick mode)

### 3. Test Reports

Generate HTML reports with:
- Coverage statistics
- Performance metrics
- Failed test details
- Quality gate status

## Test Implementation Priority

### Phase 1 (Immediate)
1. Core module unit tests
2. Region A1 tests
3. Basic integration tests
4. Schema validation tests

### Phase 2 (High Priority)
1. Authority module tests
2. Cache tests
3. Performance tests
4. Property-based tests

### Phase 3 (Medium Priority)
1. Additional region tests
2. Stress tests
3. Compliance tests
4. Mock API server

### Phase 4 (Low Priority)
1. Edge case tests
2. Full fixture suite
3. Benchmark suite

## Test Maintenance

1. **Test Review**: Review and update tests with each spec change
2. **Fixture Updates**: Keep test data current with real-world examples
3. **Performance Baselines**: Update targets quarterly
4. **Mock Updates**: Keep API mocks in sync with real APIs