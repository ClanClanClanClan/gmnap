# GMNAP Comprehensive Test Suite

This directory contains the comprehensive test suite for the Global Mathematician Name Authority Project (GMNAP). The tests are designed to be **hardcore**, **unforgiving**, and **comprehensive** to ensure the system can handle real-world complexity at scale.

## Test Architecture

### Core Test Categories

#### 1. **Unit Tests** (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Coverage**: Core modules, regions, authorities, validation, caching
- **Key Files**:
  - `test_globalid.py` - GlobalID generation and collision handling
  - `test_region_a1.py` - A1 region processing (Anglo-Sphere)
  - `test_schema_validation.py` - YAML schema v1.5 validation
  - `test_cache_system.py` - Zstandard compression cache
  - `test_unicode_handler.py` - Unicode normalization

#### 2. **Integration Tests** (`tests/integration/`)
- **Purpose**: Test component interactions and data flow
- **Coverage**: Full pipeline processing, multi-stage operations
- **Key Files**:
  - `test_pipeline_integration.py` - End-to-end pipeline execution

#### 3. **Hardcore Tests** (`tests/hardcore/`)
- **Purpose**: Stress testing, attack vectors, invariant verification
- **Coverage**: Real-world scenarios, edge cases, system limits
- **Key Files**:
  - `test_real_world_data.py` - Actual mathematician names and problematic Unicode
  - `test_concurrent_chaos.py` - Race conditions and concurrent access
  - `test_fuzzing_attacks.py` - Malformed inputs and attack vectors
  - `test_invariant_verification.py` - Critical system invariants
  - `test_stress_endurance.py` - Long-running stress tests

#### 4. **Performance Tests** (`tests/performance/`)
- **Purpose**: Memory usage, speed benchmarks, resource limits
- **Coverage**: Memory limits, processing speed, concurrent performance
- **Key Files**:
  - `test_performance_memory.py` - Memory usage and leak detection

#### 5. **Property-Based Tests** (`tests/property/`)
- **Purpose**: Hypothesis-driven testing with random inputs
- **Coverage**: Unicode normalization properties, system invariants
- **Key Files**:
  - `test_unicode_properties.py` - Unicode normalization properties

#### 6. **Mock API Tests** (`tests/mock_api/`)
- **Purpose**: Offline testing without external dependencies
- **Coverage**: API failure scenarios, rate limiting, network issues
- **Key Files**:
  - `test_offline_mode.py` - Mock API implementations

#### 7. **Quality Gates** (`tests/quality_gates/`)
- **Purpose**: Enforce critical system requirements
- **Coverage**: Performance thresholds, reliability metrics
- **Key Files**:
  - `test_quality_requirements.py` - System quality gates

## Critical Test Scenarios

### 1. **Real-World Data Chaos**
```python
# Historical Arabic mathematicians with complex Unicode
"الخوارزمي، محمد بن موسى"  # al-Khwārizmī, Muḥammad ibn Mūsā
"أبو عبد الله محمد بن جابر بن سنان البتاني"  # Very long patronymic

# Russian mathematicians with patronymics
"Пафну́тий Льво́вич Чебышёв"  # With stress marks
"Софья Васильевна Ковалевская"  # Feminine forms

# Chinese mathematicians
"陈省身"  # Traditional Chinese
"华罗庚"  # Simplified Chinese

# Unicode homograph attacks
"Sмith, John"  # Cyrillic 'м' instead of Latin 'm'
"Мüller, Hans"  # Mixed Cyrillic/Latin
```

### 2. **Concurrent Chaos Engineering**
- **GlobalID Uniqueness**: 10 threads generating 1000 IDs each, verifying zero duplicates
- **Cache Corruption**: Concurrent writes with immediate verification
- **Database Deadlocks**: Intentional deadlock scenarios with recovery
- **Memory Pressure**: Operations under extreme memory constraints

### 3. **Fuzzing Attack Vectors**
- **Binary Injection**: Null bytes, control characters, invalid UTF-8
- **Unicode Attacks**: Homographs, normalization exploits, invisible characters
- **Format String Attacks**: Template injection, code execution attempts
- **Memory Exhaustion**: Zip bombs, exponential backtracking, large objects

### 4. **Invariant Verification**
- **INVARIANT**: No duplicate GlobalIDs are ever generated
- **INVARIANT**: Unicode normalization is always idempotent
- **INVARIANT**: Region detection is deterministic
- **INVARIANT**: No dangerous characters survive processing
- **INVARIANT**: Pipeline never corrupts data

### 5. **Stress Endurance Testing**
- **5-Minute Continuous Generation**: 10,000+ GlobalIDs with resource monitoring
- **Concurrent Load**: 8 workers for 2 minutes with mixed operations
- **Memory Pressure**: Operations under 1.5GB memory consumption
- **Failure Recovery**: 50 cycles of failure/recovery testing

## Quality Gates

### Performance Requirements
- **Memory Limit**: ≤2GB RAM for processing large datasets
- **Processing Speed**: 
  - ≤0.1ms per GlobalID generation
  - ≤1ms per Unicode normalization
  - ≤0.5ms per region detection
- **Throughput**: ≥1M entries processed in 30 minutes (quick mode)

