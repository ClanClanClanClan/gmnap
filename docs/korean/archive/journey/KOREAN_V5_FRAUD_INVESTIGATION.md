# Korean v5 Implementation - Fraud Investigation Report

## Executive Summary

The Korean v5 implementation claims to achieve ≥97% round-trip accuracy but actually delivers between 34-72% accuracy with severely broken output. The documentation contains contradictory and misleading claims about system performance.

## Investigation Findings

### 1. Contradictory Accuracy Claims

The documentation makes wildly different claims:
- **V5_ACCURACY_SUMMARY.md**: "28.14% average similarity"
- **HONEST_V5_AUDIT.md**: "99.6% accuracy (733/736 conversions)"
- **V5_KOREAN_IMPLEMENTATION_STATUS_FINAL.md**: "≥97% round-trip accuracy"
- **Actual test results**: 34-72% accuracy

### 2. Broken Implementation

#### Missing Promised Functions
- Documentation promises `eng2kor()` and `kor2eng()` functions
- Actual code has `convert_word()`, `convert_text()`, `romanize_to_hangul_candidates()`
- No clean API as specified

#### Corrupted Output
The converter produces mixed Hangul/Latin output:
```
"An Kyu" → "안휴nkyu" (should be "안규")
"Kim Young Soo" → "킴영수" (incorrect romanization)
```

### 3. Test Results vs Claims

| Test File | Claimed Accuracy | Actual Result |
|-----------|-----------------|---------------|
| V5_ACCURACY_SUMMARY.md | 28.14% | Matches reality |
| HONEST_V5_AUDIT.md | 99.6% | **FALSE** - actual is ~34% |
| validation_report.txt | N/A | 34/100 passed (34%) |
| test_v5_accuracy.py | N/A | 71.92% similarity |

### 4. What Actually Exists

#### Working Components
- FST model files (korean_simple.fst, roman2hangul.fst, etc.)
- Test dataset with 736 Korean mathematicians
- Complex multi-system weighted converter architecture

#### Broken Components
- Mixed script output (Hangul + Latin characters)
- Incorrect romanization mappings
- Failed round-trip conversions
- Accuracy far below 97% threshold

## Conclusion

The Korean v5 implementation is a **failed system** that:
1. Does not meet the ≥97% accuracy requirement
2. Produces corrupted mixed-script output
3. Has misleading documentation claiming false success
4. Should not be used in production

## Recommendation

1. **Archive** the entire v5 implementation as a failed attempt
2. **Document** the failure honestly for future reference
3. **Implement** Korean v6 from scratch following the clean specifications
4. **Never claim** false accuracy metrics

---
*Investigation Date: 2025-07-24*
*Investigator: Claude Code*
*Result: SYSTEM FAILURE CONFIRMED*