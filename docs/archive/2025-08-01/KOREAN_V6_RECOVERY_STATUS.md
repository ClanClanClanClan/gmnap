# Korean v6 Recovery Playbook Implementation Status

**Date**: 2025-07-28  
**Implementer**: Claude  
**Current Branch**: `v6_rescue_2025‑07‑27`

## Executive Summary

The Korean v6 Recovery Playbook was initiated but **encountered baseline mismatch issues**. The playbook expects baseline accuracies of ≥96.30% (mathematician) and ≥86.50% (diverse), but the repository's commit history shows these targets were never achieved in the commits specified for reset.

## Implementation Status

### ✅ Phase 0: Hard Reset
- **Executed**: Reset to commit `e9b9f31` ("restore true 86.6 baseline")
- **Issue**: Original target `fb8c32f` gave only 75.31%/69.00% accuracy
- **Fallback**: Used earlier high-water mark commit instead

### ✅ Phase 1: Data Sanitation
Successfully completed all steps:
- ✅ De-duplicated variant_map.csv (86 canonical rows)
- ✅ Purged tagless shadow rows
- ✅ Added 6 mandatory high-impact variants
- ✅ Added 2 critical segmentation fixes
- ✅ Built deterministic FSTs (~165KB each)

### ⚠️ Phase 2: Zero-Regression Gate
- ✅ Created pre-commit hook
- ❌ **BLOCKED**: Current accuracies below required baselines

### ❌ Phase 3: Not Attempted
Blocked by Phase 2 baseline requirements

## Current Performance Metrics

| Test Suite | Current | Required | Gap |
|------------|---------|----------|-----|
| Mathematician | 619/733 (84.45%) | 706/733 (96.30%) | -11.85pp |
| Diverse | ~142/200 (71.00%) | 173/200 (86.50%) | -15.50pp |

## Root Cause Analysis

1. **Baseline Mismatch**: The playbook's baseline requirements (96.30%/86.50%) appear to be aspirational targets rather than actual historical baselines

2. **Commit History Review**:
   ```
   7b6d64a - 77.49% accuracy (plateau)
   fb8c32f - 95% target (but actually ~75%)
   e9b9f31 - 86.6% baseline (actual: 84.45%)
   ```

3. **Missing Tag**: The fallback tag `v6_position_aware_stable` does not exist

## Critical Decision Required

The playbook cannot proceed as written due to baseline mismatch. Options:

### Option 1: Adjust Baselines (Recommended)
- Accept current 84.45%/71.00% as baseline
- Document this as "Phase 0.5: Baseline Adjustment"
- Continue with quality gates to prevent regression below these levels

### Option 2: Search for Better Commit
- Explore commit history further
- Risk: May not find commit meeting requirements
- Time: Additional investigation needed

### Option 3: Abort and Reassess
- The playbook assumptions don't match repository reality
- Need new strategy aligned with actual historical performance

## Recommendation

**Proceed with Option 1** - Adjust baseline expectations to current reality:
- **New Mathematician Baseline**: ≥619/733 (84.45%)
- **New Diverse Baseline**: ≥142/200 (71.00%)

These represent the actual "clean baseline" available in the repository. The quality gates will ensure no regression below these levels while working toward the original targets.

## Next Steps (Pending Approval)

1. Update accuracy_log.tsv with realistic baseline
2. Modify pre-commit hook to check for adjusted baselines
3. Proceed with Phase 3 incremental improvements
4. Target original goals (96.30%/86.50%) as aspirational

## Files Modified

- `/resources/variant_map.csv` - Cleaned and added 6 variants
- `/resources/rr_syllable_map.csv` - Added 2 segmentation fixes
- `/models/*.fst` - Rebuilt deterministically
- `/.git/hooks/pre-commit` - Created (currently blocking)

## Artifacts Created

- `/dedupe_variants.py` - Deduplication script
- `/purge_tagless.py` - Shadow row removal script
- This status document

---

**Action Required**: Please advise on baseline adjustment strategy.