# 🏗️ GMNAP Architecture - Definitive Guide
*Date: 2025-08-01*  
*Status: AUTHORITATIVE ARCHITECTURE DOCUMENTATION*

## 📋 Overview

This document provides the **definitive architectural overview** of GMNAP, covering the current v6 implementation and the complete v7.0 "MathLineage Edition" transformation.

## 🎯 System Architecture Evolution

### Current State: GMNAP v6 (Single-Service)
```
┌─────────────────────────────────────────────────────────────┐
│                    GMNAP v6 Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│ Stage 0: Config        → Load regions, validate licenses   │
│ Stage 1: Ingest        → YAML parsing, Unicode norm       │
│ Stage 2: DetectRegion  → Script analysis, language detect │
│ Stage 3: RegionHooks   → clean→augment→validate→order_key │
│ Stage 4: AuthorityEnrich → Async API fetching            │
│ Stage 5: CollisionAnalytics → DuckDB statistics          │
│ Stage 6: TagShortForms → Populate clustering data        │
│ Stage 7: GlobalValidate → Schema validation, uniqueness  │
│ Stage 8: Write&Diff    → YAML output, HTML diffs         │
│ Stage 9: Report        → Metrics, change logs            │
│ Stage 10: IdempotencyCheck → Deterministic verification  │
└─────────────────────────────────────────────────────────────┘
             │                           │
       ┌─────────────┐            ┌─────────────┐
       │  SQLite/    │            │   Zstd      │
       │  DuckDB     │            │   Cache     │
       │ (Analytics) │            │  (APIs)     │
       └─────────────┘            └─────────────┘
```

### Target State: GMNAP v7.0 MathLineage Edition (Multi-Service)
```
┌─────────────────────────────────────────────────────────────┐
│                  GMNAP v7.0 Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│ Stage 0: Config        → Load specs, DOI credentials       │
│ Stage 1: Ingest        → YAML parsing, Unicode norm       │
│ Stage 1b: LLMExtract_ETD → GPT-4o-mini thesis parsing    │ ← NEW
│ Stage 2: DetectRegion  → Script, ICU, fastText, affil     │
│ Stage 3: RegionHooks   → clean→augment→validate→order_key │
│ Stage 4: AuthorityEnrich → ORCID_ETD, Crossref_Thesis    │
│ Stage 5: CollisionAnalytics → DuckDB; genealogy edges    │
│ Stage 6: GraphConsistency → Betweenness, Bayesian conf   │ ← NEW
│ Stage 7: TagShortForms → Populate ShortFormClusters      │
│ Stage 8: GlobalValidate → JSON-Schema, graph coherence   │
│ Stage 9: Write&Diff    → Deterministic YAML, HTML diff   │
│ Stage 10: Report       → Markdown, draft DOI, archive    │
│ Stage 11: IdempotencyCheck → Full pipeline rerun         │
└─────────────────────────────────────────────────────────────┘
             │              │              │              │
      ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐
      │  DuckDB     │ │  Memgraph   │ │  Redis   │ │ ETH Archive │
      │(Analytics)  │ │(Genealogy)  │ │ (Cache)  │ │(Snapshots)  │
      └─────────────┘ └─────────────┘ └──────────┘ └─────────────┘
             │              │              │              │
      ┌─────────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐
      │   OpenAI    │ │ Prometheus  │ │   ETH    │ │   Nginx     │
      │(LLM ETD)    │ │(Monitoring) │ │DataCite  │ │(Load Bal)   │
      └─────────────┘ └─────────────┘ └──────────┘ └─────────────┘
```

## 🗂️ Directory Structure

### Current Structure (Clean)
```
gmnap/
├── src/gmnap/
│   ├── core/              # ✅ Pipeline engine, GlobalID, config
│   ├── regions/           # ⚠️ 12/43 processors implemented
│   │   ├── a_groups/      # Anglo, Western Europe, etc.
│   │   ├── b_groups/      # Slavic, Central Europe
│   │   ├── c_groups/      # Middle East, Arabic, Persian
│   │   ├── d_groups/      # South Asia
│   │   ├── e_groups/      # East Asia (including Korean)
│   │   ├── f_groups/      # Africa (not implemented)
│   │   ├── g_groups/      # Americas
│   │   └── special/       # Historical, Residual, Quarantine
│   ├── authorities/       # ✅ 5/25 sources implemented
│   ├── linguistic/        # ⚠️ 10/34 rules implemented
│   ├── utils/            # ✅ Database, caching utilities
│   ├── validation/       # ✅ Schema validation
│   └── v7_compat.py      # ✅ V7 wrapper layer
├── tests/                # ✅ Comprehensive test suite
├── docs/                 # 🧹 CLEANED (obsolete archived)
├── cache/                # ✅ Working cache system
└── data/                 # ✅ Database files
```

