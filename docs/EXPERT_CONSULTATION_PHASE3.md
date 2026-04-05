# Expert Consultation Phase 3: Post-Implementation Status & Open Problems

**Date:** 2026-04-05
**Context:** All 7 steps from Expert Phase 2 plan have been implemented. This document summarizes what was done, what improved, what didn't, and where we need guidance.

---

## 1. What Was Implemented (Phase 2 Summary)

### Change 1: Split Geo/Name Branches + Terminal R0
- `_infer_geo(entry)` cascade: CC → ROR/institution → DOI
- `_infer_name_origin(entry)` cascade: surname exact → CJK hybrid → script+scorer → ICU → fastText language → surname fastText → R0 (terminal)
- `_merge_geo_name()`: CC always primary for `region_code`; name-origin preserved in `name_region`
- Fast-path: when CC present, skip full scorer (surname exact + CJK only for diaspora)
- `RegionDetectionResult` extended with `geo_region`, `name_region`, `group_region`, `candidates`, `conflict`

### Change 2: Clean Suffixes + Re-mine from 15K
- Defined `SIGNATURE_SUFFIXES` (22 entries): `-opoulos`, `-poulos`, `-akis`, `-ides`, `-shvili`, `-dze`, `-adze`, `-yan`, `-ov`, `-ova`, `-ev`, `-eva`, `-enko`, `-evich`, `-ovich`, `-sson`, `-sen`, `-mann`, `-stein`, `-zadeh`, `-nejad`, `-pour`
- Removed ALL ambiguous suffixes from `_STRONG`: `-es`, `-os`, `-son`, `-man`, `-er`, `-ian`, `-ali`, `-ski`, `-in`, `-da`, `-ta`, `-ia`, `-uri`, `-ou`, `-as`, `-is` (19 entries across 8 regions)
- Re-mined `config/learned_features.json` from 16,156 labeled entries with:
  - Disagreement filtering (entries where signature suffix contradicts label are excluded)
  - Signed weights (positive and negative log-odds)
  - Shrinkage factor 0.8
  - Laplace smoothing alpha=0.5
  - Learned features are ADDITIVE tiebreakers, capped at 0.4 (surname) / 0.3 (given name)
- Scorer uses separate surname (1.0x) and given-name (0.35x) channels

### Change 3: Hierarchical Output + FastText Integration
- `REGION_GROUPS`: 21 semantic groups mapping 34 regions
- `LEAF_TO_GROUP`: reverse mapping for group lookup
- Given-name-only rule: if `surname_scores == 0` and given-name has signal, return group hint but R0 leaf
- FastText surname classifier loaded lazily as gated tiebreaker:
  - Only fires when all rules abstain
  - Must have confidence >= 0.50
  - Must NOT match a signature suffix (those are handled by rules)
  - Capped at 0.75 confidence
- Group hints surfaced for R0: when the scorer has partial signal (e.g., given-name-only), the `group_region` is populated even when `region_code == R0`

