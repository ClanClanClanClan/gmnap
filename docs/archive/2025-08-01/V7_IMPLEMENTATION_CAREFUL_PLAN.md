# V7 Implementation - Careful Planning Document

## 🛑 STOP AND THINK

Before taking ANY action, let's carefully plan the correct approach to v7 implementation.

## Critical Lessons from Previous Mistake

1. **Parallel structures are wrong** - Work within existing codebase
2. **Don't duplicate code** - Wrap existing implementations
3. **Test imports first** - Ensure code can actually run
4. **Understand before acting** - Read existing code structure carefully
5. **Minimal intervention** - Change only what's necessary

## Current State Analysis

### Existing Structure
```
src/
├── gmnap/
│   ├── regions/
│   │   ├── base.py                    # Has RegionSpec class
│   │   ├── manager.py                 # Region management
│   │   ├── a_groups/
│   │   │   ├── __init__.py
│   │   │   └── a1_anglo_sphere.py     # A1_AngloSphere(RegionSpec)
│   │   ├── b_groups/
│   │   │   └── b1_east_slavic.py      # B1_EastSlavic(RegionSpec)
│   │   ├── c_groups/
│   │   │   ├── c2_persian_tajik.py
│   │   │   └── c3_arabic_levant_nile.py
│   │   └── e_groups/
│   │       ├── e1_sinophone_mainland.py
│   │       ├── e3_japan.py
│   │       └── e4_korea/               # Complex subdirectory
│   ├── core/
│   │   ├── pipeline.py
│   │   └── unicode_handler.py
│   └── authorities/
│       └── base.py
├── core/                               # Also has core modules (duplication?)
├── authorities/                        # Also has authorities (duplication?)
└── regions/                           # Also has regions (duplication?)
```

### Key Observations

1. **Multiple "regions" directories** - Which is canonical?
   - `src/gmnap/regions/` 
   - `src/regions/`
   
2. **Import confusion** - Different files import differently:
   ```python
   # In src/gmnap/regions/a_groups/a1_anglo_sphere.py:
   from src.regions.base import RegionSpec  # Uses src.regions!
   
   # But the file is in src/gmnap/regions/
   ```

3. **The RegionSpec class** already exists in the codebase - no need to redefine

## Careful V7 Implementation Plan

### Phase 1: Understand (Do This First!)
```bash
# 1. Check which regions directory is actually used
grep -r "from.*regions" src/ | head -20

# 2. Verify where RegionSpec is defined
find . -name "*.py" -type f | xargs grep "class RegionSpec"

# 3. Check how existing regions import base
grep -r "from.*RegionSpec" src/gmnap/regions/

# 4. Understand the import structure
python -c "import sys; print(sys.path)"
```

### Phase 2: Design (Only After Understanding)

**Option A: Minimal Addition**
```
src/gmnap/regions/
├── base.py           # Existing RegionSpec
├── base_v7.py        # NEW: Add v7 interfaces here
├── a_groups/
│   ├── a1_anglo_sphere.py      # Existing, don't touch
│   └── a1_anglo_sphere_v7.py   # NEW: Thin adapter
```

**Option B: Compatibility Module**
```
src/gmnap/
├── v7_compatibility/
│   ├── __init__.py
│   ├── interfaces.py    # V7 interfaces
│   └── adapters.py      # Generic adapter factory
```

### Phase 3: Implementation Checklist

Before writing ANY code:

- [ ] Verify imports will work
- [ ] Test in Python REPL first
- [ ] Create minimal example
- [ ] Ensure no duplication
- [ ] Check existing tests still pass

### Safe First Step

Instead of creating files, let's first understand:

```python
# Test script to understand structure (save as test_imports.py)
import sys
print("Python path:", sys.path)

try:
    from src.regions.base import RegionSpec
    print("✓ Can import from src.regions")
except ImportError as e:
    print("✗ Cannot import from src.regions:", e)

try:
    from src.gmnap.regions.base import RegionSpec
    print("✓ Can import from src.gmnap.regions")
except ImportError as e:
    print("✗ Cannot import from src.gmnap.regions:", e)
```

## Recommended Approach

### 1. Delete the Wrong Implementation
```bash
rm -rf gmnap_v7/  # Remove the parallel universe
```

### 2. Study Existing Code
- How do imports currently work?
- Where should v7 code go?
- What's the minimal change needed?

### 3. Create Single Test Adapter
- Start with ONE region only
- Make it work completely
- Verify imports, tests, functionality

### 4. Only Then Scale Up
- Apply pattern to other regions
- One at a time
- Test after each

## Questions to Answer First

1. **Which is the real regions directory?**
   - `src/regions/` or `src/gmnap/regions/`?
   - How do existing imports work?

2. **Where does RegionSpec live?**
   - Multiple base.py files exist
   - Which is canonical?

3. **What's the PYTHONPATH setup?**
   - How does the project handle imports?
   - Any special configuration?

4. **Do existing tests pass?**
   - Run them first
   - Ensure we don't break anything

## Red Flags to Avoid

🚫 **Don't create new directories without understanding existing ones**
🚫 **Don't duplicate any existing code**
🚫 **Don't assume import paths - test them**
🚫 **Don't implement multiple regions at once**
🚫 **Don't skip the understanding phase**

## The Right Mindset

> "Move slowly and fix things"

Better to spend an hour understanding than create another mess that needs cleanup.

## Next Actions (In Order)

1. **Delete gmnap_v7/**
2. **Run the import test script**
3. **Map out the real structure**
4. **Design minimal v7 addition**
5. **Implement ONE adapter**
6. **Test thoroughly**
7. **Only then proceed**

---

*"Measure twice, cut once. Understand twice, code once."*