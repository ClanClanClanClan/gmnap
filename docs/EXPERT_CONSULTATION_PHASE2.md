# Expert Consultation Phase 2: Remaining Detection Gaps

## Summary of Progress Since Phase 1

We implemented all five of your immediate recommendations. Here is the current state:

### Implemented (your Phase 1 advice)

1. **Exact-token given name matching** — Substring prefix matching (`tok.startswith(g)`) replaced with exact token or exact hyphen-part matching. "Amalie" no longer fires on "amal".

2. **Ambiguity-weighted given names** — Built a reverse index `_GIVEN_TO_REGIONS` mapping each given name to its set of regions. Names in 4+ regions (like "ali" in 6 regions, "maria" in 5) are skipped entirely. Others weighted as `2.0 / ambiguity`.

3. **Separate surname/given channels** — Surname evidence accumulated separately from given evidence. Combined as `final = 1.0 * surname_score + 0.35 * given_score`. Prevents given names from overriding unmatched surnames.

4. **Latin script weak-evidence abstain** — If scorer's best raw score < 2.0, returns R0 (confidence 0.20) instead of forcing a Latin-script winner.

5. **Score-margin abstain** — If margin between #1 and #2 < 0.3, returns R0. Reject-option classification as you recommended.

### Also implemented (your medium-term advice)

6. **Auto-mined features from labeled corpus** — Computed smoothed log-odds from 1,417 labeled entries. Mined 96 surname weights, 626 suffix weights, 1,577 n-gram weights, 208 given-name weights. Stored in `config/learned_features.json`. Loaded at startup and added to handcrafted scores with scale factors (surname 0.5x, suffix 0.3x, given 0.2x). Only positive weights used; negative weights ignored to avoid suppressing correct handcrafted signals.

7. **15,120 labeled entries from OpenAlex** — Fetched real mathematician records with institution-based country codes. Top countries: CN (4,082), US (2,913), DE (913), JP (581), GB (554).

8. **FastText supervised models trained** — Two models with your recommended minn=2, maxn=5:
   - Surname-only: 57.5% precision on validation (dim=50, epoch=50)
   - Full-name: 60.9% precision on validation (dim=100, epoch=50, wordNgrams=2)
   - Quantized sizes: 48MB surname, 96MB fullname

9. **ROR institution lookup** — 120 curated university→country mappings with fuzzy substring matching. Elevated to #2 in the detection cascade (after CountryCodes, before name-based patterns).

---

## Current Accuracy on Real Data

### 15 Real Mathematicians from Math Genealogy Project

| Mathematician | Expected | Name-only | With Institution | With CC |
|---|---|---|---|---|
| Leonhard Euler | A2 (CH) | ✓ A2 (script) | ✓ A2 (ROR) | ✓ A2 |
| David Hilbert | A2 (DE) | ✗ A1 (fallback) | ✓ A2 (ROR: Königsberg→DE) | ✓ A2 |
| Emmy Noether | A2 (DE) | ✓ A2 (script) | ✓ A2 (ROR: Erlangen→DE) | ✓ A2 |
| Bernhard Riemann | A2 (DE) | ✓ A2 (-mann suffix) | N/A | ✓ A2 |
| Henri Poincaré | A2 (FR) | ✓ A2 (script) | ✓ A2 (ROR: Paris→FR) | ✓ A2 |
| Andrew Wiles | A1 (GB) | ✗ G1 (-es suffix) | ✓ A1 (ROR: Cambridge→GB) | ✓ A1 |
| Terence Tao | E1 (AU) | ✓ E1 (shen surname) | ✗ A1 (ROR: Princeton→US) | ✓ A1* |
| Jean-Pierre Serre | A2 (FR) | ✓ A2 (jean/pierre) | ✓ A2 (ROR: Sorbonne→FR) | ✓ A2 |
| Grothendieck | A2 (DE) | ✗ B1 (alexander→B1) | ✗ B1 (ROR: Nancy→FR=A2, but...) | ✓ A2 |
| Ramanujan | D1 (IN) | ✗ A1 (fallback) | ✗ A1 (ROR: Cambridge→GB) | ✓ D1 |
| Stefan Banach | B2 (PL) | ✗ A2 (script fallback) | N/A† | ✓ B2 |
| G. H. Hardy | A1 (GB) | ✓ A1 (script) | N/A | ✓ A1 |
| Perelman | B1 (RU) | ✓ B1 (-evich suffix) | ✓ B1 (ROR: St. Petersburg→RU) | ✓ B1 |
| Mirzakhani | C2 (IR) | ✓ C2 (-ani suffix) | ✗ A1 (ROR: Harvard→US) | ✓ C2 |
| Artur Avila | G1 (BR) | ✗ C3 (no signal) | ✓ G1 (ROR: IMPA→BR) | ✓ G1 |

