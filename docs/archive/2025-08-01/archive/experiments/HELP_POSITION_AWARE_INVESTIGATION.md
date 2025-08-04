# Help Request: Position-Aware System Deep Investigation

## Summary
I implemented the position-aware system **exactly as instructed**, but results are far worse than predicted. After deep investigation, I suspect there may be **conflicting entries** in variant_map.csv or other factors I'm missing.

## Current State vs Predictions

| Metric | Your Prediction | Actual Result | Gap |
|--------|----------------|---------------|-----|
| **Diverse** | 91-93% | **83.50%** | -8.5pp |
| **Mathematician** | 97.8-98.0% | **88.95%** | -9pp |

## Deep Investigation Results

### 1. Variant Dictionary Analysis

When I check the built variant dictionary:
```python
jung variants: {'SURNAME_0': '정', 'GIVEN_0': '중', 'GENERAL_0': '정'}
chang variants: {'': '창', 'SURNAME_0': '장', 'GIVEN_0': '창'}
ri variants: {'': '리', 'SURNAME_0': '이', 'GIVEN_0': '리'}
```

**Key observation**: Some variants have EMPTY tag entries ('': '창', '': '리'). These might be from pre-existing entries in variant_map.csv.

### 2. Checking Original variant_map.csv

Current file analysis shows multiple conflicting entries:
```
Line 47: 정,jeong,          (empty tag)
Line 88: 장,chang,          (empty tag)  
Line 153-154: 정,jung,SURNAME_0 / 중,jung,GIVEN_0  (our additions)
Line 155-156: 장,chang,SURNAME_0 / 창,chang,GIVEN_0 (our additions)
```

**Critical finding**: Pre-existing tagless entries like `장,chang,` create dictionary entries with empty tags!

### 3. How _pick_variant Works

The function returns variants in this priority:
```python
return cand.get(tag) or cand.get("") or next(iter(cand.values()))
```

For chang:
1. Checks GIVEN_0 → finds '창' ✓
2. If not found, checks "" → would find '창' from line 88!
3. If not found, takes any value

**Empty-tag entries can interfere with position logic!**

### 4. Tokenization Verification

Verified tokenization works correctly:
```
'An, Jung-Geun' → ['An', 'Jung', 'Geun']
'Park Jung-Hee' → ['Park', 'Jung', 'Hee']
```

Position detection (i==0 for surname) is working correctly.

### 5. The Real Problem: Korean Romanization Patterns

Looking at diverse dataset failures:
```
Jeon_JungKook: Expected 전정국, Got 전중국
Seo_JungJin: Expected 서정진, Got 서중진  
Ha_JungWoo: Expected 하정우, Got 하중우
```

**Pattern**: Many names with "jung" in given position still want 정, not 중!

## Critical Discoveries

### Discovery 1: Pre-existing Entries
```bash
grep -E "^[^#].*,.*,\s*$" resources/variant_map.csv

# Found:
중,joong,
이,yi,
이,i,
정,jeong,
장,chang,
정,cheong,
이,ri,
창,chang,
```

These tagless entries weren't mentioned in the instructions!

### Discovery 2: Position Rule Validity

The position rule assumes:
- Surname jung → 정 ✓
- Given jung → 중 ❌

But reality shows:
- An Jung-Geun (안중근) → 중 ✓ (historical figure)
- Park Jung-Hee (박정희) → 정 ✓ (president)
- Most mathematician Jung-X → 정 (not 중)

### Discovery 3: Variant Priority Issues

Current _var dictionary for problematic cases:
```python
'chang': {'': '창', 'SURNAME_0': '장', 'GIVEN_0': '창'}
'jeong': {'': '정'}
'ri': {'': '리', 'SURNAME_0': '이', 'GIVEN_0': '리'}
```

Empty tag entries might be selected unexpectedly!

## Hypothesis for Poor Performance

1. **Pre-existing tagless entries** interfere with position logic
2. **Position rules are linguistically incorrect** for many Korean names
3. **Mathematician dataset has strong conventions** that override position rules

## Specific Questions

### 1. Should we clean variant_map.csv?
```bash
# Remove all tagless entries before our additions?
sed -i '' '/,$/d' resources/variant_map.csv  # Remove lines ending with comma
```

### 2. Is the position rule correct?
- You predicted jung→중 for given names
- Data shows most jung in given position still want 정
- Is this a dataset quirk or linguistic reality?

### 3. Debug variant selection priority?
Should we modify _pick_variant to handle empty tags differently?
```python
# Current:
return cand.get(tag) or cand.get("") or next(iter(cand.values()))

# Alternative:
if tag in cand:
    return cand[tag]
# Don't fall back to empty tag?
```

### 4. Why the prediction gap?
- Were predictions based on different test data?
- Are there additional rules we're missing?
- Is the empty tag interference the main issue?

## Test Commands

```bash
# Count problematic entries
grep -E "^[^#].*,.*,\s*$" resources/variant_map.csv | wc -l

# See exact variant dictionary state
python3 -c "
import sys; sys.path.append('src')
from converter import _var
for k, v in sorted(_var.items()):
    if len(v) > 1 or '' in v:
        print(f'{k}: {v}')
"

# Test specific problem cases
python3 -c "
import sys; sys.path.append('src')
from converter import eng2kor
test_cases = [
    ('Park Jung-Hee', '박정희'),
    ('Jeon Jung-Kook', '전정국'),
    ('An, Jung-Geun', '안중근'),
]
for inp, exp in test_cases:
    got = eng2kor(inp)
    print(f'{inp}: {got} (expected {exp}) {"✓" if got==exp else "✗"}')"
```

## Recommendations for Next Steps

### Option 1: Clean and Retry
1. Remove all tagless entries from variant_map.csv
2. Rebuild FSTs
3. Test again

### Option 2: Modify _pick_variant
Make position tags absolute priority:
```python
def _pick_variant(rr: str, is_surname: bool):
    cand = _var.get(rr)
    if not cand:
        return None
    tag = "SURNAME_0" if is_surname else "GIVEN_0"
    if tag in cand:
        return cand[tag]
    return cand.get("") or next(iter(cand.values()))
```

### Option 3: Accept Reality
The position rules may simply be wrong for Korean names. Consider reverting.

## Bottom Line

I implemented exactly as instructed, but:
1. **Pre-existing CSV entries** weren't accounted for
2. **Position rules don't match** actual Korean usage
3. **Need guidance** on whether to clean CSV, modify code, or abandon approach

The core issue seems to be that jung→중 in given position is linguistically incorrect for most Korean names, regardless of implementation details.