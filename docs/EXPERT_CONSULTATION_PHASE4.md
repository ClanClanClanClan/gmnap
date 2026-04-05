# Expert Consultation Phase 4: Remaining Precision Gaps

**Date:** 2026-04-06
**Context:** All Phase 3 recommendations implemented. This document details the remaining 11 wrong-leaf predictions preventing us from reaching the expert's target KPIs.

---

## 1. Current KPIs (Post Phase 3 Implementation)

| Metric | Value | Expert Target | Gap |
|--------|-------|---------------|-----|
| **MGP ground truth (no CC)** | 15/15 = **100%** | 70%+ | Exceeded |
| **Leaf precision** (emitted) | 78/89 = **88%** | >=90% | -2pp |
| **Group-or-better accuracy** | 81/91 = **89%** | >=95% | -6pp |
| **Coverage** | 89/91 = **98%** | >=85% | Exceeded |
| **CC-based detection** | 216/216 = **100%** | unchanged | Met |
| **Golden dataset** | 503/503 = **100%** | unchanged | Met |
| **Test suite** | 1733 passed, 0 failed | no regressions | Met |

---

## 2. What Was Implemented Since Phase 3 Document

### 2a. FastText CLI binary (compiled from source)
- Installed to `~/.local/bin/fasttext` (compiled from Facebook's repo)
- CLI mode detected automatically when Python `fasttext` unavailable
- **Impact:** Poincaré→A2 (99.6%), Perelman→B1 (98.4%), Wiles→A1 (95.0%)
- MGP ground truth went from 80% to **100%**
- Acceptance criteria: `p1 >= 0.50 AND (p1 - p2) >= 0.15`

### 2b. Wikidata bulk fetch
- New script: `scripts/data/fetch_wikidata_mathematicians.py`
- Fetched 10,724 unique mathematicians via SPARQL (Q170790 occupation)
- Added 100+ historical polity→CC mappings (Kingdom of Prussia→DE, Soviet Union→RU, Ottoman Empire→TR, etc.)
- Training corpus grew from 16,156 → 26,323 entries
- A2 grew from 3,068→6,495 (now includes French/Italian/Portuguese)
- B1 grew from 443→1,922 (Russian/Soviet coverage)

### 2c. Portuguese/Lusophone discrimination
- Added Portuguese surname suffixes to A2: `-eiro`, `-eira`, `-inho`, `-inha`
- Added 14 Portuguese surnames to A2 `_STRONG` and `surname_patterns`
- Added 13 Portuguese given names to A2: `joao`, `goncalo`, `nuno`, `rui`, `filipe`, etc.
- Demoted shared Lusophone surnames from G1 `_STRONG` to `_MEDIUM` (weight 1.5 vs 5.0)
- Fixed test expectations: A4 is Oceania/Pacific, PT→A2

### 2d. Maghreb patterns for F1
- Added `surname_prefix: {"ben", "bou"}` to F1
- Added 14 Maghreb surnames and 10 given names

### 2e. Yoruba/West African patterns for F2
- Added `surname_prefix: {"ade", "ola", "ogun", "ojo"}`
- Added 6 Yoruba surnames

### 2f. Re-mined features with 26K entries
- Territory roll-up mining (Phase 3 method) with expanded data
- 23 leaves now have 50+ entries (was 20)
- 65 suffix features, 335 n-gram features, 13 surname features, 9 given name features

---

## 3. The 11 Remaining Wrong-Leaf Predictions

These are the exact cases preventing us from reaching >=90% precision and >=95% group-or-better:

### Category A: Hispanic Diaspora (4 cases) — Genuinely Ambiguous

| Name | Expected | Got | Method | Analysis |
|------|----------|-----|--------|----------|
| Hernandez, Javier | G1 | A1 | surname | "Hernandez" is in A1 `hispanic_diaspora` (weight 1.0). Without CC, A1 vs G1 is genuinely unresolvable. |
| Rodriguez, Alex | G1 | A1 | surname | Same pattern. "Alex" is a Western given name. |
| Lopez, Jennifer | G1 | A1 | surname | "Jennifer" matches A1 given names, "Lopez" in A1 `hispanic_diaspora`. |
| Gonzalez, Tony | G1 | A1 | surname | "Tony" matches A1 given names. |

**Root cause:** These names have Anglo given names + Hispanic surnames. The scorer sees both A1 and G1 evidence, and A1 wins because of the given name + combination bonus. This is the classic diaspora problem that the expert already identified as fundamentally unresolvable without CC.

**Impact on KPIs:** These 4 cases account for 36% of all wrong leaves. They're already `pytest.mark.xfail` in parametrized tests. If excluded from the precision calculation (as xfail entries), precision goes from 88% to 92%.

**Question for expert:** Should we exclude genuinely ambiguous diaspora cases from the precision KPI? Or should we return R0 for these instead of forcing a leaf? Currently, the scorer produces a leaf because both A1 and G1 have strong competing signals. The alternative would be to detect the A1/G1 competition specifically and abstain.

### Category B: FastText Misclassifications (3 cases) — ML Override Problem

| Name | Expected | Got | Method | ft_prob | ft_label | Analysis |
|------|----------|-----|--------|---------|----------|----------|
| Venkataraman, Raghuram | D1 | A1 | surname-fasttext | 0.52 | A1 | South Indian surname misclassified. Model trained on modern OpenAlex where Indian academics in US institutions get A1 labels. |
| Subramaniam, Subha | D2 | A1 | surname-fasttext | 0.55 | A1 | Same issue — South Indian name, fastText says A1 due to training bias. |
| Benali, Rachid | F1 | A2 | surname-fasttext | 0.68 | A2 | Maghreb name, but "Benali" also appears among French nationals. FastText learned a French association. |

**Root cause:** The fastText surname model was trained on OpenAlex data where the `country_code` reflects the **institution country**, not the **name origin**. Indian academics at US universities get labeled US→A1. Maghrebi academics at French universities get labeled FR→A2. The model conflates geography and onomastics — exactly the problem the expert warned about with NamePrism ("excluded immigration countries like US, Canada, Australia").

**Impact on KPIs:** 3 cases. FastText fires as a tiebreaker when rules abstain, and its prediction overrides an honest R0 or group-level output. The cure is worse than the disease here.

**Question for expert:** Should we tighten the fastText acceptance threshold? Current: p1>=0.50, margin>=0.15. Or should certain regions (D1, D2, F1) be excluded from fastText predictions? Or should we retrain the model using name-origin labels (birth country) instead of institution country?

The specific issue: for "Venkataraman", the rules-based system would abstain (no strong match), and the fastText model fills in with A1 because it learned institution-country labels. Before fastText, this was an honest R0 with `group=SOUTH_ASIAN`. With fastText, it's a wrong A1.

**Possible fixes:**
1. Raise fastText threshold to p1>=0.70 (would block Venkataraman at 0.52 and Subramaniam at 0.55, but keep Benali at 0.68)
2. Add a "never override group hint" rule: if the scorer already identified a group (e.g., SOUTH_ASIAN), don't let fastText assign a leaf from a different group (A1 is ANGLO_SPHERE)
3. Retrain fastText on Wikidata birth-country labels instead of OpenAlex institution-country
4. Exclude "immigration regions" (A1, A2) from fastText predictions for non-Western names

Option 2 seems most principled — it follows the expert's hierarchical classification philosophy: if the rules already identified the group, don't let a weak ML model contradict it.

### Category C: Within-Group Leaf Ambiguity (2 cases) — Counted as Group-Correct

| Name | Expected | Got | Method | Analysis |
|------|----------|-----|--------|----------|
| Chakraborty, Satyajit | D1 | D3 | script-priority | Bengali surname. D1=India, D3=Bangladesh. Both are SOUTH_ASIAN. The scorer picks D3 because "Chakraborty" appears more in Bangladeshi data. |
| Ramanathan, Veerabhadran | D1 | D2 | script-priority | South Indian Dravidian surname. D1=North India, D2=South India. The suffix "-an" is characteristic of D2 (Tamil/Dravidian). D2 may actually be more correct than D1. |

**Root cause:** These are within-SOUTH_ASIAN leaf disambiguation failures. The training data distinguishes D1 (Hindi belt) from D2 (Dravidian) and D3 (Bengali/Bangladeshi), but the boundaries are porous — Chakraborty is a Bengali name that appears in both India and Bangladesh.

**Impact on KPIs:** These 2 cases count as "wrong leaf" but "correct group". They don't hurt group-or-better. Arguably, Ramanathan→D2 might be MORE correct than the test's expected D1.

**Question for expert:** Should we review the test expectations for D1/D2/D3? The distinction between these leaves is:
- D1: Hindi-belt India (Sharma, Gupta, Verma, Yadav)
- D2: South Indian Dravidian (Ramanathan, Venkataraman, Subramanian)
- D3: Bengali/Bangladeshi (Chakraborty, Mukherjee, Bhattacharya, Sen)

If "Chakraborty, Satyajit" is expected to be D3 (Bengali), and our system says D3, that's actually correct. The test has it as D1 (India) which is geographically correct but onomastically D3 is better. Similarly, "Ramanathan" is onomastically D2 (Dravidian) even though the test expects D1.

### Category D: Cross-Group Arabic/Persian Ambiguity (2 cases)

| Name | Expected | Got | Method | Analysis |
|------|----------|-----|--------|----------|
| Al-Khwarizmi, Muhammad | C3 (Arabic) | C2 (Persian) | surname | "Muhammad" matches C2 given names. "Al-Khwarizmi" is historically Persian/Khwarezmian, so C2 may be more correct. |
| Al-Rashid, Harun | C3 (Arabic) | C4 (Arabic) | surname-fasttext | Both are ARABIC group. C3=Levant/Nile, C4=Gulf. FastText picks C4. |

**Root cause:** Al-Khwarizmi was historically from Khwarezm (modern Uzbekistan/Turkmenistan), making C2 (Persian) arguably correct. Al-Rashid C3→C4 is within ARABIC group (Levant vs Gulf), similar to the D1/D2/D3 problem.

**Impact on KPIs:** Al-Rashid counts as group-correct (both ARABIC). Al-Khwarizmi is cross-group (ARABIC vs PERSIAN).

---

## 4. KPI Impact Analysis

If we apply the recommended fixes, the projected KPIs would be:

| Scenario | Precision | Group-or-better | Coverage |
|----------|-----------|-----------------|----------|
| **Current** | 78/89 = 88% | 81/91 = 89% | 89/91 = 98% |
| **Fix B (block fastText group-contradictions)** | 78/86 = 91% | 81/91 = 89% | 86/91 = 95% |
| **Fix A+B (xfail diaspora + block fastText)** | 78/82 = 95% | 81/87 = 93% | 82/87 = 94% |
| **Fix A+B+C (correct test expectations)** | 80/82 = 98% | 83/87 = 95% | 82/87 = 94% |

The most impactful single change is **Fix B: block fastText when it contradicts a rules-based group hint**. This removes 3 wrong leaves without losing anything valuable (those names become honest R0+group instead of wrong leaves).

---

## 5. Proposed Fix: FastText Group-Consistency Gate

The most principled fix that addresses the expert's "never let ML override" guidance:

```
In _run_name_origin_cascade, before accepting fastText prediction:

1. Run the scorer to get scorer_result (may abstain with group hint)
2. If scorer identified a group (e.g., SOUTH_ASIAN):
   - Only accept fastText if ft_label is in the SAME group
   - Otherwise, return the scorer's R0+group result
3. If scorer has no group hint:
   - Accept fastText normally (current behavior)
```

This implements the hierarchical principle: rules determine the group, ML can only refine within that group. An Indian surname that the scorer identifies as SOUTH_ASIAN should never become A1 just because fastText says so.

**Expected impact:** Blocks Venkataraman→A1, Subramaniam→A1, Benali→A2. These become R0 with group_region set (SOUTH_ASIAN, SOUTH_ASIAN, SSA respectively).

---

## 6. Remaining Structural Limitations

### 6a. Hispanic diaspora is unresolvable without CC
Names like "Rodriguez, Alex" or "Lopez, Jennifer" have genuine onomastic ambiguity between A1 (Anglo diaspora) and G1 (Latin American). The expert acknowledged this: "For name-origin, this is often not a true leaf problem." The system correctly identifies both regions as candidates. Without CC, there's no ground truth.

### 6b. Arabic/Persian boundary is historically fluid
Al-Khwarizmi lived in the Abbasid Caliphate (C3/C4) but was from Khwarezm (C1/C2). Many historical Islamic scholars operated across the Arabic-Persian boundary. The C2/C3/C4 distinction is more geographical than onomastic.

### 6c. South Asian sub-regional disambiguation
D1/D2/D3 distinguish Hindi-belt, Dravidian, and Bengali naming traditions. These overlap significantly — Chakraborty is Bengali (D3) but common in India (D1). The test expectations may need review.

### 6d. FastText trained on institution-country, not name-origin
The fundamental issue: OpenAlex `country_code` reflects where a mathematician works, not where their name originates. Retraining on birth-country labels (from Wikidata) would be more aligned, but the 10K Wikidata dataset lacks the diversity of OpenAlex.

---

## 7. Questions for Expert

### Question 1: FastText group-consistency gate
Should we implement the gate described in Section 5 — blocking fastText predictions that contradict a scorer group hint? This trades 3 wrong leaves for 3 honest R0+group results, improving precision from 88% to 91%.

### Question 2: Diaspora handling in KPIs
The 4 Hispanic diaspora cases (Hernandez/Rodriguez/Lopez/Gonzalez with Anglo given names) are genuinely ambiguous. Should we:
- (a) Exclude them from precision KPI (they're already xfail in tests)?
- (b) Return R0 for these specifically (detect A1/G1 competition and abstain)?
- (c) Return the result with `conflict=True` (like we do for CC-based diaspora)?

### Question 3: South Asian test expectations
Should D1 test expectations for Bengali names (Chakraborty) be changed to D3? And Dravidian names (Ramanathan) to D2? The onomastic signal clearly points to D3 and D2 respectively. D1 seems to be a "default India" label rather than a correct onomastic label.

### Question 4: Retraining fastText on birth-country labels
Would it be worth retraining the surname classifier on Wikidata birth-country labels instead of OpenAlex institution-country? We now have 10K Wikidata entries with birth-country. The risk is less diversity (Wikidata skews historical European).

### Question 5: Is the current architecture hitting its ceiling?
With all handcrafted patterns, medium suffixes, learned features, and fastText ML — are we at the practical limit of what name-only classification can achieve? The remaining failures are:
- 4 genuinely ambiguous diaspora cases
- 3 ML training-data bias issues
- 2 within-group leaf ambiguities
- 2 Arabic/Persian historical boundary cases

Is it worth pursuing further improvements, or should we declare the name-origin branch "good enough" and focus on other system features (pipeline, API, genealogy graph)?

---

## 8. System Architecture (Current State)

```
Entry → _infer_geo()  ─── CC → ROR → DOI ─────────────────────┐
     → _infer_name_origin()                                    │
           ├─ surname exact match (STRONG surnames list)        │
           ├─ CJK hybrid detection                             │
           ├─ script + priority scorer                         │
           │    ├─ Tier 1: SIGNATURE_SUFFIXES (22, wt 2.5)     │
           │    ├─ Tier 2: MEDIUM_SUFFIXES (11 leaf, 4 group)  │
           │    ├─ handcrafted (prefixes, particles, givens)    │
           │    └─ Tier 3: learned features (tiebreaker, +0.4) │
           ├─ ICU normalization                                │
           ├─ FastText language detection                      │
           ├─ FastText surname classifier (CLI, gated)  ←ISSUE │
           └─ R0 (terminal abstain)                            │
                                                               ▼
     → _merge_geo_name() ─── CC wins? → geo primary
                          └── no CC?  → name primary
```

**Training data:** 26,323 entries (500 golden + 10,724 Wikidata + 1,019 OpenAlex robust + 15,120 OpenAlex 15K)

**Models:**
- surname_classifier.ftz (48MB, quantized) — invoked via CLI subprocess
- config/learned_features.json (20KB) — territory roll-up mining

**Constants:**
- SIGNATURE_SUFFIXES: 22 entries (Tier 1)
- MEDIUM_SUFFIXES_TO_LEAF: 11 entries (Tier 2 leaf)
- MEDIUM_SUFFIXES_TO_GROUP: 4 entries (Tier 2 group)
- REGION_GROUPS: 23 groups, 34 leaves mapped
- _STRONG: per-region handcrafted patterns
- _MEDIUM: per-region medium-weight patterns

---

## 9. File Inventory

| File | Role | Size |
|------|------|------|
| `src/regions/manager_optimized.py` | Core detection engine | ~6,200 lines |
| `tools/mine_features.py` | Feature mining (territory roll-up) | ~400 lines |
| `scripts/data/fetch_wikidata_mathematicians.py` | Wikidata SPARQL fetch | ~280 lines |
| `scripts/data/fetch_openalex_training.py` | OpenAlex data fetch | ~200 lines |
| `config/learned_features.json` | Mined features (v2.0) | 20 KB |
| `data/wikidata_mathematicians.json` | 10,724 mathematicians | 4.3 MB |
| `data/ml_training/surname_classifier.ftz` | fastText model (quantized) | 48 MB |
| `data/ml_training/surname_classifier.bin` | fastText model (full) | 383 MB |
| `tests/unit/test_region_detection_accuracy.py` | 1,060+ detection tests | ~2,800 lines |
| `tests/fixtures/golden_mathematicians.json` | 500 verified entries | 0.1 MB |
