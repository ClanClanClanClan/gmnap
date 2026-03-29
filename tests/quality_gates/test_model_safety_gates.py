"""
Test model safety gates to prevent deployment of inferior models.

This test enforces the expert's hard requirements for any new regional detection model:
- Must beat baseline by ≥1.5 pp on golden dataset
- No class can regress >2 pp
- Overall accuracy on golden dataset must be maintained or improved

Run this test before deploying any new model to production.
"""

import pytest
from pathlib import Path
from src.ml.model_gate import evaluate, gate, EvalReport
from src.regions.hybrid_classifier import HybridRegionClassifier


# Baseline performance from v4 hybrid (validated 2025-11-01)
BASELINE_OVERALL = 0.875  # 87.5% on golden dataset (7/8)
BASELINE_PER_CLASS = {
    "A1": 1.0,
    "A2": 1.0,
    "B1": 1.0,
    "E1": 1.0,
    "E4": 1.0,
    "G1": 0.0,  # José García was misclassified as E7 before expert router
}

# With expert's dynamic router (integrated 2025-11-01)
INTEGRATED_BASELINE_OVERALL = 1.0  # 100% on golden dataset (8/8)


def get_baseline_model_fn():
    """Get baseline model function (v4 hybrid with expert router)."""
    classifier = HybridRegionClassifier()

    def predict(name: str) -> str:
        result = classifier.detect_region({"CanonicalNative": name})
        return result.region_code

    return predict


def test_baseline_model_accuracy():
    """
    Test that baseline model (v4 hybrid + expert router) achieves expected accuracy.
    This establishes the performance threshold for all future models.
    """
    golden_path = "data/golden/GOLDEN_v2.csv"

    if not Path(golden_path).exists():
        pytest.skip(f"Golden dataset not found: {golden_path}")

    baseline_fn = get_baseline_model_fn()
    baseline_eval = evaluate(baseline_fn, golden_path)

    # With expert's router, we should get 100% (8/8)
    assert (
        baseline_eval.overall >= INTEGRATED_BASELINE_OVERALL
    ), f"Baseline model accuracy dropped: {baseline_eval.overall:.1%} < {INTEGRATED_BASELINE_OVERALL:.1%}"

    print(
        f"\n✅ Baseline accuracy: {baseline_eval.overall:.1%} ({int(baseline_eval.overall * 8)}/8)"
    )
    print(f"   Per-class: {baseline_eval.per_class}")


def test_model_safety_gate_enforcement():
    """
    Test that model safety gate correctly blocks inferior models.

    This simulates the CI/CD gate that prevents deployment of models that:
    - Don't beat baseline by ≥1.5 pp
    - Regress >2 pp on any class
    """
    # Simulate baseline (current v4 hybrid performance before router integration)
    baseline = EvalReport(
        overall=0.875, per_class={"A1": 1.0, "A2": 1.0, "B1": 1.0, "E1": 1.0, "E4": 1.0, "G1": 0.0}
    )

    # Test Case 1: Good candidate (beats baseline by 2.5 pp)
    good_candidate = EvalReport(
        overall=0.900, per_class={"A1": 1.0, "A2": 1.0, "B1": 1.0, "E1": 1.0, "E4": 1.0, "G1": 0.4}
    )
    assert gate(
        good_candidate, baseline, min_gain=0.015
    ), "Gate should PASS for model beating baseline by ≥1.5 pp"

    # Test Case 2: Marginal gain (<1.5 pp) - should FAIL
    marginal_candidate = EvalReport(
        overall=0.880, per_class={"A1": 1.0, "A2": 1.0, "B1": 1.0, "E1": 1.0, "E4": 1.0, "G1": 0.03}
    )
    assert not gate(
        marginal_candidate, baseline, min_gain=0.015
    ), "Gate should FAIL for model with <1.5 pp improvement"

    # Test Case 3: Class regression (>2 pp drop in A1) - should FAIL
    regressed_candidate = EvalReport(
        overall=0.920,  # Overall is better
        per_class={"A1": 0.75, "A2": 1.0, "B1": 1.0, "E1": 1.0, "E4": 1.0, "G1": 0.8},
    )
    assert not gate(
        regressed_candidate, baseline, min_gain=0.015
    ), "Gate should FAIL for model with >2 pp regression on any class"

    print("\n✅ Model safety gate enforcement working correctly")


def test_candidate_model_deployment_gate():
    """
    THIS IS THE CRITICAL TEST FOR CI/CD.

    Add a candidate model function here to test if it passes safety gates.
    If this test fails, the deployment MUST be blocked.

    Example usage:
        def candidate_model(name: str) -> str:
            # Your new model implementation
            return predicted_region

        candidate_eval = evaluate(candidate_model, "data/golden/GOLDEN_v2.csv")
        assert gate(candidate_eval, baseline_eval, min_gain=0.015)
    """
    golden_path = "data/golden/GOLDEN_v2.csv"

    if not Path(golden_path).exists():
        pytest.skip(f"Golden dataset not found: {golden_path}")

    # Get baseline performance
    baseline_fn = get_baseline_model_fn()
    baseline_eval = evaluate(baseline_fn, golden_path)

    # TODO: When testing a new candidate model, replace this with actual candidate
    # For now, test that baseline passes its own gate (sanity check)
    candidate_eval = baseline_eval

    passed = gate(candidate_eval, baseline_eval, min_gain=0.0)  # Use 0.0 for baseline vs baseline

    if not passed:
        failure_msg = f"""
        ❌ MODEL DEPLOYMENT BLOCKED ❌

        Candidate model FAILED safety gates:
        - Candidate overall: {candidate_eval.overall:.1%}
        - Baseline overall: {baseline_eval.overall:.1%}
        - Required gain: ≥1.5 pp

        Per-class performance:
        """
        for cls in set(baseline_eval.per_class.keys()) | set(candidate_eval.per_class.keys()):
            base_acc = baseline_eval.per_class.get(cls, 0.0)
            cand_acc = candidate_eval.per_class.get(cls, 0.0)
            diff = cand_acc - base_acc
            failure_msg += (
                f"\n        {cls}: {cand_acc:.1%} (baseline: {base_acc:.1%}, diff: {diff:+.1%})"
            )

        pytest.fail(failure_msg)

    print(f"\n✅ Model safety gate: PASSED")
    print(f"   Candidate: {candidate_eval.overall:.1%}")
    print(f"   Baseline: {baseline_eval.overall:.1%}")


def test_v5_fixed_would_be_blocked():
    """
    Regression test: Verify that v5_FIXED (which had 75% accuracy) would be blocked.

    This test documents the failure that led to expert's model gate requirement.
    """
    # v4 baseline
    baseline = EvalReport(
        overall=0.875, per_class={"A1": 1.0, "A2": 1.0, "B1": 1.0, "E1": 1.0, "E4": 1.0, "G1": 0.0}
    )

    # v5_FIXED performance (from V5_MODEL_FIX_DEPLOYMENT_SUMMARY_2025_10_31.md)
    v5_fixed = EvalReport(
        overall=0.75,  # 6/8 correct
        per_class={"A1": 1.0, "A2": 1.0, "B1": 1.0, "E1": 0.0, "E4": 1.0, "G1": 0.0},
    )

    # v5_FIXED should be BLOCKED (75% < 87.5% + 1.5% = 89%)
    assert not gate(
        v5_fixed, baseline, min_gain=0.015
    ), "v5_FIXED should be blocked by model gate (75% << 87.5% baseline)"

    print("\n✅ Regression test passed: v5_FIXED would be correctly blocked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