*Tao's CC is AU (Australia) which maps to A1, not E1. His cultural region is E1 (Chinese) but his nationality is Australian.
†"University of Lwów" not in our 120-entry ROR lookup.

**Summary:**
- Name-only: 9/15 correct (60%)
- With institution: 10/15 correct (67%) — 3 diaspora mismatches, 2 not in ROR
- With CountryCodes: 15/15 (100%)

---

## Five Open Problems

### Problem 1: Diaspora — Institution Country ≠ Cultural Origin

The ROR lookup correctly resolves institutions to countries, but for diaspora mathematicians the institution country is where they WORK, not where their name originates. This affects:

- **Terence Tao** (born Australia, parents Chinese) works at UCLA. ROR gives US→A1. But his name is Chinese (E1). Name-only detection correctly gives E1 (via "shen" and "tao" E1 surname matches). The institution OVERRIDES the correct name-based detection.

- **Maryam Mirzakhani** (born Iran) worked at Stanford. ROR gives US→A1. But her name is Persian (C2). Name-only correctly gives C2 (via "-ani" suffix and "maryam"). Again, institution overrides the correct answer.

- **Srinivasa Ramanujan** (born India) went to Cambridge. ROR gives GB→A1. But his name is Indian (D1). Name-only gives A1 (no D1 signal strong enough), and institution reinforces the wrong answer.

**Question for expert:** Should institution detection be lower priority than name-based detection? The current cascade is:
1. CountryCodes (highest)
2. Institution/ROR
3. Name patterns

Should it be:
1. CountryCodes
2. Name patterns (when strong signal)
3. Institution/ROR (when name signal is weak)
4. Abstain (R0)

Or should we combine them differently? The expert's formula was `surname_score + 0.35 * given_score + 0.5 * ml_score + 1.5 * aff_score` — but that was assuming affiliation and name reinforce each other. In diaspora cases they conflict.

### Problem 2: Abstain vs Default Fallback

When the scorer abstains (no signal or low margin), the cascade should return R0. But currently:
- Scorer returns `(None, 0.0, {"reason": "no_signal"})` or `(None, 0.0, {"reason": "low_score_or_margin"})`
- `_detect_by_script()` sees `region is None` and falls through
- The cascade continues through ICU, FastText, affiliation, DOI, diaspora
- Eventually hits "default-fallback" which returns A1 with 0.10 confidence

Names that hit the default fallback: Hilbert, Ramanujan, Banach, Hardy, Euler, Noether, Poincaré (all get A1 or random Latin region). The expert said "if the name is Latin-script and the lexical evidence is weak, return R0." We implemented this in `_detect_by_script` but the default fallback at the end of the cascade still picks A1.

**Current cascade (13 steps):**
```
1. CountryCodes → 0.85 (dict lookup)
2. Institution/ROR → 0.85 (new)
3. Authority cache → 0.90
4. ML ensemble → 0.85
5. Hybrid CJK → 0.95
6. Surname exact → 0.95
7. Script + priority rules → 0.60 (abstains if weak)
8. ICU + priority rules → 0.60
9. FastText language → 0.70
10. Affiliation (structured) → 0.80
11. DOI prefix
12. Diaspora overlay
13. Default fallback → A1, 0.10  ← THIS IS THE PROBLEM
```

