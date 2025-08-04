# Korean v7 Module - Deployment Summary

## 🚀 Deployment Status: READY

### Performance Baseline (2025-08-01)
- **Math Dataset**: 97.42% (717/736) ✅
- **Diverse Dataset**: 89.50% (179/200) ⚠️
- **Independent Dataset**: ~94% ✅

### Integration Points

#### 1. GMNAP Integration
The module is fully integrated with GMNAP v7 through:
- `src/regions/e_groups/e4_korea/processor.py` - Main processor class
- `src/regions/e_groups/e4_korea/converter_v7.py` - V7 converter wrapper
- `src/regions/e_groups/__init__.py` - E4 export

#### 2. Key Files
```
Production:
├── src/converter.py              # Core conversion logic
├── resources/rr_syllable_map.csv # Mapping database (11,473 entries)
├── scripts/build_fsts_multi.py   # FST builder
├── models/*.fst                  # Compiled FSTs (9 files)
└── converter_v7.py              # V7 GMNAP wrapper

Testing:
├── scripts/test_math_dataset.py
├── scripts/test_diverse_dataset.py
└── scripts/test_independent_dataset.py
```

#### 3. Build Process
```bash
# To rebuild FSTs after any CSV changes:
python3 purge_duplicates.py
python3 scripts/build_fsts_multi.py
python3 build_han2rom_loan.py
```

### Usage Example
```python
from src.regions.e_groups.e4_korea import E4KoreaProcessor

processor = E4KoreaProcessor()
entry = {
    "CanonicalLatin": "Park, Sukjin",
    "ISO_Region": "KR"
}
cleaned = processor.clean(entry)
# cleaned["CanonicalNative"] = "박, 석진"
```

### Known Limitations
1. **Diverse Dataset Performance**: Below 97.5% target due to fundamental FST architecture conflicts
2. **Multi-character patterns**: Not supported in current syllable-by-syllable architecture
3. **Dataset-specific optimization**: Cannot optimize for all datasets simultaneously

### Recommendations
1. Deploy as-is with documented performance levels
2. Monitor production accuracy metrics
3. Plan architectural improvements for v8 if higher accuracy needed

### Compliance
- ✅ Meets GMNAP v7 CJK Round-Trip rule (≥97% for Math dataset)
- ✅ Implements position-aware processing (Rule 13)
- ✅ Handles hyphen/space variations
- ✅ Supports both KR and KP territories

---
*Module frozen at stable configuration - do not modify weights without extensive testing*