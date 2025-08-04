# Korean V5 Failure Analysis Report

## Summary
Out of 20 remaining failures:
- 16 are Eng→Kor conversion failures
- 4 are roundtrip failures (mostly English names like David, Grace, Linda)

## Root Cause Analysis

### 1. FST vs CSV Mapping Conflicts (11 fixable cases)

The primary issue is that the FST file (`rom2han_multi.fst`) contains incorrect mappings that override the correct mappings in the CSV file:

| Romanization | FST (incorrect) | CSV (correct) | Affected Names |
|--------------|-----------------|---------------|----------------|
| chun         | 전              | 천            | Chun_Baekjin, Chun_Hong-Mok |
| cheong       | 청              | 정            | Cheong_Munho |
| yom          | 욤              | 염            | Yom_Ha-Rim |
| yum          | 윰              | 염            | Yum_Young-Tae |
| pae          | 패              | 배            | Pae_Soonjung |

These are straightforward to fix by either:
1. Rebuilding the FST with correct mappings
2. Modifying the converter to prioritize CSV over FST for these specific cases

### 2. Missing Mappings (2 cases)

Some romanizations have no mapping in either FST or CSV:
- `boo` → should map to 부 (Boo_Kyungmin)
- `jee` → should map to 지 (Jee_Sungmin)

### 3. Complex/Ambiguous Cases (3 cases)

These require special handling:
- `Ri_Young-Chul`: Uses North Korean romanization (리 vs 이)
- `um` vs `eom`: Both are valid romanizations for different surnames (음 vs 엄)
- Given name components with context-dependent mappings

### 4. Hard-to-Fix Cases (4 cases)

- `Kim_RareInitialsBlock`: Special case with asterisk
- Given name parsing issues: `Huh_Junghan`, `Moon_Sukja`
- English names: David, Grace, Linda (roundtrip failures)

## Recommendations

### Immediate Fixes (11 cases can be resolved)

1. **Option A: Fix the FST** (Recommended)
   - Rebuild `rom2han_multi.fst` with correct mappings
   - Ensures consistency across the system

2. **Option B: Override in converter.py**
   - Add a mapping override dictionary before FST lookup
   - Quick fix but less elegant

### Example Implementation for Option B:

```python
# In converter.py
OVERRIDE_MAPPINGS = {
    'chun': '천',
    'cheong': '정', 
    'yom': '염',
    'yum': '염',
    'pae': '배',
    'boo': '부',
    'jee': '지',
    'um': '음',  # Choose preferred mapping
}

def _rr2han(rr):
    # Check overrides first
    if rr in OVERRIDE_MAPPINGS:
        return OVERRIDE_MAPPINGS[rr]
    # Then proceed with normal FST lookup
    return first_output(pn.accep(rr)@ROM2) or rom2han().get(rr)
```

## Impact Assessment

- Fixing the 11 straightforward cases would bring accuracy from 730/750 (97.33%) to 741/750 (98.80%)
- The remaining 9 cases require architectural decisions or are inherently ambiguous
- Overall system would achieve >98% accuracy with minimal changes