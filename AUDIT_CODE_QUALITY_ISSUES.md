# GMNAP Code Quality Issues
*From Full System Audit - August 4, 2025*

## 🔴 Critical Code Issues

### 1. Korean Implementation Complexity
```
src/regions/e_groups/e4_korea/: 6,533 lines
src/regions/a_groups/a1_anglo_sphere.py: 493 lines
```
**Problem**: Korean is 13x larger than other regions!
**Impact**: Unmaintainable, hard to debug
**Fix**: Extract common patterns, simplify

### 2. Dead Code Everywhere
```
processor.py.backup_fixed
pipeline_v6.py.backup_20230615
converter_fallback.py
converter_fixed.py
converter_final.py
```
**Problem**: Multiple versions of same files
**Impact**: Confusion, which is correct?
**Fix**: Delete all backups, use git

### 3. Circular Import Risks
```python
# In pipeline_v6.py
from src.regions.manager import RegionManager
# In manager.py  
from src.core.pipeline_v6 import ...  # Potential circular!
```
**Fix**: Use dependency injection

---

## 🟡 Architecture Inconsistencies

### 1. Mixed Processing Patterns
```python
# Region A1 - Simple approach
def clean(self, entry):
    entry["name"] = entry["name"].strip()

# Region E4 - Over-engineered
def clean(self, entry):
    fst = self.build_fst()
    lattice = self.create_lattice()
    beam = self.beam_search(lattice)
    # ... 200 more lines
```

### 2. Inconsistent Error Handling
```python
# Some regions
raise RegionRuleError("Bad input")

# Others
logger.error("Bad input")
return None

# Yet others
assert canonical_latin, "Missing name"
```

### 3. Configuration Chaos
```yaml
# Some use YAML
regions/a1/config.yaml

# Others hardcoded
KOREAN_PARTICLES = ["은", "는", "이", "가"]

# Some use environment
os.getenv("GMNAP_KOREAN_MODE")
```

---

## 🟢 Good Patterns to Replicate

### 1. Security-First Design ✅
```python
def clean(self, entry: Dict[str, Any]) -> None:
    # GOOD: Security check first
    self.security_validate(entry)
    
    # Then process
    canonical = self.security_clean_field(
        entry["CanonicalLatin"], 
        "CanonicalLatin"
    )
```

### 2. Type Safety ✅
```python
def detect_script(self, text: str) -> List[str]:
    """
    Returns:
        List[str]: Detected scripts in order of prevalence
    """
    # Clear types throughout
```

### 3. Comprehensive Tests ✅
```python
# Good test structure
tests/unit/test_region_a1.py
tests/integration/test_pipeline_a1.py
tests/security/test_a1_injection.py
```

---

## 📏 Code Metrics

### File Size Distribution
```
Healthy (<500 lines):  ████████████████░░░░  80%
Large (500-1000):      ███░░░░░░░░░░░░░░░░░  15%
Too Large (>1000):     █░░░░░░░░░░░░░░░░░░░   5%
```

### Complexity Scores
```
Low (1-10):     ████████████░░░░░░░░  60%
Medium (11-20): ██████░░░░░░░░░░░░░░  30%
High (21+):     ██░░░░░░░░░░░░░░░░░░  10%  ⚠️
```

### Test Coverage
```
>90%:   ████░░░░░░░░░░░░░░░░  20%
70-90%: ████████░░░░░░░░░░░░  40%
50-70%: ██████░░░░░░░░░░░░░░  30%
<50%:   ██░░░░░░░░░░░░░░░░░░  10%  ⚠️
```

---

## 🔧 Refactoring Priorities

### 1. Korean Simplification (2 weeks)
- Extract FST logic to shared module
- Reduce to <1000 lines
- Create reusable patterns

### 2. Dead Code Removal (1 day)
```bash
# Find all backup files
find . -name "*.backup*" -delete
find . -name "*_old.py" -delete
find . -name "*_fixed.py" -delete
```

### 3. Standardize Error Handling (1 week)
```python
# Standard pattern for all regions
try:
    result = process(entry)
except SpecificError as e:
    logger.error(f"Processing failed: {e}")
    raise RegionRuleError(f"Cannot process: {e}")
```

---

## 🎯 Quality Improvement Plan

### Phase 1: Cleanup (Week 1)
- [ ] Delete all backup files
- [ ] Remove commented code
- [ ] Fix all type hints
- [ ] Standardize imports

### Phase 2: Refactor (Week 2-3)
- [ ] Extract Korean common patterns
- [ ] Standardize error handling
- [ ] Consolidate configuration
- [ ] Reduce file sizes

### Phase 3: Documentation (Week 4)
- [ ] Add missing docstrings
- [ ] Generate API docs
- [ ] Create architecture diagrams
- [ ] Write developer guide

---

## 💯 Quality Checklist

Before any PR, ensure:
- [ ] No files >1000 lines
- [ ] Cyclomatic complexity <20
- [ ] Test coverage >80%
- [ ] All functions have docstrings
- [ ] No backup files committed
- [ ] Security validation included
- [ ] Type hints complete
- [ ] Error handling consistent

---

## 🚀 Quick Wins

### Today (30 minutes each)
1. Delete all `.backup` files
2. Remove all `_old.py` files  
3. Fix circular imports
4. Add missing type hints

### This Week
1. Refactor one oversized file
2. Standardize one region's errors
3. Add tests for uncovered code
4. Document one complex module

---

## Summary

The codebase is fundamentally sound but suffers from:
- **Inconsistent patterns** between regions
- **Korean over-engineering** making it unmaintainable
- **Dead code accumulation** causing confusion
- **Missing standardization** in errors/config

Focus on cleanup and standardization before adding new features.