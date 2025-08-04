# Korean Converter v6 Implementation Plan
**Part of GMNAP v7 Project Specifications**

## Purpose
Create a Korean name converter achieving ≥97% round-trip accuracy using PyNini FSTs with a clean, maintainable codebase.

## Key Improvements over Previous Attempts
- **Version Stability**: Hard-pinned PyNini 2.1.5 + OpenFST 1.8.3 to avoid version conflicts
- **API Compatibility**: Replaced deprecated `pn.acceptor` with `pn.accep` 
- **Dependency Management**: Pure Python DICE calculation to avoid RapidFuzz API changes
- **Self-Contained**: Internal CSV generation eliminating external download dependencies
- **Segmentation Fix**: Added 5 critical long-tail syllables to fix segmentation holes
- **Clean Architecture**: Canonical folder structure with clear separation of concerns
- **Testing**: Single-line test snippets compatible with zsh

## Target Folder Structure
```
gmnap_kor_v6/
├── env.yml                    # Conda environment manifest
├── resources/                 # Data files only
├── models/                    # Compiled FST binaries  
├── scripts/                   # One-off generators/validators
├── src/                       # Importable Python modules
└── korean.yaml                # Ground truth test data
```

## Implementation Steps

### 0. Environment Bootstrap (Option A - Recommended)
```bash
conda create -n korenv python=3.12 -y
conda activate korenv
conda install -c conda-forge pynini=2.1.5 openfst=1.8.3 rapidfuzz pandas scikit-learn pyyaml regex tqdm -y
```

### 1. Resource Generation
- Generate 11,172 Hangul syllables with Revised Romanization mapping
- Add 5 critical long-tail syllables: ahn, cheol, hwan, kim, young
- Create common tokens for segmentation

### 2. Core Modules
- `fst_utils.py`: Path-safe FST string extraction
- `syllable_lexicon.py`: Syllable validation lexicon
- `segment.py`: Dynamic programming segmentation
- `lookup.py`: Cached ROM→HAN dictionary
- `preprocess.py`: Name tokenization
- `converter.py`: Main eng2kor/kor2eng functions

### 3. Success Criteria
- Forward: `eng2kor("Kim Young Soo")` → `"김영수"` ✅
- Back: `kor2eng("김영수")` → `"kim young soo"` ✅ 
- Validation: `scripts/validate.py` prints ≥97% ✅

## Integration with GMNAP v7
This Korean converter will be integrated as a core component of the Global Mathematician Authority Project v7, providing accurate Korean name conversion for the mathematician database.

## Critical Implementation Notes
- Follow steps exactly without deviation
- Copy-paste all code verbatim 
- If validation < 97%, add missing syllables to CSV and rebuild FSTs
- All test snippets use heredoc format compatible with zsh

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| ModuleNotFoundError: pynini | Missing conda activate korenv |
| ImportError: openfst_python | Rerun conda install step |
| Segmentation merges names | Verify 5 extra rows in CSV |
| Validation < 97% | Add missing syllables to CSV |