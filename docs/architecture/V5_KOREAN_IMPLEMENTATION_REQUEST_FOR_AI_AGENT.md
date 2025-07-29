# V5 Korean Implementation - Complete Requirements Document for AI Agent

## 🎯 PROJECT CONTEXT & CRITICAL UNDERSTANDING

**ESSENTIAL CONTEXT**: This is NOT a standalone Korean converter project. V5 Korean processing is THE solution for achieving GMNAP v6.1's mandatory 97% round-trip script accuracy requirement for Korean mathematicians (specs line 341: roundtrip_script_rate threshold 0.97).

**INTEGRATION TARGET**: Must integrate seamlessly into GMNAP's E4 Korea region handler (docs/specs v6.1.yaml lines 187-191) as part of the existing pipeline architecture.

**SUCCESS CRITERIA**: 
- Achieve ≥97% round-trip accuracy on 751 Korean mathematician entries in `/korean.yaml`
- Pass GMNAP quality gates (line 341)
- Maintain deterministic processing within existing pipeline
- Handle Korean Hyphen/Space variants (linguistic rule #13, line 288)

## 🔧 TECHNICAL ARCHITECTURE REQUIREMENTS

### 1. WFST (Weighted Finite State Transducer) Implementation

**CRITICAL REQUEST**: Provide complete, working WFST architecture using PyNini for:

#### A. Phonotactic Segmentation FST
```python
# NEED COMPLETE IMPLEMENTATION - Current version has only placeholders
# Required: Actual syllable boundary detection for compound names like "Songkangho" → "Song kang ho"
# Must handle: Korean phonotactic rules, consonant cluster analysis, probabilistic scoring
```

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. What are the exact Korean phonotactic rules for syllable boundary detection?
2. How should consonant clusters be scored probabilistically for segmentation?
3. What beam search implementation works best with Korean syllable patterns?
4. How to handle edge cases like single-syllable surnames vs. compound segmentation?

#### B. Romanization Normalization FST
```python
# NEED COMPLETE ROMANIZATION TABLES - Current has only 8 basic mappings
# Required: Comprehensive Korean → Latin mappings for all romanization systems
```

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. Complete romanization tables for:
   - Revised Romanization (RR) - official Korean standard
   - McCune-Reischauer system 
   - Yale romanization system
   - MLTR (Ministry of Land, Transport and Maritime Affairs)
2. How to handle romanization ambiguities (e.g., ㅓ vs ㅗ in certain contexts)?
3. Systematic vowel disambiguation rules for compound names?
4. Edge case handling for foreign-origin Korean names?

#### C. Hangul Generation FST
```python
# NEED COMPLETE JAMO COMPOSITION LOGIC
# Required: Roman syllables → Korean Hangul with proper Unicode composition
```

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. Complete jamo (초성/중성/종성) composition tables?
2. Unicode normalization strategy for Hangul composition?
3. How to handle irregular romanizations that don't map cleanly to standard jamo?
4. Syllable validation logic to prevent invalid Hangul generation?

### 2. PyNini API Corrections

**CRITICAL ISSUE**: Current documentation uses incorrect PyNini API calls that will fail immediately.

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. What is the correct PyNini 2.1.6.post1 API for creating acceptors? (Current uses non-existent `pynini.acceptor()`)
2. Proper syntax for `num_arcs()` method calls? (Current fails with argument errors)
3. Working examples of FST composition and optimization in PyNini 2.1.6.post1?
4. Beam search implementation patterns that work with current PyNini version?

### 3. Training Data & Frequency Weights

**CRITICAL BLOCKER**: OSCAR-23.01 Korean corpus access is blocked ("Dataset scripts are no longer supported").

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **ALTERNATIVE DATA SOURCES**: What large Korean text corpora are currently accessible for frequency weight extraction?
2. **FREQUENCY EXTRACTION**: Exact methodology for extracting Korean syllable/morpheme frequencies from text?
3. **OSCAR WORKAROUND**: Are there alternative ways to access OSCAR Korean data, or equivalent datasets?
4. **WEIGHT INTEGRATION**: How to incorporate frequency weights into PyNini FST arcs effectively?

### 4. V4 Back-off Lexicon Integration

**CURRENT STATUS**: Multiple existing Korean modules found but integration strategy unclear.

**EXISTING MODULES DISCOVERED**:
- `korean_back_converter_v4.cpython-312.pyc`
- `korean_enhanced_syllable_segmenter.cpython-312.pyc` 
- `korean_surname_database_comprehensive.cpython-312.pyc`
- Multiple other Korean processing components

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **INTEGRATION STRATEGY**: How to properly integrate existing V4 components with new V5 WFST system?
2. **LEXICON STRUCTURE**: What should the V4 back-off lexicon format look like?
3. **PENALTY WEIGHTING**: Implementation of λ=3.0 penalty weighting for back-off transitions?
4. **FALLBACK LOGIC**: When should system fall back from WFST to V4 lexicon lookup?

## 📊 VALIDATION & TESTING REQUIREMENTS

### 1. Korean Mathematician Dataset

**VALIDATION DATA**: `/korean.yaml` contains 751 entries with structure:
```yaml
Ahn_DaeHoon:
  CanonicalLatin: "Ahn, Dae-Hoon"
  CanonicalWestern: "Dae-Hoon Ahn"
  AllCommonVariants: [...]
  CJK: "安大勲"
  MathSciNet: "Ahn, Dae-Hoon"
  zbMATH: "Ahn, Dae-Hoon"
```

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **TESTING METHODOLOGY**: How to systematically test all 751 entries for 97% accuracy?
2. **DICE COEFFICIENT**: Exact implementation of Dice coefficient calculation for round-trip accuracy?
3. **VARIANT HANDLING**: How should the system handle multiple romanization variants per mathematician?
4. **EDGE CASE VALIDATION**: Specific test cases for compound names, hyphenated names, stage names?

### 2. Round-trip Accuracy Measurement

**REQUIREMENT**: Round-trip conversion (Roman → Hangul → Roman) must achieve ≥97% accuracy using Dice coefficient after NFC casefold.

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **EXACT ALGORITHM**: Step-by-step Dice coefficient calculation with NFC casefold normalization?
2. **ACCURACY REPORTING**: How to generate detailed accuracy reports for validation?
3. **FAILURE ANALYSIS**: Systematic approach to analyze and fix <97% cases?
4. **REGRESSION TESTING**: How to ensure improvements don't break existing working cases?

## 🔌 GMNAP INTEGRATION REQUIREMENTS

### 1. E4 Region Handler Integration

**TARGET FILE**: `src/regions/e_groups/e4_korea.py` (needs creation)

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **CLASS STRUCTURE**: Complete E4_Korea class implementation following GMNAP region handler patterns?
2. **PIPELINE INTEGRATION**: How to integrate V5 processing into existing GMNAP pipeline stages?
3. **ERROR HANDLING**: Proper exception handling and fallback strategies?
4. **PERFORMANCE**: Optimization strategies for processing large batches of Korean names?

### 2. Configuration Integration

**REQUIREMENTS**: 
- Integration with GMNAP's config system
- Proper logging and monitoring
- Quality gate compliance

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **CONFIG STRUCTURE**: How to structure V5-specific configuration within GMNAP's config system?
2. **LOGGING INTEGRATION**: Proper logging patterns for Korean processing steps?
3. **MONITORING**: What metrics should be tracked for Korean processing performance?
4. **QUALITY GATES**: How to implement quality gate checks specific to Korean processing?

## 🛠️ DEVELOPMENT & IMPLEMENTATION QUESTIONS

### 1. Development Environment

**CURRENT STATUS**: 
- PyNini 2.1.6.post1 available (not 2.1.5 as originally specified)
- 277GB disk space available
- Python 3.12 environment
- All GMNAP dependencies installed per requirements.txt

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **DEVELOPMENT SETUP**: Step-by-step development environment setup for V5 Korean processing?
2. **TESTING FRAMEWORK**: How to set up comprehensive testing for Korean processing?
3. **DEBUGGING TOOLS**: Recommended tools for debugging WFST processing and Korean conversion?
4. **PERFORMANCE PROFILING**: How to profile and optimize Korean processing performance?

### 2. Implementation Strategy

**APPROACH NEEDED**: Systematic implementation plan that avoids previous failures.

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **IMPLEMENTATION ORDER**: What order should components be implemented in (FSTs, integration, testing)?
2. **INCREMENTAL VALIDATION**: How to validate each component before moving to the next?
3. **RISK MITIGATION**: How to avoid overfitting to test data while achieving 97% accuracy?
4. **FALLBACK STRATEGIES**: What should happen when V5 processing fails for specific names?

## 🎯 CRITICAL SUCCESS FACTORS

### 1. Avoid Previous Failures

**LESSONS LEARNED FROM CONVERSATION**:
- No 100% accuracy claims on small test sets
- No exact mappings for specific failing cases (overfitting)
- No shortcuts or simple RegionSpec approaches
- Must test continuously on unseen data

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **OVERFITTING PREVENTION**: How to build general solutions without overfitting to specific test cases?
2. **ROBUST TESTING**: How to ensure testing on truly diverse, unseen Korean names?
3. **LINGUISTIC CORRECTNESS**: How to prioritize linguistic accuracy over test optimization?
4. **GENERALIZATION**: How to build solutions that work on new Korean names not in training data?

### 2. Production Readiness

**REQUIREMENTS**: System must be production-ready for GMNAP v6.1 integration.

**SPECIFIC QUESTIONS FOR AI AGENT**:
1. **PRODUCTION DEPLOYMENT**: How to deploy V5 Korean processing in production GMNAP environment?
2. **MONITORING & ALERTING**: What production monitoring should be implemented?
3. **ERROR RECOVERY**: How should the system handle and recover from processing errors?
4. **SCALABILITY**: How to ensure Korean processing scales with large mathematician datasets?

## 📋 DELIVERABLES REQUESTED

Please provide complete, working implementations for:

1. **COMPLETE WFST ARCHITECTURE** - No placeholders, fully functional PyNini implementation
2. **COMPREHENSIVE ROMANIZATION TABLES** - All Korean romanization systems with edge cases
3. **INTEGRATION CODE** - Complete E4_Korea region handler with GMNAP integration
4. **TESTING FRAMEWORK** - Systematic testing for 751 mathematician entries
5. **VALIDATION TOOLS** - Dice coefficient calculation and accuracy reporting
6. **PRODUCTION CONFIGURATION** - All necessary config files and deployment scripts
7. **DOCUMENTATION** - Complete technical documentation for maintenance

## ⚠️ CRITICAL CONSTRAINTS

1. **NO OVERFITTING**: Solutions must work on unseen Korean names, not just test data
2. **NO SHORTCUTS**: Must implement proper WFST architecture, not simple lookup tables
3. **LINGUISTIC ACCURACY**: Must prioritize Korean linguistics correctness over test optimization
4. **GMNAP COMPLIANCE**: Must integrate seamlessly with existing GMNAP architecture
5. **PERFORMANCE**: Must meet GMNAP's processing speed requirements
6. **ACCURACY**: Must achieve ≥97% round-trip accuracy on mathematician validation dataset

---

**FINAL REQUEST**: Please provide complete, working implementations for ALL components listed above, with detailed explanations, working code examples, and comprehensive testing strategies. This is critical for GMNAP v6.1 compliance and cannot have any placeholders or incomplete implementations.