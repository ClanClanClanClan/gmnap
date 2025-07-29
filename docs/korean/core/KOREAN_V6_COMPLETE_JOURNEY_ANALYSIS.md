# Korean Converter v6: Complete Journey Analysis & Lessons Learned

## Executive Summary

This document provides a comprehensive analysis of the Korean converter v6 journey, from initial success (97%/80%) through various "improvement" attempts that resulted in significant regression (95.63%/43.5%). It serves as a critical lessons-learned document for future development.

## Timeline & Performance Trajectory

### 1. **Original v6 Success** (Baseline)
- **Mathematician**: 97.27% (712/733)
- **Diverse**: 80.5% (161/200)
- **Method**: Systematic manual fixes to variant mappings
- **Key insight**: Simple, targeted data fixes worked brilliantly

### 2. **Position-Aware Variant Attempt** 
- **Mathematician**: 95.63% (701/733) ↓ -1.64%
- **Diverse**: 84.5% (169/200) ↑ +4%
- **Method**: Added SURNAME_0/GIVEN_0 tags to variant_map.csv
- **Result**: Small diverse gain, but mathematician regression
- **Issues**: 
  - Position rules too simplistic for Korean names
  - Conflicts between position tags
  - jung→중 for given names was incorrect

### 3. **Beam Search Implementation**
- **Mathematician**: 91.41% (670/733) ↓ -5.86%
- **Diverse**: 75.5% (151/200) ↓ -5%
- **Method**: Probabilistic name-level beam search with bigram LM
- **Result**: Significant regression on both datasets
- **Issues**:
  - Synthetic bigram model inadequate
  - Beam search made incorrect probabilistic choices
  - Added complexity without benefit

### 4. **Track A: Korean Corpus Attempt**
- Downloaded 1GB Korean Wikipedia
- Built real bigram model (43,400 unique bigrams)
- Built name-specific bigram model
- **Result**: 39.5% on diverse (catastrophic failure)
- **Key Learning**: General Korean text patterns ≠ name patterns

### 5. **Today's "Surgical Fixes"**
- **Mathematician**: 95.63% (700/732) ↓ -1.64% from original
- **Diverse**: 43.5% (87/200) ↓ -37% from original!
- **Method**: Attempted to fix variant map systematically
- **Issues**:
  - Added conflicting mappings (중,jung vs 정,jung)
  - Broke existing working mappings
  - Lost track of what was already working

## Critical Analysis: What Went Wrong?

### 1. **Fixing What Wasn't Broken**
The original v6 at 97%/80% was already excellent. Instead of preserving this success, we:
- Added unnecessary complexity
- Introduced new points of failure
- Lost sight of the working baseline

### 2. **Complexity Creep**
Each "improvement" added layers:
- Position-aware tags → mapping conflicts
- Beam search → probabilistic errors
- Corpus data → irrelevant patterns
- Today's fixes → compounded conflicts

### 3. **Lack of Regression Testing**
We didn't systematically test that each change maintained baseline performance before moving forward.

### 4. **Misunderstanding the Problem**
- Korean romanization is NOT a probabilistic problem
- It's a data quality problem
- The original surgical fixes understood this

## Key Discoveries & Insights

### What Actually Works:
1. **Direct variant mappings**: `희찬,heuichan` ✓
2. **Simple surname mappings**: `이,lee,SURNAME_0` ✓
3. **Targeted compound fixes**: `순신,sunsin` ✓
4. **One-to-one syllable mappings**: Clear and unambiguous

### What Doesn't Work:
1. **Position-aware complexity**: Too many edge cases
2. **Probabilistic approaches**: Korean names aren't statistical
3. **General corpus data**: Names follow different patterns
4. **Overlapping mappings**: Cause priority conflicts

### Critical Technical Insights:
1. **Segmentation matters**: `sangil` → `['san', 'gil']` vs `['sang', 'il']`
2. **Tokenization is crucial**: Hyphen handling affects everything
3. **FST weights are fragile**: Small changes → big impacts
4. **Variant map order matters**: Later entries override earlier ones

## Reversion Attempt Results

### What We Discovered:
After reverting to what we believed was the original v6:
- **Mathematician**: 92.62% (678/732) - NOT the expected 97.27%
- **Diverse**: 30.00% (60/200) - NOT the expected 80.5%

### Key Issues Found:
1. **Tokenizer bug**: Had `\\s` instead of `\s` in regex, breaking space handling
2. **Import path issues**: Fixed with proper `_BASE_DIR` handling
3. **Missing mappings**: Still missing critical variant mappings like:
   - 류 → Ryu (maps to 유 instead)
   - 연아 → YuNa (maps to 유나 instead)
4. **Spacing issues**: "안 대훈" expected but getting "안대훈"

### Critical Realization:
**The "original v6" we reverted to was NOT the actual 97% version.** Either:
1. The 97% claim was incorrect, OR
2. We're missing critical configuration/data files, OR
3. The true working version was lost in the numerous iterations

## Sustainable Path Forward

### Immediate Actions:
1. **Accept current state** (92.62%/30%) as new baseline
2. **Document exact issues** preventing 97%/80%
3. **Create minimal fix plan** targeting specific failures

### Recommended Fixes for Next Agent:

