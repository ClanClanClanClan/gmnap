# AI Guidance Request: Position-Aware System Unexpected Results

## Executive Summary

We implemented the position-aware variant system **exactly as specified** but got significantly different results than predicted. Need guidance on whether to proceed, revert, or try a different approach.

### Results Summary

| Dataset | Predicted | Actual | Gap | 
|---------|-----------|---------|-----|
| **Diverse (200)** | 91-93% | **83.50%** | -8.5pp |
| **Mathematician (733)** | 97.8-98.0% | **88.95%** | -9pp |

**Critical Issue**: Mathematician dataset lost 8.32pp (from 97.27% to 88.95%)

## Detailed Implementation Verification

### ✅ Step 1: Added Position Tags to variant_map.csv
```csv
# Added exactly as specified:
정,jung,SURNAME_0
중,jung,GIVEN_0
장,chang,SURNAME_0
창,chang,GIVEN_0
이,ri,SURNAME_0
리,ri,GIVEN_0
훈,hun,GIVEN_0
헌,hun,SURNAME_0

# Plus optional additions:
여,yeo,GIVEN_0
순,sun,GIVEN_0
교,gyo,GIVEN_0
위,wi,GIVEN_0
용,yong,GIVEN_0
위,wei,GIVEN_0
종,jong,GIVEN_0
```

### ✅ Step 2: Replaced Variant Loader
```python
# Implemented exactly as specified:
_var = {}           # roman → {tag: hangul}
for h, r, *tag in csv.reader(open(...)):
    if not r or r.startswith("#"):
        continue
    key = (tag[0] if tag else "").upper()  # "", SURNAME_0, GIVEN_0 …
    _var.setdefault(r.lower(), {})[key] = h
```

### ✅ Step 3: Added _pick_variant Helper
```python
# Implemented exactly as specified:
def _pick_variant(rr: str, is_surname: bool):
    cand = _var.get(rr)
    if not cand:
        return None
    # exact tag match beats generic:
    tag = "SURNAME_0" if is_surname else "GIVEN_0"
    return cand.get(tag) or cand.get("") or next(iter(cand.values()))
```

### ✅ Step 4: Modified eng2kor
```python
# Implemented exactly as specified:
for i, tok in enumerate(tokens):
    rom = tok.lower().replace(",", "").replace(" ", "")
    # ❶ position‑aware variant check
    h = _pick_variant(rom, is_surname=(i == 0))
    if h:
        out.append(h)
        continue
    # ❷ existing hyphen split + segment fallback
    for part in tok.split("-"):
        h = _pick_variant(part.lower(), is_surname=False)
        # ... rest exactly as specified
```

## Why Results Differ from Predictions

### 1. Mathematician Dataset Regression Analysis

The system is making **technically correct** position-based decisions that are **linguistically wrong** for mathematician names:

#### Sample of New Failures (was correct, now wrong):
```
Bae_Jungchul: 배정철 → 배중철 ❌ (jung in given position → 중)
Kim_Eun-Jung: 김은정 → 김은중 ❌ (jung in given position → 중)
Park_JungYun: 박정윤 → 박중윤 ❌ (jung in given position → 중)
Yoo_Jungmin: 유정민 → 유중민 ❌ (jung in given position → 중)
Kim_Junghyun: 김정현 → 김중현 ❌ (jung in given position → 중)
```

**Pattern**: The mathematician dataset strongly prefers jung→정 even in given name positions, contradicting our position rule.

### 2. Diverse Dataset Limited Improvement

#### Still Failing Cases:
```
Jeon_JungKook: 전중국 (got 중) but expected 전정국 (needs 정)
Seo_JungJin: 서중진 (got 중) but expected 서정진 (needs 정)
Ha_JungWoo: 하중우 (got 중) but expected 하정우 (needs 정)
Random_058 (구정규): 구중규 (got 중) but expected 구정규 (needs 정)
```

**Pattern**: Even in the diverse dataset, many "jung" in given position still want 정, not 중.

### 3. Position Rule Limitations

The position-aware system assumes:
- Surname position jung → 정 ✅
- Given name position jung → 중 ❌ (Often still needs 정)

But reality is more complex:
- Cultural preferences override position
- Historical figures have fixed romanizations
- Modern names follow different patterns
- Same romanization has multiple valid Hangul

## Specific Test Results

### Working as Intended:
```python
✅ An, Jung-Geun → 안중근 (Historical figure, jung→중)
✅ Jung Myung-Hoon → 정명훈 (Surname Jung stays 정)
✅ Shim, Chang-Min → 심창민 (chang→창 in given)
✅ Jang, Yu-Ri → 장유리 (ri→리 in given)
```

