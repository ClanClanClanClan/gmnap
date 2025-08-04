# 🎯 GMNAP V7.0 Implementation Master Plan
*Date: 2025-08-01*  
*Status: DEFINITIVE IMPLEMENTATION GUIDE*

## 📋 Executive Summary

This document provides the **definitive, step-by-step implementation plan** to achieve 100% GMNAP v7.0 "MathLineage Edition" compliance as specified in `docs/specs v7.0.yaml`.

**Critical Insight**: V7.0 is not an upgrade but a **complete transformation** from "name authority" to "academic genealogy platform" with graph databases, LLM integration, and multi-service architecture.

**Development Strategy**: Build everything locally without operational costs. Costs only apply when deployed operationally.

## 🚀 Implementation Phases Overview

| Phase | Focus | Duration | Effort | Dependencies |
|-------|-------|----------|--------|--------------|
| **Phase 1** | Regional Completion | 3-4 months | 800-1200h | None |
| **Phase 2** | Graph Database Core | 1-2 months | 300-400h | Memgraph-CE |
| **Phase 3** | LLM Integration | 1-2 months | 200-300h | OpenAI API |
| **Phase 4** | Multi-Service Arch | 1 month | 150-200h | Docker Compose |
| **Phase 5** | Full V7 Polish | 1 month | 100-150h | All above |

**Total Estimated Timeline**: 8-10 months  
**Total Estimated Effort**: 1,550-2,250 hours

## 📊 Phase 1: Regional Processor Completion
**Priority: HIGHEST** | **Duration: 3-4 months** | **Effort: 800-1200 hours**

### 1.1 Missing A-Group Regions (3 regions)

#### A3 Nordic-Baltic (DK, NO, SE, FI, IS, FO, AX, EE, LV, LT)
```python
# Implementation Required:
- Icelandic patronymic system (linguistic rule #8)
- Scandinavian particle handling
- Baltic surname patterns
- Script detection for mixed Latin/diacritics

# Files to Create:
- src/gmnap/regions/a_groups/a3_nordic_baltic/
- tests/unit/test_a3_nordic_baltic.py
- docs/regional/A3_NORDIC_BALTIC.md
```

#### A4 Oceania Island States (FJ, PG, SB, VU, WS, TO, KI, TV, NR, CK, NU, PF, NC)
```python
# Implementation Required:
- Polynesian macron restoration (linguistic rule #31)
- Island-specific name patterns
- Māori/Samoan/Tongan forms
- Colonial vs indigenous naming

# Files to Create:
- src/gmnap/regions/a_groups/a4_oceania/
- tests/unit/test_a4_oceania.py
- docs/regional/A4_OCEANIA.md
```

#### A5 Dutch/French Caribbean (CW, SX, BQ, MQ, GF, GP, RE, YT, PM)
```python
# Implementation Required:
- Creole particle handling
- Apostrophe normalization
- French/Dutch colonial patterns
- Caribbean-specific surnames

# Files to Create:
- src/gmnap/regions/a_groups/a5_caribbean/
- tests/unit/test_a5_caribbean.py
- docs/regional/A5_CARIBBEAN.md
```

### 1.2 Missing B-Group Regions (1 region)

#### B3 Greek World (GR, CY)
```python
# Implementation Required:
- ELOT 743 & ISO 843 romanisation
- Greek script detection
- Ancient vs modern Greek handling (rule #25)
- Χατζη- variants (rule #19)

# Files to Create:
- src/gmnap/regions/b_groups/b3_greek/
- tests/unit/test_b3_greek.py
- docs/regional/B3_GREEK.md
```

### 1.3 Missing C-Group Regions (6 regions)

#### C1 Greater-Turkic (TR, AZ, UZ, TM, KG, KZ)
```python
# Implementation Required:
- Script reform schedules (UZ 2023-, TM 2019-, KZ 2023→2031)
- Turkish İ/i ambiguity (rule #6) 
- Turkic -oğlu/-ogly handling (rule #20)
- Multi-script detection (Latin/Cyrillic/Arabic)

# Files to Create:
- src/gmnap/regions/c_groups/c1_turkic/
- config/script_switch.yaml
- tests/unit/test_c1_turkic.py
```

