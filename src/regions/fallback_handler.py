#!/usr/bin/env python3
"""
Fallback Handler for Abstained ML Predictions

When ML classifier abstains (confidence < threshold), use fallback strategies:
1. Top-3 candidates + rule matching
2. Phase 1 rule-based detection
3. Graph priors (if person has known connections)
4. Default to R0 (Residual)

Based on expert guidance and integration contract.
"""

from typing import Dict, Optional, Tuple
from collections import namedtuple

DetectionResult = namedtuple(
    "DetectionResult", ["region_code", "confidence", "detection_method", "metadata"]
)


class FallbackHandler:
    """
    Handle abstained predictions with fallback strategies

    Usage:
        handler = FallbackHandler(phase1_classifier, graph_db=None)

        if ml_result['abstained']:
            fallback_result = handler.handle_abstention(
                name, ml_result, entry
            )
    """

    def __init__(self, phase1_classifier=None, graph_db=None):
        """
        Initialize fallback handler

        Args:
            phase1_classifier: Phase 1 rule-based classifier (RegionManager)
            graph_db: Optional graph database for prior extraction
        """
        self.phase1_classifier = phase1_classifier
        self.graph_db = graph_db

    def handle_abstention(
        self,
        name: str,
        ml_result: Dict,
        entry: Dict,
        use_phase1: bool = True,
        use_topk: bool = True,
        use_graph_priors: bool = True,
    ) -> DetectionResult:
        """
        Handle abstained prediction with fallback strategies

        Strategy priority:
        1. Check if top-k candidates match Phase 1 rules
        2. Use Phase 1 rules directly
        3. Use graph priors if available
        4. Default to R0

        Args:
            name: Person's name
            ml_result: ML prediction result (with abstained=true)
            entry: Full entry dict (for Phase 1)
            use_phase1: Whether to use Phase 1 fallback
            use_topk: Whether to check top-k candidates
            use_graph_priors: Whether to use graph priors

        Returns:
            DetectionResult with fallback prediction
        """
        metadata = {
            "ml_abstained": True,
            "ml_abstain_reason": ml_result.get("abstain_reason"),
            "ml_topk": ml_result.get("topk", [])[:3],
            "fallback_strategy": None,
        }

        # Strategy 1: Top-k + Phase 1 agreement
        if use_topk and use_phase1 and self.phase1_classifier:
            result = self._topk_phase1_agreement(name, ml_result, entry)
            if result:
                metadata["fallback_strategy"] = "topk_phase1_agreement"
                return DetectionResult(
                    region_code=result[0],
                    confidence=result[1],
                    detection_method="fallback-topk-phase1",
                    metadata=metadata,
                )

        # Strategy 2: Phase 1 rules only
        if use_phase1 and self.phase1_classifier:
            result = self._phase1_only(entry)
            if result:
                metadata["fallback_strategy"] = "phase1_only"
                return result

        # Strategy 3: Graph priors
        if use_graph_priors and self.graph_db:
            result = self._graph_priors(name, ml_result)
            if result:
                metadata["fallback_strategy"] = "graph_priors"
                return result

        # Strategy 4: Default to R0
        metadata["fallback_strategy"] = "default_r0"
        return DetectionResult(
            region_code="R0",
            confidence=0.50,
            detection_method="fallback-default-r0",
            metadata=metadata,
        )

    def _topk_phase1_agreement(
        self, name: str, ml_result: Dict, entry: Dict
    ) -> Optional[Tuple[str, float]]:
        """
        Check if any top-k ML candidate matches Phase 1 prediction

        Returns: (region_code, confidence) or None
        """
        if not self.phase1_classifier:
            return None

        # Get Phase 1 prediction
        phase1_result = self.phase1_classifier.detect_region(entry)
        phase1_region = phase1_result.region_code

        # Check if Phase 1 prediction is in ML top-k
        ml_topk = ml_result.get("topk", [])

        for candidate in ml_topk:
            if candidate["region"] == phase1_region:
                # Agreement found!
                # Use boosted confidence (avg of Phase 1 + ML top-k prob)
                ml_prob = candidate["p"]
                phase1_conf = phase1_result.confidence
                boosted_conf = (ml_prob + phase1_conf) / 2

                return (phase1_region, boosted_conf)

        return None

    def _phase1_only(self, entry: Dict) -> Optional[DetectionResult]:
        """
        Use Phase 1 rules only

        Returns: DetectionResult or None
        """
        if not self.phase1_classifier:
            return None

        result = self.phase1_classifier.detect_region(entry)

        return DetectionResult(
            region_code=result.region_code,
            confidence=result.confidence,
            detection_method="fallback-phase1-only",
            metadata={
                "phase1_method": result.detection_method,
                "phase1_metadata": result.metadata,
            },
        )

    def _graph_priors(self, name: str, ml_result: Dict) -> Optional[DetectionResult]:
        """
        Use graph priors (advisor/student regions)

        Returns: DetectionResult or None
        """
        if not self.graph_db:
            return None

        # TODO: Query graph for advisors/students of this person
        # Extract their regions and use majority vote

        # Placeholder implementation
        return None

    def explain_fallback(self, result: DetectionResult) -> str:
        """
        Generate human-readable explanation of fallback decision

        Args:
            result: DetectionResult from handle_abstention

        Returns:
            Explanation string
        """
        metadata = result.metadata

        if not metadata.get("ml_abstained"):
            return "ML classifier did not abstain (no fallback needed)"

        strategy = metadata.get("fallback_strategy")

        if strategy == "topk_phase1_agreement":
            return (
                f"ML abstained ({metadata['ml_abstain_reason']}). "
                f"Fallback: Agreement between ML top-k and Phase 1 rules. "
                f"Predicted: {result.region_code} (confidence: {result.confidence:.2f})"
            )

        elif strategy == "phase1_only":
            return (
                f"ML abstained ({metadata['ml_abstain_reason']}). "
                f"Fallback: Phase 1 rule-based detection. "
                f"Predicted: {result.region_code} (confidence: {result.confidence:.2f}, "
                f"method: {metadata.get('phase1_method')})"
            )

        elif strategy == "graph_priors":
            return (
                f"ML abstained ({metadata['ml_abstain_reason']}). "
                f"Fallback: Graph priors from known connections. "
                f"Predicted: {result.region_code} (confidence: {result.confidence:.2f})"
            )

        elif strategy == "default_r0":
            return (
                f"ML abstained ({metadata['ml_abstain_reason']}). "
                f"Fallback: Default to R0 (Residual Latin-ASCII). "
                f"No confident prediction available."
            )

        else:
            return f"Unknown fallback strategy: {strategy}"


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("FALLBACK HANDLER DEMO")
    print("=" * 80)

    # Simulate an abstained ML result
    abstained_result = {
        "model_name": "fasttext-v5-etymology",
        "model_version": "2025-10-30",
        "label_policy": "etymology",
        "region_top1": None,
        "region_top1_confidence": None,
        "topk": [
            {"region": "A1", "p": 0.45},
            {"region": "G1", "p": 0.38},
            {"region": "A2", "p": 0.12},
        ],
        "abstained": True,
        "abstain_reason": "Confidence 0.450 < threshold 0.55",
    }

    print("\nML Result (Abstained):")
    print(f"  Abstained: {abstained_result['abstained']}")
    print(f"  Reason: {abstained_result['abstain_reason']}")
    print(f"  Top-3 candidates:")
    for cand in abstained_result["topk"]:
        print(f"    {cand['region']}: {cand['p']:.3f}")

    # Create mock Phase 1 classifier
    class MockPhase1:
        def detect_region(self, entry):
            # Simulate Phase 1 predicting A1
            return DetectionResult(
                region_code="A1",
                confidence=0.75,
                detection_method="phase1-rules",
                metadata={"rule": "anglo_surname_pattern"},
            )

    phase1 = MockPhase1()
    handler = FallbackHandler(phase1_classifier=phase1)

    # Test fallback
    print("\n" + "=" * 80)
    print("FALLBACK STRATEGIES")
    print("=" * 80)

    entry = {"CanonicalNative": "García"}

    # Strategy 1: Top-k + Phase 1 agreement
    print("\nStrategy 1: Top-k + Phase 1 Agreement")
    result = handler.handle_abstention(
        "García", abstained_result, entry, use_phase1=True, use_topk=True
    )

    print(f"  Result: {result.region_code}")
    print(f"  Confidence: {result.confidence:.3f}")
    print(f"  Method: {result.detection_method}")
    print(f"  Strategy: {result.metadata['fallback_strategy']}")

    explanation = handler.explain_fallback(result)
    print(f"\n  Explanation:\n    {explanation}")

    # Strategy 2: Phase 1 only (simulate top-k not matching)
    print("\n" + "-" * 80)
    print("Strategy 2: Phase 1 Only (no top-k match)")

    no_match_result = abstained_result.copy()
    no_match_result["topk"] = [
        {"region": "A2", "p": 0.45},
        {"region": "G1", "p": 0.38},
        {"region": "E1", "p": 0.12},
    ]

    result2 = handler.handle_abstention(
        "García", no_match_result, entry, use_phase1=True, use_topk=True
    )

    print(f"  Result: {result2.region_code}")
    print(f"  Confidence: {result2.confidence:.3f}")
    print(f"  Method: {result2.detection_method}")

    explanation2 = handler.explain_fallback(result2)
    print(f"\n  Explanation:\n    {explanation2}")

    # Strategy 3: Default R0 (no Phase 1)
    print("\n" + "-" * 80)
    print("Strategy 3: Default R0 (no fallback available)")

    handler_no_phase1 = FallbackHandler(phase1_classifier=None)

    result3 = handler_no_phase1.handle_abstention(
        "Ambiguous Name", abstained_result, entry, use_phase1=True, use_topk=True
    )

    print(f"  Result: {result3.region_code}")
    print(f"  Confidence: {result3.confidence:.3f}")
    print(f"  Method: {result3.detection_method}")

    explanation3 = handler_no_phase1.explain_fallback(result3)
    print(f"\n  Explanation:\n    {explanation3}")

    print("\n" + "=" * 80)
    print("✅ FALLBACK HANDLER DEMO COMPLETE")
    print("=" * 80)
