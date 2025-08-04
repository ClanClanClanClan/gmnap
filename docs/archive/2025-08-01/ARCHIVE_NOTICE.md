# Korean v5 Implementation Archive Notice

## Status: ARCHIVED DUE TO FAILURE

The Korean v5 implementation has been investigated and found to be fundamentally broken:

### Investigation Results:
- **Claimed accuracy**: ≥97% round-trip
- **Actual accuracy**: 34-72% (depending on test set)
- **Critical flaw**: Produces mixed Hangul/Latin output (e.g., "안휴nkyu")
- **Documentation**: Contains false and contradictory accuracy claims

### What Was Done:
1. Created fraud investigation report documenting the failures
2. Archived warning in `/archive/failed_v5_korean/`
3. Original files remain in `/Users/dylanpossamai/Dropbox/Work/Maths/gmnap/` for reference

### Next Steps:
- Implement Korean v6 from scratch in `/components/korean_v6/`
- Follow the clean 8-section implementation plan
- Validate actual ≥97% accuracy before any claims
- Maintain honest documentation throughout

### Do Not:
- Use any v5 code as a base
- Trust v5 documentation claims
- Attempt to "fix" the v5 implementation

The v5 system is fundamentally flawed and should be considered a learning experience only.

---
*Date: 2025-07-24*
*Action: Korean v5 marked as failed, v6 implementation to proceed*