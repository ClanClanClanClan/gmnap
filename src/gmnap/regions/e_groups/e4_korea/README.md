# E4 Korea Regional Module - GMNAP v6.1

## Overview

This is the **E4 Korea regional processor** for the Global Mathematician Name Authority Project (GMNAP) v6.1. It handles Korean mathematician names with ≥97% round-trip accuracy as required by the v6.1 specifications.

## Quick Start

```bash
# 1. Navigate to E4 module
cd src/gmnap/regions/e_groups/e4_korea

# 2. Setup environment  
conda create -n korenv python=3.12 -y && conda activate korenv
conda install -c conda-forge pynini=2.1.5 openfst=1.8.3 rapidfuzz pandas scikit-learn pyyaml regex tqdm -y

# 3. Build resources and models
python scripts/make_rr_table.py
python scripts/build_fsts.py

# 4. Validate accuracy
python scripts/validate.py
# Expected: ≥97% round-trip accuracy

# 5. Test integration
python -c "from converter_v6 import KoreanConverterV6; c=KoreanConverterV6(); print(c.english_to_korean('Kim Young'))"
# Expected: 김영
```

## Documentation

- **[Complete Setup Guide](KOREAN_V6_COMPLETE_SETUP_GUIDE.md)** - Detailed step-by-step implementation
- **[Implementation Status](KOREAN_V6_IMPLEMENTATION_STATUS.md)** - Current status and features
- **[Implementation Plan](KOREAN_CONVERTER_V6_IMPLEMENTATION_PLAN.md)** - Original v6 plan
- **[V5 Fraud Investigation](KOREAN_V5_FRAUD_INVESTIGATION.md)** - Why v5 was replaced

## Architecture

```
e4_korea/
├── converter_v6.py      # GMNAP-compatible converter class
├── processor.py         # E4 regional processor (pipeline integration)
├── data/               # Test datasets (736 mathematicians)
├── resources/          # Generated syllable mappings
├── models/            # Compiled FST binaries
├── src/               # Core conversion modules
├── scripts/           # Build and validation tools
└── tests/             # Unit tests
```

## GMNAP v6.1 Compliance

- **Region Code**: E4 (Korea)
- **ISO Territories**: KR, KP
- **Primary Scripts**: Hangul, Hanja
- **Linguistic Rules**: 
  - Rule 11: CJK Round-Trip ≥97% accuracy (Dice coefficient)
  - Rule 13: Korean Hyphen/space variation handling
- **Quality Gate**: `roundtrip_script_rate: {threshold: 0.97}`

## Features

- ✅ **Bidirectional conversion**: English ↔ Korean
- ✅ **≥97% accuracy**: Validated on 736 mathematician dataset
- ✅ **2025-proof**: PyNini 2.1.5 + OpenFST 1.8.3 compatibility
- ✅ **Self-contained**: No external dependencies
- ✅ **GMNAP integration**: Plugs into stage 3 (RegionHooks)
- ✅ **Future-proof maintenance**: Add syllables without code changes

## Integration

```python
from converter_v6 import KoreanConverterV6

converter = KoreanConverterV6()
korean = converter.english_to_korean("Kim Young Soo")  # "김영수"
english = converter.korean_to_english("김영수")         # "kim young soo"
accuracy = converter.validate_round_trip("Kim Young Soo")  # ≥0.97
```

## Status

- **Implementation**: ✅ Complete
- **Testing**: ✅ Unit tests pass
- **Validation**: ✅ ≥97% accuracy achieved  
- **GMNAP Integration**: ✅ Ready for pipeline
- **Production Ready**: ✅ Deployed as E4 regional module

---

**GMNAP v6.1 Regional Module E4 Korea**  
*Part of the Global Mathematician Name Authority Project*