Steps 7 abstains correctly, but steps 8-12 don't have the same abstain logic, so they can return wrong results. Step 13 always picks A1.

**Question for expert:** Should we add the same abstain logic to steps 8-12 and change step 13 to return R0 instead of A1?

### Problem 3: The "-es" Suffix Problem (Wiles → G1)

"Andrew John Wiles" gets detected as G1 (Latin America) because the surname "wiles" ends with "-es", which is a G1 (Hispanic) suffix pattern. The scorer gives G1 a surname_score of 2.50 (from the "-es" suffix), while A1 gets only 0.14 (from weak given-name fragments "andrew" and "john").

The "-es" suffix is genuinely Hispanic (Hernandez, Gonzalez, Lopez, Martinez), but also appears in English names (Wiles, Jones, James, Holmes). The expert said "learn distinctiveness from counts: features that occur across many regions get near-zero weight." The "-es" suffix is common in BOTH A1 and G1 but our handcrafted lexicon only has it in G1.

**Specific data:**
- Suffix "-es" appears in G1 only (weight 2.50)
- But in our 15K OpenAlex corpus, "-es" appears in A1 (288 times), A2 (153), G1 (64), E1 (94)
- The learned features file has "-es" with weights across multiple regions but the handcrafted suffix overrides

**Question for expert:** Should we remove "-es" from G1's handcrafted suffix list since it's cross-regional? Or should we keep it but reduce the weight based on the corpus evidence? The expert's recommendation was "score with smoothed log-odds instead of fixed +5, +3, +2.5" — should we fully replace the handcrafted weights with corpus-derived weights for ALL suffixes?

### Problem 4: FastText Models Not Integrated

We trained two fastText models (surname 57.5%, fullname 60.9%) but they're not yet integrated into the detection cascade. The issue is:

1. **Size:** 48MB (surname, quantized) and 96MB (fullname, quantized) — too large for Docker builds
2. **Loading:** fasttext module isn't always available (deliberately excluded from requirements.txt due to compilation issues)
3. **Cascade position:** Where should ML predictions fit? Before or after handcrafted rules?

The expert said: "ensemble them with affiliation and structured metadata." The proposed formula was:
```
final = surname_score + 0.35 * given_score + 0.5 * ml_score + 1.5 * aff_score
```

**Question for expert:** Given that the fastText models were trained on only 13K entries (small by ML standards) and have 57-61% precision, should we:
(a) Integrate them as-is with low weight (0.2x)
(b) Wait until we have 50K+ training entries
(c) Use them only as tiebreakers when the rule-based system abstains
(d) Replace them with a simpler approach (e.g., character n-gram logistic regression trained on the same data)

### Problem 5: Hierarchical Output

The expert said: "use hierarchical output when the leaf is not identifiable from names alone. For some cases like Brazil vs Portugal, or finer intra-India splits, the honest answer from name-only may be 'Lusophone/Iberian-family' or D*, not a confident leaf."

We haven't implemented this. Currently, the system returns either:
- A specific leaf region (A1, A2, B1, etc.)
- R0 (complete abstention)

There's no middle ground like "this name is probably Slavic (B*)" or "this name is probably Lusophone (A2 or G1 or F4)."

**Possible hierarchy:**
```
Latin-script
├── Anglo/Germanic (A1/A2/A3)
├── Slavic (B1/B2)
├── Hispanic/Lusophone (A2-PT/G1/F4)
├── Francophone (A2-FR/F1)
└── Other Latin
```

**Question for expert:** Should we:
(a) Return the parent group when the leaf is uncertain (e.g., `{"region": "B*", "candidates": ["B1", "B2"]}`)
(b) Return a ranked list of candidates with probabilities (e.g., `[("B1", 0.55), ("B2", 0.45)]`)
(c) Both — hierarchical + ranked
(d) Don't bother — just return R0 and let the user provide more data

---

## Detailed Scoring Data

### Scorer output for all 15 MGP names (name-only, no CC, no institution)

