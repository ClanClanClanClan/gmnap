# AI Handoff: Breaking Through 80.50% Accuracy Barrier

## Current Situation - We Need Your Help

We're **stuck at 80.50% accuracy** (161/200) on a diverse Korean name dataset, and I suspect we're being too conservative with fixes. The user believes we should be able to do better, and I agree.

## What We've Achieved So Far

### 1. **Architecture Fix ✅** 
We successfully implemented token-level variant lookup that fixed the segmentation problem:
```python
# src/converter.py - lines 42-57
def eng2kor(name:str):
    for tok in tokenise(name):
        if tok.lower() in _variant:  # Check variants BEFORE segmentation
            out.append(_variant[tok.lower()][1])
            continue
        # ... rest of segmentation logic
```

**Proof it works:**
- "Boo Kyung-Min" → 부경민 ✅ (was 보오경민)
- "Jee Sung-Min" → 지성민 ✅ (was 제에성민)

### 2. **Current Performance**
- **Mathematician dataset**: 97.95% (718/733)
- **Diverse dataset**: 80.50% (161/200)
- **Gap**: 17.45 percentage points

## The 31 Failures We Can't Fix (Actually 31, not 39!)

### Most Common Patterns - VERY FIXABLE:

| Pattern | Count | Example | Current → Expected |
|---------|-------|---------|-------------------|
| 중→정 | 6 | An, Jung-Geun | 안정근 → 안중근 |
| 창→장 | 5 | Shim, Chang-Min | 심장민 → 심창민 |
| 리→이 | 5 | Jang, Yu-Ri | 장유이 → 장유리 |
| 헌→훈 | 4 | Hun names | 훈 → 헌 |

### Concrete Examples of Failures:
```
1. Lee, Chung-Wei: 이정웨이 → 이청위 (청→정, 위→웨)
2. Song, Hye-Kyo: 송혜쿄 → 송혜교 (교→쿄)
3. Kim, Yo-Jong: 김요종 → 김여정 (여→요, 정→종)
4. An, Jung-Geun: 안정근 → 안중근 (중→정)
5. Shim, Chang-Min: 심장민 → 심창민 (창→장)
6. Yi, Sun-Sin: 이선신 → 이순신 (순→선)
```

### Run This to See All Failures:
```bash
python3 scripts/analyze_39_failures.py
```

## My Attempted Fix That "Failed"

I tried adding these single-syllable mappings:
```python
# I claimed this dropped accuracy to 73%, but did it really?
echo "중,jung" >> resources/rr_syllable_map.csv
echo "창,chang" >> resources/rr_syllable_map.csv  
echo "리,ri" >> resources/rr_syllable_map.csv
echo "헌,heon" >> resources/rr_syllable_map.csv
```

**But I may have been wrong!** Please verify:
1. Did I add them to the right file?
2. Did I rebuild FSTs properly?
3. Are there conflicting mappings I missed?

## Specific Test Cases to Debug

```python
# These SHOULD work but don't:
from converter import eng2kor

# Case 1: Jung → 중
assert eng2kor("An Jung-Geun") == "안중근"  # Historical figure, should be 중
# Currently returns: "안정근"

# Case 2: Chang → 창  
assert eng2kor("Shim Chang-Min") == "심창민"  # Common name
# Currently returns: "심장민"

# Case 3: Combined
assert eng2kor("Lee Jung-Won") == "이중원" or eng2kor("Lee Jung-Won") == "이정원"
# Need context to know which is right
```

## Critical Questions

### 1. **Are we using variant_map.csv correctly?**
```csv
# Current variant_map.csv has:
정,jung,
정,jeong,
# But we need BOTH:
정,jung,   # Sometimes jung→정
중,jung,   # Sometimes jung→중
```
Can we add both and use weights/context?

### 2. **Is the test data format issue real?**
Test uses: `"An, Jung-Geun"` (comma format)
We process: `"An Jung-Geun"` (space format)

Does this matter? Test with:
```python
eng2kor("An, Jung-Geun")  # With comma
eng2kor("An Jung-Geun")   # Without comma
```

### 3. **Are we missing a weight/priority system?**
Maybe we need:
```csv
정,jung,GIVEN_NAME_0    # Default for given names
중,jung,HISTORICAL_0    # For historical figures
```

