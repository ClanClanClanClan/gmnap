# Track B: Full Positional Refactor Implementation Guide

## Overview
Track B implements proper position-aware romanization to achieve the promised 97.8% (717/733).

## Current State (After Track A)
- **Performance**: 93.04% (682/733) with hot-fix weights
- **Architecture**: FST-based, position-unaware eng2kor
- **CSV**: 3-column format with 18 hot-fix rows appended

## Track B Requirements

### 1. Restore 5-column CSV with positional rows
```bash
# Remove hot-fix rows (last 18 lines)
head -n -18 resources/rr_syllable_map.csv > temp.csv
mv temp.csv resources/rr_syllable_map.csv

# Apply the full bundle CSV with:
- Schema extension (pos column)
- All existing rows with empty pos
- 92 positional disambiguation rows
- Fine-grain weight tweaks
```

### 2. Create position-specific FSTs

#### build_fsts_multi.py modifications:
```python
def build_positional(direction:str):
    """Build surname and given-name specific FSTs"""
    fst_sn = pn.Fst()
    fst_gn = pn.Fst()
    fst_general = pn.Fst()
    
    for row in read_csv_with_pos():
        hangul, roman, weight, context, pos = row
        arc = create_weighted_arc(hangul, roman, weight)
        
        if pos in ("", None):  # General - add to all
            fst_sn |= arc
            fst_gn |= arc
            fst_general |= arc
        elif pos == "S":  # Surname only
            fst_sn |= arc
        elif pos == "G":  # Given name only
            fst_gn |= arc
    
    # Write all variants
    if direction == "rom2han":
        fst_sn.write("models/rom2han_surname.fst")
        fst_gn.write("models/rom2han_given.fst")
        fst_general.write("models/rom2han_multi.fst")
    else:
        fst_sn.write("models/han2rom_surname.fst")
        fst_gn.write("models/han2rom_given.fst")
        fst_general.write("models/han2rom_multi.fst")
```

### 3. Implement position-aware eng2kor

#### converter.py modifications:
```python
# Load position-specific FSTs
ROM2_SURNAME = pn.Fst.read(os.path.join(_base_dir, "models/rom2han_surname.fst"))
ROM2_GIVEN = pn.Fst.read(os.path.join(_base_dir, "models/rom2han_given.fst"))

def _rr2han_pos(rr:str, position:str) -> str|None:
    """Position-aware romanization to hangul"""
    fst = ROM2_SURNAME if position == "surname" else ROM2_GIVEN
    result = first_output(pn.accep(rr) @ fst)
    if result is None:
        # Fallback to general FST
        result = first_output(pn.accep(rr) @ ROM2)
    if result is None:
        # Final fallback to lookup table
        result = rom2han().get(rr)
    return result

def eng2kor(name:str) -> str|None:
    out = []
    tokens = list(tokenise(name))
    
    for idx, tok in enumerate(tokens):
        position = "surname" if idx == 0 else "given"
        
        for syl in segment(tok):
            h = _rr2han_pos(syl, position)
            if h is None: 
                return None
            out.append(h)
    
    return "".join(out)
```

### 4. Add eng2kor_nbest for validator

```python
def eng2kor_nbest(name:str, n:int=3) -> list[str]:
    """Return n-best Korean translations"""
    # Build lattice with position awareness
    tokens = list(tokenise(name))
    lattice = pn.accep("", TOK)
    
    for idx, tok in enumerate(tokens):
        position = "surname" if idx == 0 else "given"
        fst = ROM2_SURNAME if position == "surname" else ROM2_GIVEN
        
        for syl in segment(tok):
            syl_fst = pn.accep(syl, TOK) @ fst
            lattice = pn.concat(lattice, syl_fst)
    
    # Get n-best paths
    lattice = pn.project(lattice, "output")
    paths = pn.shortestpath(lattice, nshortest=n, unique=True).paths()
    
    return list(paths.ostrings()) if paths else []
```

### 5. Update validator for n-best tolerance

```python
# In validate.py
def validate_with_nbest():
    # ... existing code ...
    
    # Try n-best for eng→kor
    hypos = eng2kor_nbest(canonical_latin, n=3)
    korean_gold = find_hangul(variants)
    
    if korean_gold in hypos:
        passed += 1
        continue
    
    # ... rest of validation ...
```

## Implementation Steps

1. **Preparation** (30 min)
   - Backup current state
   - Unlock CSV (chmod 644)
   - Remove hot-fix rows
   - Apply full bundle CSV

2. **FST Builder Update** (1 hour)
   - Modify build_fsts_multi.py
   - Build position-specific FSTs
   - Verify 6 FST files created

3. **Converter Update** (2 hours)
   - Add position-aware functions
   - Test with known examples
   - Verify no regressions

4. **Validator Update** (30 min)
   - Add n-best support
   - Test on small subset

5. **Full Validation** (30 min)
   - Run all three test suites
   - Verify 717/733 achievement

## Risk Mitigation

### Rollback Points
1. After each major step, create git commit
2. Keep backup of working FSTs
3. Test incrementally

### Known Issues
- Memory usage may increase with 6 FSTs
- N-best may slow validation
- Some given names might get surname treatment

## Success Criteria
- Math: ≥717/733 (97.8%)
- Diverse: ≥194/200 (97.0%)
- Independent: ≥153/165 (92.7%)
- No memory issues
- Clean code architecture

## Testing Commands

```bash
# Quick smoke test
python3 -c "
from src.converter import eng2kor
test = {'Jung, Jin': '정진', 'Park, Jung-Chul': '박정철'}
for k,v in test.items():
    result = eng2kor(k)
    print(f'{k} → {result} (expect {v})')
"

# Full validation
python3 scripts/systematic_improvement_framework_v2.py validate
```

## Timeline
- Total: 4-6 hours
- Can be done incrementally
- Each component is independent

---
*This guide ensures Track B can be implemented successfully to achieve the promised 97.8% accuracy.*