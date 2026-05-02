# MathLineage — Architecture (reviewer one-pager)

**Audience:** someone evaluating whether this project is methodologically
sound. For a deep dive, see `docs/ARCHITECTURE_DEFINITIVE.md` (605
lines) and `docs/EXPERT_CONSULTATION_*.md` (the onomastics expert's
review thread). This file is a 10-minute read that answers the five
questions a reviewer asks first.

---

## 1. Why separate "where was this person born" from "what culture does this name come from"?

The single most important design decision in the system.

Given a mathematician like **T. Tao**:
- **Geo** (citizenship, affiliation, birthplace): Australia → A1 (Anglo-Sphere)
- **Name-origin** (etymology of the name string): E1 (Chinese)

A naive system that only looks at one axis either (a) classifies him by
birthplace and misses the Chinese heritage or (b) classifies him by
surname and claims he works in China. Both are wrong for different
queries. We keep both axes visible on every record:

```python
# RegionDetectionResult (src/regions/manager_optimized.py:2951)
region_code:      str           # canonical, primary
geo_region:       Optional[str] # derived from CC → ROR → DOI
name_region:      Optional[str] # derived from the name string
group_region:     Optional[str] # broader group (e.g. ANGLO_SPHERE)
resolution_level: Optional[str] # "leaf" | "group" | "abstain"
candidates:       Optional[List] # ranked alternatives
conflict:         bool           # True when geo ≠ name (the "diaspora" case)
```

The external reviewer called this out explicitly in
`docs/EXPERT_CONSULTATION_PHASE5.md`: "the split architecture is what
turns this from a name classifier into an authority record — the two
axes are rarely the same signal and collapsing them throws away real
information."

**File:** `src/regions/manager_optimized.py` (the split resolution
logic sits in `detect_region()` + `_infer_name_origin_fast()`).

---

## 2. Why three tiers of surname signals instead of one?

Given a surname, we could ask fastText for a prediction and be done.
We don't, because fastText is confidently wrong on the boundary cases
that matter — e.g. it routinely sends Soviet-era names to Poland (B2)
when they should be East-Slavic (B1), because the training corpus
under-represents Central Asia.

Instead we use three tiers that each cover a different evidence
strength:

| Tier | Example suffixes | Action |
|---|---|---|
| **SIGNATURE** (22) | `-ović`, `-ский`, `-esco`, `-fsson`, `-oğlu` | Fire leaf directly (score 2.5) |
| **MEDIUM_TO_LEAF** (11) | `-ski`, `-sky`, `-ov` | Fire leaf only when corroborated; otherwise fire group |
| **MEDIUM_TO_GROUP** (4) | bare `-ou`, `-is` (Hellenic) | Fire group only — the ambiguity is inherent |

This tiering is what makes **honest abstention** possible (see §4).

**Files:**
- Constants: `src/regions/manager_optimized.py` (search `SIGNATURE_SUFFIXES`,
  `MEDIUM_SUFFIXES_TO_LEAF`, `MEDIUM_SUFFIXES_TO_GROUP`).
- Scorer: `_infer_name_origin_fast` in the same file.

---

## 3. Why does fastText need a same-group gate?

fastText's top prediction can silently cross groups (e.g. predict
Hungarian A2 for a name whose rule-based scorer said it's Slavic B1).
When that happens, the model is overriding our calibrated rules with
something that looks statistically confident but is structurally
different.

Rule: **fastText can only refine within the scorer's group, never
cross groups.** If the scorer says B1/B2 ambiguity (both Slavic) and
fastText says B1, great — accept. If the scorer says B1 and fastText
says A2, abstain.

**File:** `src/regions/manager_optimized.py` — the
`_detect_by_surname_fasttext` method checks `label in self.IMPLEMENTED_REGIONS`
AND that the label matches the scorer's group.

---

## 4. Why abstain (R0) instead of forcing the most-likely answer?

On the 843-entry adjudicated benchmark, forcing a leaf on every entry
gives ~56 % accuracy against *citizenship* labels — which is the wrong
comparison (name-origin ≠ citizenship). The right metric is
**leaf-precision on emitted leaves**, and there abstaining on hard
cases lifts us to **100 % precision on 523 entries** (`482/482` correct
emitted leaves, with 41 honest R0 + group abstentions).

