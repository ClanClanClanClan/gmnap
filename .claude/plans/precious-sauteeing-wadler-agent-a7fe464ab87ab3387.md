# Region Detection Test Improvement Plan

## Current State Analysis

### File Under Modification
**Primary file:** `tests/unit/test_region_detection_accuracy.py` (2183 lines)

### Current Test Breakdown
- **REGION_TEST_CASES** (with CC): ~736 entries across 37 regions -- all use CountryCodes, exercising only the dict lookup at line 3158-3170 of manager_optimized.py
- **EXPANDED_NO_CC_CASES** (without CC): 91 entries covering only 21 of 37 regions -- the only tests that exercise the actual detection cascade
- **NO_CC_CASES**: Smaller earlier set of ~46 cases, also without CC
- **Accuracy gates**: 50% for NO_CC_CASES, 65% for EXPANDED_NO_CC_CASES, 98% for with-CC

### 16 Regions with ZERO No-CC Tests
C1 (Turkic), C2 (Persian-Tajik), C4 (Arabic Gulf), C5 (Arabic Maghreb), C6 (Hebrew), D3 (Bengali), D4 (Pakistan), D5 (Sinhala), E2 (Traditional Chinese), E6 (Mainland SEA), E7 (Maritime SEA), F3 (Horn of Africa), F4 (Lusophone Africa), H1 (Historical), R0 (Residual), Z0 (Quarantine)

### Detection Cascade (what we need to test)
The _detect_region_uncached_sync method at line 3145 follows this cascade when no CountryCode is present:
1. ML Ensemble (_detect_by_ml_ensemble) -- conf >= 0.85
2. Hybrid name detection (_detect_hybrid_name) -- conf >= 0.95
3. Surname pattern matching (_detect_by_surname) -- conf > 0.95
4. Script analysis with priority rules (_detect_by_script) -- conf >= 0.60
5. ICU processing (_detect_by_icu) -- conf >= 0.60
6. FastText language detection (_detect_by_language) -- conf >= 0.7
7. Affiliation/DOI/Diaspora hints
8. Fallback to R0

The _STRONG lexicon (lines 67-2120) contains surname lists, given name fragments, and suffix patterns for all 37 regions.

---

## Implementation Plan

### Phase 1: Expand EXPANDED_NO_CC_CASES to Cover All 37 Regions (~199 new cases)

Add 8-12 cases per missing region and 3-5 per under-covered region. Select names from the _STRONG lexicon.

#### New cases for 16 missing regions:

**C1 - Greater Turkic (10 cases):** Yilmaz/Mehmet, Ozturk/Ahmet, Mammadov/Eldar, Demir/Mustafa, Hasanov/Samir, Karimov/Alisher, Erdogan/Recep, Aliyev/Ilham, Polat/Osman, Sultanov/Ruslan

**C2 - Persian-Tajik (10 cases):** Hosseini/Mohammad, Ahmadi/Reza, Mohammadi/Ali, Rezaei/Hossein, Hashemi/Mehdi, Rahimizadeh/Ahmad, Karimi/Fatima, Jafari/Zahra, Rostami/Hassan, Bagheri/Ahmad

**C4 - Arabic Gulf (8 cases):** Al-Otaibi/Abdullah, Al-Qahtani/Mohammed, Al-Shammari/Sultan, Al-Mutairi/Khalid, Al-Dosari/Fahad, Al-Khalifa/Hamad, Al-Maktoum/Rashid, Al-Sabah/Nasser

**C5 - Arabic Maghreb (8 cases):** Belkacem/Rachid, Bouazza/Karim, Slimani/Sofiane, Messaoudi/Amine, Idrissi/Youssef, Boudiaf/Mohamed, Benmohamed/Tarek, Meziane/Mustapha

**C6 - Hebrew & Diaspora (8 cases):** Cohen/David, Levi/Sarah, Mizrahi/Yosef, Shapiro/Amos, Goldstein/Miriam, Friedman/Avraham, Rosenberg/Chaim, Abramowitz/Isaac

**D3 - Bengali (8 cases):** Chatterjee/Sourav, Banerjee/Abhijit, Sengupta/Arijit, Ghosh/Tanmoy, Bose/Indranil, Biswas/Prasenjit, Sarkar/Ananyo, Dutta/Arindam

**D4 - Pakistan/Urdu (8 cases):** Siddiqui/Muhammad, Qureshi/Imran, Chaudhry/Usman, Akhtar/Bilal, Rizvi/Kamran, Bokhari/Asif, Iqbal/Tariq, Nawaz/Ashfaque

**D5 - Sinhala (8 cases):** Jayawardena/Mahela, Wickramasinghe/Nuwan, Gunawardena/Chandana, Rajapaksa/Pradeep, Dissanayake/Dinesh, Senanayake/Chaminda, Karunaratne/Sanduni, Amarasekara/Dilani

**E2 - Traditional Chinese/HK (8 cases):** Hsueh/Chih-wei, Tsai/Hsin-yi, Hsu/Yu-chen, Wong/Ka-ming, Cheung/Siu-fung, Leung/Wai-keung, Lau/Yuk-lin, Chow/Yun-fat

**E6 - Mainland SEA (10 cases):** Srisawat/Somchai, Charoenrat/Siriporn, Rattanakosin/Nittaya, Phongsavanh/Bouasone, Sisavath/Khamla, Chanthavong/Phonethip, Sok/Sovann, Chea/Sophea, Kyaw/Aung, Htun/Mya