#### C5 Arabic Maghreb (MA, DZ, TN, LY, EH, MR) 
```python
# Implementation Required:
- Ben... prefixes (linguistic rule #32)
- French transliteration patterns
- Maghreb-specific Arabic variants
- Colonial name influences

# Files to Create:
- src/gmnap/regions/c_groups/c5_maghreb/
- tests/unit/test_c5_maghreb.py
```

#### C6 Hebrew & Diaspora (IL)
```python
# Implementation Required:
- ISO 259 romanisation
- Hebrew script detection
- Optional niqqud handling
- Diaspora vs Israeli patterns

# Files to Create:
- src/gmnap/regions/c_groups/c6_hebrew/
- tests/unit/test_c6_hebrew.py
```

#### C7 Armenian (AM)
```python
# Implementation Required:
- Hübschmann-Meillet romanisation
- Armenian script detection
- Eastern vs Western Armenian
- Diaspora patterns

# Files to Create:
- src/gmnap/regions/c_groups/c7_armenian/
- tests/unit/test_c7_armenian.py
```

#### C8 Georgian (GE)
```python
# Implementation Required:
- ISO 9984 transliteration
- Georgian script detection
- Surname vs patronymic patterns
- Regional variations

# Files to Create:
- src/gmnap/regions/c_groups/c8_georgian/
- tests/unit/test_c8_georgian.py
```

#### C9 Caucasus-Turkic (RU-NC, AZ-IR border)
```python
# Implementation Required:
- Latin/Cyrillic/Arabic hybrid handling
- Regional overlay mapping
- Complex script mixing
- Cross-border patterns

# Files to Create:
- src/gmnap/regions/c_groups/c9_caucasus_turkic/
- tests/unit/test_c9_caucasus_turkic.py
```

### 1.4 Missing D-Group Regions (4 regions)

#### D2 South Asia - Dravidian (IN-South, LK-TA)
```python
# Implementation Required:
- Patronymic initials (rule #26)
- Tamil script detection
- Mononym handling (rule #14)
- South Indian naming patterns

# Files to Create:
- src/gmnap/regions/d_groups/d2_dravidian/
- tests/unit/test_d2_dravidian.py
```

#### D3 South Asia - Bengali (BD, IN-WB, TR, AS)
```python
# Implementation Required:
- Bengali script detection
- Frequent script switching
- Bengali romanisation patterns
- Cross-border variations

# Files to Create:
- src/gmnap/regions/d_groups/d3_bengali/
- tests/unit/test_d3_bengali.py
```

#### D4 Pakistan & Urdu (PK)
```python
# Implementation Required:
- bin/binte patterns (rule #3)
- Urdu script detection
- Arabic loan integration
- Pakistani naming conventions

# Files to Create:
- src/gmnap/regions/d_groups/d4_pakistani/
- tests/unit/test_d4_pakistani.py
```

#### D5 Sinhala (LK-SI)
```python
# Implementation Required:
- UN 2003 transliteration
- Sinhala script detection
- Sri Lankan patterns
- Buddhist naming conventions

# Files to Create:
- src/gmnap/regions/d_groups/d5_sinhala/
- tests/unit/test_d5_sinhala.py
```

### 1.5 Missing E-Group Regions (4 regions)

#### E2 Sinophone Traditional (TW, HK, MO)
```python
# Implementation Required:
- Traditional Chinese script detection
- Cantonese romanisation
- Hong Kong naming patterns
- Cross-strait variations

# Files to Create:
- src/gmnap/regions/e_groups/e2_traditional_chinese/
- tests/unit/test_e2_traditional_chinese.py
```

#### E5 Vietnam (VN)
```python
# Implementation Required:
- Vietnamese tone handling (rule #4)
- Numeric tone variants
- ASCII fallback patterns
- Vietnamese surname patterns

# Files to Create:
- src/gmnap/regions/e_groups/e5_vietnam/
- tests/unit/test_e5_vietnam.py
```

#### E6 Mainland SEA (TH, KH, LA)
```python
# Implementation Required:
- Thai RTGS romanisation (rule #27)
- Khmer UNGEGN transliteration
- Lao MOICT 2019 standards
- SEA round-trip testing (≥97% accuracy)

# Files to Create:
- src/gmnap/regions/e_groups/e6_mainland_sea/
- tests/sea_roundtrip/test_thai_khmer_lao.py
```