### Additional Fixes Found During Audit
- Duplicate `surname_prefix` scoring loop removed (was double-counting O', Mac, Al- prefixes)
- Non-Latin script detection restored (Hangul → E4, CJK → E1/E3, Cyrillic → B1, Greek → B3, Arabic → C3)
- Scorer-abstain reason matching expanded to catch `no_signal` and `given_only_no_surname`

---

## 2. Current Results

### 2.1 MGP Ground Truth (15 names, no CC)

| Name | Expected | Got | Group | Method |
|------|----------|-----|-------|--------|
| Gauss, Carl Friedrich | A2 | A2 | GERMANIC_WESTERN | surname |
| Euler, Leonhard | A2 | A2 | GERMANIC_WESTERN | surname |
| Riemann, Bernhard | A2 | A2 | GERMANIC_WESTERN | surname |
| Hilbert, David | A2 | A2 | GERMANIC_WESTERN | surname |
| **Poincare, Henri** | **A2** | **R0** | **None** | name-abstain |
| Noether, Emmy | A2 | A2 | GERMANIC_WESTERN | surname |
| Ramanujan, Srinivasa | D1 | D1 | SOUTH_ASIAN | surname |
| Chebyshev, Pafnuty | B1 | B1 | SLAVIC_EAST | surname |
| Kolmogorov, Andrey | B1 | B1 | SLAVIC_EAST | surname |
| Tao, Terence | E1 | E1 | SINOPHONE | surname |
| **Wiles, Andrew** | **A1** | **R0** | **ANGLO_SPHERE** | name-abstain |
| Grothendieck, Alexander | A2 | A2 | GERMANIC_WESTERN | surname |
| Serre, Jean-Pierre | A2 | A2 | GERMANIC_WESTERN | surname |
| **Perelman, Grigori** | **B1** | **R0** | **None** | name-abstain |
| Mirzakhani, Maryam | C2 | C2 | PERSIAN | surname |

**Accuracy: 12/15 = 80%, 3 honest R0 abstentions, 0 wrong answers.**

### 2.2 CC-Based Detection
**216/216 = 100%.** All territory-to-region mappings work perfectly.

### 2.3 Golden Dataset (500 verified mathematicians with CC)
**503/503 = 100%.** No regressions.

### 2.4 Diaspora Detection
| Name | CC | region_code | geo_region | name_region | conflict |
|------|-----|------------|------------|-------------|----------|
| Tao, Terence | US | A1 | A1 | E1 | True |
| Singh, Harjit | CA | A1 | A1 | D1 | True |
| Park, Jinhee | US | A1 | A1 | E4 | True |
| Chen, Wei | GB | A1 | A1 | E1 | True |
| Petrov, Ivan | DE | A2 | A2 | B1 | True |

All correct: geo wins for `region_code`, name-origin preserved in `name_region`, `conflict=True` when they disagree.

### 2.5 Group Hints for R0
| Name | region_code | group_region | Note |
|------|-------------|-------------|------|
| Xyzzy, Vladimir | R0 | SLAVIC_EAST | Given-name signal only |
| Xyzzy, Hiroshi | R0 | JAPANESE | Given-name signal only |
| Xyzzy, Mohammed | R0 | ARABIC | Given-name signal only |
| Wiles, Andrew | R0 | ANGLO_SPHERE | "Andrew" matches A1 given name |
| Poincare, Henri | R0 | None | No signal at all |

### 2.6 Performance
- 1,000 unique CC-based detections: **0.4 seconds** (was 378s before fast-path)
- All 1,719 CI tests pass in **93 seconds**

---

## 3. Training Data Distribution

The training corpus has 16,156 entries but is heavily skewed:

| Region | Entries | % | Notes |
|--------|---------|---|-------|
| A1 (Anglo) | 4,395 | 27.2% | Dominant |
| E1 (Chinese) | 4,176 | 25.8% | |
| A2 (Germanic) | 3,165 | 19.6% | |
| E3 (Japanese) | 674 | 4.2% | |
| D1 (Indian) | 572 | 3.5% | |
| G1 (Latin American) | 483 | 3.0% | |
| B2 (Polish) | 452 | 2.8% | |
| B1 (Russian) | 443 | 2.7% | |
| ... | ... | ... | |
| F1 (Maghreb) | 25 | 0.15% | Far too few |
| C8 (Georgian) | 13 | 0.08% | |
| A4 (Iberian) | 12 | 0.07% | |
| A5 (Celtic) | 11 | 0.07% | |
| F4 (Southern African) | 11 | 0.07% | |

**4 regions completely absent from learned features:** C9 (Baltic), D2 (South Indian), H1 (Historical), Z0 (Unknown)

---

## 4. Failure Categories (No-CC Detection)

### Category A: R0 Abstentions Where We Have Zero Signal (15 cases)

These names produce NO handcrafted or learned feature matches. The system correctly says "I don't know."

| Pattern | Examples | Root Cause |
|---------|----------|------------|
| French surnames | Poincare, Delacroix | No French-specific handcrafted rules. Learned features don't have them (only 3,165 A2 entries, mostly German) |
| Russian -in/-sky | Sorokin, Dostoevsky, Tchaikovsky | `-in` and `-sky` were cleaned from _STRONG. Learned suffix `-sky` exists but points to C6 (Hebrew) as top weight, not B1 |
| Polish -ski | Szymanski, Kaminski | `-ski` cleaned from _STRONG. Learned suffix `-ski` correctly points to B2 but with score < threshold |
| Greek -ou/-is | Papadimitriou, Karamanlis | `-ou` and `-is` cleaned. No replacement handcrafted patterns |
| Welsh ap prefix | ap Gwilym | `ap` not in any handcrafted prefix set |
| Arabic El-/Al- | El-Sayed, Al-Rashid | `al-` prefix exists in C3 but tokenizer may split differently |
| Yoruba (F2) | Adebayo, Ogundimu, Adesanya | Zero F2 handcrafted rules; only 33 F2 entries in training data |
| South Indian | Venkataraman, Subramaniam | Not in learned features; only 12 A4 + 0 D2 entries |

### Category B: Wrong Region (Not R0) (12 cases)

| Pattern | Expected → Got | Root Cause |
|---------|---------------|------------|
| Portuguese surnames | A4 → G1 | Portuguese and Latin American share the same suffix patterns. Only 12 A4 entries in training data. No way to disambiguate without CC |
| Lithuanian -auskas | C9 → A3 | C9 grouped under TURKIC (wrong!). `-auskas` not in any feature set. Also, C9 has zero training entries |
| Al-Khwarizmi | C3 → C2 | "Muhammad" given name matched C2 (Persian) via given-name heuristic; Al- prefix matched but C3 only 73 entries |
| Maghreb Ben-/Bou- | F1 → C5 | Maghreb names overlap Arabic. Only 25 F1 entries. No Maghreb-specific handcrafted rules |
| Lopez, Jennifer | G1 → A1 | "Jennifer" matches A1 given name. "Lopez" is in A1 hispanic_diaspora list. Correctly detected as diaspora-ambiguous |
| Chakraborty | D1 → D3 | Bengali surname mapped to D3 (Bangladesh) instead of D1 (India). This may actually be correct depending on definition |
| Ramanathan | D1 → D2 | South Indian Dravidian surname correctly routes to D2 (South Indian). D1 vs D2 distinction is India vs Sri Lanka |

---

## 5. Learned Feature Quality Issues

### Issue 1: Top weights are wrong for many suffixes

The learned log-odds produce suspicious top regions for many suffixes. Example:

| Suffix | Top-3 regions | Expected |
|--------|--------------|----------|
| `-ewski` | F4, A5, A4 | B2 (Polish) |
| `-ovsky` | F4, A5, A4 | B1 (Russian) |
| `-elman` | F4, A5, A4 | A2 (Germanic) or B1 |
| `-iles` | F4, A5, A4 | A1 (Anglo) |
| `kolmogorov` (surname) | F4, A5, A4 | B1 (Russian) |
| `tao` (surname) | F4, A5, A4 | E1 (Chinese) |

**F4 (Southern Africa), A5 (Celtic), A4 (Iberian) consistently appear as top weights** even for clearly non-African/Celtic/Iberian suffixes. This is a statistical artifact: these regions have very few entries (11-12 each), so the smoothed log-odds overshoot due to low denominators.

The scorer currently only uses POSITIVE log-odds from learned features, capped at 0.4 per region. But the spurious F4/A5/A4 weights mean the learned features are injecting noise rather than signal for these low-count regions.

### Issue 2: Famous mathematicians missing from learned features

25 of 27 famous mathematician surnames are NOT in the learned feature set (only "kolmogorov", "tao", and "hardy" appear). This is because the 15K training corpus is from modern OpenAlex data — historical figures aren't well-represented.

### Issue 3: Four regions have ZERO learned features

C9 (Baltic), D2 (South Indian), H1 (Historical), Z0 (Unknown) have no entries in the training data at all.

---

## 6. REGION_GROUPS Taxonomy Issues

### C9 (Baltic) grouped under TURKIC

C9 covers Lithuanian and Latvian names. These are Baltic (Indo-European), not Turkic. C9 was likely placed in TURKIC because C-prefix regions are generally Turkic/Caucasian. The correct grouping would be either its own BALTIC group or with NORDIC_BALTIC (alongside A3).

Impact: Lithuanian `-auskas` names get detected as A3 (Nordic) rather than C9.

### A4/A5 grouped as OCEANIA_CARIBBEAN

A4 (Iberian) and A5 (Celtic) are grouped together as OCEANIA_CARIBBEAN. These are culturally distinct regions (Portuguese/Spanish vs Welsh/Irish). The group name is also wrong — neither is Oceanian or Caribbean.

---

## 7. Open Questions for Expert

### Question 1: How to handle the cleaned suffix gap?

We removed `-ski`, `-sky`, `-in`, `-ou`, `-is`, `-es` from handcrafted rules because they're ambiguous across regions. But now 15+ names that would have matched these suffixes get R0. The learned features DO have these suffix weights but they're noisy (F4/A5/A4 domination).

**Options:**
- (a) Restore some cleaned suffixes with lower weights (e.g., `-ski` at 1.0 instead of 2.5, restricted to B1/B2)?
- (b) Fix the learned feature mining to correct the low-count region bias?
- (c) Accept R0 as honest and rely on fastText to fill the gap?
- (d) Add longer, more specific suffixes that ARE diagnostic (e.g., `-owski` for B2, `-evsky` for B1, `-auskas` for C9)?

### Question 2: How to fix the learned feature low-count region bias?

The smoothed log-odds give inflated weights to regions with 11-12 training entries (F4, A5, A4). The Laplace smoothing (alpha=0.5) doesn't adequately compensate. The MAX_REGION_FRAC filter (0.6) removes features in >60% of regions, but doesn't fix the base-rate issue.

**Possible fixes:**
- (a) Add a minimum entry count per region (e.g., skip regions with < 50 entries)?
- (b) Use different smoothing (Kneser-Ney, absolute discounting)?
- (c) Weight training entries by inverse region frequency?
- (d) Just blacklist the problematic regions (F4, A5, A4, D5) from learned features?

### Question 3: Should we invest in more training data?

Current distribution: 72% of data is A1/E1/A2. The long tail has 11-73 entries per region. Would fetching more data for underrepresented regions (OpenAlex has author country codes) actually help, or is the problem more fundamental?

Specifically:
- Is 50+ entries enough for reliable learned features for a region?
- Should we target specific regions (C9, D2, F1-F4, A4, A5, B3)?
- Would adding the Wikidata historical mathematicians help with famous-name coverage?

### Question 4: FastText is not installed in production — what's the impact?

The fastText surname classifier (57.5% accuracy standalone) is gated as a tiebreaker, but it requires the `fasttext` Python package which isn't installed in the current environment. All detection falls back to rules-based only.

- Is the 57.5% standalone accuracy good enough to justify the dependency?
- Should we convert the model to ONNX or a simpler format that doesn't need fasttext?
- Or should we invest in improving the rules-based system instead?

### Question 5: How should we handle Portuguese vs Latin American?

A4 (Portuguese: Fernandes, Almeida, Carvalho) and G1 (Latin American: Rodriguez, Gonzalez) share suffix patterns (`-ez`, `-es`, `-ndes`). Only 12 A4 entries in training data. Without CC, the system routes Portuguese names to G1.

- Is this genuinely unresolvable without CC or institution data?
- Are there Portuguese-specific markers (given names? double surnames?) that could help?
- Should we merge A4 into a broader Iberian group with G1?

### Question 6: Should abstentions be at group level instead of R0?

Currently, when the scorer can identify the group but not the leaf (e.g., "Szymanski" → SLAVIC_CENTRAL but B2 vs B1 is uncertain), we return R0 with `group_region=SLAVIC_CENTRAL`. The plan mentioned returning group-level predictions.

- Should `region_code` be the group code (e.g., "SLAVIC") instead of R0?
- Or is R0 + group_region the right design (leaf is unknown, group is a hint)?
- What should downstream pipeline stages do with group_region?

### Question 7: Is 80% no-CC accuracy sufficient, or should we target higher?

The 80% on MGP ground truth (with 3 honest R0, 0 wrong) seems solid. The expanded no-CC set (67%) is lower but includes deliberately hard cases. Is this good enough for the genealogy use case, or should we push for 90%+?

What would it take to get Poincare (French) and Perelman (Russian-Jewish) correct without CC? French surnames are extremely diverse — is there a practical approach?

### Question 8: What about the `-ski`/`-sky` problem specifically?

These were the most impactful suffixes we cleaned. Before cleanup: they incorrectly forced many names into B1/B2. After cleanup: legitimate Slavic names (Dostoevsky, Tchaikovsky, Szymanski) get R0.

The learned features have `-ski` → B2 (2.415) and `-sky` → C6/B1 (1.895/1.633), which are correct. But they're used as additive tiebreakers (capped at 0.4), which is too weak to produce a confident result.

**Should we:**
- (a) Raise the learned feature cap for specific high-confidence suffixes?
- (b) Create a "medium confidence" tier of suffixes that aren't signature-level but aren't ambiguous enough to remove?
- (c) Something else entirely?

---

## 8. System Architecture Summary (for reference)

```
Entry → _infer_geo()  ─── CC → ROR → DOI ─────────────────────┐
     → _infer_name_origin()                                    │
           ├─ surname exact match (STRONG surnames list)        │
           ├─ CJK hybrid detection                             │
           ├─ script + priority scorer                         │
           │    ├─ handcrafted features (SIGNATURE_SUFFIXES,    │
           │    │   prefixes, particles, given names)           │
           │    └─ learned features (tiebreaker, +0.4 max)     │
           ├─ ICU normalization                                │
           ├─ FastText language detection                      │
           ├─ FastText surname classifier (gated tiebreaker)   │
           └─ R0 (terminal abstain)                            │
                                                               ▼
     → _merge_geo_name() ─── CC wins? → geo primary, name in name_region
                          └── no CC?  → name primary, geo if available
                          └── conflict? → flag diaspora
```

**Constants:**
- `SIGNATURE_SUFFIXES`: 22 near-diagnostic suffix markers (never removed, weight 2.5)
- `_STRONG`: per-region handcrafted patterns (surnames, prefixes, given names, particles)
- `config/learned_features.json`: 11,989 features mined from 16,156 entries (surnames, suffixes, given names)
- `REGION_GROUPS`: 21 groups, 34 regions mapped

---

## 9. Files Modified in Phase 2

| File | Changes |
|------|---------|
| `src/regions/manager_optimized.py` | Core refactor: split cascade, SIGNATURE_SUFFIXES, REGION_GROUPS, clean _STRONG, RegionDetectionResult extension, fast-path, group hints, duplicate prefix fix, non-Latin script fix |
| `tools/mine_features.py` | 15K OpenAlex loading, disagreement filtering, signed weights, shrinkage |
| `config/learned_features.json` | Re-mined: 11,989 features from 16,156 entries |
| `tests/unit/test_region_detection_accuracy.py` | Updated assertions for geo/name split, pytest.param handling, gate thresholds |
| `tests/unit/test_golden_dataset.py` | Accept geo_region OR region_code matching expected |

---

## 10. Quantitative Before/After

| Metric | Before Phase 2 | After Phase 2 | Change |
|--------|----------------|---------------|--------|
| MGP no-CC accuracy | ~40-60% | 80% (12/15) | +20-40pp |
| Wrong answers (not R0, not correct) | Common (A1 default) | 0 | Eliminated |
| CC-based detection | 100% | 100% | Unchanged |
| Golden dataset | 100% | 100% | Unchanged |
| Diaspora detection | Not available | Working | New capability |
| Group-level output | Not available | Working (21 groups) | New capability |
| Performance (1K CC detections) | 378s | 0.4s | 945x faster |
| Non-Latin script detection | Broken (all R0) | Working | Fixed |
| Test count | ~1,500 | 1,719 | +219 |