#### Priority 1: Critical Variant Mappings
Add these to variant_map.csv:
```csv
류,ryu,
연아,yuna,
년,nyeon,
석열,seokyeol,
상일,sangil,
```

#### Priority 2: Spacing Rules
The mathematician dataset expects spaces in certain names:
- "안 대훈" not "안대훈"
- Need to understand the spacing convention

#### Priority 3: Segmentation Issues
Fix syllable segmentation for:
- "sangil" → should be ['sang', 'il'] not ['san', 'gil']
- Add missing syllables to rr_syllable_map.csv

## Questions & Doubts for Next Agent

1. **Was 97% Ever Real?** 
   - Documentation claims 97.27% but we can't reproduce it
   - Current "original" achieves only 92.62%
   - Were additional files/configs lost?

2. **Diverse Dataset Complexity**
   - 30% is very low - suggests fundamental mapping issues
   - Many celebrity/athlete names with non-standard romanizations
   - May need name-specific exceptions

3. **Beam Search Paradox**
   - The "broken" beam search version (95.63%) outperformed 
   - the "original" (92.62%) on mathematicians
   - Should we reconsider beam search with better data?

4. **Configuration Mystery**
   - Are we missing critical configuration files?
   - Was there a different variant_map.csv that achieved 97%?
   - Check git history for lost commits?

## Final Recommendations

### For the Next AI Agent:

1. **Start Fresh Assessment**
   - Run accuracy test on current state
   - Document EXACT current performance
   - Don't trust historical claims without verification

2. **Incremental Improvements Only**
   - Fix one specific issue at a time
   - Test after EVERY change
   - Never go below current baseline

3. **Focus on Data Quality**
   - Variant mappings are KEY
   - Most failures are data issues, not algorithm issues
   - Study the specific failures systematically

4. **Avoid Complexity Traps**
   - No beam search unless data quality is perfect
   - No corpus-based approaches for names
   - No position-aware systems until basics work

5. **Document Everything**
   - Keep accuracy logs after every change
   - Track which mappings help/hurt
   - Maintain regression test suite

## Technical Notes for Implementation

### Current Working State:
- Converter: src/converter.py (original v6 style)
- Variant map: resources/variant_map.csv (restored from .bak)
- Tokenizer: Fixed `\s` regex bug
- Imports: Fixed path issues with _BASE_DIR

### Known Issues to Fix:
1. Missing 류,ryu mapping
2. Wrong 연아 mapping (should map to YuNa not 유나)
3. Spacing convention for mathematician names
4. Segmentation issues (sangil, seokyeol, etc)

## Conclusion

This journey from 97% to 92% (with a detour through 95% and 43%) illustrates a fundamental principle: **complexity is the enemy of reliability**. The Korean converter's best performance came from simple, direct data mappings, not sophisticated algorithms.

The next agent should resist the temptation to add clever features and instead focus on understanding and fixing the specific data quality issues that prevent the simple approach from achieving its full potential.

Remember: Korean name romanization is a **mapping problem**, not a **modeling problem**.

#### For Mathematician Dataset (97% → 99%):
1. The 21 failures are likely edge cases
2. May include inherent ambiguities
3. Consider if 97% is the practical ceiling

### Architecture Recommendations:
1. **KISS Principle**: Keep it simple
2. **Data > Algorithms**: Fix the data, not the code
3. **Test Everything**: Every change needs full regression test
4. **Version Control**: Keep working versions safe

## Questions & Doubts for Discussion

### 1. **Is 97%/80% the realistic ceiling?**
Some failures might be inherently ambiguous or have multiple valid answers.

### 2. **Should we handle spaces differently?**
The `안대훈` vs `안 대훈` issue affects accuracy counting but not actual conversion quality.

### 3. **Are we solving the right problem?**
Maybe round-trip accuracy isn't the best metric for real-world usage.

### 4. **Version control strategy?**
How do we prevent future regressions while allowing experimentation?

## Document Cleanup Recommendations

### Keep (Core Documents):
1. `KOREAN_V6_FINAL_SUMMARY.md` - High-level overview
2. `README_FINAL_V6.md` - Implementation guide
3. `KOREAN_V6_COMPLETE_JOURNEY_ANALYSIS.md` - This document
4. `converter_v6.py` - Original working implementation

### Archive (Journey Documents):
1. Position-aware attempts: `POSITION_AWARE_*.md`
2. Beam search attempts: `BEAM_SEARCH_*.md`
3. Auto-fix attempts: `AUTO_FIX_*.md`
4. Intermediate analyses: `FAILURE_ANALYSIS_*.md`

### Delete (Obsolete):
1. Working documents: `HANDOFF_*.md`, `HANDOVER_*.md`
2. Failed attempts: `SURGICAL_REPAIR_*.md`
3. Intermediate status: `*_STATUS.md`

## Conclusion

The journey from 97%/80% to 95.63%/43.5% is a textbook case of how "improvements" can degrade a working system. The original v6's simple, data-driven approach was correct. Future work should:

1. Start from the working v6 baseline
2. Make minimal, tested changes
3. Preserve what works
4. Accept that 97%/80% might be excellent enough

**Key Lesson**: Sometimes the best improvement is to stop improving.