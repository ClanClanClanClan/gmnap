#!/usr/bin/env python3
"""
Hybrid Regional Name Classifier - Phase 1 + Phase 2 Ensemble

Combines rule-based (Phase 1) and ML-based (Phase 2) detection:
- Phase 1: Context-aware rules for ambiguous Latin-script regions
- Phase 2: Morphological learning for distinctive patterns

Strategy: Region-based routing to use each system where it performs best.
Expected accuracy: 94-95% (vs 91.36% Phase 1, 91.91% Phase 2)
"""

from collections import namedtuple
from pathlib import Path
from typing import Dict, Optional, Set

try:
    import fasttext

    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False

from src.ml import router_dynamic
from src.regions.manager_optimized import RegionManager

# Detection result structure
DetectionResult = namedtuple(
    "DetectionResult", ["region_code", "confidence", "detection_method", "metadata"]
)


class HybridRegionClassifier:
    """
    Hybrid classifier combining Phase 1 (rules) and Phase 2 (ML).

    Routing Strategy:
    - Use Phase 2 for regions with distinctive morphological patterns
    - Use Phase 1 for context-dependent Latin-script regions
    - Fallback to Phase 2 for unimplemented regions
    """

    # Regions where Phase 2 ML outperforms Phase 1 rules
    # Updated based on v4_optimized performance (2025-10-27)
    PHASE2_PREFERRED: Set[str] = {
        # Excellent ML performance (>85%)
        "E1",  # Mainland Chinese: 90.9%
        "E3",  # Japanese: 97.1%
        "B1",  # East Slavic: 84.6%
        # Good ML performance (>70%)
        "E4",  # Korean: 75.5%
        "C2",  # Persian-Tajik: 72.2%
        "B3",  # Greek: 70.6%
        # Non-Latin scripts where ML works better than rules
        "E2",  # Traditional Chinese
        "E5",  # Vietnamese
        "E6",  # Mainland SEA
        "E7",  # Maritime SEA
        "C1",  # Turkic
        "C3",  # Levantine Arabic
        "C4",  # Gulf Arabic
        "C5",  # Maghreb Arabic
        "C6",  # Hebrew
        "C7",  # Armenian
        "C8",  # Georgian
        "C9",  # Caucasus Turkic
        "D1",  # Hindi Belt
        "D2",  # Dravidian
        "D3",  # Bengali
        "D4",  # Pakistani Urdu
        "D5",  # Sinhala
        "B2",  # South/Central Slavic
        # Fallback regions
        "H1",  # Historical
        "R0",  # Residual Latin
        "Z0",  # Quarantine
    }

    # Regions where Phase 1 rules outperform Phase 2 ML
    # Updated based on v4_optimized performance (2025-10-27)
    # Primarily Latin-script regions where surname patterns work better
    PHASE1_PREFERRED: Set[str] = {
        "A1",  # Anglo-Sphere: Surname patterns (80-90%) vs ML (69.2%)
        "A2",  # Western Europe: Surname patterns (85-95%) vs ML (68.7%)
        "A3",  # Nordic-Baltic: Surname patterns (70-80%) vs ML (57.1%)
        "G1",  # Latin America: Surname patterns (75-85%) vs ML (46.0%) ← CRITICAL
        "A4",  # Oceania: Rules better (limited features)
        "A5",  # Caribbean: Rules better (context-dependent)
        "F1",  # Francophone Africa: French surname patterns
        "F2",  # Anglophone Africa: English surname patterns
        "F3",  # Horn of Africa: Mixed, prefer rules
        "F4",  # Lusophone Africa: Portuguese surnames
    }

    def __init__(self, fasttext_model_path: Optional[str] = None, use_ml: bool = True):
        """
        Initialize hybrid classifier.

        Args:
            fasttext_model_path: Path to trained fastText model
            use_ml: Whether to use ML component (False = Phase 1 only)
        """
        # Initialize Phase 1 (always available)
        self.phase1 = RegionManager()

        # Initialize Phase 2 (optional)
        self.use_ml = use_ml and FASTTEXT_AVAILABLE
        self.phase2 = None

        if self.use_ml:
            if fasttext_model_path is None:
                # Default path - USE v4 BASELINE (Oct 4, 2025)
                # v4 baseline: 87.5% golden dataset, 92.98% on Tier 1 holdout (2,720 names)
                # BEST PERFORMING MODEL - DO NOT REPLACE unless new model beats 87.5%
                fasttext_model_path = "data/ml_training/regional_classifier.bin"

            model_path = Path(fasttext_model_path)
            if model_path.exists():
                try:
                    self.phase2 = fasttext.load_model(str(model_path))
                    print(f"✅ Loaded Phase 2 ML model: {model_path}")
                except Exception as e:
                    print(f"⚠️  Failed to load fastText model: {e}")
                    print("   Falling back to Phase 1 only")
                    self.use_ml = False
            else:
                print(f"⚠️  fastText model not found: {model_path}")
                print("   Falling back to Phase 1 only")
                self.use_ml = False

    def detect_region(self, entry: Dict) -> DetectionResult:
        """
        Detect region using hybrid approach.

        Strategy: Run both Phase 1 and Phase 2, then intelligently select.

        Args:
            entry: Name entry dict with 'CanonicalNative' field

        Returns:
            DetectionResult with region, confidence, method, metadata
        """
        # Step 1: Always run Phase 1 (fast, provides baseline)
        phase1_result = self.phase1.detect_region(entry)
        phase1_region = phase1_result.region_code
        phase1_conf = phase1_result.confidence

        # Step 2: Run Phase 2 if available
        if not self.use_ml or not self.phase2:
            # No ML available, use Phase 1 only
            return DetectionResult(
                region_code=phase1_region,
                confidence=phase1_conf,
                detection_method="phase1-only",
                metadata={"phase1_method": phase1_result.detection_method},
            )

        name = entry.get("CanonicalNative", "")
        if not name:
            # No name available, fall back to Phase 1
            return DetectionResult(
                region_code=phase1_region,
                confidence=phase1_conf,
                detection_method="hybrid-rules-fallback",
                metadata={"reason": "no_name"},
            )

        # Run Phase 2
        try:
            pred = self.phase2.predict(name, k=1)
            ml_region = pred[0][0].replace("__label__", "")
            ml_conf = float(pred[1][0])
        except Exception as e:
            # ML failed, fall back to Phase 1
            return DetectionResult(
                region_code=phase1_region,
                confidence=phase1_conf,
                detection_method="hybrid-rules-fallback",
                metadata={"error": str(e)},
            )

        # Step 3: Use expert's dynamic router (Nov 1, 2025 expert kit)
        # Solves José García problem with multi-label support

        # Create adapter functions for expert's router interface
        def phase1_fn(name_str):
            # Return router_dynamic.Result format
            return router_dynamic.Result(
                region=phase1_region,
                confidence=phase1_conf,
                distribution=None,  # Phase 1 doesn't provide distribution
            )

        def phase2_fn(name_str):
            # Return router_dynamic.Result format
            return router_dynamic.Result(
                region=ml_region,
                confidence=ml_conf,
                distribution=None,  # Could enhance later with top-k probabilities
            )

        # Call expert's dynamic router
        result = router_dynamic.route(
            name=name,
            phase1_fn=phase1_fn,
            phase2_fn=phase2_fn,
            phase1_calibration=None,  # Could add per-region accuracy calibration
            phase2_calibration=None,
        )

        # Convert expert's Result to DetectionResult
        metadata = {
            "phase1_region": phase1_region,
            "phase1_confidence": phase1_conf,
            "phase2_region": ml_region,
            "phase2_confidence": ml_conf,
            "routing_method": result.method,
        }

        # Add distribution if multi-label (Iberophone ambiguity)
        if result.distribution:
            metadata["distribution"] = result.distribution

        return DetectionResult(
            region_code=result.region,
            confidence=result.confidence,
            detection_method=f"hybrid-expert-{result.method}",
            metadata=metadata,
        )

    def detect_region_topk(self, entry: Dict, k: int = 3) -> list:
        """
        Detect top-k most likely regions for ambiguous cases.

        This is crucial for handling inherently ambiguous names like:
        - Hispanic surnames (A1/G1/A5 confusion)
        - A4/A1 overlap (without Māori markers)
        - Arabic names spanning regions (C3/D4/F3)

        Args:
            entry: Name entry dict with 'CanonicalNative' field
            k: Number of predictions to return (default: 3)

        Returns:
            List of DetectionResult tuples, sorted by confidence
        """
        results = []

        # Get Phase 1 prediction
        phase1_result = self.phase1.detect_region(entry)
        results.append(
            DetectionResult(
                region_code=phase1_result.region_code,
                confidence=phase1_result.confidence,
                detection_method="phase1",
                metadata={"source": "systematic_rules"},
            )
        )

        # Get Phase 2 predictions if available
        if self.use_ml and self.phase2:
            name = entry.get("CanonicalNative", "")
            if name:
                try:
                    # Get top-k from ML
                    pred = self.phase2.predict(
                        name, k=k * 2
                    )  # Get 2x for deduplication

                    for i in range(min(k * 2, len(pred[0]))):
                        ml_region = pred[0][i].replace("__label__", "")
                        ml_conf = float(pred[1][i])

                        results.append(
                            DetectionResult(
                                region_code=ml_region,
                                confidence=ml_conf,
                                detection_method="phase2-ml",
                                metadata={"source": "fasttext", "rank": i + 1},
                            )
                        )
                except Exception:
                    # ML failed, just use Phase 1
                    pass

        # Deduplicate and sort by confidence
        seen_regions = {}
        for result in results:
            region = result.region_code
            if (
                region not in seen_regions
                or result.confidence > seen_regions[region].confidence
            ):
                seen_regions[region] = result

        # Sort by confidence
        topk_results = sorted(
            seen_regions.values(), key=lambda x: x.confidence, reverse=True
        )[:k]

        return topk_results

    def get_routing_info(self, region: str) -> Dict:
        """
        Get routing information for a region.

        Args:
            region: Region code

        Returns:
            Dict with routing strategy and reasoning
        """
        if region in self.PHASE2_PREFERRED:
            return {
                "preferred_method": "Phase 2 (ML)",
                "reason": "Morphological patterns / perfect accuracy",
                "available": self.use_ml,
            }
        elif region in self.PHASE1_PREFERRED:
            return {
                "preferred_method": "Phase 1 (Rules)",
                "reason": "Context-aware disambiguation",
                "available": True,
            }
        else:
            return {
                "preferred_method": "Phase 1 (Default)",
                "reason": "No explicit routing preference",
                "available": True,
            }

    def get_statistics(self) -> Dict:
        """Get classifier statistics."""
        return {
            "phase1_available": True,
            "phase2_available": self.use_ml,
            "total_regions": 37,
            "phase2_preferred_regions": len(self.PHASE2_PREFERRED),
            "phase1_preferred_regions": len(self.PHASE1_PREFERRED),
            "default_regions": 37
            - len(self.PHASE2_PREFERRED)
            - len(self.PHASE1_PREFERRED),
            "expected_phase2_accuracy": "85-95% (non-Latin scripts)",
            "expected_phase1_accuracy": "75-85% (Latin scripts, surname patterns)",
            "expected_hybrid_accuracy": "82-88% (overall, based on v4_optimized + surname patterns)",
        }


