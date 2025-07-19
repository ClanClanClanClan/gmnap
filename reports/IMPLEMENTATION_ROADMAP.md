# GMNAP Implementation Plan

## Overview
Current state: ~15% complete
Target state: 100% functional production system
Gap: 85% of functionality

## Phase 1: Critical Fixes (Days 1-2)

### 1.1 Database Configuration Fix
**Problem**: DatabaseManager expects DatabaseConfig object, tests pass strings
**Solution**: 
- Update pipeline_v6.py to properly instantiate DatabaseConfig
- Fix all database-related imports and constructors
- Ensure proper database initialization
**Success Metric**: test_database_operations.py passes

### 1.2 Authority Integration Fix  
**Problem**: QuotaManager and OpenAlexFetcher have wrong constructors
**Solution**:
- Fix QuotaManager to handle optional source_manifest parameter
- Fix OpenAlexFetcher to handle optional config parameter
- Update all test fixtures to match actual constructors
**Success Metric**: test_authority_integration.py runs without errors

### 1.3 Implement SQLite Database Layer
**Problem**: No actual database persistence
**Solution**:
- Create SQLite schema for mathematician entries
- Implement CRUD operations in DatabaseManager
- Add proper transaction handling
- Implement connection pooling for concurrent access
**Success Metric**: Can store and retrieve mathematician entries

## Phase 2: Core Functionality (Days 3-7)

### 2.1 Pipeline Implementation
**Problem**: Pipeline doesn't actually process data
**Solution**:
- Connect all components: fetch → normalize → validate → generate ID → store
- Implement proper error handling and retry logic
- Add logging and monitoring hooks
- Create pipeline orchestration logic
**Success Metric**: Can process a mathematician entry end-to-end

### 2.2 Implement Critical Regions (5 regions)
**Problem**: Only A1 (Anglo) implemented, need global coverage
**Priority Regions**:
1. **B1 (Russian/Cyrillic)**: ~10% of mathematicians
2. **C2 (Chinese)**: ~15% of mathematicians  
3. **B2 (Arabic/Middle East)**: ~5% of mathematicians
4. **C3 (Japanese)**: ~8% of mathematicians
5. **A2 (Latin America)**: ~7% of mathematicians

**Implementation per region**:
- Create region processor class
- Implement name normalization rules
- Add script validation
- Define naming conventions
- Add test coverage
**Success Metric**: 6/43 regions working (14% regional coverage)

### 2.3 Fix Concurrent Operations
**Problem**: Deadlocks and race conditions in concurrent tests
**Solution**:
- Review and fix locking strategy in CacheManager
- Add proper connection pooling to database
- Implement thread-safe queue for pipeline processing
- Add backoff and retry logic
**Success Metric**: test_concurrent_chaos.py passes

## Phase 3: Extended Coverage (Days 8-14)

### 3.1 Implement Remaining Regions (36 regions)
**Grouped by similarity**:
- **European variants** (A3-A7, D1-D4): 10 regions
- **Asian variants** (B5-B6, C1, C4-C6, E1-E6, F1-F4): 16 regions  
- **African** (B3-B4): 2 regions
- **Historical** (G1-G3): 3 regions
- **Diaspora** (H1-H3): 3 regions
- **Special** (R0, Z0): 2 regions

**Success Metric**: All 43 regions implemented

### 3.2 Quota Management System
**Problem**: No API quota tracking
**Solution**:
- Implement quota tracking per API source
- Add rate limiting with token bucket algorithm
- Persist quota state across restarts
- Add quota alerts and notifications
**Success Metric**: Can track and enforce API quotas

### 3.3 Authority Data Fetching
**Problem**: No actual API integration
**Solution**:
- Implement OpenAlex API client
- Add ORCID integration
- Implement retry logic with exponential backoff
- Add response caching
- Handle API errors gracefully
**Success Metric**: Can fetch real data from APIs

## Phase 4: Production Readiness (Days 15-20)

### 4.1 Security Implementation
- Input validation and sanitization
- SQL injection prevention
- API key management
- Audit logging
- Data encryption at rest

### 4.2 Performance Optimization  
- Database query optimization
- Caching strategy improvement
- Batch processing for bulk operations
- Memory usage optimization

### 4.3 Monitoring and Observability
- Metrics collection
- Health check endpoints
- Performance monitoring
- Error tracking

## Testing Strategy

### Incremental Testing
- Fix one test file at a time
- Ensure no regressions
- Add tests for new functionality

### Test Priority Order:
1. test_database_operations.py
2. test_authority_integration.py  
3. test_regional_processing.py
4. test_pipeline_memory.py
5. test_concurrent_chaos.py
6. test_configuration_security.py
7. Remaining test files

## Success Metrics

### Phase 1 Complete:
- Database tests pass
- Authority tests run without errors
- Can persist and retrieve data

### Phase 2 Complete:
- Pipeline processes entries end-to-end
- 6 regions implemented
- Concurrent operations work

### Phase 3 Complete:
- All 43 regions implemented
- API integration working
- Quota management active

### Phase 4 Complete:
- All tests pass
- Security hardened
- Production ready

## Risk Mitigation

### Technical Risks:
- **Concurrent operations complexity**: Start simple, add complexity gradually
- **Regional variation**: Create base class with common functionality
- **API reliability**: Implement robust retry and caching

### Timeline Risks:
- **Scope creep**: Stick to plan, defer nice-to-haves
- **Unknown unknowns**: Add 20% buffer to estimates
- **Testing overhead**: Automate wherever possible

## Daily Checklist

1. [ ] Run test suite, note improvements
2. [ ] Implement planned features
3. [ ] Fix any regressions
4. [ ] Update documentation
5. [ ] Commit working code

## Conclusion

This plan will take the GMNAP system from 15% to 100% complete in approximately 20 days of focused development. The phased approach ensures we fix blockers first, implement core functionality next, and then achieve full coverage.

The key is disciplined execution: fix problems systematically, test continuously, and maintain quality throughout.