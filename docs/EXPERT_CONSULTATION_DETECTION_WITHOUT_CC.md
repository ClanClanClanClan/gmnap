# Expert Consultation: Region Detection Without Country Codes

## Problem Statement

GMNAP's region detection achieves 100% accuracy when `CountryCodes` are provided (simple dictionary lookup), but only **40-60% accuracy** when detecting from name alone. For a system processing millions of mathematician names — many of which lack country metadata — this is insufficient.

## System Architecture

The detection cascade (in `src/regions/manager_optimized.py`) tries these methods in order:

1. **CountryCodes** (if provided) → 0.85 confidence, dictionary lookup → **100% accurate**
2. **Authority cache** (if OFFLINE=0) → cached from prior enrichment
3. **ML ensemble** (if fasttext model available) → language detection
4. **Surname patterns** → exact match against surname pools per region
5. **Script analysis + priority rules** → Unicode script + lexical scoring
6. **ICU processing** → locale-based analysis
7. **FastText language** → n-gram language classification
8. **Fallback** → R0 (residual)

Most names fall through to step 5 (script analysis + priority rules), which is where the problems are.

## The Scoring Function (`_score_priority_rules`)

For each candidate region, the scorer assigns points based on:

| Signal | Weight | Example |
|--------|--------|---------|
| Exact surname match | 5.0 | "smith" → A1 |
| Given name fragment | 3.0 | "david" → A1, "jean" → A2 |
| Surname suffix | 2.5 | "-ov" → B1, "-opoulos" → B3 |
| Surname prefix | 3.0 | "o'" → A1, "mac" → A1 |
| Hyphenated given | 2.5 | "jae-in" → E4 |

The region with the highest total score wins.

## Root Cause Analysis

### Problem 1: Given names are cross-regional but treated as strong signals

"David" is common in English (A1), German (A2), French (A2), Hebrew (C6), Spanish (G1). But the system assigns it exclusively to A1 with weight 3.0. This causes:

- "David Hilbert" (German, A2) → detected as A1 because "david" is an A1 given_frag
- "Alexander Grothendieck" (German/French, A2) → detected as B1 because "alexander" is a B1 given_frag

**Concrete data from MGP validation:**

| Name | Expected | Detected | Reason |
|------|----------|----------|--------|
| David Hilbert | A2 (DE) | A1 | "david" → A1 given_frag (3.0) |
| Emmy Amalie Noether | A2 (DE) | C4 | "amalie" contains "amal" → C4 given_frag (3.0) |
| Alexander Grothendieck | A2 (FR/DE) | B1 | "alexander" → B1 given_frag (3.0) |
| Srinivasa Ramanujan | D1 (IN) | D2 | "srinivasa" → D2 given_frag (3.0) |
| Stefan Banach | B2 (PL) | A2 | No pattern match, falls to script default |
| A. Avila | G1 (BR) | C3 | No pattern match, falls to script default |

### Problem 2: No negative/disambiguation signals

The system has positive signals (name matches region X) but no negative signals (name does NOT match region Y). For example:
- "Hilbert" does not match any A1 surname — this should weaken the A1 score
- "Grothendieck" has Germanic morphology (-dieck) — this should boost A2
- "Banach" is a distinctly Polish surname — but it's not in B2's surname list

### Problem 3: Script analysis default is arbitrary for Latin

When no pattern matches, `_detect_by_script()` returns a default region for Latin script. This is essentially random among Latin-script regions (A1, A2, A3, B2, G1, etc.). There's no "I don't know" fallback with low confidence.

### Problem 4: Surname pools are too small

Each region has 15-80 exact surnames. With millions of mathematicians, many surnames won't be in the pool. The suffix patterns help (e.g., "-ov" → B1) but only exist for some regions. Many Latin-script regions (A2, B2, G1) lack suffix patterns.

## Current Lexicon Statistics

| Region | Surnames | Suffixes | Given Frags | Detection Capability |
|--------|----------|----------|-------------|---------------------|
| A1 (Anglo) | 84 | 3 + prefixes | 46 | Good (large surname pool + prefixes) |
| A2 (Germanic) | 74 | 14 | 26 | Moderate (suffix -mann/-stein helps) |
| A3 (Nordic) | 46 | 5 | 29 | Good (-sson/-sen suffixes distinctive) |
| B1 (E. Slavic) | 31 | 13 | 27 | Good (-ov/-ev/-enko suffixes) |
| B2 (W. Slavic) | 40 | 17 | 24 | Moderate (-ski/-ová helps) |
| B3 (Hellenic) | 27 | 8 | 24 | Good (-opoulos/-ou distinctive) |
| C7 (Armenian) | 12 | 1 (-yan) | 12 | Good (-yan very distinctive) |
| C8 (Georgian) | 20 | 6 | 14 | Good (-dze/-shvili distinctive) |
| E3 (Japanese) | 36 | 8 | 21 | Good (large distinctive surname pool) |
| E4 (Korean) | 30 | 0 | 18 | Good (small surname pool = high recall) |
| G1 (Latin Am) | 28 | 6 | 15 | Moderate (-ez suffix helps) |
| D1 (Indian) | 21 | 0 | 19 | Weak (no suffixes, shared given names) |

## What Would Improve Accuracy

