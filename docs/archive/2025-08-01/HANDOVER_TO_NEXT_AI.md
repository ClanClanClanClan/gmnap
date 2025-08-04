# Korean Converter v6 - Handover Document for Next AI

## 🎯 Current Situation

I was asked to continue implementing the Korean converter v6 following a specific plan. The user was frustrated because previous attempts deviated from the plan. The key instruction was: **"STOP and follow the plan EXACTLY as written"**.

## ✅ What I Actually Did

### 1. **Found and Used Existing Tools** (Instead of Creating Fallbacks)
- The plan said to use conda for PyNini installation
- I initially started following a path that would have created a fallback system
- But I caught myself and found conda at `~/miniconda3/bin/conda`
- Successfully installed PyNini 2.1.5 with OpenFST 1.8.2

### 2. **Built Real FSTs with PyNini**
- Generated 11,246 syllable mappings from the Unicode Hangul block
- Built actual FST files: `models/rom2han.fst` and `models/han2rom.fst`
- These are real PyNini weighted finite state transducers, not JSON lookups

### 3. **Fixed Multiple Technical Issues**

#### Issue 1: Wrong Converter Import
```python
# Was importing:
from src.converter_final import eng2kor, kor2eng  # This uses JSON fallback

# Fixed to:
from src.converter import eng2kor, kor2eng  # This uses PyNini FSTs
```

#### Issue 2: FST Token Type Error
```python
# Was failing with:
TOK="utf8"  # StrToWeight: Bad weight: utf8

# Fixed to:
TOK=None  # Use default token type
```

#### Issue 3: CSV Format Inconsistency
```
# Original generated entries:
가,ga  # (hangul, romanization)

# Manually added entries were backwards:
hyun,현  # (romanization, hangul)

# Fixed all 62 reversed entries to be consistent
```

#### Issue 4: Korean-to-English Conversion
```python
# Was trying full string (failing):
def kor2eng(h:str): return first_output(pn.accep(h)@HAN2)

# Fixed to character-by-character:
def kor2eng(h:str):
    result = []
    for char in h:
        rom = first_output(pn.accep(char)@HAN2)
        if rom is None: return None
        result.append(rom)
    return " ".join(result)
```

## 📊 Current Performance

### What's Working:
- **92.22% conversion rate** (676 out of 733 test cases convert successfully)
- **Bidirectional conversion works**: English → Korean → English
- **Simple names work perfectly**: Lee → 이 → lee (100% accuracy)

### What's NOT Working:
- **Round-trip accuracy is below 97% threshold**
- Many names fail the Dice coefficient test due to spelling variations

### Examples of the Problem:
```
"Ahn, Dae-Hoon" → "안대훈" → "an dae hun"
- Original: "Ahn" (with 'h')
- Round-trip: "an" (no 'h')
- Dice score: 0.222 (FAIL - needs ≥0.97)

"Kim Young Soo" → "킴영수" → "kim young su"
- Original: "Soo" (double 'o')
- Round-trip: "su" (single 'u')
- Dice score: 0.842 (FAIL - needs ≥0.97)
```

## 🔍 Root Cause Analysis

### The Fundamental Problem:
Korean romanization is **many-to-one** by nature:
- Multiple English spellings → Same Korean → One "standard" spelling back

Examples:
- "Lee", "Yi", "Rhee", "I" → "이" → "i" (by default)
- "Park", "Pak", "Bak" → "박" → "bak" (by default)
- "Ahn", "An" → "안" → "an" (by default)

### Why FSTs Struggle:
1. **FSTs are deterministic**: One input → One output
2. **Can't preserve original spelling**: Once converted to Korean, original spelling information is lost
3. **Current approach**: Last mapping wins (if multiple exist)

## 🛠️ What Needs to Be Done

### Option 1: Multi-Path FST Design (Recommended)
Instead of simple one-to-one FSTs, build FSTs that:
1. Keep track of common spelling variants
2. Use weighted paths to prefer certain spellings
3. Return the most likely original spelling based on frequency

### Option 2: Hybrid Approach
1. Use FST for Korean → Multiple possible English spellings
2. Use a statistical model to pick the most likely spelling
3. Consider context (e.g., if input had "Park", prefer "Park" over "Pak")

### Option 3: Name-Specific Rules
1. Build separate FSTs for common Korean surnames
2. These preserve exact spellings: Park → 박 → Park (not pak)
3. Fall back to general FST for other syllables

### Option 4: Metadata Preservation
1. During English → Korean, store spelling hints
2. Use these hints during Korean → English conversion
3. This breaks pure FST model but ensures round-trip accuracy

## 📁 Key Files to Understand

1. **`src/converter.py`** - The PyNini-based converter (THIS IS WHAT WE USE)
2. **`src/converter_final.py`** - JSON fallback (DO NOT USE)
3. **`scripts/build_fsts.py`** - Builds the FST files from syllable mappings
4. **`resources/rr_syllable_map.csv`** - 11,246 Hangul-romanization pairs
5. **`scripts/validate_hangul.py`** - Validation script using Dice coefficient

## ⚠️ Critical Warnings

1. **DO NOT create new fallback systems** - Use the existing PyNini infrastructure
2. **DO NOT switch back to converter_final.py** - It's the JSON fallback
3. **The user wants ≥97% accuracy** - Current 92% is not acceptable
4. **Follow any new plan EXACTLY** - The user is frustrated with deviations

## 🎯 Success Criteria

To complete this task, you need:
1. **≥97% round-trip accuracy** on the 733-entry test set
2. Using **actual PyNini FSTs** (not fallbacks)
3. Integrated with **GMNAP v6.1 E4 regional module**
4. **No improvisation** - follow instructions exactly

## 💡 My Recommendation

The current single-path FST approach will never achieve 97% accuracy due to the many-to-one nature of romanization. You'll need to implement one of the options above, likely Option 1 (weighted multi-path FSTs) or Option 3 (name-specific rules) to meet the requirement.

Good luck! The infrastructure is solid - you just need to enhance the FST design to handle the spelling variation challenge.

---
*Handover Date: 2025-07-25*  
*Current Status: 92% conversion rate, <97% round-trip accuracy*  
*Main Challenge: Many-to-one romanization mapping*