Downstream consumers always have a choice:
- Need a leaf? Use `region_code` (may be R0).
- Need *any* region signal? Use `group_region` (always present when
  there's enough evidence to even name the family).
- Need a ranked list? Use `candidates`.

Honest abstention preserves calibration; forcing answers destroys it.

**Benchmark:** `tests/fixtures/name_origin_benchmark.json` (843
entries, three-track evaluation in
`tests/unit/test_benchmark_evaluation.py`).

---

## 5. How was the operating point chosen?

The four threshold knobs (`GMNAP_SCORER_MIN_SCORE`,
`GMNAP_SCORER_MIN_MARGIN`, `GMNAP_FASTTEXT_P1`, `GMNAP_FASTTEXT_MARGIN`)
were swept by `tools/rc_curve.py` across 16 operating points. The
finding (in `docs/risk_coverage.md`):

> Across all 16 operating points, coverage varies by only 0.001 and
> leaf-precision by 0.001. The four threshold knobs studied here are
> **not the dominant lever** on this benchmark — most abstentions
> happen earlier in the pipeline (no surname signal at all) and never
> reach these thresholds.

This is an important null result. It tells the expert "we looked and
confirmed: knobs don't matter once the tiered scorer is in place."
Real leverage is in the rule families, not the thresholds.

---

## 12-stage pipeline (one-liner each)

All stages are in `src/core/pipeline_v7.py`. Stages 0–8 are async,
9–11 are sync.

| # | Stage | What it does |
|---|---|---|
| 0 | `_stage_0_config` | Validate mode, credentials, schema version |
| 1 | `_stage_1_ingest` | NFC → NFKD → fold → NFC Unicode normalization |
| 1b | `_stage_1b_llm_etd` | **NOT wired into V7** — `pipeline_v7.py:373` has the entry commented out (`# TODO: Implement`). The class `LLMExtractETDStage` exists at `src/pipeline/stage_1b_llm_extract.py` but the pipeline never calls it. Activate by un-commenting + setting `pipeline.enable_llm_extraction: True` + configuring an LLM provider. |
| 2 | `_stage_2_detect_region` | The split geo/name-origin detection above |
| 3 | `_stage_3_region_hooks` | `clean → augment → validate → order_key` per region |
| 4 | `_stage_4_authority_enrich` | 9 tier-0/1 sources (OpenAlex, Crossref, ORCID, …) |
| 5 | `_stage_5_collision_analytics` | DuckDB + in-memory fallback duplicate detection |
| 6 | `_stage_6_graph_consistency` | Bayesian coherence; optional Memgraph |
| 7 | `_stage_7_short_form_tagging` | Initials clustering (e.g. "J. R. R." → "Tolkien") |
| 8 | `_stage_8_schema_validation` | v2.0 schema — advisory / quarantine / reject |
| 9 | `_stage_9_write_diff` | YAML snapshot + SQL/Cypher changelog |
| 10 | `_stage_10_report` | DOI draft, SFTP archive, `ATTRIBUTION.txt` |
| 11 | `_stage_11_idempotency_check` | Re-run must produce byte-identical output |

---

## Notable optimisations that matter for reviewers

1. **Persistent fastText CLI worker** (`FastTextCLIWorker` in
   `src/regions/manager_optimized.py`). Spawns one subprocess per
   process lifetime and pipes queries over stdin. ~60× faster than
   `subprocess.run(["fasttext", ...])` per query, and ~2.3× faster
   end-to-end on the synthetic benchmark (190 → 430 entries/s). Covered
   by `tests/unit/test_fasttext_cli_worker.py` (8 tests including
   respawn + concurrent access).
2. **Hashcash batching** in the web UI (`static/app.js:generateHashcash`).
   Batches 256 SHA-256 digests per `Promise.all` instead of awaiting
   per iteration → ~10× faster 18-bit mining in the browser.
3. **Curated genealogy JSON** (`data/genealogy_enrichment.json`,
   ~20,600 entries — Git LFS-tracked). Loaded once per process into
   the `GenealogyLookup` singleton; all CLI / API / web-UI enrichment
   goes through it. Diacritic- and particle-aware name matching covered
   by `tests/unit/test_genealogy_lookup.py` (23 tests).

---

## What this system is *not*

- **Not a general name-etymology service.** It's scoped to
  mathematicians because the MGP and Wikidata P184 graph gives us
  verifiable ground truth.
- **Not a citizenship predictor.** 56 % on citizenship labels looks bad
  until you realise that's the wrong target.
- **Not currently wired to Memgraph in production.** The graph DB
  code paths exist (`src/genealogy/load_memgraph.py`, the lineage
  endpoint's first-try branch), but production serves genealogy from
  the curated JSON. Graph store becomes worthwhile past ~100 k entries.
- **Not a replacement for the MGP.** Complements it: we add
  linguistic/regional signals, name-variant reconciliation, and a
  machine-readable schema over the top.