#### E7 Maritime SEA (ID, MY, SG, BN, PH, TL)
```python
# Implementation Required:
- Malay bin/binti patterns (rule #28)
- Indonesian mononyms (rule #29)
- Filipino maternal middle names (rule #30)
- Maritime naming variations

# Files to Create:
- src/gmnap/regions/e_groups/e7_maritime_sea/
- tests/unit/test_e7_maritime_sea.py
```

### 1.6 Missing F-Group Regions (4 regions - Africa)

#### F1 SSA - Francophone (18 countries)
```python
# Countries: BJ, BF, CM, CF, CG, CI, DJ, GA, GN, ML, NE, SN, TG, TD, KM, SC, MG, BI
# Implementation Required:
- Accented French particles
- African surname patterns
- Colonial naming influences
- Multi-ethnic handling

# Files to Create:
- src/gmnap/regions/f_groups/f1_francophone_africa/
- tests/unit/test_f1_francophone_africa.py
```

#### F2 SSA - Anglophone (18 countries)
```python
# Countries: GH, NG, KE, UG, TZ, ZW, ZM, MW, GM, LR, SL, BW, LS, NA, RW, SZ, MU, SS
# Implementation Required:
- Hyphenated given names (rule #23)
- Middle initials patterns
- African surname patterns
- Colonial vs traditional names

# Files to Create:
- src/gmnap/regions/f_groups/f2_anglophone_africa/
- tests/unit/test_f2_anglophone_africa.py
```

#### F3 Horn of Africa (ET, ER)
```python
# Implementation Required:
- Ge'ez script detection
- Patronymic chain (given-father-grandfather)
- Ethiopian naming conventions
- Eritrean variations

# Files to Create:
- src/gmnap/regions/f_groups/f3_horn_africa/
- tests/unit/test_f3_horn_africa.py
```

#### F4 Lusophone Africa (AO, MZ, CV, GW, ST)
```python
# Implementation Required:
- Portuguese particles (rule #33)
- Lusophone surname patterns
- African Portuguese variations
- Island vs mainland differences

# Files to Create:
- src/gmnap/regions/f_groups/f4_lusophone_africa/
- tests/unit/test_f4_lusophone_africa.py
```

### 1.7 Missing Special Regions (3 regions)

#### H1 Historical (≤1850)
```python
# Implementation Required:
- Latinised names (rule #34)
- Epithets handling
- Historical context detection
- Pre-modern naming patterns

# Files to Create:
- src/gmnap/regions/special/h1_historical/
- tests/unit/test_h1_historical.py
```

#### R0 Residual Latin-ASCII
```python
# Implementation Required:
- Catch-all for unmapped territories
- Minimal matching rules
- Fallback mechanisms
- Basic Latin processing

# Files to Create:
- src/gmnap/regions/special/r0_residual/
- tests/unit/test_r0_residual.py
```

#### Z0 Quarantine
```python
# Implementation Required:
- Detector confidence < 50% handling
- Error state management
- Quarantine logic
- Recovery mechanisms

# Files to Create:
- src/gmnap/regions/special/z0_quarantine/
- tests/unit/test_z0_quarantine.py
```

## 🗄️ Phase 2: Graph Database Integration
**Priority: HIGH** | **Duration: 1-2 months** | **Effort: 300-400 hours**

### 2.1 Memgraph-CE Setup
```yaml
# docker-compose.yml addition:
services:
  memgraph:
    image: memgraph/memgraph-platform:2.12
    ports:
      - "7687:7687"  # Bolt protocol
    volumes:
      - memgraph-data:/var/lib/memgraph
    environment:
      - MEMGRAPH_ENTERPRISE_LICENSE=
      - MEMGRAPH_ORGANIZATION_NAME=GMNAP
```

### 2.2 Schema v2.0 Migration
```python
# New schema objects to implement:

class GenealogyRelation:
    source_id: str          # GlobalID of student
    target_id: str          # GlobalID of advisor
    relation_type: Literal["doctoralAdvisor", "adviserCommitteeMember", 
                           "postdocMentor", "habilitationAdvisor"]
    qualifier: Optional[str] # "co-advisor", "external", etc.
    confidence: float       # 0.0 - 1.0

class DegreeDate:
    date: str              # YYYY-MM-DD
    precision: Literal["year", "month", "day"]

class ShadowNode:
    original_id: str       # For GDPR erasure
    erased_date: str       # When erased
    reason: str           # "gdpr_request", "privacy"

class BetweennessScore:
    node_id: str          # GlobalID
    score: float          # 0.0 - 1.0 normalized
    updated: str          # Last calculation date
```