### Target V7.0 Structure (Extended)
```
gmnap/
├── src/gmnap/
│   ├── core/              # Enhanced pipeline with 12 stages
│   ├── regions/           # All 43 processors implemented
│   ├── authorities/       # All 15 sources across 4 tiers
│   ├── linguistic/        # All 34 rules implemented
│   ├── graph/             # ← NEW: Memgraph integration
│   │   ├── memgraph_client.py
│   │   ├── genealogy_queries.py
│   │   ├── relationship_manager.py
│   │   └── centrality_calculator.py
│   ├── llm/               # ← NEW: LLM integration
│   │   ├── openai_client.py
│   │   ├── etd_extractor.py
│   │   ├── cost_monitor.py
│   │   └── mock_responses.py
│   ├── api/               # ← NEW: REST API + rate limiting
│   ├── monitoring/        # ← NEW: Prometheus metrics
│   └── utils/
├── docker/                # ← NEW: Multi-service deployment
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── monitoring/
└── tests/                 # Expanded to 1500 fixtures
```

## 🔧 Core Components Deep Dive

### 1. Pipeline Engine (`src/gmnap/core/`)

#### Current Implementation (v6)
```python
class PipelineV6:
    def __init__(self):
        self.stages = [
            ConfigStage(),
            IngestStage(),
            DetectRegionStage(),
            RegionHooksStage(),
            AuthorityEnrichStage(),
            CollisionAnalyticsStage(),
            TagShortFormsStage(),
            GlobalValidateStage(),
            WriteDiffStage(),
            ReportStage(),
            IdempotencyCheckStage()
        ]
    
    def run(self, entries: List[dict]) -> PipelineResult:
        for stage in self.stages:
            entries = stage.process(entries)
        return PipelineResult(entries)
```

#### Target V7.0 Implementation
```python
class PipelineV7:
    def __init__(self):
        self.stages = [
            ConfigStage(),
            IngestStage(),
            LLMExtractETDStage(),        # ← NEW
            DetectRegionStage(),
            RegionHooksStage(),
            AuthorityEnrichStage(),
            CollisionAnalyticsStage(),
            GraphConsistencyStage(),     # ← NEW
            TagShortFormsStage(),
            GlobalValidateStage(),
            WriteDiffStage(),
            ReportStage(),
            IdempotencyCheckStage()
        ]
    
    async def run(self, entries: List[dict]) -> PipelineResult:
        # Enhanced async processing with graph operations
        for stage in self.stages:
            entries = await stage.process(entries)
        return PipelineResult(entries)
```

### 2. Regional Processors (`src/gmnap/regions/`)

#### Processor Interface (Current & Target)
```python
class RegionSpec:
    """Standardized interface for all regional processors"""
    code: str                          # A1, B2, E4, etc.
    yaml_files: list[str]             # Region-specific YAML files
    scripts: list[str]                # Primary scripts handled
    mixed_scripts: bool = False       # Multi-script regions
    canonical_order: Literal[
        "Family, Given", "Given Family",
        "Patronymic", "Mononym"
    ]
    romanisation_standards: list[str]  # ISO standards used
    
    # Mandatory hooks (all processors must implement)
    def clean(self, entry: dict) -> None: ...
    def augment(self, entry: dict) -> None: ...
    def validate(self, entry: dict) -> None: ...
    def order_key(self, entry: dict) -> str: ...
    
    # Optional bulk operations
    def batch_enrich(self, entries: list[dict]) -> None: ...
    
    # Optional file-level hooks
    def on_file_load(self, data: dict) -> None: ...
    def before_write(self, data: dict) -> None: ...
    def after_write(self, data: dict) -> None: ...
```

