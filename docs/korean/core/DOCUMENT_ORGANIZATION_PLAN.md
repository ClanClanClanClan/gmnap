# Korean v6 Document Organization Plan

## Current Document Inventory (41 documents)

### 1. Core Implementation Documents (KEEP)
These are essential for understanding and maintaining the system:
- `README.md` - Main project documentation
- `README_FINAL_V6.md` - v6 specific implementation guide  
- `converter_v6.py` - Original working implementation
- `KOREAN_V6_COMPLETE_JOURNEY_ANALYSIS.md` - Comprehensive lessons learned

### 2. Summary Documents (KEEP) 
High-level overviews worth preserving:
- `KOREAN_V6_FINAL_SUMMARY.md` - Technical summary of v6
- `V6_FINAL_IMPLEMENTATION_STATUS.md` - Final status report
- `IMPLEMENTATION_COMPLETE.md` - Completion documentation

### 3. Journey/Analysis Documents (ARCHIVE)
Documents that show the development process but aren't needed for operation:
- `KOREAN_CONVERTER_V6_IMPLEMENTATION_PLAN.md`
- `SYSTEMATIC_IMPROVEMENT_FINAL_REPORT.md`
- `VARIANT_LOOKUP_SUCCESS_REPORT.md`
- `diverse_dataset_analysis_report.md`
- `POSITION_AWARE_RESULTS.md`
- `BEAM_SEARCH_IMPLEMENTATION_*.md`
- `AUTO_FIX_SYSTEM_*.md`
- `FAILURE_ANALYSIS_REPORT.md`
- `RECOVERY_PLAN_RESULTS.md`

### 4. Handoff Documents (ARCHIVE)
Intermediate communication documents:
- `AI_GUIDANCE_POSITION_AWARE_ISSUES.md`
- `AI_HANDOFF_*.md`
- `HANDOVER_TO_NEXT_AI.md`
- `CRITICAL_HANDOVER_TO_NEXT_AI.md`
- `HELP_POSITION_AWARE_INVESTIGATION.md`

### 5. Request Documents (DELETE)
Obsolete implementation requests:
- `V5_KOREAN_IMPLEMENTATION_REQUEST_FOR_AI_AGENT.md`
- `V5_KOREAN_IMPLEMENTATION_STATUS.md`
- `KOREAN_V5_*` files
- All `*_REQUEST.md` files

### 6. Experimental Results (ARCHIVE)
Failed experiments that provide learning value:
- `FORENSIC_CLEANUP_RESULTS.md`
- `SURGICAL_REPAIR_KIT_OUTCOME_ANALYSIS.md`
- `FIX_CATEGORIZATION_ANALYSIS.md`
- `FINAL_AUTO_FIX_*.md`

## Recommended Directory Structure

```
e4_korea/
├── README.md                          # Main documentation
├── converter_v6.py                    # Working implementation
├── src/                              # Source code
│   ├── converter.py                  # Current converter
│   ├── preprocess.py                 # Preprocessing
│   ├── segment.py                    # Segmentation
│   └── ...                          # Other source files
├── resources/                        # Data files
│   ├── variant_map.csv             # Variant mappings
│   ├── rr_syllable_map.csv         # Syllable lexicon
│   └── ...                         # Other resources
├── models/                          # FST models
├── data/                           # Test datasets
├── docs/                           # Organized documentation
│   ├── core/                       # Essential docs
│   │   ├── README_FINAL_V6.md
│   │   ├── KOREAN_V6_FINAL_SUMMARY.md
│   │   └── JOURNEY_ANALYSIS.md
│   └── archive/                    # Historical docs
│       ├── journey/                # Development journey
│       ├── experiments/            # Failed attempts
│       └── handoffs/               # Communication docs
└── scripts/                        # Utility scripts
```

## Cleanup Commands

```bash
# Create organized structure
mkdir -p docs/core docs/archive/journey docs/archive/experiments docs/archive/handoffs

# Move core documents
mv README_FINAL_V6.md KOREAN_V6_FINAL_SUMMARY.md KOREAN_V6_COMPLETE_JOURNEY_ANALYSIS.md docs/core/

# Archive journey documents
mv *IMPLEMENTATION*.md *REPORT*.md *RESULTS*.md docs/archive/journey/

# Archive experiments
mv *AUTO_FIX*.md *BEAM_SEARCH*.md *POSITION_AWARE*.md docs/archive/experiments/

# Archive handoffs
mv *HANDOFF*.md *HANDOVER*.md *GUIDANCE*.md docs/archive/handoffs/

# Delete obsolete files
rm V5_*.md *_REQUEST*.md *_STATUS.md
```

## Priority Actions

1. **Immediate**: Revert to original v6 configuration
2. **Next**: Execute document organization
3. **Then**: Create snapshot of working v6 for safety
4. **Finally**: Document exact v6 configuration in detail

This organization will make it much easier for future developers to:
- Find the working implementation quickly
- Understand what was tried and why it failed
- Avoid repeating the same mistakes