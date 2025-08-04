# Position-Aware Variant System Results

## Summary

Implemented the position-aware variant system as specified, achieving significant improvements on the diverse dataset while maintaining a trade-off with mathematician accuracy.

## Final Results

| Dataset | Before | After | Change |
|---------|--------|-------|--------|
| **Diverse (200)** | 80.50% | **83.50%** | **+3.00pp** |
| **Mathematician (733)** | 97.27% | **88.95%** | **-8.32pp** |

## What Was Implemented

### 1. Position Tags Added to variant_map.csv
```csv
정,jung,SURNAME_0    # Surname Jung → 정
중,jung,GIVEN_0      # Given name jung → 중
장,chang,SURNAME_0   # Surname Chang → 장
창,chang,GIVEN_0     # Given name chang → 창
이,ri,SURNAME_0      # Surname Ri → 이
리,ri,GIVEN_0        # Given name ri → 리
훈,hun,GIVEN_0       # Given name hun → 훈
헌,hun,SURNAME_0     # Surname Hun → 헌
```

Plus 7 additional optional variants (yeo, sun, gyo, wi, yong, wei, jong).

### 2. Position-Aware Variant Dictionary
```python
_var = {}  # roman → {tag: hangul}
# Now stores: {"jung": {"SURNAME_0": "정", "GIVEN_0": "중"}}
```

### 3. Position-Based Selection
```python
def _pick_variant(rr: str, is_surname: bool):
    # Selects variant based on position in name
    tag = "SURNAME_0" if is_surname else "GIVEN_0"
```

## Key Successes

✅ **An, Jung-Geun → 안중근** (Historical figure - correctly uses 중)  
✅ **Jung Myung-Hoon → 정명훈** (Surname Jung correctly stays 정)  
✅ **Shim, Chang-Min → 심창민** (Given name chang correctly → 창)  
✅ **Jang, Yu-Ri → 장유리** (Given name ri correctly → 리)  

## Issues Discovered

### 1. Mathematician Dataset Regression

The position-aware system caused many mathematician names with "Jung" in given name position to incorrectly map to 중 instead of 정:

- Bae_Jungchul: 배정철 → 배중철 ❌
- Kim_Eun-Jung: 김은정 → 김은중 ❌  
- Park_JungYun: 박정윤 → 박중윤 ❌

**Root Cause**: The mathematician dataset predominantly uses jung→정 even in given name positions, while the diverse dataset has mixed usage.

### 2. Diverse Dataset Improvement Limited

While we improved from 80.50% to 83.50%, this is far from the predicted 91-93%:

- Some jung→정 cases still fail because they need 정 even in given position
- sun→선 conflicts remain (added sun→순 for given names, but some need 선)
- Format issues persist (comma-hyphen tokenization)

## Analysis

The position-aware system works as designed but reveals a fundamental challenge:

1. **Different datasets have different romanization conventions**
   - Mathematicians: Consistent jung→정 preference
   - Diverse names: Mixed jung→정/중 based on actual usage

2. **Position alone is insufficient**
   - Need context beyond just surname vs given name
   - Some names have historical/cultural preferences

3. **Trade-off is unfavorable**
   - Lost 8.32pp on primary dataset (mathematicians)
   - Gained only 3.00pp on secondary dataset (diverse)

## Recommendation

**Revert to the original system** for production use:
- Maintains 97.27% on mathematician dataset (primary target)
- Accept 80.50% on diverse dataset as reasonable generalization

The position-aware system demonstrates that further improvements require:
- Name-specific mappings rather than position rules
- Larger training corpus to learn context patterns
- Potentially different converters for different domains

## Lessons Learned

1. **Position-aware variants work technically** but need careful dataset alignment
2. **Simple position rules are insufficient** for Korean name romanization
3. **Dataset-specific conventions dominate** over general linguistic rules
4. **Production systems need stability** on primary use cases

The experiment successfully showed both the potential and limitations of position-based variant selection.