# 🚨 CRITICAL: Broken Imports Discovered in GMNAP Codebase

## The Issue

While carefully analyzing the codebase structure before implementing v7 changes, I discovered a **fundamental import issue** that prevents the code from running.

## What I Found

### Expected Structure (Based on Imports)
Files like `src/gmnap/regions/a_groups/a1_anglo_sphere.py` contain imports like:
```python
from src.regions.base import RegionRuleError, RegionSpec
```

### Actual Structure
```
src/
├── core/                    # ✅ EXISTS
├── authorities/             # ✅ EXISTS  
├── gmnap/
│   ├── regions/
│   │   └── base.py         # ✅ RegionSpec is HERE
│   ├── core/               # ⚠️ DUPLICATE of src/core/
│   └── authorities/        # ⚠️ DUPLICATE of src/authorities/
└── regions/                # ❌ DOES NOT EXIST
```

### The Problem
The imports expect `src/regions/base.py` but the file is actually at `src/gmnap/regions/base.py`.

## Impact

This means:
1. **The code cannot actually run** (ModuleNotFoundError)
2. **Tests likely fail** if they try to import regions
3. **Any v7 work built on this would be broken**

## Verification

```bash
# This fails:
PYTHONPATH=src python3 -c "from src.regions.base import RegionSpec"
# ModuleNotFoundError: No module named 'src.regions'

# This should work:
PYTHONPATH=src python3 -c "from src.gmnap.regions.base import RegionSpec"
```

## Root Cause Analysis

It appears there was a code reorganization where:
1. Old structure: `src/regions/`, `src/core/`, `src/authorities/`
2. New structure: `src/gmnap/regions/`, `src/gmnap/core/`, `src/gmnap/authorities/`
3. Some components (core, authorities) exist in BOTH places
4. But regions only exists in the new location
5. **Imports were never updated** to match the new structure

## Critical Decision Point

Before I can implement any v7 changes, I need to fix this fundamental issue. Two options:

### Option 1: Fix All Imports
Update all imports from:
```python
from src.regions.base import RegionSpec
```
To:
```python
from src.gmnap.regions.base import RegionSpec
```

### Option 2: Create Compatibility Structure  
Create symlinks or move files to match expected imports:
```bash
# Create compatibility structure
mkdir -p src/regions
cp src/gmnap/regions/base.py src/regions/base.py
```

## Recommendation

**Option 1 (Fix Imports)** is cleaner because:
- No file duplication
- Clear single source of truth
- Follows the intended structure

## Files That Need Import Updates

Based on my analysis, these files likely have broken imports:
- `src/gmnap/regions/a_groups/a1_anglo_sphere.py`
- `src/gmnap/regions/b_groups/b1_east_slavic.py`
- `src/gmnap/regions/c_groups/c2_persian_tajik.py`
- `src/gmnap/regions/c_groups/c3_arabic_levant_nile.py`
- `src/gmnap/regions/e_groups/e1_sinophone_mainland.py`
- `src/gmnap/regions/e_groups/e3_japan.py`
- `src/gmnap/regions/manager.py`
- Any other files importing from `src.regions`

## Required Action

**I need your permission to fix these imports before proceeding with v7 implementation.**

The fix is straightforward but touches multiple files:
1. Change `from src.regions.base import` → `from src.gmnap.regions.base import`
2. Change `from src.core.` → `from src.gmnap.core.` (if needed)
3. Test that imports work

This is a prerequisite for any v7 work because the current codebase cannot even run.

## Alternative

If you prefer not to touch the existing imports, I could:
1. Create the expected `src/regions/` structure
2. Move or copy files to match what imports expect
3. Then proceed with v7 work

But this would create duplication and maintenance issues.

---

**Question**: Should I fix the broken imports to match the actual file structure, or would you prefer a different approach?

This is blocking all further v7 work until resolved.