#### Implementation Status Matrix
```python
# Current: 12/43 implemented
IMPLEMENTED_REGIONS = {
    "A1": "✅ Core Anglo-Sphere (100%)",
    "A2": "✅ Western Europe (100%)", 
    "B1": "✅ East-Slavic (100%)",
    "B2": "✅ South-Slavic & Central Europe (100%)",
    "C2": "✅ Persian-Tajik (100%)",
    "C3": "✅ Arabic Levant-Nile (100%)",
    "C4": "✅ Arabic Gulf (100%)",
    "D1": "✅ South Asia Hindi Belt (100%)",
    "E1": "✅ Sinophone Mainland (100%)",
    "E3": "⚠️ Japan (80% - needs completion)",
    "E4": "✅ Korea (97.42% accuracy)",
    "G1": "⚠️ Latin America (40% skeleton)"
}

# Target: 43/43 implemented
MISSING_REGIONS = [
    "A3", "A4", "A5",        # Nordic, Oceania, Caribbean
    "B3",                     # Greek World
    "C1", "C5", "C6", "C7", "C8", "C9",  # Turkic, Maghreb, Hebrew, etc.
    "D2", "D3", "D4", "D5",   # Dravidian, Bengali, Pakistani, Sinhala  
    "E2", "E5", "E6", "E7",   # Traditional Chinese, Vietnam, SEA
    "F1", "F2", "F3", "F4",   # All of Africa
    "H1", "R0", "Z0"          # Historical, Residual, Quarantine
]
```

### 3. Authority Sources (`src/gmnap/authorities/`)

#### Current Implementation (5 sources)
```python
CURRENT_SOURCES = {
    # Tier 0 (Free)
    "OpenAlex": {"quota": 864000, "licence": "CC0"},
    "Crossref": {"quota": 4300000, "licence": "CC0"}, 
    "ORCID": {"quota": 500, "licence": "CC0"},
    "zbMATH": {"quota": 200, "licence": "CC-BY"},
    "DBLP": {"quota": "local", "licence": "CC-BY"}
}
```

#### Target V7.0 Implementation (15 sources)
```python
V7_SOURCES = {
    # Tier 0 (Free)
    "OpenAlex": {"quota": 864000, "licence": "CC0"}, 
    "Crossref": {"quota": 4300000, "licence": "CC0"},
    "ORCID_ETD": {"quota": 100000, "licence": "CC0"},      # ← NEW
    "Crossref_Thesis": {"quota": 100000, "licence": "CC0"}, # ← NEW
    
    # Tier 1 (Subscription/Free Academic)
    "Wikidata_P184": {"quota": "dump", "licence": "CC0"},    # ← NEW
    "OAI_University": {"quota": "dump", "licence": "Mixed"}, # ← NEW
    "HAL": {"quota": 86400, "licence": "CC-BY"},
    "GND": {"quota": "unlimited", "licence": "CC-BY"},
    "zbMATH": {"quota": 200, "licence": "CC-BY"},
    
    # Tier 2 (Commercial)
    "MathSciNet_HTML": {"quota": 20000, "licence": "Subscription"},
    "Scopus": {"quota": 20000, "licence": "Elsevier"},
    "Dimensions": {"quota": 10000, "licence": "DigitalScience"},
    
    # Tier 3 (Premium/Opt-in)
    "ProQuest_ETD": {"quota": 50000, "licence": "Commercial", "opt_in": True},
    "Google Scholar": {"quota": "undefined", "licence": "Scraping", "opt_in": True}
}
```

### 4. Graph Database Layer (`src/gmnap/graph/`) - NEW in v7.0

#### Core Architecture
```python
class MemgraphClient:
    """Bolt protocol client for Memgraph-CE"""
    def __init__(self, uri="bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(uri)
    
    def execute_query(self, cypher: str, params: dict) -> Result:
        with self.driver.session() as session:
            return session.run(cypher, params)

class GenealogyManager:
    """High-level genealogy relationship management"""
    def add_advisor_relationship(self, student_id: str, advisor_id: str, 
                               relation_type: str, confidence: float) -> None:
        cypher = """
        MERGE (s:Person {global_id: $student_id})
        MERGE (a:Person {global_id: $advisor_id})
        MERGE (s)-[r:ADVISED_BY {
            type: $relation_type,
            confidence: $confidence,
            created: datetime()
        }]->(a)
        """
        self.client.execute_query(cypher, {
            "student_id": student_id,
            "advisor_id": advisor_id, 
            "relation_type": relation_type,
            "confidence": confidence
        })
    
    def calculate_betweenness_centrality(self) -> Dict[str, float]:
        cypher = """
        CALL gds.betweenness.stream({
            nodeProjection: 'Person',
            relationshipProjection: 'ADVISED_BY'
        })
        YIELD nodeId, score
        MATCH (p:Person) WHERE id(p) = nodeId
        RETURN p.global_id AS person_id, score
        """
        result = self.client.execute_query(cypher)
        return {record["person_id"]: record["score"] for record in result}
```