### 2.3 Graph Query Layer
```python
# Files to Create:
- src/gmnap/graph/
  ├── __init__.py
  ├── memgraph_client.py      # Bolt protocol client
  ├── genealogy_queries.py    # Cypher queries
  ├── relationship_manager.py # CRUD operations
  ├── centrality_calculator.py # Betweenness algorithms
  └── graph_validator.py      # Coherence checking

# Key Methods to Implement:
- add_genealogy_relation(source_id, target_id, relation_type)
- calculate_betweenness_centrality()
- find_academic_lineage(person_id, depth=3)
- detect_cycles(max_depth=3)
- validate_graph_coherence()
```

### 2.4 Pipeline Integration
```python
# Add Stage 6: GraphConsistency
def stage_6_graph_consistency(entries: List[dict]) -> None:
    """
    - Calculate betweenness centrality for all nodes
    - Apply Bayesian confidence scoring
    - Reject cycles < 3 degrees
    - Update BetweennessScore objects
    """
    
# Quality Gate Addition:
graph_coherence_score_min: {quick: 0.85, full: 0.92, extreme: 0.97}
genealogy_edge_conflict_pct: {quick_max: 2.0, full_max: 1.0, extreme_max: 0.0}
```

## 🤖 Phase 3: LLM Integration Framework
**Priority: HIGH** | **Duration: 1-2 months** | **Effort: 200-300 hours**

### 3.1 OpenAI Integration
```python
# Files to Create:
- src/gmnap/llm/
  ├── __init__.py
  ├── openai_client.py        # GPT-4o-mini integration
  ├── etd_extractor.py        # Thesis PDF parsing
  ├── json_validator.py       # Schema validation
  ├── cost_monitor.py         # CHF 40/month cap
  └── mock_responses.py       # Development testing

# Configuration:
llm_extract:
  engine: "gpt-4o-mini"
  cost_cap_chf_per_month: 40
  max_pdf_pages: 400
  timeout_seconds: 120
```

### 3.2 PDF Processing Pipeline
```python
# ETD Extraction JSON Schema:
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ETD-LLM-Output",
  "type": "object",
  "required": ["title", "authors", "advisors", "degree_date", "institution"],
  "properties": {
    "title": {"type": "string", "minLength": 2},
    "authors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    "advisors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    "degree_date": {"type": "string", "pattern": "^[0-9]{4}(-[0-9]{2}){0,2}$"},
    "degree": {"type": "string"},
    "institution": {"type": "string"},
    "language": {"type": "string", "maxLength": 16}
  }
}
```

### 3.3 Pipeline Integration
```python
# Add Stage 1b: LLMExtract_ETD
def stage_1b_llm_extract_etd(pdf_path: str) -> dict:
    """
    - Parse PDF with GPT-4o-mini (max 400 pages)
    - Extract thesis metadata
    - Validate against JSON schema
    - Cache results with cost tracking
    """
    
# Cost Monitoring:
- Track API usage in real-time
- Enforce CHF 40/month hard cap
- Generate cost reports
- Fail gracefully when limit reached
```

## 🐳 Phase 4: Multi-Service Architecture
**Priority: MEDIUM** | **Duration: 1 month** | **Effort: 150-200 hours**

### 4.1 Docker Compose Infrastructure
```yaml
# docker-compose.yml (complete):
version: '3.8'
services:
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [memgraph, redis]
    
  memgraph:
    image: memgraph/memgraph-platform:2.12
    ports: ["7687:7687"]
    volumes: [memgraph-data:/var/lib/memgraph]
    
  duckdb-batch:
    build: .
    command: python -m src.core.batch_processor
    volumes: [./data:/app/data]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes: [./nginx.conf:/etc/nginx/nginx.conf]

volumes:
  memgraph-data:
```

### 4.2 Monitoring Stack
```yaml
# monitoring/docker-compose.monitoring.yml:
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes: [./prometheus.yml:/etc/prometheus/prometheus.yml]
    
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes: [grafana-data:/var/lib/grafana]
```

