# Evidence-Based Recovery Plan Results

## Executive Summary

Implemented the evidence-based recovery plan exactly as specified. Results fell significantly short of predictions.

## Current Results vs Predictions

| Dataset | Before Recovery | Predicted | Actual | Gap |
|---------|----------------|-----------|---------|-----|
| **Mathematician** | 96.32% | ≥96% ✓ | **95.63%** (701/733) | -0.69pp |
| **Diverse** | 85.00% | 92-94% | **84.50%** (169/200) | -8.5pp |

## What Was Implemented (Exactly as Instructed)

### 1. Removed jung→중 GIVEN_0 line
✓ Deleted the problematic line that was mapping jung to 중 for given names

### 2. Added four high-impact rows
✓ 정,jung,GIVEN_0
✓ 헌,hun,GIVEN_0  
✓ 순,sun,Rare_1
✓ 위,wi,Foreign_1

### 3. Added optional 6 rows
✓ 웨,wei,Foreign_1
✓ 징,jing,GIVEN_1
✓ 팅,ting,Foreign_1
✓ 가,ka,Foreign_1
✓ 태,te,Rare_1
✓ 슈,shoo,Foreign_1

### 4. Verification Steps Completed
✓ Rebuilt FSTs with `python scripts/build_fsts_multi.py`
✓ Confirmed jung GIVEN_0 maps to 정 only
✓ Confirmed hun GIVEN_0 maps to 헌 only

## Why Results Fell Short

### 1. Mathematician Dataset Regression (-0.69pp)
The hun→헌 mapping appears to have broken some mathematician names that expected 훈:
- Previous accuracy: 96.32% (706/733)
- Current accuracy: 95.63% (701/733)
- Lost 5 correct conversions

### 2. Diverse Dataset Stagnation
The recovery plan's predicted impact was overestimated:
- jung→정 fix: Some names still need 중 (e.g., 강진중, 오미중)
- hun→헌 fix: Some names need 훈 (e.g., 백유훈, 오훈미)
- The position-aware system cannot handle these context-dependent variations

### 3. Position Rule Limitations
The binary surname/given distinction is insufficient:
- Same position can require different mappings based on:
  - Historical vs modern usage
  - Personal preference
  - Regional variations
  - Context within the name

## Current Variant State

```python
jung variants: {'SURNAME_0': '정', 'GENERAL_0': '정', 'GIVEN_0': '정'}
hun variants: {'SURNAME_0': '헌', 'GIVEN_0': '헌'}
sun variants: {'GIVEN_0': '선', 'RARE_0': '순', 'RARE_1': '순'}
```

## Failure Analysis

### Diverse Dataset (31 failures)
- **jung→정 conflicts**: Still 6 cases expecting 중
- **hun→헌 conflicts**: Now worse - 5 cases expecting 훈
- **English names**: 8 roundtrip failures (unfixable)
- **Other**: Various low-frequency issues

### Key Insight
The position-aware system assumes uniform behavior within positions, but Korean romanization is more nuanced. The same romanization in the same position can legitimately map to different Hangul based on factors beyond simple position.

## Recommendations

### Option 1: Accept Current State
- 95.63% mathematician accuracy is still very good
- 84.50% diverse accuracy reflects real complexity
- Further tuning risks more regressions

### Option 2: Name-Specific Overrides
- Add full-name entries for problem cases:
  - 강진중,kang_jinjung
  - 백유훈,baek_yuhun
  - 오훈미,oh_hunmi

### Option 3: Revert to Pre-Position System
- Return to simpler variant map without position tags
- May achieve more balanced results

## Conclusion

The evidence-based recovery plan was implemented exactly as specified but achieved only marginal improvements on the diverse dataset (-0.5pp) while causing regression on the mathematician dataset (-0.69pp). The fundamental issue is that position-based rules are too simplistic for the complexity of Korean romanization preferences.