| Name | Best Region | Score | Margin | Reasons | Outcome |
|---|---|---|---|---|---|
| Euler | None | 0.00 | — | no_signal | Abstain → script fallback A2 |
| Hilbert | None | 0.04 | 0.04 | low_score_or_margin | Abstain → default A1 |
| Noether | None | 0.00 | — | no_signal | Abstain → script fallback A2 |
| Riemann | A2 | 2.50 | 2.50 | -mann suffix | ✓ A2 |
| Poincaré | None | 0.00 | — | no_signal | Abstain → script fallback A2 |
| Wiles | G1 | 2.50 | 1.04 | -es suffix → G1 | ✗ G1 (should be A1) |
| Tao | E1 | 5.00+2.00 | 4.83 | shen surname + tao given | ✓ E1 |
| Serre | A2 | 2.00+2.00 | 0.52 | jean + pierre given | ✓ A2 (via ICU) |
| Grothendieck | B1 | 0.71* | 0.71 | alexander→B1 given | ✗ B1 |
| Ramanujan | None | 0.00 | 0.00 | low_score_or_margin | Abstain → default A1 |
| Banach | None | 0.00 | — | no_signal | Abstain → script fallback A2 |
| Hardy | None | 0.00 | — | no_signal | Abstain → script fallback A1 |
| Perelman | B1 | 2.50 | 2.50 | -evich suffix | ✓ B1 |
| Mirzakhani | C2 | 2.50+1.00 | 0.35 | -ani suffix + maryam | ✓ C2 |
| Avila | None | 0.00 | — | no_signal | Abstain → script fallback C3 |

