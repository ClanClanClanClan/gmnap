# Forensic Cleanup Results

## Executive Summary

Implemented the forensic cleanup patch to fix tagless entries in variant_map.csv. Results improved from the catastrophic 32% but fell short of predictions.

## Current Results vs Predictions

| Dataset | Predicted | Actual | Gap |
|---------|-----------|---------|-----|
| **Mathematician** | ~98% (718±1) | **96.32%** (706/733) | -1.68pp |
| **Diverse** | 92-94% (184-188) | **85.00%** (170/200) | -8pp |

## What Was Fixed

### 1. Tagless Entry Cleanup
- Fixed variant loader to ignore commented entries with `h.startswith("#")`
- All tagless legacy entries properly commented out
- Audit script confirms: "Tag-less rows: 0"

### 2. Mapping Corrections
- jung → 정 for both surname and given positions (not 중)
- sun → 선 for given position (was 순)
- Rebuilt FSTs after all changes

## Remaining Issues

### 1. Position Rule Conflicts
The diverse dataset reveals fundamental conflicts with position rules:
- **jung**: Some given names need 중, not 정 (Random_008: 강진중)
- **hun/heon**: Some names need 헌, not 훈 (Random_048: 심헌철)

### 2. Special Cases Not Handled
- Historical figure "An Jung-Geun" (안중근) needs special 중 mapping
- English names fail roundtrip (David, Sarah, Grace)
- Some compounds not recognized (ChunHyang: 춘향→전향)

### 3. Architecture Limitations
The position-aware system assumes binary rules (surname vs given) but Korean naming patterns are more complex:
- Same romanization can map differently based on context
- Historical/modern usage differs
- Personal preference variations exist

## Failure Analysis

### Most Common Patterns (30 failures):
1. **중/정 conflicts**: 8 cases (26.7%)
2. **헌/훈 conflicts**: 4 cases (13.3%)
3. **English names**: 8 cases (26.7%)
4. **Other mappings**: 10 cases (33.3%)

### By Category:
- Politics: 71.4% accuracy (lowest)
- Business: 75.0% accuracy
- Other: 84.9% accuracy

## Why Results Fell Short

### 1. Dataset Differences
The mathematician dataset may have different naming conventions than the diverse dataset, making position rules that work for one fail for the other.

### 2. Oversimplified Position Rules
The binary surname/given distinction doesn't capture the full complexity of Korean romanization preferences.

### 3. Competing Requirements
Optimizing for one dataset (mathematicians) degraded performance on another (diverse), suggesting fundamental conflicts in the data.

## Recommendations

### Option 1: Accept Current Results
- 96.32% mathematician accuracy is very good
- 85% diverse accuracy is reasonable given complexity
- Position system works but has limitations

### Option 2: Dataset-Specific Tuning
- Maintain separate variant maps for different domains
- Use weighted voting across multiple strategies

### Option 3: Revert to Simpler System
- Remove position awareness
- Focus on high-frequency corrections only
- May achieve better balanced results

## Technical Details

### Current Variant System
```python
# Correctly ignores commented entries
if not r or r.startswith("#") or h.startswith("#"):
    continue

# Position-based selection with fallbacks
key_order = ["SURNAME_0", "GIVEN_0", ""]
```

### Key Mappings
- jung: SURNAME_0→정, GIVEN_0→정, HISTORIC_1→중
- sun: GIVEN_0→선, RARE_0→순
- chang: SURNAME_0→장, GIVEN_0→창

## Conclusion

The forensic cleanup successfully fixed the catastrophic failure mode (32% → 85%) but revealed fundamental limitations in the position-aware approach. The gap between predicted and actual results suggests the position rules derived from one dataset don't generalize well to diverse Korean names.