# GMNAP v7 Organization Plan
**Global Mathematician Authority Project - Version 7 Architecture**

## Executive Summary

This document outlines the complete reorganization of the GMNAP project for v7, incorporating the new Korean converter v6 implementation while maintaining compatibility with existing v5 systems and establishing a clean, maintainable architecture.

## Current Project State Analysis

### Existing Structure (Found in `/Users/dylanpossamai/Dropbox/Work/Maths/gmnap/`)
- **Comprehensive v5 Korean Implementation**: Already functional system with ~97% accuracy
- **Complete Testing Infrastructure**: Extensive test suites, validation scripts, and performance monitoring
- **Production-Ready Components**: Docker containerization, monitoring, caching, and API layers
- **Rich Documentation**: Multiple implementation guides, audit reports, and status documents

### Issues with Current Structure
- **Scattered Files**: Mixed temporary files with production code
- **Version Confusion**: v4, v5, and development files intermixed  
- **Duplicate Implementations**: Multiple converter approaches without clear hierarchy
- **Cache Pollution**: Temporary test files mixed with permanent assets

## GMNAP v7 Target Architecture

### Primary Directory Structure
```
/Users/dylanpossamai/Dropbox/Work/Maths/gmnap_v7/
├── README.md                           # Project overview and quick start
├── ARCHITECTURE.md                     # v7 architecture documentation
├── CHANGELOG.md                        # Version history and migration notes
├── docker-compose.yml                  # Production deployment
├── requirements.txt                    # Python dependencies
├── Makefile                           # Build and deployment scripts
├── 
├── components/                        # Modular component implementations
│   ├── korean_v6/                    # New Korean converter v6
│   │   ├── README.md                 # v6-specific documentation  
│   │   ├── env.yml                   # Conda environment specification
│   │   ├── resources/                # Generated syllable maps and tokens
│   │   ├── models/                   # Compiled FST binaries
│   │   ├── scripts/                  # Generation and validation scripts
│   │   ├── src/                      # Core converter modules
│   │   └── korean.yaml               # Ground truth test data
│   │
│   ├── korean_v5/                    # Legacy v5 (maintained for compatibility)
│   │   └── [existing v5 structure]
│   │
│   └── core/                         # Shared infrastructure
│       ├── pipeline/                 # Data processing pipeline
│       ├── authorities/              # External API integrations
│       ├── validation/               # Schema and data validation
│       └── monitoring/               # Performance and health monitoring
│
├── data/                             # Persistent data and configurations
│   ├── config/                       # Environment configurations
│   ├── schemas/                      # Data validation schemas
│   ├── test_datasets/                # Curated test data
│   └── cache/                        # Persistent cache (separated from temp)
│
├── infrastructure/                   # Deployment and operations
│   ├── docker/                       # Container configurations
│   ├── k8s/                         # Kubernetes manifests (if applicable)
│   ├── monitoring/                   # Observability configurations
│   └── scripts/                      # Operations and maintenance scripts
│
├── tests/                           # Comprehensive testing framework
│   ├── unit/                        # Component unit tests
│   ├── integration/                 # Cross-component integration tests
│   ├── performance/                 # Load and stress testing
│   ├── quality_gates/               # Accuracy and reliability benchmarks
│   └── regression/                   # Version compatibility tests
│
├── docs/                            # Centralized documentation
│   ├── api/                         # API documentation
│   ├── architecture/                # System design documents
│   ├── deployment/                  # Operations guides
│   ├── development/                 # Developer setup and guidelines
│   └── migration/                   # Version upgrade guides
│
└── archive/                         # Historical versions and deprecated code
    ├── v4_backup/                   # Archived v4 implementation
    ├── experimental/                # Research and prototyping code
    └── temp_cleanup/                # Temporary files to be reviewed/deleted
```

## Migration Strategy

### Phase 1: Archive and Clean (Priority: HIGH)
1. **Create v7 Structure**: Establish clean directory hierarchy
2. **Archive Legacy**: Move v4 and experimental code to archive
3. **Preserve v5**: Maintain functional v5 Korean converter
4. **Extract Core**: Identify and preserve essential shared components

### Phase 2: Implement Korean v6 (Priority: HIGH)
1. **Setup v6 Environment**: Create isolated conda environment
2. **Implement Core Modules**: Build v6 converter following exact specifications
3. **Validation Framework**: Ensure ≥97% accuracy benchmark
4. **Integration Points**: Define interfaces with core pipeline

### Phase 3: Integration and Testing (Priority: MEDIUM)
1. **Core Pipeline**: Integrate v6 with existing infrastructure
2. **Testing Framework**: Comprehensive test coverage
3. **Performance Validation**: Benchmark against v5 performance
4. **Documentation**: Complete API and usage documentation

### Phase 4: Production Deployment (Priority: LOW)
1. **Container Optimization**: Docker configurations for v7
2. **Monitoring Integration**: Observability and alerting
3. **Deployment Automation**: CI/CD pipeline setup
4. **Rollback Preparation**: Fallback to v5 if needed

## Korean Converter v6 Integration Points

### Core Interface Contract
```python
# Standard interface for all Korean converters
class KoreanConverterInterface:
    def eng2kor(self, name: str) -> str | None:
        """Convert English romanized name to Korean"""
        
    def kor2eng(self, name: str) -> str | None:  
        """Convert Korean name to English romanization"""
        
    def validate_roundtrip(self, name: str) -> float:
        """Return similarity score for round-trip conversion"""
```

### Performance Requirements
- **Accuracy**: ≥97% round-trip accuracy on test dataset
- **Speed**: <100ms response time for single name conversion
- **Memory**: <512MB peak memory usage
- **Reliability**: 99.9% uptime with graceful fallback to v5

### Compatibility Requirements
- **v5 Fallback**: Automatic failover if v6 unavailable
- **API Compatibility**: Maintain existing API contracts
- **Data Format**: Compatible with existing test datasets
- **Configuration**: Environment-based feature flagging

## Implementation Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1: Archive & Clean | 2 hours | Clean v7 structure, preserved v5 |
| 2: Korean v6 | 4 hours | Working v6 converter with ≥97% accuracy |
| 3: Integration | 2 hours | v6 integrated into core pipeline |
| 4: Production | 1 hour | Documentation and deployment configs |

## Risk Mitigation

### Technical Risks
- **v6 Performance**: Fallback to v5 if accuracy drops below 97%
- **Environment Issues**: Containerized deployment reduces dependency conflicts  
- **Integration Bugs**: Comprehensive testing framework catches regressions

### Operational Risks
- **Data Loss**: All existing data preserved in archive
- **Service Disruption**: v5 remains operational during v6 development
- **Compatibility**: Careful interface design maintains API contracts

## Success Criteria

### Functional Requirements
- ✅ Korean v6 converter achieves ≥97% round-trip accuracy
- ✅ Clean, maintainable project structure established
- ✅ All existing functionality preserved and accessible
- ✅ Comprehensive documentation and testing framework

### Non-Functional Requirements  
- ✅ Sub-100ms response times for name conversion
- ✅ Memory usage under 512MB per converter instance
- ✅ Zero-downtime deployment capability
- ✅ Clear separation between components and versions

## Next Steps

1. **Begin Phase 1**: Create clean v7 structure and archive legacy code
2. **Implement Korean v6**: Follow exact specifications for 2025-proof implementation
3. **Integration Testing**: Ensure seamless operation with existing infrastructure
4. **Documentation**: Complete technical documentation and deployment guides

This organization plan ensures GMNAP v7 maintains all existing functionality while providing a clean foundation for the Korean converter v6 and future enhancements.