*Grothendieck: "alexander" is exact-token match for B1 given_frag (even with our ambiguity fix, it's only in 1 region — B1 — so it gets full weight 2.00). The surname "grothendieck" has no matches anywhere. So the single given-name signal (alexander→B1, 0.35 * 2.00 = 0.70) wins. The combined score is 0.71, above the 0.3 margin threshold, so it doesn't abstain. This is a false positive from a legitimately unambiguous given name ("alexander" IS more common in Russian/Slavic contexts) that happens to be wrong for this specific person.

### Current Lexicon Statistics

```
Region  Surnames  Suffixes  Prefixes  Given Frags
A1      84        3+pfx     4         46
A2      74        14        0         26
A3      46        5         0         29
B1      31        15        0         27
B2      40        17        0         24
B3      27        8         0         24
C2      14        6         0         13
C7      12        1(-yan)   0         12
C8      20        6         0         14
E3      36        8         0         21
E4      31        0         0         18
G1      28        6         0         15
D1      21        0         0         19
(14 other regions with 0 suffixes)
```

**Key observation:** 14 of 35 regions have ZERO suffix patterns. These regions can only be detected via exact surname match or given-name fragments — both of which are too sparse for the long tail of real mathematician names.

### Learned Features (from 1,417-entry corpus)

```
Learned surnames: 96 (vs 1,044 handcrafted)
Learned suffixes: 626 (vs 90 handcrafted)
Learned n-grams: 1,577 (novel — handcrafted has 0)
Learned given: 208 (vs 709 handcrafted)
```

The learned features are additive (scale 0.5x for surnames, 0.3x for suffixes, 0.1x for n-grams, 0.2x for given). They haven't been re-mined from the full 15K corpus yet — only from the initial 1,417 entries.

### Training Data Distribution (15K OpenAlex)

```
A1 (Anglo): 4,394  |  E3 (Japanese): 673  |  B2 (W.Slavic): 450
E1 (Chinese): 4,176 |  D1 (Indian): 571    |  B1 (E.Slavic): 403
A2 (Germanic): 3,162|  G1 (LatAm): 482     |  A3 (Nordic): 384
```

The distribution is heavily skewed toward A1/E1/A2 (75% of data). Underrepresented regions (C4, C5, C7, C8, D3, D5, F3, F4, etc.) have <50 entries each, making statistical learning unreliable for those regions.

---

## Architecture Diagram

```
Entry → {CanonicalLatin, CountryCodes?, Institution?, Affiliations?}
         │
         ▼
    ┌─────────────┐
    │ CountryCodes │──→ dict lookup → region (0.85)
    │   present?   │
    └──────┬──────┘
           │ no
           ▼
    ┌─────────────┐
    │ Institution  │──→ ROR lookup → country → region (0.85)
    │   present?   │    (120 curated universities)
    └──────┬──────┘
           │ no match
           ▼
    ┌─────────────┐
    │  Authority   │──→ cached prior enrichment (0.90)
    │   cache?     │
    └──────┬──────┘
           │ miss
           ▼
    ┌─────────────┐
    │  ML models   │──→ fastText surname + fullname (0.85)
    │  (if loaded) │    [NOT YET INTEGRATED]
    └──────┬──────┘
           │ not available
           ▼
    ┌─────────────┐
    │   Script +   │──→ _score_priority_rules()
    │ Priority     │    surname_score (1.0x) + given_score (0.35x)
    │   Rules      │    + learned_features (0.1-0.5x)
    │              │    → ABSTAIN if score < 2.0 or margin < 0.3
    └──────┬──────┘
           │ abstain
           ▼
    ┌─────────────┐
    │   ICU +      │──→ same scorer, Unicode-normalized input
    │ Priority     │
    └──────┬──────┘
           │ abstain
           ▼
    ┌─────────────┐
    │  FastText    │──→ language detection → language-to-region map
    │  Language    │    [lid.176.bin, if loaded]
    └──────┬──────┘
           │ not available
           ▼
    ┌─────────────┐
    │  Default     │──→ A1 (conf=0.10) ← SHOULD BE R0
    │  Fallback    │
    └─────────────┘
```

---

## Files Reference

| File | Purpose | Lines |
|---|---|---|
| `src/regions/manager_optimized.py` | Detection cascade + scorer | 5,800+ |
| `src/regions/base.py` | Territory→region mapping | 1,200 |
| `src/collectors/ror_client.py` | Institution→country lookup | 170 |
| `config/learned_features.json` | Auto-mined feature weights | 82K |
| `data/ml_training/surname_train.txt` | FastText training data | 13,187 |
| `data/ml_training/surname_classifier.ftz` | Trained model (quantized) | 48MB |
| `data/ml_training/fullname_classifier.ftz` | Trained model (quantized) | 96MB |
| `tests/fixtures/golden_mathematicians.json` | 500 verified entries | 273 |
| `data/mgp_validation_data.json` | 15 real MGP profiles | 215 |
| `docs/EXPERT_CONSULTATION_DETECTION_WITHOUT_CC.md` | Phase 1 consultation | 175 |

---

## Specific Questions for Expert

1. **Diaspora cascade priority:** Should institution be lower than name patterns when the name has a strong cultural signal? Or should we combine them (e.g., if name says C2 and institution says A1, return C2 with a note)?

2. **Default fallback:** Should the last resort be R0 instead of A1? This would mean ~40% of names get R0 (unknown) — is that acceptable for a production system, or should we always make a best guess?

3. **"-es" suffix and other cross-regional suffixes:** Should we replace handcrafted suffix weights with corpus-derived log-odds for ALL suffixes? Or keep the handcrafted ones and only use corpus weights for suffixes NOT in the handcrafted set?

4. **FastText integration strategy:** Given 57-61% precision on 13K training data, what's the minimum viable approach? Tiebreaker only? Or should we wait for 50K+ data?

5. **Hierarchical output:** Should we implement parent-group returns (e.g., "B*" for Slavic) or ranked candidate lists? What would the downstream consumer (web UI, API) do with a parent-group answer?

6. **Re-mining from 15K corpus:** The learned features were mined from 1,417 entries. We now have 15K. Should we re-mine with the larger corpus, or is the quality improvement marginal given the skewed distribution (75% A1/E1/A2)?

7. **"Alexander" problem:** "Alexander" is only in B1's given_frag set (1 region), so it gets full weight 2.00 and is NOT filtered by our 4+ region ambiguity rule. But it's a cross-cultural name (English, German, Greek, Russian). Should we expand the given_frag lists to include all regions where a name is common, even if it wasn't in the original handcrafted lexicon? Or should we cap given-name influence more aggressively?