### Approach A: Reduce given_frag weight (Quick Fix, ~+10% accuracy)
Given names are cross-regional. Reducing their weight from 3.0 to 1.0 would prevent them from overriding stronger surname signals. Risk: some correct detections that rely on given names would lose confidence.

**Implementation:** Change line ~2279 in `_score_priority_rules()`:
```python
scores[r] += 1.0  # was 3.0
```

### Approach B: Cross-regional given name exclusion (Better Fix, ~+15%)
Instead of reducing weight globally, exclude given names that appear in 3+ regions from the scoring entirely. "David", "Alexander", "Maria" appear in many cultures and carry no regional signal.

**Implementation:** Build a set of ambiguous given names at startup, skip them in scoring.

### Approach C: Expand surname suffix patterns (Best Fix, ~+20%)
Add suffix patterns to regions that lack them:
- **B2**: `-ski`, `-owski`, `-czyk`, `-ová`, `-escu`, `-ević` (already partial)
- **G1**: `-ez`, `-illo`, `-eira`, `-ão` (Hispanic/Portuguese morphology)
- **D1/D2**: `-kar`, `-rthy`, `-nath`, `-wamy` (Indian morphology)
- **A2**: `-bauer`, `-hofer`, `-stein`, `-mann`, `-eux`, `-eau` (already partial, expand)

### Approach D: FastText/ML language detection (Most Accurate, ~+30%)
The system has a fasttext-based language detector but it's not loaded in most environments (model file `lid.176.bin` is 125MB). If loaded, it provides language → region mapping that's much more accurate than lexical patterns alone.

**Barrier:** The model isn't included in Docker builds due to size. Could be downloaded at startup or served separately.

### Approach E: Institution-based detection (High Accuracy for enriched data)
Many entries from OpenAlex/Crossref include institution affiliations ("ETH Zürich", "Université de Paris"). Institutions strongly imply country → region. The system already has `_detect_by_affiliation()` but it requires structured affiliation data, not free text.

**Implementation:** Add a free-text institution → country lookup table (top 500 universities → countries).

### Approach F: Combined ensemble with confidence threshold
Instead of winner-takes-all, combine multiple weak signals:
- Surname suffix match: +2 for region X
- Given name match: +1 for region Y (weighted down)
- Language detection: +3 for region Z
- Institution hint: +4 for region W

Return the region only if total score exceeds a threshold; otherwise return R0 (unknown) with low confidence. This is honest: "I don't know" is better than a wrong answer.

## Recommended Strategy

1. **Immediate (1 hour):** Reduce given_frag weight from 3.0 to 1.0 (Approach A)
2. **Short-term (1 day):** Expand surname suffix patterns for weak regions (Approach C)
3. **Medium-term (1 week):** Include fasttext model in deployment (Approach D)
4. **Long-term:** Institution lookup table + combined ensemble (Approaches E + F)

## Data for Expert Review

### Real MGP Failures (15 mathematicians)

```
✗ David Hilbert (DE)        → A1 because "david" is A1 given_frag
✗ Emmy Noether (DE)         → C4 because "amalie" starts with "amal" (C4 given_frag)
✗ Grothendieck (DE/FR)      → B1 because "alexander" is B1 given_frag
✗ Ramanujan (IN)            → D2 because "srinivasa" is D2 given_frag (should be D1)
✗ Banach (PL)               → A2 because no B2 pattern matches, Latin script default
✗ Avila (BR)                → C3 because no G1 pattern matches, Latin script default
```

### Working Detections (for comparison)

```
✓ Riemann (DE)              → A2 because "-mann" suffix matches A2
✓ Wiles (GB)                → A1 because "andrew", "john" are A1 given_frags
✓ Tao (CN/AU)               → E1 because "tao" is E1 surname, "shen" is E1 surname
✓ Serre (FR)                → A2 because "jean" is A2 given_frag
✓ Perelman (RU)             → B1 because "-evich" (patronymic) matches B1 suffix
✓ Mirzakhani (IR)           → C2 because "maryam" + "-ani" suffix match C2
```

### Key Insight

The failures all share one pattern: **a cross-regional given name (David, Alexander, Amalie) overrides the correct but unmatched surname**. The surname "Hilbert" has no match in any region's pattern pool, so the given name "David" (which happens to be in A1) wins by default.

The fix is either (a) make given names less influential, or (b) add more surname patterns so surnames win more often, or (c) use ML-based detection that doesn't rely on handcrafted lexicons.

## Files Reference

- Detection cascade: `src/regions/manager_optimized.py` (lines 3138-3250)
- Scoring function: `src/regions/manager_optimized.py` (function `_score_priority_rules`, line 2219)
- Lexicon data: `src/regions/manager_optimized.py` (`_STRONG` dict, line 67, ~2000 lines)
- Base territory mapping: `src/regions/base.py` (`TERRITORY_TO_REGION`, line 900)
- Hybrid classifier: `src/regions/hybrid_classifier.py` (ML ensemble wrapper)
- FastText model: `config/lid.176.bin` (125MB, not in Docker builds)
- MGP validation data: `data/mgp_validation_data.json` (15 real profiles)
- Golden dataset: `tests/fixtures/golden_mathematicians.json` (500 entries)