### Accuracy Requirements
- **Script Detection**: ≥95% accuracy
- **Region Detection**: ≥90% accuracy  
- **Unicode Roundtrip**: ≥97% preservation for CJK/SEA
- **GlobalID Uniqueness**: 100% (zero tolerance)

### Reliability Requirements
- **No Invariant Violations**: Zero tolerance for core invariants
- **Graceful Degradation**: System continues operating under resource pressure
- **Data Integrity**: No corruption during concurrent operations
- **Recovery**: System recovers from all failure scenarios

## Running the Tests

### Quick Test Run
```bash
# Run core tests only
python -m pytest tests/unit tests/integration -v

# Run hardcore tests (subset)
python tests/hardcore/test_runner.py --quick

# Run specific category
python -m pytest tests/hardcore/test_invariant_verification.py -v
```

### Full Test Suite
```bash
# Run all tests with comprehensive reporting
python tests/hardcore/test_runner.py

# Run with specific categories
python tests/hardcore/test_runner.py --categories invariant_verification real_world_data

# Run with custom output directory
python tests/hardcore/test_runner.py --output-dir ./test_results
```

### Performance Testing
```bash
# Run performance tests
python -m pytest tests/performance -v --benchmark-only

# Run stress tests (long-running)
python -m pytest tests/hardcore/test_stress_endurance.py -v -s -m slow
```

### Property-Based Testing
```bash
# Run property-based tests with Hypothesis
python -m pytest tests/property -v --hypothesis-show-statistics

# Run with more examples
python -m pytest tests/property -v --hypothesis-profile=dev
```

## Test Configuration

### Environment Variables
- `OFFLINE=1` - Run in offline mode (no external API calls)
- `HYPOTHESIS_PROFILE=ci` - Use CI-friendly Hypothesis settings
- `PYTEST_TIMEOUT=300` - Set test timeout (seconds)

### Test Data
- **Fixtures**: `tests/fixtures/` - Curated test data
- **Real Data**: Actual mathematician names (anonymized)
- **Edge Cases**: Unicode torture tests, malformed inputs
- **Performance Data**: Large datasets for load testing

## Monitoring and Reporting

### Resource Monitoring
- **Memory Usage**: RSS/VMS tracking with leak detection
- **CPU Usage**: Process CPU utilization monitoring
- **File Descriptors**: FD leak detection
- **Garbage Collection**: Object count tracking

### Test Reports
- **JSON Reports**: Machine-readable test results
- **Human Reports**: Executive summaries with recommendations
- **Resource Reports**: Memory/CPU usage graphs
- **Quality Gates**: Pass/fail status for critical requirements

## Continuous Integration

### GitHub Actions
```yaml
name: GMNAP Hardcore Tests
on: [push, pull_request]

jobs:
  hardcore-tests:
    runs-on: ubuntu-22.04
    steps:
      - name: Run hardcore test suite
        run: |
          python tests/hardcore/test_runner.py
          
      - name: Check quality gates
        run: |
          python -c "
          import json
          with open('test_results/hardcore_test_report.json') as f:
              report = json.load(f)
          assert report['overall_status'] == 'PASSED'
          assert len(report['critical_failures']) == 0
          "
```

## Failure Analysis

### Common Failure Patterns
1. **Memory Leaks**: Gradual memory growth over time
2. **Race Conditions**: Non-deterministic failures in concurrent tests
3. **Unicode Corruption**: Data loss in normalization
4. **Invariant Violations**: Core system guarantees broken
5. **Resource Exhaustion**: System failure under load

### Debug Strategies
1. **Isolation**: Run single test with verbose output
2. **Monitoring**: Enable resource monitoring during test
3. **Reproduction**: Use seed values for property-based tests
4. **Logging**: Enable debug logging for component analysis

## Contributing

### Adding New Tests
1. **Identify Gap**: Find untested scenarios or edge cases
2. **Create Test**: Write comprehensive test with assertions
3. **Add Documentation**: Document test purpose and expectations
4. **Integrate**: Add to test runner and CI pipeline

### Test Quality Standards
- **Comprehensive**: Cover all code paths and edge cases
- **Realistic**: Use real-world data and scenarios
- **Deterministic**: Tests should be reproducible
- **Fast**: Unit tests should complete quickly
- **Isolated**: Tests should not depend on external state

## Architecture Notes

### Why Hardcore Testing?
The GMNAP system processes millions of mathematician names with complex Unicode, multiple scripts, and various cultural naming conventions. Traditional testing approaches are insufficient for this complexity. Hardcore testing ensures:

1. **Real-World Readiness**: System handles actual mathematician names, not just "Smith, John"
2. **Unicode Robustness**: Proper handling of complex Unicode scenarios
3. **Concurrency Safety**: System works correctly under concurrent load
4. **Attack Resistance**: System resists malicious inputs and attacks
5. **Performance Guarantees**: System meets strict performance requirements
6. **Reliability**: System maintains data integrity under all conditions

### Test Philosophy
- **Assume Malice**: Every input could be malicious
- **Expect Chaos**: System must handle concurrent chaos
- **Verify Invariants**: Core guarantees must never be violated
- **Test Reality**: Use real-world data and scenarios
- **Measure Everything**: Monitor all resources and metrics
- **Zero Tolerance**: Critical requirements have no exceptions

This comprehensive test suite ensures the GMNAP system is production-ready for processing millions of mathematician names reliably, accurately, and securely.