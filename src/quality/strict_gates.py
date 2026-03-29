"""
Strict Quality Gates Enforcement for GMNAP V7
Implements blocking quality gates that prevent deployment if not met.
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class StrictQualityGates:
    """
    Strict quality gates that BLOCK processing if not met.
    Implements V7 spec requirement for 0-byte idempotency and quality enforcement.
    """

    def __init__(self, mode: str = "production", strict: bool = True):
        """
        Initialize strict quality gates.

        Args:
            mode: Processing mode (production, staging, dev)
            strict: If True, gates are blocking. If False, warnings only.
        """
        self.mode = mode
        self.strict = strict

        # V7 Spec Requirements - STRICT thresholds
        self.thresholds = {
            "max_error_rate": 0.01,  # 1% max error rate (stricter than 5%)
            "min_authority_coverage": 0.2,  # 20% min (relaxed for now, 3 sources)
            "min_graph_coherence": 0.3,  # 30% min coherence
            "max_runtime_per_million": 35,  # 35 minutes per million
            "max_duplicate_rate": 0.001,  # 0.1% max duplicates
            "min_idempotency_score": 1.0,  # 100% idempotency required
            "min_validation_score": 0.95,  # 95% validation score
            "max_collision_rate": 0.02,  # 2% max collision rate
        }

        # Production mode is strictest
        if mode == "production":
            self.thresholds["max_error_rate"] = 0.005  # 0.5% in production
            self.thresholds["min_validation_score"] = 0.98  # 98% in production

    def check_duplicate_global_ids(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Check for duplicate GlobalIDs."""
        if not entries:
            return True, 0.0, "No entries to check"

        gids = [e.get("GlobalID") for e in entries if e.get("GlobalID")]
        if not gids:
            return False, 1.0, "No GlobalIDs found"

        counter = Counter(gids)
        duplicates = sum(1 for count in counter.values() if count > 1)
        duplicate_rate = duplicates / len(gids)

        passed = duplicate_rate <= self.thresholds["max_duplicate_rate"]
        message = f"Duplicate rate: {duplicate_rate:.3%} (threshold: {self.thresholds['max_duplicate_rate']:.3%})"

        return passed, duplicate_rate, message

    def check_error_rate(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Check validation error rate."""
        if not entries:
            return True, 0.0, "No entries to check"

        errors = sum(1 for e in entries if e.get("ValidationErrors"))
        error_rate = errors / len(entries)

        passed = error_rate <= self.thresholds["max_error_rate"]
        message = f"Error rate: {error_rate:.3%} (threshold: {self.thresholds['max_error_rate']:.3%})"

        return passed, error_rate, message

    def check_authority_coverage(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Check authority source coverage."""
        if not entries:
            return True, 0.0, "No entries to check"

        with_authority = sum(1 for e in entries if e.get("AuthoritySources"))
        coverage = with_authority / len(entries)

        passed = coverage >= self.thresholds["min_authority_coverage"]
        message = f"Authority coverage: {coverage:.1%} (threshold: {self.thresholds['min_authority_coverage']:.0%})"

        return passed, coverage, message

    def check_graph_coherence(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Check graph coherence scores."""
        if not entries:
            return True, 0.5, "No entries to check"

        coherence_values = []
        for e in entries:
            if "GraphCoherence" in e:
                coherence_values.append(e["GraphCoherence"])

        if not coherence_values:
            # No coherence data
            return True, 0.5, "No graph coherence data available"

        avg_coherence = sum(coherence_values) / len(coherence_values)

        passed = avg_coherence >= self.thresholds["min_graph_coherence"]
        message = f"Graph coherence: {avg_coherence:.3f} (threshold: {self.thresholds['min_graph_coherence']:.1f})"

        return passed, avg_coherence, message

    def check_runtime_performance(
        self, entries: List[Dict[str, Any]], runtime_seconds: float
    ) -> Tuple[bool, float, str]:
        """Check processing performance."""
        if not entries or runtime_seconds <= 0:
            return True, 0.0, "No runtime data available"

        entries_per_second = len(entries) / runtime_seconds
        minutes_per_million = (
            (1000000 / entries_per_second / 60)
            if entries_per_second > 0
            else float("inf")
        )

        passed = minutes_per_million <= self.thresholds["max_runtime_per_million"]
        message = f"Runtime per 1M: {minutes_per_million:.1f} min (threshold: {self.thresholds['max_runtime_per_million']} min)"

        return passed, minutes_per_million, message

    def check_idempotency(self, hash1: str, hash2: str) -> Tuple[bool, float, str]:
        """Check idempotency (0-byte difference required)."""
        if not hash1 or not hash2:
            return False, 0.0, "Missing hash data for idempotency check"

        identical = hash1 == hash2
        score = 1.0 if identical else 0.0

        passed = score >= self.thresholds["min_idempotency_score"]
        message = f"Idempotency: {'PASSED' if identical else 'FAILED'} (0-byte difference required)"

        return passed, score, message

    def check_collision_rate(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Check collision detection rate."""
        if not entries:
            return True, 0.0, "No entries to check"

        collisions = sum(1 for e in entries if e.get("HasCollision"))
        collision_rate = collisions / len(entries)

        passed = collision_rate <= self.thresholds["max_collision_rate"]
        message = f"Collision rate: {collision_rate:.2%} (threshold: {self.thresholds['max_collision_rate']:.0%})"

        return passed, collision_rate, message

    def enforce_quality_gates(
        self,
        entries: List[Dict[str, Any]],
        runtime_seconds: float = 0,
        idempotency_hashes: Tuple[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Enforce all quality gates with strict blocking.

        Args:
            entries: Processed entries to validate
            runtime_seconds: Total processing time
            idempotency_hashes: Tuple of (first_run_hash, second_run_hash)

        Returns:
            Dictionary with gate results and overall pass/fail
        """
        results = {
            "passed": True,
            "blocked": False,
            "gates": {},
            "failures": [],
            "warnings": [],
            "scores": {},
        }

        # Run all quality checks
        checks = [
            ("duplicate_ids", self.check_duplicate_global_ids(entries)),
            ("error_rate", self.check_error_rate(entries)),
            ("authority_coverage", self.check_authority_coverage(entries)),
            ("graph_coherence", self.check_graph_coherence(entries)),
            (
                "runtime_performance",
                self.check_runtime_performance(entries, runtime_seconds),
            ),
            ("collision_rate", self.check_collision_rate(entries)),
        ]

        # Add idempotency check if hashes provided
        if idempotency_hashes:
            checks.append(("idempotency", self.check_idempotency(*idempotency_hashes)))

        # Process results
        for gate_name, (passed, score, message) in checks:
            results["gates"][gate_name] = {
                "passed": passed,
                "score": score,
                "message": message,
            }
            results["scores"][gate_name] = score

            if not passed:
                if self.strict:
                    results["failures"].append(f"[BLOCKED] {gate_name}: {message}")
                    results["blocked"] = True
                else:
                    results["warnings"].append(f"[WARNING] {gate_name}: {message}")
                results["passed"] = False
            else:
                logger.info(f"✅ {gate_name}: {message}")

        # Calculate overall score
        if results["scores"]:
            results["overall_score"] = sum(results["scores"].values()) / len(
                results["scores"]
            )
        else:
            results["overall_score"] = 0.0

        # Log results
        if results["passed"]:
            logger.info(
                f"✅ All quality gates PASSED (score: {results['overall_score']:.2f})"
            )
        else:
            if results["blocked"]:
                logger.error("❌ Quality gates BLOCKED processing:")
                for failure in results["failures"]:
                    logger.error(f"   {failure}")
                raise QualityGateBlockedException(
                    f"Quality gates failed: {len(results['failures'])} blocking issues",
                    results,
                )
            else:
                logger.warning("⚠️  Quality gates passed with warnings:")
                for warning in results["warnings"]:
                    logger.warning(f"   {warning}")

        return results


class QualityGateBlockedException(Exception):
    """Exception raised when quality gates block processing."""

    def __init__(self, message: str, gate_results: Dict[str, Any]):
        super().__init__(message)
        self.gate_results = gate_results
        self.failures = gate_results.get("failures", [])
        self.blocked = gate_results.get("blocked", False)
