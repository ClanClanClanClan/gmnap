# GMNAP V7.0 Compliance Implementation Plan
*Date: 2025-08-02*

## 📊 Current Compliance Status

Based on V7.0 spec analysis, GMNAP currently achieves:
- **Security**: 100% ✅
- **Classification**: 100% (for 11/43 regions) ⚠️
- **Performance**: 57 min/1M (target: ≤35 min) ❌
- **V7 Features**: 7/12 (58.3%) ⚠️

## 🎯 V7.0 MathLineage Edition Requirements

### Core Requirements from specs_v7.yaml:

1. **Performance Targets**
   - Quick mode: ≤35 min per 1M entries
   - Full mode: ≤70 min per 1M entries
   - Current: 57 min (1.6x slower than Quick target)

2. **Graph Database (Memgraph)**
   - Academic genealogy relationships
   - Betweenness centrality calculations
   - Cycle detection (<3 generations)
   - Docker deployment required

3. **LLM Integration (GPT-4o-mini)**
   - PDF thesis parsing
   - Extract: title, authors, advisors, degree_date
   - Cost cap: CHF 40/month
   - Max 400 pages per PDF

4. **Regional Coverage**
   - All 43 regions must be implemented
   - Currently: 11/43 (26%)
   - Missing: 32 regions

5. **Quality Gates**
   - Roundtrip script accuracy: ≥97%
   - Graph coherence score: ≥0.85 (quick), ≥0.92 (full)
   - Idempotent diff: 0 bytes
   - Peak RSS: ≤6GB

## 🚀 Implementation Roadmap

### Phase 1: Performance Optimization (2 weeks)
**Goal**: Meet 35 min/1M target

1. **Week 1: Deploy Optimizations**
   - [ ] Fix and deploy `manager_optimized.py`
   - [ ] Implement batch processing (8000 chunk size per spec)
   - [ ] Add multi-process support (4 workers for Quick mode)
   - [ ] Profile and optimize bottlenecks

2. **Week 2: Performance Testing**
   - [ ] Benchmark with 1M synthetic entries
   - [ ] Tune FastText singleton loading
   - [ ] Implement streaming to reduce memory
   - [ ] Achieve ≤35 min target

### Phase 2: Graph Database Integration (4 weeks)
**Goal**: Academic genealogy features

1. **Week 3-4: Memgraph Setup**
   - [ ] Docker Compose configuration
   - [ ] Bolt connector (port 7687)
   - [ ] Data model for mathematicians
   - [ ] Import existing entries

2. **Week 5-6: Genealogy Features**
   - [ ] Advisor-student relationships
   - [ ] Betweenness centrality algorithm
   - [ ] Cycle detection (<3 generations)
   - [ ] GraphConsistency stage implementation

### Phase 3: Regional Coverage (12 weeks)
**Goal**: Implement all 43 regions

Priority order based on mathematician populations:

1. **Weeks 7-9: High Priority (6 regions)**
   - [ ] E4 Korea (Korean v7 converter exists)
   - [ ] A3 Nordic/Baltic 
   - [ ] B3 Greek
   - [ ] C1 Turkish
   - [ ] E2 Traditional Chinese
   - [ ] F1 SSA Francophone

2. **Weeks 10-12: Medium Priority (10 regions)**
   - [ ] A4 Oceania, A5 Caribbean
   - [ ] C5 Maghreb, C6 Hebrew, C7 Armenian
   - [ ] C8 Georgian, C9 Caucasus
   - [ ] D2 Dravidian, D3 Bengali, D4 Urdu

3. **Weeks 13-15: Lower Priority (11 regions)**
   - [ ] D5 Sinhala
   - [ ] E5 Vietnam, E6 Mainland SEA, E7 Maritime SEA
   - [ ] F2 SSA Anglophone, F3 Horn of Africa, F4 Lusophone
   - [ ] H1 Historical, R0 Residual, Z0 Quarantine

4. **Weeks 16-18: Missing E4 Korea Integration**
   - [ ] Complete E4 processor (Korean v7 exists)
   - [ ] Integrate with pipeline
   - [ ] Test 97% round-trip accuracy

### Phase 4: LLM Integration (4 weeks)
**Goal**: PDF thesis parsing

1. **Weeks 19-20: GPT-4o-mini Setup**
   - [ ] OpenAI API integration
   - [ ] Cost tracking (CHF 40/month cap)
   - [ ] JSON schema validation
   - [ ] Rate limiting

2. **Weeks 21-22: PDF Processing**
   - [ ] PDF text extraction
   - [ ] Page limit handling (400 max)
   - [ ] Structured data extraction
   - [ ] Error handling and fallbacks

### Phase 5: Production Deployment (2 weeks)
**Goal**: Docker Compose multi-service

1. **Week 23: Infrastructure**
   - [ ] Docker Compose setup
   - [ ] Services: api, memgraph, duckdb-batch, redis, nginx
   - [ ] Prometheus + Grafana monitoring
   - [ ] Daily backups to ETH Data Archive

2. **Week 24: Testing & Launch**
   - [ ] Full integration testing
   - [ ] Idempotency verification
   - [ ] Quality gate compliance
   - [ ] Documentation update

## 📈 Success Metrics

### Must Meet (for V7 compliance):
- Performance: ≤35 min/1M (Quick mode)
- Regional Coverage: 43/43 (100%)
- Graph Coherence: ≥0.85
- Round-trip Accuracy: ≥97%
- Memory: ≤6GB RSS
- Idempotency: 0 byte diff

### Nice to Have:
- API response: p95 <2s
- Cost: <CHF 120/month
- Uptime: 99.9%

## 💰 Resource Requirements

### Development (one-time):
- Developer time: ~24 weeks
- No infrastructure costs (use local/free tiers)

### Production (monthly):
- Memgraph CE: Free
- OpenAI API: CHF 40
- Infrastructure: CHF 80
- Total: CHF 120/month

## 🏁 Timeline Summary

- **Weeks 1-2**: Performance optimization
- **Weeks 3-6**: Graph database
- **Weeks 7-18**: Regional coverage
- **Weeks 19-22**: LLM integration
- **Weeks 23-24**: Production deployment

**Total Duration**: 6 months
**Effort**: ~960 hours
**Cost**: CHF 120/month operational

## ⚠️ Risks and Mitigations

1. **Performance Target Miss**
   - Risk: Cannot achieve 35 min/1M
   - Mitigation: Implement distributed processing

2. **Regional Complexity**
   - Risk: Some regions harder than expected
   - Mitigation: Start with similar regions, reuse patterns

3. **LLM Costs**
   - Risk: Exceed CHF 40/month
   - Mitigation: Implement strict rate limiting

4. **Graph Database Scale**
   - Risk: Memgraph performance at scale
   - Mitigation: Test with 2M entries early

## 🎯 Next Immediate Actions

1. Fix `manager_optimized.py` import issue
2. Run performance benchmarks
3. Set up Memgraph Docker container
4. Start A3 Nordic/Baltic implementation
5. Create LLM cost tracking system

**Recommendation**: Focus on performance first (Phase 1), as it's blocking production readiness. Regional coverage can be done incrementally after core performance meets targets.