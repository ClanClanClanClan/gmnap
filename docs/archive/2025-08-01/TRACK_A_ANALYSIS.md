# Track A Hot-Fix Analysis

## Current Status
- **Expected**: 712/733 = 97.13%
- **Actual**: 682/733 = 93.04%
- **Gap**: 30 passes missing

## Findings

### 1. Hot-fix weights ARE being applied correctly
All test cases show correct character selection:
- Jung → 정 ✓
- Park → 박 ✓
- Jun → 준 ✓
- Seok → 석 ✓

### 2. Missing hot-fix entries
The 18 hot-fix weights don't cover all problematic cases:
- **춘 (Chun)**: No hot-fix weight, but has failures (Chun_Youngsup, Chun_MiYoung)
- **이 (Lee)**: Complex variations causing roundtrip failures

### 3. Weight calibration mismatch
The dossier claims weights were "re-fitted on your 733-name corpus" but:
- May have assumed different baseline CSV
- May have included additional entries not in the 18-row list
- Grid search parameters not provided

## Hypothesis
The 97.13% promise assumed either:
1. A different baseline CSV state
2. Additional hot-fix rows beyond the 18 listed
3. Different existing weights in the base CSV

## Next Steps

### Option 1: Debug missing cases
Identify the 30 failing names and add targeted hot-fix weights

### Option 2: Proceed with Track B
Since Track A isn't achieving promised results, implement full positional refactor

### Option 3: Accept 93.04% 
Already exceeds v7 minimum (≥97% on diverse dataset achieved)

## Recommendation
Given that:
- We have 98% on diverse dataset (exceeds requirement)
- Math dataset at 93.04% is close to baseline
- Track A didn't deliver promised improvement

**Recommend proceeding directly to Track B** for proper positional implementation.