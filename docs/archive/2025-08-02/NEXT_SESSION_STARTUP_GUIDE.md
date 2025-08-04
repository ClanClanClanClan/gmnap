# 🚀 Next Session Startup Guide
*Date: 2025-08-01*  
*Status: CRYSTAL CLEAR INSTRUCTIONS FOR IMMEDIATE ACTION*

## 📋 CRITICAL: Read This First

**All documentation has been cleaned up and consolidated.** Previous session reports and analysis documents have been archived. The current state is now definitively documented in these authoritative files:

1. **`CURRENT_STATE_DEFINITIVE.md`** - What we have now (88% infrastructure, 28% regional coverage)
2. **`V7_IMPLEMENTATION_MASTER_PLAN.md`** - Complete roadmap to v7.0 compliance  
3. **`ARCHITECTURE_DEFINITIVE.md`** - How everything fits together
4. **This file** - Immediate next actions

## 🎯 Current Status (Authoritative)

**GMNAP Status**: Functional v6 implementation with Korean v7 integration  
**V7.0 Compliance**: ~15% (v7.0 is complete transformation, not upgrade)  
**Regional Coverage**: 12/43 regions (28%)  
**Next Priority**: Complete remaining 31 regional processors

## 🚀 Immediate Next Actions (Start Here)

### Option A: Continue V7.0 Full Implementation
**If goal is complete v7.0 "MathLineage Edition" compliance:**

```bash
# 1. Start with A3 Nordic-Baltic regional processor
mkdir -p src/gmnap/regions/a_groups/a3_nordic_baltic
cd src/gmnap/regions/a_groups/a3_nordic_baltic

# 2. Create processor template
# Follow the pattern from existing processors like a1_anglo_sphere
# Implement: clean(), augment(), validate(), order_key()

# 3. Key requirements for A3:
# - Icelandic patronymic system (linguistic rule #8)
# - Scandinavian particle handling  
# - Baltic surname patterns
# - Mixed Latin/diacritics script detection
```

### Option B: Focus on Regional Completion First
**If goal is solid foundation before v7.0 transformation:**

```bash
# 1. Systematically implement all 31 missing regions
# Priority order: A3, A4, A5, B3, C1, C5, C6, C7, C8, C9...
# Use V7_IMPLEMENTATION_MASTER_PLAN.md section 1.1-1.7 as guide

# 2. Each regional processor needs:
# - src/gmnap/regions/{group}/processor.py
# - tests/unit/test_{region}.py  
# - docs/regional/{REGION}.md
```

### Option C: Implement Graph Database Foundation
**If goal is to start v7.0 genealogy features:**

```bash
# 1. Set up Memgraph-CE locally
docker run -p 7687:7687 memgraph/memgraph-platform:2.12

# 2. Create graph database layer
mkdir -p src/gmnap/graph
# Implement: memgraph_client.py, genealogy_queries.py, etc.

# 3. Add schema v2.0 migration
# Add GenealogyRelation, DegreeDate, BetweennessScore objects
```

## 📁 Key Files for Reference

### Essential Documentation (Read These)
- **`docs/CURRENT_STATE_DEFINITIVE.md`** - Current status
- **`docs/V7_IMPLEMENTATION_MASTER_PLAN.md`** - Implementation roadmap
- **`docs/ARCHITECTURE_DEFINITIVE.md`** - System architecture
- **`docs/specs v7.0.yaml`** - Target specification

### Working Codebase (Modify These)
- **`src/gmnap/regions/`** - Regional processors (12/43 done)
- **`src/gmnap/core/pipeline.py`** - Pipeline engine
- **`src/gmnap/v7_compat.py`** - V7 compatibility layer
- **`tests/`** - Test suites

### Configuration Files (Don't Break These)
- **`cache/config/source_manifest.json`** - Authority sources
- **`docs/schema_v1.5.json`** - Current YAML schema
- **`CLAUDE.md`** - ⚠️ NEEDS UPDATE (contains obsolete info)

## 🔧 Development Workflow

