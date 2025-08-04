# 🚨 CRITICAL HANDOFF: Korean v6 to v7 Integration Gap Analysis

## Executive Summary
**CRITICAL DISCREPANCY**: Implementation bundle promised 97.8% (717/733) but achieved only 92.77% (680/733)
- **Gap**: 37 missing passes (5.03% shortfall)
- **Regression**: Actually LOST 3 passes from baseline (683→680)

## 🔍 Ultra-Detailed Implementation Audit

### Starting Point
- **Baseline**: 93.18% (683/733) - n-best lattice + dice scoring
- **Method**: 10-best paths with dice coefficient matching to original romanization
- **Code State**: Simple, working converter.py with lattice construction

### What Was Implemented (Verbatim from Bundle)

#### 1. CSV Schema Extension ✅
```csv
# ⇥ New columns ⇥
# context := {SN,GN,Both, …}   (unchanged)
# pos     := [S]urname‑only | [G]iven‑name‑only | (blank) Either
```
**Status**: Applied exactly. All rows now have 5 columns.

#### 2. 92 Positional Rows ✅
Added exactly as specified:
- 정,jung,0.000,SN,S
- 정,jeong,-1.500,SN,S
- ... (all 92 rows appended)

#### 3. Converter.py Patch ❌ CRITICAL ISSUE
The bundle specified:
```python
@@
-    for token_type, token in zip(types, tokens):
-        # rows = (roman, hangul, weight, context)
-        table = SURNAME_ROWS if token_type == "surname" else GIVEN_ROWS
-        lattice |= pynini.string_map([(r, h, float(w)) for r, h, w, ctx in table])
+    for token_type, token in zip(types, tokens):
+        table = SURNAME_ROWS if token_type == "surname" else GIVEN_ROWS
+        rows   = []
+        for r, h, w, ctx, *rest in table:             # rest[0] may be pos
+            pos = rest[0] if rest else ""
+            if   token_type == "surname" and pos not in ("", "S"):  # reject G‑only
+                continue
+            elif token_type == "given"   and pos not in ("", "G"):
+                continue
+            rows.append((r, h, float(w)))
+        lattice |= pynini.string_map(rows)
```

**PROBLEM**: Our converter.py doesn't have:
- `SURNAME_ROWS` or `GIVEN_ROWS` variables
- `pynini.string_map()` construction
- `token_type` classification system

**What We Have Instead**:
```python
def eng2kor(name:str):
    out=[]
    for tok in tokenise(name):
        for syl in segment(tok):
            h=_rr2han(syl)
            if h is None: return None
            out.append(h)
    return "".join(out)
```

#### 4. build_fsts_multi.py Parser ✅
Updated to handle 5-column CSV format correctly.

#### 5. Fine-grain Weight Tweaks ⚠️
Applied but couldn't verify if rows existed:
- ㅣ,i,-1.0,GN, → ㅣ,i,-2.0,GN,
- ㅣ,ee,0.2,GN, → ㅣ,ee,0.8,GN,
- 연,yeon,-1.0,GN, → 연,yeon,-1.5,GN,

#### 6. File Permissions ✅
- Created .gitattributes
- Created pre-receive hook
- Set CSV to read-only (444)

## 🔬 Diagnostic Analysis

### Performance Comparison
| Metric | Expected | Actual | Delta |
|--------|----------|---------|--------|
| Math | 717/733 (97.8%) | 680/733 (92.77%) | -37 (-5.03%) |
| Diverse | 194/200 (97.0%) | 195/200 (97.50%) | +1 (+0.50%) |
| Independent | 153/165 (92.7%) | 153/165 (92.73%) | 0 (0.00%) |

### Failure Pattern Analysis
Top 5 failures show mixed patterns:
1. 'Chun_Youngsup' → eng→kor failure
2. 'Kim_RareInitialsBlock' → eng→kor failure  
3. 'Baik_Junghyun' → roundtrip (baek vs baik)
4. 'Chun_MiYoung' → eng→kor failure
5. 'Huh_June' → roundtrip anomaly

### Critical Observations

1. **Converter Architecture Mismatch**
   - Bundle assumes table-driven token classification
   - Our code uses FST-based syllable conversion
   - No position awareness in eng2kor direction

2. **Weight Application Issues**
   - Positional weights in CSV but not utilized in eng2kor
   - FSTs built but no position-specific selection logic
   - n-best working in kor2eng but not eng2kor

