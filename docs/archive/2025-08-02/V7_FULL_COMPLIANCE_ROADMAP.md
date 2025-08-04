# 🎯 GMNAP v7 Full Compliance Implementation Roadmap
*Date: 2025-08-01*

## 📋 Executive Summary

This document provides a comprehensive roadmap for achieving **100% GMNAP v7.0 compliance** "to the letter" as specified in `docs/specs v7.0.yaml`. 

**Key Discovery**: V7.0 is not just an architecture enhancement - it's a complete **MathLineage Edition** transformation that adds genealogy tracking, LLM-powered ETD extraction, and graph database capabilities.

## 🔍 Critical V7.0 vs Current GMNAP Gap Analysis

### Major New Requirements in V7.0:

#### 1. **MathLineage Edition Features** ❌ NOT IMPLEMENTED
- **Graph Database**: Memgraph-CE integration for genealogy relationships
- **LLM ETD Extraction**: GPT-4o-mini powered thesis parsing 
- **Genealogy Relations**: Doctoral advisor tracking with betweenness centrality
- **DOI Minting**: ETH-Bibliothek DataCite integration
- **Archive Integration**: ETH Data Archive snapshots

#### 2. **Enhanced Pipeline** ⚠️ PARTIALLY IMPLEMENTED
- **12 Stages** (vs current 10): Added LLMExtract_ETD and GraphConsistency
- **Expanded Authority Sources**: New genealogy-focused sources
- **Enhanced Quality Gates**: Graph coherence scoring

#### 3. **New Schema Objects** ❌ NOT IMPLEMENTED
- `GenealogyRelation` objects
- `DegreeDate` with precision tracking
- `ShadowNode` for GDPR erasure
- `BetweennessScore` for centrality analysis

#### 4. **Infrastructure Changes** ❌ NOT IMPLEMENTED
- **Memory Limit**: Increased from 2GB to 6GB RSS
- **Cost Caps**: CHF 120/month for overall, CHF 40/month for LLM
- **Docker Compose**: Multi-service architecture
- **Monitoring**: Prometheus + Grafana stack

## 📊 Current GMNAP vs V7.0 Compliance Matrix

| Component | Current Status | V7.0 Requirement | Gap |
|-----------|---------------|------------------|-----|
| **Regional Processors** | 12/43 (28%) | 43/43 (100%) | 31 regions ❌ |
| **Pipeline Stages** | 10 stages | 12 stages | LLMExtract + GraphConsistency ❌ |
| **Authority Sources** | 5 tier-0 | 15 sources across 4 tiers | 10 new sources ❌ |
| **Graph Database** | None | Memgraph-CE | Full implementation ❌ |
| **LLM Integration** | None | GPT-4o-mini ETD | Full implementation ❌ |
| **Genealogy Features** | None | Full advisor tracking | Full implementation ❌ |
| **Schema Version** | v1.5 | v2.0 | Schema upgrade ❌ |
| **Memory Limit** | 2GB | 6GB | Configuration change ✅ |
| **Testing** | 1000 fixtures | 1500 fixtures | 500 more tests ❌ |

**Overall V7.0 Compliance: ~15%** (much lower than previous 38% v6 estimate)

## 🎯 V7.0 Implementation Phases

### Phase 1: Core Infrastructure (Months 1-2)
**Estimated Effort: 300-400 hours**

#### 1.1 Graph Database Integration
- [ ] Install and configure Memgraph-CE Docker container
- [ ] Create genealogy schema and relationship models
- [ ] Implement graph query layer for advisor relationships
- [ ] Add betweenness centrality calculations

#### 1.2 LLM ETD Extraction System
- [ ] Integrate OpenAI GPT-4o-mini API
- [ ] Implement PDF parsing pipeline (max 400 pages)
- [ ] Create JSON schema validation for thesis metadata
- [ ] Add cost monitoring and CHF 40/month cap enforcement

#### 1.3 Pipeline Enhancement
- [ ] Add Stage 1b: LLMExtract_ETD
- [ ] Add Stage 6: GraphConsistency
- [ ] Implement DOI minting with ETH-Bibliothek DataCite
- [ ] Create ETH Data Archive integration

