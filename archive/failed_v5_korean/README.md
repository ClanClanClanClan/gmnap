# Failed Korean v5 Implementation Archive

## WARNING: This Implementation Does Not Work

This directory contains the archived Korean v5 implementation that **failed to achieve its promised accuracy**.

### Key Failures:
- **Claimed**: ≥97% round-trip accuracy
- **Actual**: 34-72% accuracy (varies by test set)
- **Output**: Produces corrupted mixed Hangul/Latin text
- **Status**: SYSTEM FAILURE - DO NOT USE

### What's Archived Here:
- Original v5 source code showing the flawed approach
- Misleading documentation claiming false success rates
- Test results proving the system failure
- FST models that produce incorrect conversions

### Lessons Learned:
1. Always verify accuracy claims with actual tests
2. Mixed-script output indicates fundamental encoding issues
3. Complex weighted multi-system approaches can mask core failures
4. Documentation must reflect actual system performance

### Moving Forward:
Korean converter v6 is being implemented from scratch with:
- Clean architecture
- Verified PyNini 2.1.5 compatibility
- Actual ≥97% accuracy validation
- Honest documentation

---
*Archived: 2025-07-24*
*Reason: System failure - does not meet accuracy requirements*
*Do not resurrect this code*