### 5. LLM Integration (`src/gmnap/llm/`) - NEW in v7.0

#### ETD Extraction Pipeline
```python
class ETDExtractor:
    """GPT-4o-mini powered thesis metadata extraction"""
    
    def __init__(self):
        self.client = OpenAI()
        self.cost_monitor = CostMonitor(monthly_cap_chf=40)
        self.schema_validator = JSONSchemaValidator()
    
    async def extract_metadata(self, pdf_path: str) -> dict:
        """Extract thesis metadata with cost monitoring"""
        
        if not self.cost_monitor.can_make_request():
            raise CostCapExceededError("Monthly CHF 40 limit reached")
        
        # Extract text from PDF (max 400 pages)
        text = self.extract_pdf_text(pdf_path, max_pages=400)
        
        # Generate structured extraction prompt
        prompt = self.build_extraction_prompt(text)
        
        # Call GPT-4o-mini
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        # Track costs
        self.cost_monitor.record_usage(response.usage)
        
        # Validate against schema
        extracted = json.loads(response.choices[0].message.content)
        self.schema_validator.validate(extracted)
        
        return extracted
    
    def build_extraction_prompt(self, text: str) -> str:
        return f"""
        Extract the following information from this thesis document:
        
        Required fields:
        - title: Full thesis title
        - authors: List of author names
        - advisors: List of advisor/supervisor names  
        - degree_date: Date degree was conferred (YYYY-MM-DD format)
        - institution: Institution where degree was earned
        
        Optional fields:
        - degree: Type of degree (PhD, Masters, etc.)
        - language: Primary language of thesis
        
        Return as valid JSON matching this schema: {self.get_json_schema()}
        
        Thesis text:
        {text[:10000]}...  # Truncate for context limits
        """
```

### 6. Schema Evolution (v1.5 → v2.0)

#### Current Schema v1.5 (YAML)
```yaml
"<CanonicalLatin>":
  GlobalID: "<sha256-128bit>"
  UpdatedAt: "<ISO-8601 UTC>"
  CanonicalLatin: "<Family, Given>"
  CanonicalNative: "<native script>"
  # ... existing fields
```

#### Target Schema v2.0 (YAML + Graph)
```yaml
"<CanonicalLatin>":
  GlobalID: "<sha256-128bit>"
  UpdatedAt: "<ISO-8601 UTC>"
  
  # Traditional fields (unchanged)
  CanonicalLatin: "<Family, Given>"
  CanonicalNative: "<native script>"
  
  # NEW: Genealogy relations
  GenealogyRelations:
    - source_id: "<GlobalID>"
      target_id: "<GlobalID>"
      relation_type: "doctoralAdvisor"
      qualifier: "co-advisor"
      confidence: 0.95
  
  # NEW: Enhanced degree information
  DegreeDate:
    date: "1985-06-15"
    precision: "day"
  
  # NEW: Graph analytics
  BetweennessScore: 0.23
  GraphUpdated: "2025-08-01T10:30:00Z"
  
  # NEW: GDPR compliance
  GDPR_DATA: false
  ShadowNode: null  # or ShadowNode details if erased
```

## 🔄 Data Flow Architecture

### V6 Data Flow (Current)
```
[YAML Input] → [Unicode Norm] → [Region Detection] → [Region Processing]
      ↓              ↓               ↓                    ↓
[Authority APIs] → [DuckDB Analytics] → [Validation] → [YAML Output]
```

### V7.0 Data Flow (Target) 
```
[YAML Input] → [Unicode Norm] → [LLM ETD Extract] → [Region Detection]
      ↓              ↓               ↓                    ↓
[Region Processing] → [Authority APIs] → [DuckDB Analytics] → [Graph DB]
      ↓                    ↓                ↓                   ↓
[Genealogy Relations] → [Betweenness Calc] → [Validation] → [Multi Output]
      ↓                    ↓                   ↓               ↓
[Cost Monitoring] → [Quality Gates] → [DOI Minting] → [ETH Archive]
```