### Phase 2: Schema & Data Model Upgrade (Months 2-3)
**Estimated Effort: 200-300 hours**

#### 2.1 Schema v2.0 Migration
- [ ] Upgrade from YAML schema v1.5 to v2.0
- [ ] Add `GenealogyRelation` objects
- [ ] Implement `DegreeDate` with precision tracking
- [ ] Add `ShadowNode` for GDPR compliance
- [ ] Create `BetweennessScore` centrality tracking

#### 2.2 Enhanced Authority Sources
- [ ] Implement ORCID_ETD specialized endpoint
- [ ] Add Crossref_Thesis domain-specific queries
- [ ] Integrate Wikidata P184 genealogy data
- [ ] Create OAI_University thesis harvesting
- [ ] Add ProQuest_ETD commercial integration

### Phase 3: Regional Processor Completion (Months 3-6)
**Estimated Effort: 800-1200 hours**

#### 3.1 Missing A-Group Regions
- [ ] A3 Nordic-Baltic (DK, NO, SE, FI, IS, FO, AX, EE, LV, LT)
- [ ] A4 Oceania Island States (FJ, PG, SB, VU, WS, TO, etc.)
- [ ] A5 Dutch/French Caribbean (CW, SX, BQ, MQ, GF, GP, etc.)

#### 3.2 Missing B-Group Regions  
- [ ] B3 Greek World (GR, CY)

#### 3.3 Missing C-Group Regions
- [ ] C1 Greater-Turkic (TR, AZ, UZ, TM, KG, KZ)
- [ ] C5 Arabic Maghreb (MA, DZ, TN, LY, EH, MR)
- [ ] C6 Hebrew & Diaspora (IL)
- [ ] C7 Armenian (AM)
- [ ] C8 Georgian (GE)
- [ ] C9 Caucasus-Turkic (RU, AZ border regions)

#### 3.4 Missing D-Group Regions
- [ ] D2 South Asia - Dravidian (IN-South, LK-TA)
- [ ] D3 South Asia - Bengali (BD, IN-WB, TR, AS)
- [ ] D4 Pakistan & Urdu (PK)
- [ ] D5 Sinhala (LK-SI)

#### 3.5 Missing E-Group Regions
- [ ] E2 Sinophone Traditional (TW, HK, MO)
- [ ] E5 Vietnam (VN)
- [ ] E6 Mainland SEA (TH, KH, LA)
- [ ] E7 Maritime SEA (ID, MY, SG, BN, PH, TL)

#### 3.6 Missing F-Group Regions (Africa)
- [ ] F1 SSA - Francophone (18 countries)
- [ ] F2 SSA - Anglophone (18 countries)
- [ ] F3 Horn of Africa (ET, ER)
- [ ] F4 Lusophone Africa (AO, MZ, CV, GW, ST)

#### 3.7 Missing Special Regions
- [ ] H1 Historical (≤1850)
- [ ] R0 Residual Latin-ASCII
- [ ] Z0 Quarantine

### Phase 4: Quality & Operations (Months 6-7)
**Estimated Effort: 200-300 hours**

#### 4.1 Enhanced Testing
- [ ] Expand from 1000 to 1500 test fixtures
- [ ] Add lineage graph coherence tests
- [ ] Implement snapshot rollback testing
- [ ] Add cost guard CI tests (CHF limits)

#### 4.2 Operations Infrastructure
- [ ] Deploy Docker Compose multi-service stack
- [ ] Implement Prometheus + Grafana monitoring
- [ ] Create rate limiting (free: 60 req/min, paid: 10k req/min)
- [ ] Set up ETH Data Archive daily backups

#### 4.3 Quality Gates
- [ ] Graph coherence scoring (85%/92%/97% by mode)
- [ ] Genealogy edge conflict detection (<2%/1%/0%)
- [ ] Enhanced idempotency checking

### Phase 5: Deployment & Integration (Month 8)
**Estimated Effort: 100-200 hours**

#### 5.1 Production Deployment
- [ ] Deploy complete v7.0 system
- [ ] Validate all 43 regional processors
- [ ] Test genealogy relationship extraction
- [ ] Verify LLM ETD processing pipeline

