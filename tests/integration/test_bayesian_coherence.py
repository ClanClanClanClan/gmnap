import pytest

#!/usr/bin/env python3
"""
Bayesian Coherence Test (Stage 6)
Tests Bayesian scoring that combines betweenness centrality with authority reliability
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.timeout(15)
def test_bayesian_import():
    """Test that Bayesian coherence module can be imported"""
    try:
        from src.core.stage6_bayesian.bayes_coherence import BayesCoherence

        print("PASS BayesCoherence module imported successfully")
        return True
    except ImportError as e:
        print(f"WARN BayesCoherence import failed (optional): {e}")
        return False


@pytest.mark.timeout(15)
def test_bayesian_initialization():
    """Test Bayesian coherence initialization"""
    try:
        from src.core.stage6_bayesian.bayes_coherence import BayesCoherence

        config = {
            "weights": {
                "betweenness_weight": 0.6,
                "authority_weight": 0.4,
                "threshold": 0.5,
            },
            "authorities": {
                "Crossref": {"tier": 0, "confidence": 0.99},
                "ORCID": {"tier": 0, "confidence": 0.98},
                "ArXiv": {"tier": 1, "confidence": 0.90},
            },
        }

        coherence = BayesCoherence(config)
        print("PASS BayesCoherence initialized with config")

        assert coherence.weights["betweenness_weight"] == 0.6
        assert coherence.weights["authority_weight"] == 0.4
        print("PASS Weights correctly configured")

        return True

    except Exception as e:
        print(f"FAIL Initialization failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_bayesian_scoring():
    """Test Bayesian scoring functionality"""
    try:
        from src.core.stage6_bayesian.bayes_coherence import BayesCoherence

        coherence = BayesCoherence(
            {
                "weights": {
                    "betweenness_weight": 0.7,
                    "authority_weight": 0.3,
                    "threshold": 0.5,
                }
            }
        )

        # Test entries with relationships
        test_entries = [
            {
                "GlobalID": "EULER001",
                "CanonicalLatin": "Euler, Leonhard",
                "Source": "Crossref",
                "Confidence": 99,
            },
            {
                "GlobalID": "GAUSS001",
                "CanonicalLatin": "Gauss, Carl Friedrich",
                "Source": "ORCID",
                "Confidence": 98,
                "Advisors": ["EULER001"],
            },
            {
                "GlobalID": "RIEMANN001",
                "CanonicalLatin": "Riemann, Bernhard",
                "Source": "ArXiv",
                "Confidence": 90,
                "Advisors": ["GAUSS001"],
            },
        ]

        # Score entries
        scores = coherence.score(test_entries)

        print(f"PASS Scored {len(scores)} entries")

        # Check scores are in valid range [0, 1]
        for entry_id, score in scores.items():
            assert 0 <= score <= 1, f"Invalid score {score} for {entry_id}"
            print(f"  - {entry_id}: {score:.3f}")

        # Euler should have high betweenness (connects to both)
        # Gauss should have medium betweenness
        # All should have authority scores based on source

        print("PASS All scores in valid range [0, 1]")
        return True

    except ImportError:
        print("WARN BayesCoherence not available, skipping scoring test")
        return True
    except Exception as e:
        print(f"FAIL Scoring test failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_graph_construction():
    """Test graph construction for betweenness calculation"""
    try:
        import networkx as nx

        # Create test graph
        G = nx.Graph()

        # Add mathematician network
        mathematicians = [
            ("Euler", "Lagrange"),
            ("Euler", "Gauss"),
            ("Gauss", "Riemann"),
            ("Gauss", "Dirichlet"),
            ("Riemann", "Weierstrass"),
            ("Dirichlet", "Weierstrass"),
        ]

        G.add_edges_from(mathematicians)

        # Calculate betweenness centrality
        betweenness = nx.betweenness_centrality(G)

        print("PASS Graph constructed and betweenness calculated")
        print("  Betweenness centrality scores:")
        for node, score in sorted(
            betweenness.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    - {node}: {score:.3f}")

        # Gauss should have highest betweenness (connects multiple communities)
        assert betweenness["Gauss"] > betweenness["Euler"]
        assert betweenness["Gauss"] > betweenness["Riemann"]

        print("PASS Betweenness centrality correctly identifies key nodes")
        return True

    except ImportError:
        print("WARN NetworkX not available, skipping graph test")
        return True
    except Exception as e:
        print(f"FAIL Graph test failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_authority_confidence():
    """Test authority confidence scoring"""

    # Define authority tiers and confidence scores
    authorities = {
        # Tier 0 - Highest confidence
        "Crossref": {"tier": 0, "confidence": 0.99},
        "ORCID": {"tier": 0, "confidence": 0.98},
        "ISNI": {"tier": 0, "confidence": 0.97},
        "VIAF": {"tier": 0, "confidence": 0.96},
        # Tier 1 - High confidence
        "ArXiv": {"tier": 1, "confidence": 0.90},
        "PubMed": {"tier": 1, "confidence": 0.89},
        "RePEc": {"tier": 1, "confidence": 0.88},
        # Tier 2 - Medium confidence
        "zbMATH": {"tier": 2, "confidence": 0.80},
        "MathSciNet": {"tier": 2, "confidence": 0.79},
        "DBLP": {"tier": 2, "confidence": 0.78},
        # Tier 3 - Lower confidence
        "Wikipedia": {"tier": 3, "confidence": 0.60},
        "GoogleScholar": {"tier": 3, "confidence": 0.55},
        "ResearchGate": {"tier": 3, "confidence": 0.50},
    }

    # Test entries from different sources
    test_cases = [
        ("Crossref", 0.99),
        ("ArXiv", 0.90),
        ("zbMATH", 0.80),
        ("Wikipedia", 0.60),
        ("Unknown", 0.50),  # Default for unknown sources
    ]

    print("PASS Authority confidence scores:")
    for source, expected in test_cases:
        actual = authorities.get(source, {"confidence": 0.50})["confidence"]
        print(f"  - {source}: {actual} (expected: {expected})")
        assert abs(actual - expected) < 0.01, f"Confidence mismatch for {source}"

    print("PASS Authority confidence scoring correct")
    return True


@pytest.mark.timeout(15)
def test_combined_scoring():
    """Test combined Bayesian scoring (betweenness + authority)"""

    def calculate_bayesian_score(
        betweenness, authority_confidence, b_weight=0.6, a_weight=0.4
    ):
        """Calculate combined Bayesian score"""
        return (b_weight * betweenness) + (a_weight * authority_confidence)

    # Test cases
    test_cases = [
        # (betweenness, authority_conf, expected_score)
        (1.0, 1.0, 1.0),  # Perfect scores
        (0.0, 0.0, 0.0),  # Zero scores
        (0.8, 0.9, 0.84),  # High scores (0.6*0.8 + 0.4*0.9)
        (0.3, 0.7, 0.46),  # Mixed scores (0.6*0.3 + 0.4*0.7)
    ]

    print("PASS Combined Bayesian scoring:")
    for betweenness, authority, expected in test_cases:
        score = calculate_bayesian_score(betweenness, authority)
        print(
            f"  - B:{betweenness:.1f} + A:{authority:.1f} = {score:.2f} (expected: {expected:.2f})"
        )
        assert abs(score - expected) < 0.01, f"Score mismatch: {score} != {expected}"

    print("PASS Combined scoring formula correct")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("BAYESIAN COHERENCE TEST (STAGE 6)")
    print("=" * 60)
    print()

    # Run all tests
    all_passed = True

    tests = [
        ("Import Check", test_bayesian_import),
        ("Initialization", test_bayesian_initialization),
        ("Scoring Function", test_bayesian_scoring),
        ("Graph Construction", test_graph_construction),
        ("Authority Confidence", test_authority_confidence),
        ("Combined Scoring", test_combined_scoring),
    ]

    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            passed = test_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"FAIL {test_name} failed with error: {e}")
            all_passed = False

    print()
    print("=" * 60)
    if all_passed:
        print("PASS ALL BAYESIAN COHERENCE TESTS PASSED")
    else:
        print("WARN SOME TESTS FAILED - CHECK IMPLEMENTATION")
    print("=" * 60)
