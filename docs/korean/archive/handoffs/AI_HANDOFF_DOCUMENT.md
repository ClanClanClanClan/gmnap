# AI Handoff Document: Korean Name Converter Architecture Issue

## URGENT: Need Solutions for Segmentation-Before-Variants Problem

### Current Status Summary

**Achievement**: 97.27% accuracy on Korean mathematician dataset (713/733 correct)
**Problem**: Only 82.50% accuracy on diverse Korean names (165/200 correct)
**Root Cause**: Architecture limitation preventing fixes from working

### What We've Built

#### 1. **Weighted FST System (Working)**
```
Input: "Park, Jung-Hee" 
→ Tokenize: ["Park", "Jung-Hee"]
→ Segment: ["park", "jung", "hee"] 
→ FST Lookup: [박, 정, 희]
→ Output: "박정희"
```

#### 2. **Auto-Fix Detection System (Working)**
- Correctly identifies 16 high-confidence fixes
- 100% safety validation (no false positives)
- Categorizes fixes by type and viability

#### 3. **The Critical Architecture Problem (BLOCKING)**

**Current Flow**:
```
"Boo Kyung-Min" 
→ segment("boo") = ["bo", "o"]  ← PROBLEM: segments BEFORE variant check
→ FST lookup: bo=보, o=오
→ Result: "보오경민" (WRONG)
```

**Needed Flow**:
```
"Boo Kyung-Min"
→ Check variants FIRST: "boo" → 부  ← SOLUTION NEEDED HERE
→ segment("kyung") = ["kyung"]
→ FST lookup: boo=부, kyung=경, min=민
→ Result: "부경민" (CORRECT)
```

### Specific Files and Functions

#### Core Problem Location:
**File**: `src/converter.py:22-29`
```python
def eng2kor(name:str):
    out=[]
    for tok in tokenise(name):          # ← Tokenizes "Boo Kyung-Min" → ["Boo", "Kyung-Min"]
        for syl in segment(tok):        # ← segment("Boo") → ["bo", "o"] PROBLEM HERE
            h=_rr2han(syl)             # ← Looks up "bo" and "o" separately
            if h is None: return None
            out.append(h)
    return "".join(out)
```

#### Supporting Files:
- `src/segment_fixed.py`: Contains segmentation logic
- `src/syllable_lexicon_fixed.py`: Lexicon for valid syllables
- `resources/variant_map.csv`: Contains correct mappings like `부,boo,SURNAME_0`
- `scripts/build_fsts_multi.py`: Builds FSTs with variant weights

### Attempted Solutions (All Failed)

#### 1. **Adding Mappings to CSV** ❌
```bash
echo "부,boo" >> resources/rr_syllable_map.csv
```
**Result**: Ignored because segmentation happens first

#### 2. **Variant Map Entries** ❌
```csv
부,boo,SURNAME_0
```
**Result**: Never checked because "boo" gets segmented to ["bo", "o"]

#### 3. **Override Dictionary** ❌
```python
OVERRIDES = {'boo': '부', 'jee': '지'}
```
**Result**: Would work but bypasses the systematic FST approach

### What We Need: Clear Solutions

#### Option A: Pre-Segmentation Variant Check
**Modify `eng2kor()` to check variants BEFORE segmentation:**
```python
def eng2kor(name:str):
    out=[]
    for tok in tokenise(name):
        # NEW: Check if whole token is a known variant FIRST
        if tok.lower() in VARIANT_MAP:
            out.append(VARIANT_MAP[tok.lower()])
            continue
        # EXISTING: Fall back to segmentation
        for syl in segment(tok):
            h=_rr2han(syl)
            if h is None: return None
            out.append(h)
    return "".join(out)
```

#### Option B: Lexicon-Aware Segmentation
**Modify `segment_fixed.py` to prefer longer matches:**
```python
def segment(token: str, max_len: int = 8) -> list[str]:
    # NEW: Prioritize known variants from variant_map.csv
    if token.lower() in KNOWN_VARIANTS:
        return [token.lower()]
    # EXISTING: Fall back to current segmentation
    # ... rest of current logic
```

#### Option C: Multi-Pass Lookup
**Try variants first, then segment:**
```python
def _rr2han_with_variants(text):
    # Pass 1: Try as complete variant
    if text in VARIANT_MAP:
        return VARIANT_MAP[text]
    # Pass 2: Try FST lookup
    return _rr2han(text)
```

### Specific Test Cases to Fix

Our auto-fix system identified these high-confidence cases that SHOULD work:

| Input | Expected | Current | Issue |
|-------|----------|---------|-------|
| boo | 부 | 보오 | segments to ["bo", "o"] |
| jee | 지 | 제에 | segments to ["je", "e"] |
| chun | 천 | 전 | variant conflict |
| yom | 염 | 욤 | missing mapping |
| pae | 배 | 패 | wrong FST weight |

### Success Metrics

If you solve this architecture issue, we should see:
- **Diverse dataset accuracy**: 82.50% → ~94% (+11.5%)
- **Auto-fix success rate**: 40% → 95%+
- **Working fixes**: 6/16 → 15/16

### Critical Questions for You

1. **Which architectural approach** (A, B, or C above) makes most sense?
2. **How to implement** variant checking before segmentation without breaking existing code?
3. **Where exactly** should the variant map be loaded and checked?
4. **How to handle** precedence between variant_map.csv and rr_syllable_map.csv?
5. **Performance impact** of additional lookups?

### What NOT to Do

- ❌ Don't add more CSV mappings (they'll be ignored due to segmentation)
- ❌ Don't modify FST files directly (bypasses systematic approach)
- ❌ Don't create special-case hard-coding (breaks maintainability)
- ✅ DO solve the fundamental segmentation-before-variants architecture

### Files You'll Need to Examine

```
src/
├── converter.py           # Main conversion logic (NEEDS MODIFICATION)
├── segment_fixed.py       # Segmentation logic (MIGHT NEED MODIFICATION)
├── syllable_lexicon_fixed.py  # Available syllables
└── preprocess_fixed.py    # Tokenization

resources/
├── variant_map.csv        # Contains correct mappings being ignored
└── rr_syllable_map.csv    # Base mappings

scripts/
├── build_fsts_multi.py    # FST building (uses variant_map.csv)
└── auto_fix_system_v2.py  # Shows exactly what needs fixing
```

### Expected Outcome

After your fix, this should work:
```python
from converter import eng2kor
assert eng2kor("Boo Kyung-Min") == "부경민"  # Currently fails
assert eng2kor("Jee Sung-Min") == "지성민"   # Currently fails
assert eng2kor("Park Jung-Hee") == "박정희"  # Currently works
```

**Please provide a specific implementation solution that fixes the segmentation-before-variants architecture problem.**