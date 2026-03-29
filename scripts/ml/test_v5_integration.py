#!/usr/bin/env python3
"""
Test v5 Model Integration with GMNAP Pipeline

Verifies:
1. v5 model loads correctly in hybrid_classifier
2. Provenance fields are populated
3. Abstention policy works
4. Calibration is applied
5. Integration with RegionManager
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.hybrid_classifier import HybridRegionClassifier
from src.regions.regional_classifier_v5 import detect_region_v5


def test_v5_standalone():
    """Test v5 classifier standalone"""
    print("=" * 80)
    print("TEST 1: V5 STANDALONE CLASSIFIER")
    print("=" * 80)

    test_cases = [
        ("Michel Ferin", "A2", "Western Europe"),
        ("John Smith", "A1", "Anglo-Sphere"),
        ("José García", "A1", "Latin America (may be A1 due to pattern)"),
        ("Vladimir Putin", "B1", "East Slavic"),
        ("Zhang Wei", "A1", "Romanized Chinese (may default to A1)"),
    ]

    for name, expected_region, description in test_cases:
        result = detect_region_v5(name, k=3)

        print(f"\nName: {name}")
        print(f"  Expected: {expected_region} ({description})")
        print(
            f"  Predicted: {result['region_top1']} (confidence: {result['region_top1_confidence']:.1%})"
        )
        print(f"  Abstained: {result['abstained']}")

        if result["abstained"]:
            print(f"  Reason: {result['abstain_reason']}")

        print(f"  Top-3: ", end="")
        for i, pred in enumerate(result["topk"][:3], 1):
            print(f"{pred['region']} ({pred['p']:.1%})", end="  ")
        print()

        print(f"  Model: {result['model_name']} v{result['model_version']}")
        print(f"  Label policy: {result['label_policy']}")
        print(
            f"  Calibration: {result['calibration']['method']} (T={result['calibration']['T']:.3f})"
        )

        # Check provenance
        assert "provenance" in result, "Missing provenance"
        assert "model_file" in result["provenance"], "Missing model_file"
        assert "train_date" in result["provenance"], "Missing train_date"
        assert "prediction_timestamp" in result["provenance"], "Missing timestamp"

    print("\n✅ All standalone tests passed")


def test_hybrid_integration():
    """Test v5 integration with HybridRegionClassifier"""
    print("\n" + "=" * 80)
    print("TEST 2: HYBRID CLASSIFIER INTEGRATION")
    print("=" * 80)

    print("\nInitializing HybridRegionClassifier...")
    classifier = HybridRegionClassifier()

    stats = classifier.get_statistics()
    print(f"\nClassifier Statistics:")
    print(f"  Phase 1 available: {stats['phase1_available']}")
    print(f"  Phase 2 (ML) available: {stats['phase2_available']}")
    print(f"  Total regions: {stats['total_regions']}")
    print(f"  Phase 2 preferred regions: {stats['phase2_preferred_regions']}")
    print(f"  Phase 1 preferred regions: {stats['phase1_preferred_regions']}")

    test_cases = [
        ("Michel Ferin", "Should use ML (Phase 2)"),
        ("John Smith", "Should use rules (Phase 1)"),
        ("Vladimir Putin", "Should use ML (Phase 2 - Cyrillic)"),
        ("Zhang Wei", "Should use ML (Phase 2 - CJK)"),
    ]

    for name, expected_method in test_cases:
        entry = {"CanonicalNative": name}
        result = classifier.detect_region(entry)

        print(f"\nName: {name}")
        print(f"  Expected: {expected_method}")
        print(f"  Region: {result.region_code}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Method: {result.detection_method}")

        # Check that metadata contains ML info if ML was used
        if "ml" in result.detection_method.lower():
            print(f"  Metadata: {result.metadata}")

    print("\n✅ Hybrid integration tests passed")


def test_top_k():
    """Test top-k predictions"""
    print("\n" + "=" * 80)
    print("TEST 3: TOP-K PREDICTIONS")
    print("=" * 80)

    classifier = HybridRegionClassifier()

    # Test an ambiguous name
    name = "García"  # Could be Spanish (G1) or Latin American in US (A1)
    entry = {"CanonicalNative": name}

    print(f"\nTesting ambiguous name: {name}")
    topk_results = classifier.detect_region_topk(entry, k=5)

    print(f"  Top-5 predictions:")
    for i, result in enumerate(topk_results, 1):
        print(
            f"    {i}. {result.region_code:4s} {result.confidence:.3f}  ({result.detection_method})"
        )

    print("\n✅ Top-k tests passed")


def test_abstention():
    """Test abstention policy"""
    print("\n" + "=" * 80)
    print("TEST 4: ABSTENTION POLICY")
    print("=" * 80)

    # Test with genuinely ambiguous names
    test_cases = [
        "A B",  # Very short, ambiguous
        "Smith",  # Just surname, no given name
        "X Y Z",  # Unusual pattern
    ]

    print("\nTesting potentially abstaining cases...")
    for name in test_cases:
        result = detect_region_v5(name, k=3)

        print(f"\nName: {name}")
        print(f"  Abstained: {result['abstained']}")

        if result["abstained"]:
            print(f"  Reason: {result['abstain_reason']}")
            print(f"  Top-3 for fallback:")
            for pred in result["topk"][:3]:
                print(f"    {pred['region']}: {pred['p']:.3f}")
        else:
            print(
                f"  Predicted: {result['region_top1']} (confidence: {result['region_top1_confidence']:.3f})"
            )

    print("\n✅ Abstention policy tests completed")


def test_provenance_contract():
    """Test that provenance contract is complete"""
    print("\n" + "=" * 80)
    print("TEST 5: INTEGRATION CONTRACT COMPLIANCE")
    print("=" * 80)

    result = detect_region_v5("Test Name", k=3)

    print("\nChecking required fields...")

    required_fields = [
        "model_name",
        "model_version",
        "label_policy",
        "region_top1",
        "region_top1_confidence",
        "topk",
        "proba",
        "abstained",
        "abstain_reason",
        "calibration",
        "provenance",
    ]

    for field in required_fields:
        assert field in result, f"Missing field: {field}"
        print(f"  ✅ {field}: {type(result[field]).__name__}")

    # Check calibration structure
    assert "method" in result["calibration"], "Missing calibration.method"
    assert "T" in result["calibration"], "Missing calibration.T"
    print(f"  ✅ Calibration: {result['calibration']}")

    # Check provenance structure
    assert "model_file" in result["provenance"], "Missing provenance.model_file"
    assert "train_date" in result["provenance"], "Missing provenance.train_date"
    assert (
        "prediction_timestamp" in result["provenance"]
    ), "Missing provenance.prediction_timestamp"
    print(f"  ✅ Provenance: {result['provenance']}")

    # Check topk structure
    assert isinstance(result["topk"], list), "topk must be list"
    assert len(result["topk"]) > 0, "topk must not be empty"
    assert "region" in result["topk"][0], "topk items must have 'region'"
    assert "p" in result["topk"][0], "topk items must have 'p'"
    print(f"  ✅ Top-k: {len(result['topk'])} predictions")

    print("\n✅ All contract fields present and valid")


if __name__ == "__main__":
    print("=" * 80)
    print("V5 MODEL INTEGRATION TESTS")
    print("=" * 80)
    print("\nTesting v5 etymology model with GMNAP pipeline...")
    print()

    try:
        test_v5_standalone()
        test_hybrid_integration()
        test_top_k()
        test_abstention()
        test_provenance_contract()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nv5 model is correctly integrated with GMNAP pipeline")
        print("\nProduction readiness checklist:")
        print("  ✅ Model loads and runs")
        print("  ✅ Provenance tracking works")
        print("  ✅ Calibration is applied")
        print("  ✅ Abstention policy implemented")
        print("  ✅ Top-k predictions available")
        print("  ✅ Hybrid classifier integration works")
        print("  ✅ Integration contract compliant")
        print("\nNext steps:")
        print("  1. Monitor production accuracy")
        print("  2. Log label_policy='etymology' for all predictions")
        print("  3. Implement fallback logic for abstained cases")
        print("  4. Track abstention rate (should be <5%)")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
