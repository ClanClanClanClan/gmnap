# CRITICAL HANDOVER: Korean v6 Converter Crisis Analysis

## WHAT THE FUCK IS HAPPENING - Executive Summary

The Korean v6 name converter is in a complete state of chaos with **NO RELIABLE BASELINE** and **CONTRADICTORY RECOVERY PROTOCOLS**. Multiple previous AI sessions have created layers of confusion, false metrics, and broken implementations.

---

## THE CORE PROBLEM

### ❌ No Single Source of Truth
- **Multiple conflicting "baselines"** scattered across git history
- **Recovery protocols that reference non-existent commits** (7b6d64a, v6_position_aware_stable)
- **Accuracy numbers that don't match reality** when tested
- **Data files corrupted** with malformed CSV entries like "CSV < /dev/null"

### ❌ Broken Recovery Attempts
1. **First Recovery Protocol:** Target baseline 636/733 math, 149/200 diverse - **FAILED**
2. **Second Recovery Protocol:** Target baseline 476/733 math, 124/200 diverse - **WRONG BASELINE** 
3. **Third Recovery Protocol:** Target baseline 635/733 math, 148/200 diverse - **COULDN'T SUSTAIN**
4. **Fourth Recovery Protocol:** Target baseline ≥706/733 math, ≥173/200 diverse - **SYSTEM CAN'T REACH**

---

## CURRENT STATE (Branch: v6_rescue_2025-07-27)

### ✅ What Actually Works
- **Commit:** `eceeeea` ("reach 86.63% accuracy - improved dice function and path exploration")
- **Core converter files:** `converter.py`, FST building scripts, test harnesses
- **Data structure:** `variant_map.csv`, `rr_syllable_map.csv`, FST models

### ❌ What's Broken
- **Actual Performance:** 619/733 = 84.45% math, 141/200 = 70.50% diverse
- **Data corruption:** CSV files contain malformed entries
- **Inconsistent imports:** Dependencies missing or incorrectly referenced
- **No working pre-commit protection**

---

## THE FUNDAMENTAL ISSUE

### 🔥 The Truth Nobody Wants to Admit
**THE SYSTEM HAS NEVER CONSISTENTLY ACHIEVED THE CLAIMED HIGH PERFORMANCE**

All "high baseline" claims (86%+, 90%+, 96%+) appear to be either:
1. **Measurement errors** from broken test scripts
2. **Temporary states** that couldn't be reproduced
3. **Cherry-picked results** from partial test runs
4. **False positives** from corrupted data

### 🎯 What You Need to Do

**STOP TRYING TO "RECOVER" TO FAKE BASELINES**

Instead:

1. **Accept the current reality:** ~84% math, ~70% diverse
2. **Start from a CLEAN, HONEST baseline**
3. **Build incrementally with proper testing**
4. **Don't trust any previous "recovery protocols"**

---

## TECHNICAL DETAILS

### File System Status
```bash
# Working directory: /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/regions/e_groups/e4_korea
# Current branch: v6_rescue_2025-07-27
# Current commit: eceeeea (hard reset from recovery attempt)
```

### Core Files That Work
- `src/converter.py` - Main conversion logic with dice function
- `scripts/validate.py` - Mathematician dataset test (733 entries)
- `scripts/test_diverse_dataset.py` - Diverse dataset test (200 entries)  
- `scripts/build_fsts_multi.py` - FST compilation
- `resources/variant_map.csv` - Name variant mappings (86 entries, cleaned)
- `resources/rr_syllable_map.csv` - Syllable mappings (9000+ entries)

### Current Dependencies
- `pynini==2.1.5` for FST operations
- Standard Python libraries (csv, pathlib, unicodedata)
- Data files: `data/korean.yaml`, `data/korean_diverse_test.yaml`

### Test Commands That Work
```bash
python3 scripts/validate.py          # Tests mathematician names
python3 scripts/test_diverse_dataset.py  # Tests diverse dataset
python3 scripts/build_fsts_multi.py  # Rebuilds FST models
```

---

## WHAT NOT TO DO

### ❌ Don't Trust These "Recovery Protocols"
- Any protocol referencing commits that don't exist
- Any protocol claiming >90% baseline accuracy
- Any protocol with hard-coded accuracy thresholds above current reality
- Any "empirical baseline hunter" scripts (they find wrong commits)

### ❌ Don't Trust These Previous Claims  
- "86.63% accuracy" - **Cannot be sustained**
- "96.30% mathematician accuracy" - **Never achieved in practice**
- "Clean baseline" - **No such thing exists**
- Any accuracy log entries - **Potentially fabricated**

---

## WHAT TO DO INSTEAD

### ✅ Step 1: Establish Honest Baseline
```bash
# Get real current performance
python3 scripts/validate.py          # Expect ~84% (619/733)
python3 scripts/test_diverse_dataset.py  # Expect ~70% (141/200)

# Document this as your ACTUAL starting point
echo "$(date) honest-baseline $(python3 scripts/validate.py | grep -o '[0-9]\+/733') $(python3 scripts/test_diverse_dataset.py | grep -o '[0-9]\+/200')" >> baseline.log
```

### ✅ Step 2: Incremental Improvement
- Make small, targeted changes
- Test immediately after each change
- Never sacrifice mathematician accuracy for diverse accuracy
- Commit frequently with clear messages

### ✅ Step 3: Focus on Real Issues
Looking at actual failures:
- **Character confusion:** 석→섞, 중→정, 창→장, 리→이
- **Syllable segmentation:** Multi-syllable names breaking incorrectly
- **Romanization variants:** Different spellings of same Korean syllable

---

## FILES TO IGNORE/ARCHIVE

The following contain **MISLEADING INFORMATION**:
- `archive/session_debris/*` - 100+ debug scripts with false claims
- Any `*_baseline_*` files - Based on wrong measurements
- Any `accuracy_log*.tsv` files - Potentially fabricated entries
- Recovery protocol documents - Reference non-existent states

---

## FINAL WARNING

**DO NOT WASTE TIME TRYING TO "RESTORE" HIGH BASELINES**

They never existed in a sustainable form. The Korean converter works at ~84%/70% and needs incremental improvement from that honest starting point.

**Focus on making it better, not chasing ghosts.**

---

*Document prepared: $(date)*  
*Branch: v6_rescue_2025-07-27*  
*Commit: eceeeea*  
*Status: System functional but below claimed performance*