#### 5.2 Documentation & Training
- [ ] Update all documentation for v7.0
- [ ] Create deployment guides
- [ ] Write genealogy API documentation
- [ ] Prepare handoff materials

## 📊 Resource Requirements

### Development Effort
- **Total Estimated Hours**: 1,600-2,400 hours
- **Timeline**: 8 months (full-time equivalent)
- **Complexity**: Very High (requires ML, graph databases, multi-service architecture)

### Infrastructure Costs (CHF/month)
- **OpenAI GPT-4o-mini**: CHF 40 (hard cap)
- **Overall pipeline**: CHF 120 (hard cap)
- **Memgraph-CE**: Free (community edition)
- **ETH services**: Negotiated rates
- **Total**: ~CHF 160/month operational costs

### Technical Dependencies
- **New Technologies**: Memgraph, OpenAI API, Docker Compose
- **ETH Integration**: DataCite DOI minting, Data Archive
- **Monitoring Stack**: Prometheus, Grafana, Redis
- **Database**: DuckDB + Memgraph dual-database architecture

## 🚨 Critical Risks & Challenges

### 1. **Scope Explosion**
V7.0 is not an upgrade but a complete **reimagining** as "MathLineage Edition". The genealogy features alone represent a new product category.

### 2. **ETH Dependencies**
Heavy reliance on ETH-Bibliothek services (DOI minting, data archive) creates external dependencies that may not be available to all users.

### 3. **Cost Management**
LLM processing costs could spiral without careful monitoring. The CHF 40/month cap requires sophisticated usage tracking.

### 4. **Graph Database Complexity**
Memgraph integration adds significant operational complexity vs. current SQLite/DuckDB approach.

### 5. **Data Quality**
Genealogy relationship extraction requires high-precision parsing of thesis metadata - error rates could be significant.

## 💡 Strategic Recommendations

### Option A: Full V7.0 Implementation
- **Effort**: 1,600-2,400 hours
- **Timeline**: 8 months
- **Risk**: Very High
- **Benefit**: Complete MathLineage Edition with genealogy features

### Option B: V7.0-Lite (Core Features Only)
- **Focus**: Graph DB + basic genealogy, skip LLM extraction
- **Effort**: 800-1,200 hours  
- **Timeline**: 4-5 months
- **Risk**: Medium
- **Benefit**: Genealogy tracking without LLM complexity

### Option C: V6.1+ Enhancement
- **Focus**: Complete current 31 regional processors first
- **Effort**: 600-800 hours
- **Timeline**: 3-4 months
- **Risk**: Low
- **Benefit**: Solid foundation before v7.0 leap

### Option D: Staged Migration
- **Phase 1**: Complete v6.1 regions (months 1-3)
- **Phase 2**: Add graph DB (months 4-5)
- **Phase 3**: Add LLM extraction (months 6-7)
- **Phase 4**: Full v7.0 compliance (month 8)

## 🏁 Recommendation

**Recommended Path: Option D (Staged Migration)**

1. **Immediate**: Complete remaining 31 regional processors (solid foundation)
2. **Short-term**: Add Memgraph integration for genealogy relationships
3. **Medium-term**: Integrate LLM ETD extraction capabilities
4. **Long-term**: Achieve full v7.0 MathLineage Edition compliance

This approach:
- ✅ Builds on existing strong foundation
- ✅ Reduces risk through incremental delivery
- ✅ Provides value at each stage
- ✅ Allows learning and course correction
- ✅ Maintains production stability

## 📋 Next Immediate Actions

1. **Validate User Need**: Confirm demand for genealogy features vs. regional coverage
2. **ETH Partnership**: Establish relationship with ETH-Bibliothek for services
3. **Proof of Concept**: Build minimal Memgraph integration prototype
4. **Cost Analysis**: Model LLM processing costs with sample thesis corpus
5. **Architecture Review**: Design multi-service Docker Compose structure

---

**The v7.0 specification represents a fundamental pivot from "name authority" to "academic genealogy platform." This is not an incremental upgrade but a complete product transformation requiring careful strategic planning.**