### 1. Regional Processor Template
```python
# src/gmnap/regions/{group}/{region}/processor.py
from src.gmnap.core.region_spec import RegionSpec

class {Region}Processor(RegionSpec):
    code = "{XX}"  # Region code
    scripts = ["Latin", "Diacritics"]  # Primary scripts
    
    def clean(self, entry: dict) -> None:
        """Clean and normalize entry data"""
        # Remove honorifics, normalize spacing, etc.
        pass
    
    def augment(self, entry: dict) -> None:
        """Add region-specific data"""
        # Add surname patterns, cultural context, etc.
        pass
    
    def validate(self, entry: dict) -> None:
        """Validate entry meets region requirements"""
        # Check name format, script usage, etc.
        pass
    
    def order_key(self, entry: dict) -> str:
        """Generate deterministic sort key"""
        # Must be pure function, called twice by CI
        return f"{entry['family_name']}, {entry['given_name']}"
```

### 2. Testing Pattern
```python
# tests/unit/test_{region}.py
import pytest
from src.gmnap.regions.{group}.{region}.processor import {Region}Processor

class Test{Region}Processor:
    def setup_method(self):
        self.processor = {Region}Processor()
    
    def test_clean_removes_honorifics(self):
        entry = {"name": "Dr. Johann Schmidt"}
        self.processor.clean(entry)
        assert "Dr." not in entry["name"]
    
    def test_order_key_deterministic(self):
        entry = {"family_name": "Schmidt", "given_name": "Johann"}
        key1 = self.processor.order_key(entry)
        key2 = self.processor.order_key(entry)
        assert key1 == key2  # Must be deterministic
```

### 3. Registration Pattern
```python
# src/gmnap/v7_compat.py (add new processor)
try:
    from .regions.{group}.{region} import {Region}Processor
    v7_manager.register_processor({Region}Processor())
    logger.info("Loaded {Region}Processor")
except ImportError as e:
    logger.warning(f"Could not load {Region}Processor: {e}")
```

## ⚠️ Critical Don'ts

### DON'T:
- ❌ Create new session reports or analysis documents (archived)
- ❌ Modify CLAUDE.md without updating it completely
- ❌ Break existing working processors (A1, B1, C2, C3, D1, E1, E4, etc.)
- ❌ Add operational costs without explicit user approval
- ❌ Create conflicting documentation

### DO:
- ✅ Follow the established patterns from working processors
- ✅ Update the definitive docs when making significant changes
- ✅ Test thoroughly before committing changes
- ✅ Focus on one region at a time for quality

## 🎯 Decision Points for Next Session

### Quick Decisions Needed:
1. **Which approach?** Regional completion vs v7.0 transformation vs graph database
2. **Starting point?** A3 Nordic-Baltic vs systematic order vs user preference
3. **Depth vs breadth?** Perfect one region vs implement all regions quickly

### Recommended Path:
**Start with Regional Completion (Option B)** because:
- ✅ Builds on solid foundation
- ✅ Provides immediate value
- ✅ Less architectural risk
- ✅ Prepares for v7.0 transformation

## 📊 Success Metrics

### Short-term (Next 1-2 sessions):
- [ ] 1-3 new regional processors implemented and tested
- [ ] All existing tests still pass
- [ ] Documentation updated for new regions

### Medium-term (Next 5-10 sessions):
- [ ] 20+ regional processors implemented (>50% coverage)
- [ ] Architectural decisions made for v7.0 components
- [ ] Performance maintained >555 entries/sec

### Long-term (Next 20+ sessions):
- [ ] All 43 regional processors implemented (100% coverage)
- [ ] V7.0 MathLineage Edition features implemented
- [ ] Production-ready deployment

## 🔥 Immediate Command to Run

```bash
# Verify current working state
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap

# Check what's working
python3 -c "
import sys
sys.path.append('src')
from gmnap.v7_compat import v7_manager
print(f'Registered processors: {len(v7_manager.processors)}')
for code, proc in v7_manager.processors.items():
    print(f'  {code}: {proc.__class__.__name__}')
"

# Run a quick test to verify system is working
python3 -m pytest tests/ -x -v --tb=short
```

## 📋 Final Checklist

Before starting implementation work:
- [ ] ✅ Read CURRENT_STATE_DEFINITIVE.md 
- [ ] ✅ Read V7_IMPLEMENTATION_MASTER_PLAN.md relevant sections
- [ ] ✅ Understand ARCHITECTURE_DEFINITIVE.md
- [ ] ✅ Verify current system is working (run tests)
- [ ] ✅ Choose implementation approach (A, B, or C above)
- [ ] 🚀 Start coding!

---

**The foundation is solid. The documentation is clear. The path forward is defined. Time to build!** 🎯