3. **Missing Components**
   - No `eng2kor_nbest()` function as referenced in bundle
   - No position-aware lattice construction in eng2kor
   - No token type classification system

## 🎯 Specific Questions for Guidance

### 1. Converter.py Architecture
**Q**: The patch references a completely different architecture with SURNAME_ROWS tables and pynini.string_map. Should we:
- a) Implement the missing table-driven architecture?
- b) Adapt the position logic to our FST-based approach?
- c) Is there a different converter.py version we should be using?

### 2. Position-Aware eng2kor
**Q**: Our eng2kor doesn't use positional FSTs. Should we:
```python
# Current:
h = _rr2han(syl)  # No position awareness

# Needed?:
position = "surname" if token_idx == 0 else "given"
h = _rr2han_pos(syl, position)  # Use position-specific FST
```

### 3. Weight Effectiveness
**Q**: The positional weights seem to be fighting each other:
- 정,jung,0.000,SN,S (surname preference)
- 정,jeong,-1.500,SN,S (strong surname)
- 정,jeong,0.800,GN,G (given name)

Are these weights calibrated for our FST approach or the table approach?

### 4. Missing 37 Passes
**Q**: We need to gain exactly 37 more passes. The bundle mentions:
- "Peak RSS unchanged (670 MB on 2 M names)"
- "Math corpus accuracy ↑ 11.3 pp"

But we only gained -0.41pp (actually lost). What's the missing component?

### 5. Validation Methodology
**Q**: The bundle mentions "n-best tolerance for YAML accepted:" but our validate.py doesn't implement this. Is this critical for achieving 97.8%?

## 🔧 Hypotheses for the Gap

### Hypothesis 1: Wrong Converter Base
The patch assumes a table-driven converter but we have an FST-driven one. The position logic might need complete reimplementation.

### Hypothesis 2: eng2kor Position Blindness
Our eng2kor completely ignores the positional data. Adding position-aware FST selection might unlock the missing accuracy.

### Hypothesis 3: Weight Calibration
The weights might be calibrated for a different algorithm. Our FST uses -log probabilities; the bundle might assume different scoring.

### Hypothesis 4: Missing N-best in eng2kor
The bundle references `eng2kor_nbest()` but we only have single-path eng2kor. Multi-path might be essential.

## 🚀 Recommended Next Steps

1. **Clarify Architecture**: Is the table-driven converter.py the correct base?
2. **Implement Position-Aware eng2kor**: Add FST selection based on token position
3. **Add eng2kor_nbest**: Implement multi-path for eng→kor direction
4. **Debug Specific Failures**: Why did we lose Baik_Junghyun and others?
5. **Verify Weight Application**: Ensure the fine-grain tweaks actually applied

## 📊 Technical Deep Dive

### Current FST Loading
```python
ROM2 = pn.Fst.read("models/rom2han_multi.fst")  # General
HAN2 = pn.Fst.read("models/han2rom_multi.fst")  # General
# Position-specific FSTs exist but unused in eng2kor
```

### Missing Position Logic in eng2kor
```python
def eng2kor(name:str):
    out=[]
    for tok in tokenise(name):  # No position tracking
        for syl in segment(tok):
            h=_rr2han(syl)  # No position parameter
            if h is None: return None
            out.append(h)
    return "".join(out)
```

### Working kor2eng (n-best + dice)
```python
def kor2eng(h:str, original_rr:str|None=None)->str|None:
    # Builds lattice with n-best paths
    # Uses dice scoring when original_rr provided
    # This part works! (achieves baseline)
```

## 🆘 Critical Questions Summary

1. **Architecture**: Table-driven vs FST-driven converter?
2. **Position Logic**: How to integrate position awareness into eng2kor?
3. **Weights**: Are these calibrated for our approach?
4. **N-best**: Is eng2kor_nbest essential for 97.8%?
5. **Missing Component**: What explains the 37-pass gap?

## 📈 Path to 97.8%

To achieve 717/733, we need to:
- Fix 37 current failures
- Not break any current successes
- Identify the architectural mismatch
- Implement the missing position logic correctly

**The bundle achieved 97.8% somewhere - we need to understand where and how.**

---
*Prepared with ultra-analysis for ultra-guidance on achieving the promised 97.8% accuracy.*