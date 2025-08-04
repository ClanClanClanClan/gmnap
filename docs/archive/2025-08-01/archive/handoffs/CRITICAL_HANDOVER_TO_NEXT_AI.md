# CRITICAL HANDOVER: PyNini 2.1.5 API Incompatibility with v6-FINAL Plan

## 🚨 IMMEDIATE ISSUE

I was instructed to follow the v6-FINAL upgrade plan EXACTLY as written, but I have hit a fundamental API incompatibility between the plan and PyNini 2.1.5.

## 📋 WHAT I DID EXACTLY

### Step 1: ✅ COMPLETED EXACTLY
```csv
# Created resources/variant_map.csv exactly as specified
박,park,SURNAME_0
박,pak,
박,bak,
이,lee,SURNAME_0
이,yi,
이,i,
# ... etc
```

### Step 2: ✅ COMPLETED EXACTLY  
```python
# Created scripts/build_fsts_multi.py exactly as specified
import csv, pathlib, pynini as pn
def read_rows():
    # 1) base RR table rows (weight 0)
    for row in csv.reader(open("resources/rr_syllable_map.csv",encoding="utf8")):
        if len(row) >= 2 and not row[0].startswith('#'):
            h, r = row[0], row[1]
            yield h,r,0.0
    # 2) variant rows
    for row in csv.reader(open("resources/variant_map.csv",encoding="utf8")):
        if len(row) >= 3 and not row[0].startswith('#'):
            h, r, tag = row[0], row[1], row[2]
            w = 0.0 if tag=="SURNAME_0" else 1.0
            yield h,r,w
# ... rest exactly as in plan
```

### Step 3a-3b: ✅ COMPLETED EXACTLY
```python
# Updated converter.py exactly as specified
ROM2 = pn.Fst.read("models/rom2han_multi.fst")
HAN2 = pn.Fst.read("models/han2rom_multi.fst")

def _dice(a,b):
    a=b"" if not a else unicodedata.normalize("NFC",a.casefold()).encode()
    b=b"" if not b else unicodedata.normalize("NFC",b.casefold()).encode()
    bigr=lambda s:{s[i:i+2] for i in range(len(s)-1)}
    x,y=bigr(a),bigr(b); return (2*len(x&y))/(len(x)+len(y) or 1)
```

### Step 3c: ❌ EXACT PLAN FAILS WITH API ERROR

**THE PLAN SPECIFIES:**
```python
def kor2eng(h:str, original_rr:str|None=None)->str|None:
    # build lattice char by char
    lat = pn.accep("",TOK)
    for ch in h:
        lat = lat + (pn.accep(ch,TOK) @ HAN2)
    # get top‑5 paths
    best5=list(pn.shortestpath(lat, nshortest=5, unique=True).paths())
    if not best5: return None
    if original_rr:
        # choose variant with highest Dice to original
        scored=[(_dice(original_rr," ".join(p.ostring().split())),p.ostring()) for p in best5]
        return max(scored)[1]
    return best5[0].ostring()
```

**EXACT ERRORS WHEN FOLLOWING THIS:**

1. **Error 1:** `TOK="utf8"` → `_pywrapfst.FstBadWeightError: utf8`
   - **Fix Applied:** `TOK=None` (minimal change)

2. **Error 2:** `lat + (pn.accep(ch,TOK) @ HAN2)` → `DeterminizeFst: Argument not an acceptor`
   - **Fix Applied:** Added `lat = pn.project(lat, "output")` (minimal change)

3. **Error 3:** `list(pn.shortestpath(...).paths())` → `TypeError: '_pynini._StringPathIterator' object is not iterable`
   - **THIS IS THE CRITICAL BLOCKER**

## 🔍 DETAILED TECHNICAL ANALYSIS

### The Core Problem: PyNini 2.1.5 `paths()` API

```python
# THE PLAN EXPECTS THIS TO WORK:
best5=list(pn.shortestpath(lat, nshortest=5, unique=True).paths())

# BUT IN PYNINI 2.1.5:
paths_iterator = pn.shortestpath(lat, nshortest=5, unique=True).paths()
print(type(paths_iterator))  # <class '_pynini._StringPathIterator'>
print(hasattr(paths_iterator, '__iter__'))  # False
print(hasattr(paths_iterator, '__next__'))  # False

# RESULT: Cannot convert to list, cannot iterate
```

### What Actually Works in PyNini 2.1.5:

```python
# SINGLE PATH WORKS:
shortest = pn.shortestpath(lat, nshortest=1, unique=True)
result = shortest.string()  # ✅ Works

# MULTIPLE PATHS FAIL:
shortest = pn.shortestpath(lat, nshortest=5, unique=True)
result = shortest.string()  # ❌ "State has multiple outgoing arcs"
```

### Current Status:
- **30.42% accuracy** using single-path + manual variants
- **Target: 97%**
- **Gap: 66.58 percentage points**

## 🆘 WHAT I NEED FROM THE NEXT AI

### Critical Questions:

1. **Is there a different PyNini 2.1.5 API to extract multiple paths?**
   - Can you find documentation or examples for PyNini 2.1.5 path iteration?
   - Are there alternative methods like `compose()`, `union()`, or `rmepsilon()` that could work?

2. **Should I modify the FST building to work with single paths?**
   - Can the multi-path FSTs be restructured to work with `nshortest=1`?
   - Should the weights be applied differently?

3. **Is there a workaround within the plan's architecture?**
   - Can the n-best selection be done at the FST level rather than path level?
   - Should we build separate FSTs for each variant?

4. **What is the exact PyNini version the plan was written for?**
   - The plan assumes `list(shortestpath().paths())` works
   - PyNini 2.1.5 clearly doesn't support this
   - Should we upgrade/downgrade PyNini?

### Specific Technical Requests:

1. **Test this exact code in your PyNini environment:**
   ```python
   import pynini as pn
   fst = pn.union(pn.accep("hello"), pn.accep("world"))
   shortest = pn.shortestpath(fst, nshortest=2, unique=True)
   paths = shortest.paths()
   path_list = list(paths)  # Does this work in your version?
   ```

2. **If it doesn't work, find the correct PyNini 2.1.5 way to:**
   - Extract multiple weighted paths from an FST
   - Iterate through n-best paths with their outputs
   - Get path strings from a multi-path lattice

3. **If no solution exists, determine:**
   - Should we use a different approach entirely?
   - Can the 97% target be achieved with single-path + smarter variants?
   - Is the plan fundamentally incompatible with PyNini 2.1.5?

## 📊 CURRENT STATE SUMMARY

- ✅ Multi-path FSTs built correctly (weighted variants working)
- ✅ Single-path extraction works (`박` → `"park"` due to SURNAME_0 weight)
- ❌ Multi-path extraction fails due to API incompatibility
- ⚠️ Currently at 30.42% using workarounds

## 🎯 SUCCESS CRITERIA

I need the next AI to either:

1. **Find the correct PyNini 2.1.5 API** to make the plan work exactly as written
2. **Provide a modified version of Step 3c** that achieves the same n-best + Dice logic using available APIs
3. **Confirm that 97% is impossible** with PyNini 2.1.5 and explain why

**CRITICAL:** Do not deviate from the plan's core architecture (weighted FSTs + n-best + Dice selection) unless you can prove it's technically impossible with PyNini 2.1.5.

---

*Handover Date: 2025-07-25*  
*Blocker: PyNini 2.1.5 paths() API incompatibility*  
*Urgency: High - user expects exact plan compliance*