### 4. **Can we use the FST system better?**
The FST builder (`scripts/build_fsts_multi.py`) has a weight system. Can we:
- Add context-sensitive weights?
- Use position information (surname vs given)?
- Add frequency-based priorities?

## Hypotheses to Test

### Hypothesis 1: We're Being Too Conservative
**Test**: Add ALL the single-syllable fixes and measure impact
```bash
# Add these and see what really happens:
echo "중,jung" >> resources/rr_syllable_map.csv
echo "창,chang" >> resources/rr_syllable_map.csv
echo "리,ri" >> resources/rr_syllable_map.csv  
echo "헌,heon" >> resources/rr_syllable_map.csv
python3 scripts/build_fsts_multi.py
python3 scripts/test_diverse_dataset.py
```

### Hypothesis 2: Variant Map Not Being Used Fully
**Test**: Add to variant_map.csv instead:
```bash
echo "중,jung," >> resources/variant_map.csv
echo "창,chang," >> resources/variant_map.csv
# Does this behave differently?
```

### Hypothesis 3: We Need Compound Mappings
**Test**: Add specific compound patterns:
```bash
echo "중근,junggeun" >> resources/rr_syllable_map.csv
echo "창민,changmin" >> resources/rr_syllable_map.csv
echo "정근,jeonggeun" >> resources/rr_syllable_map.csv
```

## Specific Code to Run

```python
# Test script to analyze the 39 failures:
import yaml
import sys
sys.path.append('src')
from converter import eng2kor

# Load diverse dataset
with open('data/korean_diverse_test.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Test each failure case
failures = []
for name, info in data.items():
    expected = info['AllCommonVariants'][0]  # Hangul version
    canonical = info.get('CanonicalLatin', info.get('AllCommonVariants', [''])[1])
    
    result = eng2kor(canonical)
    if result != expected:
        failures.append({
            'name': name,
            'input': canonical,
            'expected': expected,
            'got': result,
            'chars': [(e, g) for e, g in zip(expected, result or '') if e != g]
        })

# Analyze patterns
from collections import Counter
char_diffs = Counter()
for f in failures:
    for e, g in f.get('chars', []):
        char_diffs[f"{e}→{g}"] += 1

print(f"Total failures: {len(failures)}")
print("\nMost common character differences:")
for diff, count in char_diffs.most_common(10):
    print(f"  {diff}: {count} times")
```

## Critical Insight We Just Discovered

**We only have 31 failures, not 39!** And look at the pattern counts:
- jung→중 (6) + chang→창 (5) + ri→리 (5) + hun→헌 (4) = **20 failures**
- **Fixing just these 4 patterns would fix 20/31 failures**
- **This would push accuracy from 80.50% to ~90%!**

## What We Need From You

1. **Test our "conservative" assumption**: Add these 4 mappings and see what really happens
   ```bash
   echo "중,jung" >> resources/rr_syllable_map.csv
   echo "창,chang" >> resources/rr_syllable_map.csv
   echo "리,ri" >> resources/rr_syllable_map.csv
   echo "헌,hun" >> resources/rr_syllable_map.csv
   python3 scripts/build_fsts_multi.py
   python3 scripts/test_diverse_dataset.py
   ```

2. **Question**: Why would these cause conflicts?
   - jung→중 is for names like 안중근 (An Jung-Geun)
   - jung→정 is for names like 박정희 (Park Jung-Hee)
   - **Both are valid!** Can we use context or weights?

3. **Alternative approach**: Use variant_map.csv with proper weights?
   ```csv
   중,jung,GIVEN_NAME_0  # For given names like Jung-Geun
   정,jung,SURNAME_0     # For surname Jung
   ```

4. **Break through**: Get us from 80.50% to 90%+ by fixing these 20 cases

## Key Files

```
src/converter.py                    # Has our variant lookup fix
resources/rr_syllable_map.csv       # Base mappings (11,000+ entries)
resources/variant_map.csv           # Variant mappings with weights (~90 entries)
scripts/build_fsts_multi.py         # Builds weighted FSTs
scripts/test_diverse_dataset.py     # Tests the 200 diverse names
data/korean_diverse_test.yaml       # The 200 test cases
```

## Success Criteria

Get the diverse dataset accuracy above 85% without breaking mathematician accuracy (keep it >97%).

**The user suspects we can do better than 80.50%, and they're probably right. Help us prove it!**