### 4.3 Rate Limiting & Access Control
```python
# src/gmnap/api/rate_limiter.py:
class RateLimiter:
    FREE_TIER = {"requests_per_min": 60, "hashcash_bits": 18}
    PAID_TIER = {"requests_per_min": 10000, "auth_scheme": "Bearer"}
    
    def check_rate_limit(self, client_id: str, tier: str) -> bool:
        # Implementation with Redis backend
        pass
```

## 🔧 Phase 5: Full V7.0 Polish & Compliance
**Priority: MEDIUM** | **Duration: 1 month** | **Effort: 100-150 hours**

### 5.1 Enhanced Authority Sources
```python
# Add missing authority sources:
authority_sources:
  # Tier 1 (genealogy-focused)
  - {service: ORCID_ETD,        daily_quota: 100000}
  - {service: Crossref_Thesis, daily_quota: 100000}
  - {service: Wikidata_P184,    daily_quota: dump}
  - {service: OAI_University,   daily_quota: dump}
  
  # Tier 3 (premium)
  - {service: ProQuest_ETD,     daily_quota: 50000, opt_in: true}
```

### 5.2 Testing Expansion
```python
# Expand test coverage:
testing_suite:
  fixtures: 1500                    # Up from 1000
  lineage_graph_coherence: true     # New test category
  snapshot_rollback: true           # Git revert testing
  cost_guard: true                  # CHF limit enforcement
```

### 5.3 Quality Gates Implementation
```python
# Enhanced quality gates:
quality_gates:
  duplicate_global_id: {quick: 0, full: 0, extreme: 0}
  genealogy_edge_conflict_pct: {quick_max: 2.0, full_max: 1.0, extreme_max: 0.0}
  graph_coherence_score_min: {quick: 0.85, full: 0.92, extreme: 0.97}
  peak_rss_gb_on_2M: 6              # Increased from 2GB
  cost_cap_enforcement: true
```

## 📊 Implementation Verification Matrix

| Component | Implementation | Testing | Documentation | V7 Compliance |
|-----------|---------------|---------|---------------|---------------|
| **31 Regional Processors** | ❌ To Do | ❌ To Do | ❌ To Do | ❌ 0% |
| **Graph Database** | ❌ To Do | ❌ To Do | ❌ To Do | ❌ 0% |
| **LLM Integration** | ❌ To Do | ❌ To Do | ❌ To Do | ❌ 0% |
| **Multi-Service Arch** | ❌ To Do | ❌ To Do | ❌ To Do | ❌ 0% |
| **Enhanced Testing** | ❌ To Do | ❌ To Do | ❌ To Do | ❌ 0% |

**Target State: All checkboxes ✅**

## 🎯 Success Criteria (Definition of Done)

### Phase 1 Complete When:
- [ ] All 43 regional processors implemented and tested
- [ ] All 34 linguistic rules implemented  
- [ ] 100% regional coverage achieved
- [ ] All existing tests pass + new regional tests

### Phase 2 Complete When:
- [ ] Memgraph-CE running in Docker
- [ ] Schema v2.0 migration complete
- [ ] Graph queries functional
- [ ] Genealogy relationships stored and retrievable
- [ ] Betweenness centrality calculated

### Phase 3 Complete When:
- [ ] GPT-4o-mini integration working (with mocks for dev)
- [ ] PDF parsing pipeline functional
- [ ] Cost monitoring with CHF caps
- [ ] ETD extraction validated against schema

### Phase 4 Complete When:
- [ ] Full Docker Compose stack running
- [ ] Prometheus + Grafana monitoring
- [ ] Rate limiting implemented
- [ ] Multi-service communication working

### Phase 5 Complete When:
- [ ] All authority sources integrated
- [ ] 1500 test fixtures passing
- [ ] All quality gates enforced
- [ ] Full v7.0 specification compliance achieved

## 🚀 Next Session Priorities

**Immediate Actions (Phase 1 Start):**
1. Begin with A3 Nordic-Baltic implementation
2. Set up systematic regional processor template
3. Create comprehensive testing framework for regions
4. Establish development workflow for parallel region development

**Reference Documents:**
- `CURRENT_STATE_DEFINITIVE.md` - What we have now
- `NEXT_SESSION_STARTUP_GUIDE.md` - Immediate actions
- `docs/specs v7.0.yaml` - Target specification

---

**This plan provides the complete roadmap to transform GMNAP from a v6 name authority system into the full v7.0 MathLineage Edition academic genealogy platform.**