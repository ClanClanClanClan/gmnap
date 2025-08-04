# Korean v6 Documentation

## Current Status
- **Mathematician Dataset**: 92.62% (678/732)
- **Diverse Dataset**: 30.00% (60/200)
- **Configuration**: Original v6 (simplified, no beam search)

## Key Documents

### Core Documentation
- [Implementation Status](core/KOREAN_V6_IMPLEMENTATION_STATUS.md) - Current system status
- [Journey Analysis](core/KOREAN_V6_COMPLETE_JOURNEY_ANALYSIS.md) - Comprehensive lessons learned
- [Final Summary](core/KOREAN_V6_FINAL_SUMMARY.md) - Technical implementation details
- [Reversion Guide](core/REVERT_TO_ORIGINAL_V6.md) - How to revert to original v6

### Quick Start
1. Read the Journey Analysis to understand what works/doesn't work
2. Check Implementation Status for current configuration
3. Run `python3 test_accuracy.py` to verify current performance
4. Make incremental improvements following guidelines in Journey Analysis

### Archive
- `archive/journey/` - Development history and analysis
- `archive/experiments/` - Failed improvement attempts
- `archive/handoffs/` - AI agent communication documents

## Important Notes
- The claimed 97% accuracy could not be reproduced
- Beam search and corpus approaches decreased performance
- Simple variant mappings are the key to improvement
- Test after EVERY change to avoid regression