### Not Working as Expected:
```python
❌ Park Jung-Hee → 박중희 (Expected 박정희)
❌ Chang Ho-Park → 장호박 (Expected 박창호 - order issue?)
❌ Many mathematician names now wrong
```

## Data Analysis

### Current Failures by Pattern (Diverse Dataset):

| Pattern | Count | Position Rule | Reality |
|---------|-------|---------------|---------|
| jung→정 needed | 8 | Given→중 | Still needs 정 |
| sun→선 needed | 5 | Given→순 | Context dependent |
| Complex vowels | 7 | N/A | wei, eui issues |
| English names | 6 | N/A | David, Sarah, etc. |

### Mathematician Dataset Impact:

- **81 new failures** introduced by position rules
- Most are jung/chang in given position
- Dataset has strong convention for jung→정

## Critical Questions

### 1. Is the Position Rule Assumption Correct?

The instruction assumed:
- "The SURNAME/GIVEN split prevents any regression on 'Jung' family names"

But we're seeing massive regression because given name "jung" often still maps to 정.

### 2. Should We Continue or Revert?

Current trade-off:
- **Gain**: +3pp on diverse (80.50% → 83.50%)
- **Loss**: -8.32pp on mathematicians (97.27% → 88.95%)

Is this acceptable?

### 3. Are We Missing Something?

Possibilities:
- Different test dataset than expected?
- Additional rules needed beyond position?
- Weight system not working as intended?
- Need more sophisticated context rules?

## Detailed Code State

### Current converter.py Key Parts:
```python
# Variant dictionary structure
_var = {
    "jung": {"SURNAME_0": "정", "GIVEN_0": "중", "GENERAL_0": "정"},
    "chang": {"SURNAME_0": "장", "GIVEN_0": "창"},
    "ri": {"SURNAME_0": "이", "GIVEN_0": "리"},
    # ... etc
}

# Position detection
for i, tok in enumerate(tokens):
    h = _pick_variant(rom, is_surname=(i == 0))  # First token = surname
```

### Current variant_map.csv End:
```csv
정,jung,SURNAME_0
중,jung,GIVEN_0
장,chang,SURNAME_0
창,chang,GIVEN_0
이,ri,SURNAME_0
리,ri,GIVEN_0
훈,hun,GIVEN_0
헌,hun,SURNAME_0
여,yeo,GIVEN_0
순,sun,GIVEN_0
교,gyo,GIVEN_0
위,wi,GIVEN_0
용,yong,GIVEN_0
위,wei,GIVEN_0
종,jong,GIVEN_0
정,jung,GENERAL_0
선,sun,GENERAL_0
```

## Options for Moving Forward

### Option A: Revert Everything
```bash
git checkout src/converter.py
git checkout resources/variant_map.csv
python3 scripts/build_fsts_multi.py
```
- Returns to 97.27% mathematicians, 80.50% diverse
- Safe but no improvement

### Option B: Refine Position Rules
Add more context:
- Check if romanization appears in known given names that prefer 정
- Add frequency-based selection
- Use compound detection (Jung-Hee vs Jung-Geun)

### Option C: Dataset-Specific Converters
```python
def eng2kor(name: str, dataset="mathematician"):
    if dataset == "mathematician":
        # Use original variant system
    else:
        # Use position-aware system
```

### Option D: Investigate Why Predictions Were Wrong
- Was this tested on different data?
- Are there additional rules we're missing?
- Should position detection work differently?

## Specific Guidance Needed

1. **Should we accept -8.32pp on mathematicians for +3pp on diverse?**

2. **Are the position rules correct as stated, or do they need refinement?**
   - Is jung→중 in given position actually the right rule?
   - Should we have exceptions for common names?

3. **Why might the predictions have been so different from reality?**
   - Different test data?
   - Missing implementation detail?
   - Wrong assumptions about Korean naming?

4. **What's the best path forward?**
   - Revert to safe 97.27%/80.50%?
   - Try to fix position rules?
   - Accept current results?
   - Try completely different approach?

## Test Commands to Reproduce

```bash
# Current state test
python3 scripts/validate.py | tail -5  # Should show 88.95%
python3 scripts/test_diverse_dataset.py | grep "Diverse Dataset:"  # Should show 83.50%

# See specific failures
python3 scripts/analyze_39_failures.py  # Shows remaining patterns

# Test specific cases
python3 -c "
import sys; sys.path.append('src')
from converter import eng2kor
print(eng2kor('Park Jung-Hee'))  # 박중희 (wrong, should be 박정희)
print(eng2kor('An, Jung-Geun'))  # 안중근 (correct)
"
```

**Please provide guidance on how to proceed given these unexpected results.**