# Convenience function for single-name detection
def detect_region_hybrid(name: str, fasttext_model_path: Optional[str] = None) -> str:
    """
    Detect region for a single name using hybrid classifier.

    Args:
        name: Person's name
        fasttext_model_path: Optional path to fastText model

    Returns:
        Region code (e.g., 'A1', 'E4')
    """
    classifier = HybridRegionClassifier(fasttext_model_path=fasttext_model_path)
    result = classifier.detect_region({"CanonicalNative": name})
    return result.region_code


if __name__ == "__main__":
    # Demo usage
    print("=" * 70)
    print("HYBRID REGION CLASSIFIER DEMO")
    print("=" * 70)
    print()

    classifier = HybridRegionClassifier()

    print("Classifier Statistics:")
    stats = classifier.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # Test cases
    test_names = [
        ("Vladimir Putin", "B1", "Phase 2"),
        ("Zhang Wei", "E1", "Phase 2"),
        ("John Smith", "A1", "Phase 1"),
        ("José García", "G1", "Phase 1"),
        ("Ahmed Al-Otaibi", "C4", "Phase 2"),
        ("Yuki Tanaka", "E3", "Phase 2"),
    ]

    print("Test Predictions:")
    for name, expected, expected_method in test_names:
        result = classifier.detect_region({"CanonicalNative": name})
        status = "✅" if result.region_code == expected else "❌"
        method_match = (
            "✓" if expected_method.lower() in result.detection_method else "✗"
        )

        print(
            f"  {status} {name:20} → {result.region_code} (conf: {result.confidence:.3f}) [{result.detection_method}] {method_match}"
        )

    print()
    print("=" * 70)