**E7 - Maritime SEA (10 cases):** Widodo/Joko, Gunawan/Budi, Setiawan/Andi, Firmansyah/Rizki, Santoso/Agus, Reyes/Maria, Bautista/Juan, Mendoza/Jose, Santos/Antonio, Cruz/Ana

**F3 - Horn of Africa (8 cases):** Tesfaye/Abebe, Bekele/Haile, Kebede/Dawit, Tadesse/Mulugeta, Getachew/Yohannes, Tsegaye/Alemayehu, Negash/Solomon, Wolde/Asefa

**F4 - Lusophone Africa (8 cases):** Dos Santos/Antonio, Neto/Carlos, Tavares/Manuel, Machado/Francisco, Marques/Pedro, Lopes/Jose, Rodrigues/Maria, Sousa/Joao

**H1 - Historical (5 cases, xfail):** Euler/Leonhard, Gauss/Carl Friedrich, Newton/Isaac, Euclid (mononym), Fibonacci/Leonardo

**R0 - Residual (5 cases, soft assert):** X/Y, Test/User, Aa/Bb, Q/Z, Admin/System

**Z0 - Quarantine (3 cases):** Belongs in security tests, not accuracy.

**Boost under-covered regions (+19):** A5 (+5), C9 (+4), D2 (+5), F1 (+5)

**Total: ~199 new no-CC cases, combined total ~290**

---

### Phase 2: Name Form Variation Tests (~120 new parametrized cases)

New section NAME_FORM_VARIATIONS testing 20 names in 6 formats each:
- "Surname, Given" (standard)
- "Given Surname" (reversed)
- "Surname, G." (initial)
- "G. Surname" (initial reversed)
- "SURNAME" (caps only)
- "surname" (lowercase only)

20 representative names: Ivanov (B1), Kowalski (B2), Papadopoulos (B3), Hosseini (C2), Hovhannisyan (C7), Ivanishvili (C8), Watanabe (E3), Choi (E4), Nguyen (E5), Zhang (E1), Okonkwo (F2), Tesfaye (F3), Jayawardena (D5), Chatterjee (D3), Hernandez (G1), Zimmermann (A2), Johansson (A3), Diop (F1), Slimani (C5), Bekele (F3)

Accuracy gate: 60% of all form variations should detect correctly.

---

### Phase 3: Academic Citation Format Tests (~40 cases)

New section ACADEMIC_CITATION_CASES testing 10 regions x 3-4 citation formats:
- "J. Smith" (initial + surname)
- "Smith, J." (surname + initial)
- "Smith, J.A." (surname + double initial)
- "Smith et al." (et al. suffix)
- "von Neumann, J." (particle + initial)

---

### Phase 4: Transliteration Variant Tests (~30 cases)

New section TRANSLITERATION_GROUPS testing ~10 groups of transliteration variants:
- Chebyshev/Tchebycheff/Tschebyschow -> B1
- Tchaikovsky/Tschaikowski/Chaikovsky -> B1
- Mao Zedong/Mao Tse-tung -> E1
- Kim Il-sung/Kim Ilsung/Kim Il Sung -> E4
- Erdogan/Erdogan (diacritic) -> C1
- etc.

All variants in a group should map to the same region.

---

### Phase 5: Raise Accuracy Gates

| Test | Current | New |
|---|---|---|
| test_statistical_accuracy_with_country_codes | 98% | 99.5% |
| test_no_cc_expanded_accuracy_gate | 65% | 75% |
| test_no_cc_accuracy_reasonable | 50% | 65% |
| test_statistical_accuracy_without_country_codes | 50% | 65% |
| NEW: test_overall_combined_accuracy_gate | -- | 95% |

---

### Phase 6: Deduplicate Existing Cases

Add test_no_duplicate_test_cases() to catch duplicates across all test lists at test time. Manually remove ~70 known duplicates from existing lists.

---

### Phase 7: Special Region Coverage (C9, D2, H1, R0, Z0)

- C9: Test with Azeri/Kumyk names, verify no misclassification as C1
- D2: Add 5 Dravidian-specific names (Subramaniam, Ramasamy, etc.)
- H1/R0/Z0: Use separate assertions (no crash, valid fallback) not accuracy gates

---

## Summary

| Category | Current | Added | New Total |
|---|---|---|---|
| With-CC cases | ~736 | 0 | ~736 |
| No-CC cases | 91 | +199 | ~290 |
| Name form variation | 0 | +120 | 120 |
| Academic citation | 0 | +40 | 40 |
| Transliteration variants | 0 | +30 | 30 |
| Dedup test | 0 | +1 | 1 |
| **Total new parametrized** | -- | **~390** | -- |

File grows from 2183 to ~2700 lines. Expected test count: ~1315 (up from ~886).

## Implementation Sequence

1. Dedup check + remove duplicates
2. Add no-CC cases for missing/under-covered regions
3. Add name form variation tests
4. Add academic citation tests
5. Add transliteration variant tests
6. Raise accuracy gates (LAST, after verifying pass rates)

## Verification

1. pytest tests/unit/test_region_detection_accuracy.py -v --tb=short
2. Verify all 37 regions have >= 5 no-CC cases
3. Verify no duplicates across all lists
4. Verify detection_method != "country-code" for no-CC tests
5. Run pytest -k "no_cc" to focus on no-CC accuracy

## Risks

1. F4 Lusophone Africa overlaps A2/G1 -> use xfail or exclude from strict gate
2. C4/C5 Arabic subregions may confuse with C3 -> accept some cross-region confusion
3. E7 Filipino overlaps G1 Latin American -> document as known limitation
4. H1/R0/Z0 are non-geographic -> separate assertion logic
