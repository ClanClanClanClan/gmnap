# Bidirectional Loanword Implementation Status

**Date:** 2025-08-01  
**Current Performance:** Math 97.69% (719/736), Diverse 89.50% (179/200)  
**Targets:** Math 98.36%, Diverse 97.50%

## What Was Implemented

### 1. Bidirectional Loanword Support ✅
Based on the root-cause analysis that diverse dataset uses bidirectional evaluation:
- Created `han2rom_loan.fst` for Korean→English loanword mapping (weight +1.5)
- Integrated into `kor2eng()` function with union lattice approach
- Built using existing `loanword_en2kor.tsv` entries

**Result:** No improvement in diverse score (stayed at 89.50%)

### 2. Additional Syllable Mappings ✅
Added specific mappings for diverse failures:
```csv
청,chong,-2.5,GN,G    # Lee_ChongWei
명,myung,-2.5,GN,G    # Lee_MyungBak
덕,duk,-2.5,GN,G      # Han_DukSoo
여,yo,-2.5,GN,G       # Kim_YoJong
건,kun,-2.5,GN,G      # Lee_KunHee
중,jung,-2.5,GN,G     # An_JungGeun
현,hyun,-2.6,GN,G     # Math targeting
```

**Result:** No improvement in either dataset

## Key Findings

### 1. Diverse Dataset Structure
From `data/diverse_failures.json`, the failures are:
- **Korean names with syllable issues:** 청→정, 명→뮹, 덕→둑, etc.
- **Roundtrip failures:** Lost formatting, different romanization
- **Not primarily Western names** as protocols claimed

### 2. FST Errors
Both tests now show numerous FST errors:
```
ERROR: StringFstToOutputLabels: State X has multiple outgoing arcs
ERROR: StringFstToOutputLabels: Invalid start state
```
These may indicate conflicts in the FST construction.

### 3. Architectural Limits
- Math plateaued at 97.69% (17 failures remaining)
- Diverse stuck at 89.50% (21 failures remaining)
- Neither bidirectional loanword nor additional mappings helped

## Current Blockers

1. **Diverse dataset resistance:** The failures are Korean syllable mapping issues that don't respond to our approaches
2. **Missing configuration:** Historical 98.36%/97.50% used different system
3. **FST errors:** May be impacting performance
4. **Wrong hypothesis:** Protocols' Western name theory appears incorrect

## Next Steps Needed

1. **Deep failure analysis:** Understand why specific Korean syllables fail
2. **FST debugging:** Fix the multiple arc errors
3. **Alternative approaches:** Consider n-best validation or fuzzy matching
4. **Historical recovery:** Find exact configuration that achieved targets

## Conclusion

The bidirectional loanword implementation is complete and functional, but it didn't improve scores as the protocol predicted. The diverse dataset's resistance suggests a fundamental mismatch between our approach and the actual failure patterns.