## 🎯 Quality Gates & Monitoring

### Current Quality Gates (v6)
```python
QUALITY_GATES_V6 = {
    "duplicate_global_id": 0,
    "duplicate_external_id_pct": 0.10,
    "roundtrip_script_rate_min": 0.97,
    "peak_rss_gb_on_2M": 2,
    "idempotent_diff_bytes": 0
}
```

### Enhanced Quality Gates (v7.0)
```python
QUALITY_GATES_V7 = {
    # Traditional gates (enhanced)
    "duplicate_global_id": 0,
    "duplicate_external_id_pct": {"quick": 0.10, "full": 0.05, "extreme": 0},
    "roundtrip_script_rate_min": 0.97,
    "peak_rss_gb_on_2M": 6,  # Increased for graph processing
    "idempotent_diff_bytes_max": 0,
    
    # NEW: Genealogy gates
    "genealogy_edge_conflict_pct": {"quick": 2.0, "full": 1.0, "extreme": 0.0},
    "graph_coherence_score_min": {"quick": 0.85, "full": 0.92, "extreme": 0.97},
    
    # NEW: Cost gates  
    "llm_cost_cap_chf_monthly": 40,
    "total_cost_cap_chf_monthly": 120,
    
    # NEW: Performance gates
    "warm_cache_runtime_per_1M_min": {"quick": 35, "full": 70}
}
```

## 🐳 Deployment Architecture

### Current Deployment (Single Service)
```bash
# Simple single-process deployment
python -m src.core.pipeline_v6 --mode=full input.yaml
```

### Target V7.0 Deployment (Multi-Service)
```yaml
# docker-compose.yml
version: '3.8'
services:
  gmnap-api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      - MEMGRAPH_URL=bolt://memgraph:7687
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on: [memgraph, redis, duckdb-batch]
    
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
    
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes: [./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml]
    
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes: [grafana-data:/var/lib/grafana]
    
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes: [./nginx.conf:/etc/nginx/nginx.conf]
    depends_on: [gmnap-api]

volumes:
  memgraph-data:
  grafana-data:
```

## 🔧 Integration Points

### External Services Integration
```python
class ExternalIntegrations:
    """All external service integrations"""
    
    # ETH-Bibliothek Services
    datacite_client: DataCiteClient       # DOI minting
    eth_archive_client: ETHArchiveClient  # Snapshot storage
    
    # Commercial APIs
    openai_client: OpenAIClient           # LLM processing
    mathscinet_client: MathSciNetClient   # Premium math database
    scopus_client: ScopusClient           # Elsevier database
    
    # Monitoring & Ops
    prometheus_client: PrometheusClient   # Metrics collection
    grafana_client: GrafanaClient         # Dashboard management
```

## 📊 Performance Characteristics

### Current Performance (v6)
- **Processing Speed**: >555 entries/sec ✅
- **Memory Usage**: <2GB RSS ✅  
- **Single-threaded**: Pipeline execution
- **Database**: SQLite/DuckDB (embedded)

### Target Performance (v7.0)
- **Processing Speed**: >555 entries/sec (maintained)
- **Memory Usage**: <6GB RSS (increased for graph processing)
- **Multi-threaded**: Async pipeline + graph operations
- **Databases**: DuckDB + Memgraph + Redis (multi-database)
- **Horizontal Scale**: Docker Compose services

## 🎯 Migration Strategy

### Phase 1: Foundation (Current → Enhanced v6)
- Complete 31 missing regional processors
- Maintain existing architecture
- No breaking changes

### Phase 2: Graph Integration (v6 → v7 Core)
- Add Memgraph-CE service
- Implement genealogy data models
- Add graph-aware pipeline stages

### Phase 3: LLM Integration (v7 Core → v7 Full)
- Add OpenAI integration
- Implement ETD extraction pipeline  
- Add cost monitoring

### Phase 4: Production Ready (v7 Full → v7 Deployed)
- Multi-service Docker deployment
- Monitoring and alerting
- Rate limiting and access control

---

**This architecture provides the complete technical foundation for GMNAP's evolution from a single-service name authority system to a comprehensive multi-service academic genealogy platform.**