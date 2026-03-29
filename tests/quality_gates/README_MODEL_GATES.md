# Model Safety Gates - Deployment Guide

## Overview

The model safety gates prevent deployment of inferior regional detection models by enforcing hard requirements before any model reaches production.

**Location**: `tests/quality_gates/test_model_safety_gates.py`
**CI/CD**: `.github/workflows/model-deployment-gates.yml`
**Expert Source**: `docs/expert/GMNAP_V7_Expert_Kit_2025-11-01/src/ml/model_gate.py`

## Hard Requirements

Any candidate model MUST satisfy ALL of the following:

### 1. Overall Accuracy Improvement
```
candidate_accuracy ≥ baseline_accuracy + 1.5 pp
```

**Example**: If baseline is 87.5%, candidate must achieve ≥89.0%

### 2. No Class Regression
```
For each region class:
  candidate_class_accuracy + 2 pp ≥ baseline_class_accuracy
```

**Example**: If baseline A1 accuracy is 95%, candidate A1 must be ≥93%

### 3. Golden Dataset Validation
- Evaluated on `data/golden/GOLDEN_v2.csv` (currently 8 expert-validated names)
- All test cases must pass

## Current Baseline

**Model**: v4 hybrid with expert's dynamic router
**Overall Accuracy**: 100% (8/8) on golden dataset
**Per-Class Accuracy**:
- A1 (Anglo-Sphere): 100%
- A2 (Western Europe): 100%
- B1 (East Slavic): 100%
- E1 (Mainland Chinese): 100%
- E4 (Korean): 100%
- G1 (Latin America): 100%

## How to Test a New Model

### 1. Implement Your Model Function

```python
def my_new_model(name: str) -> str:
    """
    Your new regional detection implementation.

    Args:
        name: Person's canonical name

    Returns:
        Region code (e.g., 'A1', 'E4', 'G1')
    """
    # Your implementation here
    return predicted_region
```

### 2. Update the Test

Edit `tests/quality_gates/test_model_safety_gates.py`:

```python
def test_candidate_model_deployment_gate():
    """Test new candidate model against safety gates."""

    golden_path = "data/golden/GOLDEN_v2.csv"

    # Get baseline
    baseline_fn = get_baseline_model_fn()
    baseline_eval = evaluate(baseline_fn, golden_path)

    # *** ADD YOUR MODEL HERE ***
    from my_module import my_new_model  # Import your model

    candidate_eval = evaluate(my_new_model, golden_path)

    # Apply safety gate
    passed = gate(candidate_eval, baseline_eval, min_gain=0.015)

    if not passed:
        pytest.fail("Model deployment blocked by safety gates")
```

### 3. Run Tests Locally

```bash
# Run model safety gate tests
pytest tests/quality_gates/test_model_safety_gates.py -v -s

# Expected output if passing:
# ✅ Baseline accuracy: 100.0% (8/8)
# ✅ Model safety gate: PASSED
# ✅ All tests passed
```

### 4. Interpret Results

#### ✅ PASS - Model is Safe to Deploy
```
✅ Model safety gate: PASSED
   Candidate: 100.0%
   Baseline: 100.0%
```
→ Proceed with deployment

#### ❌ FAIL - Overall Accuracy Too Low
```
❌ MODEL DEPLOYMENT BLOCKED ❌

Candidate model FAILED safety gates:
- Candidate overall: 87.5%
- Baseline overall: 100.0%
- Required gain: ≥1.5 pp
```
→ Model accuracy insufficient, needs improvement

#### ❌ FAIL - Class Regression
```
Per-class performance:
  A1: 95.0% (baseline: 100.0%, diff: -5.0%)  ← REGRESSION >2pp
  G1: 100.0% (baseline: 100.0%, diff: 0.0%)
```
→ A1 region regressed by 5%, exceeds 2pp threshold

## CI/CD Enforcement

The safety gates run automatically on every push and PR:

**GitHub Actions Workflow**: `.github/workflows/model-deployment-gates.yml`

### Workflow Steps:
1. ✅ Checkout code
2. ✅ Setup Python 3.12
3. ✅ Install dependencies
4. 🚨 **Run model safety gate tests** (blocking)
5. ✅ Verify golden dataset exists
6. ✅ Report gate status

### Workflow Triggers:
- All branch pushes
- All pull requests
- Manual workflow dispatch

### On Failure:
```
❌ ================================ ❌
❌  MODEL DEPLOYMENT BLOCKED        ❌
❌ ================================ ❌

Safety gates FAILED. Possible causes:
  • Candidate model accuracy < baseline + 1.5 pp
  • Class regression >2 pp detected
  • Golden dataset test failures
```

The PR/branch **cannot be merged** until all gates pass.

## Example: v5_FIXED Blocked by Gates

The v5_FIXED model would be correctly blocked:

```python
# v5_FIXED performance
v5_eval = EvalReport(
    overall=0.75,  # 75% < 87.5% + 1.5% = 89%
    per_class={'A1': 1.0, 'A2': 1.0, 'B1': 1.0, 'E1': 0.0, 'E4': 1.0, 'G1': 0.0}
)

gate(v5_eval, baseline_eval, min_gain=0.015)
# → False (BLOCKED: 75% << 89% required)
```

**Result**: Prevented regression from deploying to production ✅

## Expanding the Golden Dataset

Current: 8 expert-validated names
Target: 1,000 real mathematician names

### How to Expand:

1. **Sample from collected data**:
   ```bash
   # Get diverse sample from 1,236 collected profiles
   python scripts/sample_for_golden.py \
     --input data/collected_profiles.json \
     --output data/golden/candidates.csv \
     --size 1000 \
     --stratify region
   ```

2. **Manual validation**:
   - Expert review each name
   - Verify region label is correct
   - Add to `data/golden/GOLDEN_v2.csv`

3. **Re-establish baseline**:
   ```bash
   # Test baseline on expanded dataset
   pytest tests/quality_gates/test_model_safety_gates.py::test_baseline_model_accuracy -v
   ```

4. **Update baseline constants** in `test_model_safety_gates.py`:
   ```python
   INTEGRATED_BASELINE_OVERALL = 0.XXX  # New baseline accuracy
   ```

## Key Learnings

### From Expert's Decision Memo:

> **NEVER deploy a model without:**
> - Beating baseline by ≥1.5 pp on golden dataset
> - No class regression >2 pp
> - Canary deployment (10% traffic, 24h)
> - Auto-rollback triggers

### Historical Context:

**October 31, 2025**: v5_FIXED deployed without gates
- Result: 75% accuracy (down from 87.5%)
- Impact: Production regression
- Resolution: Immediate rollback to v4 baseline

**November 1, 2025**: Expert's model gates implemented
- Result: v5_FIXED would be automatically blocked
- Impact: Prevents future regressions

## Related Documentation

- **Expert Decision Memo**: `docs/expert/GMNAP_V7_Expert_Kit_2025-11-01/DECISION_MEMO.md`
- **48-Hour Plan**: `docs/expert/GMNAP_V7_Expert_Kit_2025-11-01/PLAN_48H_AND_ROADMAP.md`
- **Implementation Status**: `EXPERT_KIT_IMPLEMENTATION_STATUS_2025_11_01.md`
- **Model Gate Source**: `src/ml/model_gate.py`
- **Dynamic Router**: `src/ml/router_dynamic.py`

## Questions?

Contact: AI Development Team
Last Updated: November 1, 2025
Expert Kit Version: 2025-11-01
