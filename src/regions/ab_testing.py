#!/usr/bin/env python3
"""
A/B Testing Framework for ML Model Deployment

Enables gradual rollout of v5 model alongside v4 for comparison and validation.

Features:
- Traffic splitting (e.g., 10% v5, 90% v4)
- Consistent user assignment (hash-based)
- Real-time metrics collection
- Automatic winner detection
- Rollback on degradation

Usage:
    from src.regions.ab_testing import ABTestingClassifier, ABTestConfig

    # Configure A/B test
    config = ABTestConfig(
        control_model='v4',
        treatment_model='v5',
        traffic_split=0.10,  # 10% to v5
        metrics_window=1000,
        auto_promote_threshold=0.95  # Promote if v5 > 95% of v4 accuracy
    )

    # Create classifier
    classifier = ABTestingClassifier(config)

    # Predict
    result = classifier.predict(name, user_id='user123')
    # Returns: prediction + metadata about which model was used
"""

import hashlib
import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ABTestConfig:
    """A/B test configuration"""

    control_model: str = "v4"  # Baseline model
    treatment_model: str = "v5"  # New model being tested
    traffic_split: float = 0.10  # Fraction of traffic to treatment (0.0-1.0)
    metrics_window: int = 1000  # Rolling window for metrics
    auto_promote_threshold: float = 0.95  # Auto-promote if treatment/control > this
    auto_rollback_threshold: float = 0.90  # Auto-rollback if treatment/control < this
    min_samples_for_decision: int = 100  # Minimum samples before auto-decision


class ABTestingClassifier:
    """
    A/B testing wrapper for regional classifiers

    Routes traffic between control (v4) and treatment (v5) models based on
    consistent hashing of user ID.
    """

    def __init__(
        self,
        config: ABTestConfig,
        control_classifier=None,
        treatment_classifier=None,
        metrics_file: str = "logs/ab_testing_metrics.jsonl",
    ):
        """
        Initialize A/B testing classifier

        Args:
            config: A/B test configuration
            control_classifier: v4 classifier (or any baseline)
            treatment_classifier: v5 classifier (or any treatment)
            metrics_file: Path to metrics log file
        """
        self.config = config
        self.control = control_classifier
        self.treatment = treatment_classifier
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Rolling metrics
        self.control_results = deque(maxlen=config.metrics_window)
        self.treatment_results = deque(maxlen=config.metrics_window)

        # Load classifiers lazily if not provided
        if self.control is None:
            self._load_control()
        if self.treatment is None:
            self._load_treatment()

    def _load_control(self):
        """Load control model (v4)"""
        import fasttext

        model_path = "data/ml_training/regional_classifier_v4_optimized.bin"
        self.control = fasttext.load_model(model_path)

    def _load_treatment(self):
        """Load treatment model (v5)"""
        from src.regions.regional_classifier_v5 import RegionalClassifierV5

        self.treatment = RegionalClassifierV5()

    def _assign_to_treatment(self, user_id: str) -> bool:
        """
        Consistently assign user to treatment or control using hash

        Args:
            user_id: Unique user identifier (consistent across requests)

        Returns:
            True if user assigned to treatment, False for control
        """
        if user_id is None:
            # If no user_id, use random assignment (not consistent)
            import random

            return random.random() < self.config.traffic_split

        # Hash user_id and use modulo to determine assignment
        hash_val = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
        bucket = (hash_val % 100) / 100.0
        return bucket < self.config.traffic_split

    def predict(
        self,
        name: str,
        user_id: Optional[str] = None,
        ground_truth: Optional[str] = None,
        k: int = 3,
    ) -> Dict:
        """
        Predict using A/B test (route to control or treatment)

        Args:
            name: Name to classify
            user_id: User identifier for consistent assignment
            ground_truth: True region (if known, for metrics)
            k: Number of top predictions

        Returns:
            Dict with prediction + A/B test metadata
        """
        # Determine assignment
        use_treatment = self._assign_to_treatment(user_id)
        variant = (
            self.config.treatment_model if use_treatment else self.config.control_model
        )

        # Predict
        if use_treatment:
            result = self.treatment.predict(name, k=k)
            prediction = result["region_top1"] if not result["abstained"] else None
            confidence = result["region_top1_confidence"]
        else:
            # v4 prediction (simplified)
            labels, probs = self.control.predict(name, k=1)
            prediction = labels[0].replace("__label__", "")
            confidence = float(probs[0])
            result = {
                "model_name": "fasttext-v4-affiliation",
                "model_version": "2025-10-27",
                "region_top1": prediction,
                "region_top1_confidence": confidence,
                "abstained": False,
            }

        # Add A/B test metadata
        result["ab_test"] = {
            "variant": variant,
            "user_id": user_id,
            "traffic_split": self.config.traffic_split,
        }

        # Record result for metrics
        is_correct = (prediction == ground_truth) if ground_truth else None
        if use_treatment:
            self.treatment_results.append(
                {
                    "name": name,
                    "prediction": prediction,
                    "confidence": confidence,
                    "correct": is_correct,
                    "ground_truth": ground_truth,
                }
            )
        else:
            self.control_results.append(
                {
                    "name": name,
                    "prediction": prediction,
                    "confidence": confidence,
                    "correct": is_correct,
                    "ground_truth": ground_truth,
                }
            )

        # Log to file
        self._log_prediction(
            name, variant, prediction, confidence, ground_truth, user_id
        )

        # Check for auto-decision
        decision = self._check_auto_decision()
        if decision:
            result["ab_test"]["auto_decision"] = decision

        return result

    def _log_prediction(
        self,
        name: str,
        variant: str,
        prediction: str,
        confidence: float,
        ground_truth: Optional[str],
        user_id: Optional[str],
    ):
        """Log prediction to JSONL file"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "name": name,
            "variant": variant,
            "prediction": prediction,
            "confidence": confidence,
            "ground_truth": ground_truth,
            "user_id": user_id,
        }

        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_metrics(self) -> Dict:
        """
        Get current A/B test metrics

        Returns:
            Dict with control and treatment metrics
        """
        control_with_gt = [r for r in self.control_results if r["correct"] is not None]
        treatment_with_gt = [
            r for r in self.treatment_results if r["correct"] is not None
        ]

        control_accuracy = (
            sum(1 for r in control_with_gt if r["correct"]) / len(control_with_gt)
            if control_with_gt
            else 0.0
        )

        treatment_accuracy = (
            sum(1 for r in treatment_with_gt if r["correct"]) / len(treatment_with_gt)
            if treatment_with_gt
            else 0.0
        )

        control_avg_conf = (
            sum(r["confidence"] for r in self.control_results if r["confidence"])
            / len(self.control_results)
            if self.control_results
            else 0.0
        )

        treatment_avg_conf = (
            sum(r["confidence"] for r in self.treatment_results if r["confidence"])
            / len(self.treatment_results)
            if self.treatment_results
            else 0.0
        )

        # Compute relative improvement
        relative_accuracy = (
            treatment_accuracy / control_accuracy if control_accuracy > 0 else 1.0
        )

        return {
            "control": {
                "variant": self.config.control_model,
                "samples": len(self.control_results),
                "samples_with_ground_truth": len(control_with_gt),
                "accuracy": control_accuracy,
                "avg_confidence": control_avg_conf,
            },
            "treatment": {
                "variant": self.config.treatment_model,
                "samples": len(self.treatment_results),
                "samples_with_ground_truth": len(treatment_with_gt),
                "accuracy": treatment_accuracy,
                "avg_confidence": treatment_avg_conf,
            },
            "comparison": {
                "relative_accuracy": relative_accuracy,
                "accuracy_delta_pp": (treatment_accuracy - control_accuracy) * 100,
                "confidence_delta": treatment_avg_conf - control_avg_conf,
                "winner": (
                    self.config.treatment_model
                    if treatment_accuracy > control_accuracy
                    else (
                        self.config.control_model
                        if control_accuracy > treatment_accuracy
                        else "tie"
                    )
                ),
            },
            "config": asdict(self.config),
        }

    def _check_auto_decision(self) -> Optional[Dict]:
        """
        Check if auto-promote or auto-rollback thresholds are met

        Returns:
            Decision dict if threshold met, None otherwise
        """
        metrics = self.get_metrics()

        # Need minimum samples
        if (
            metrics["control"]["samples_with_ground_truth"]
            < self.config.min_samples_for_decision
            or metrics["treatment"]["samples_with_ground_truth"]
            < self.config.min_samples_for_decision
        ):
            return None

        relative_accuracy = metrics["comparison"]["relative_accuracy"]

        # Auto-promote
        if relative_accuracy >= self.config.auto_promote_threshold:
            return {
                "action": "promote",
                "reason": f"Treatment accuracy {relative_accuracy:.1%} of control (threshold: {self.config.auto_promote_threshold:.1%})",
                "recommendation": f"Promote {self.config.treatment_model} to 100% traffic",
                "metrics": metrics,
            }

        # Auto-rollback
        if relative_accuracy <= self.config.auto_rollback_threshold:
            return {
                "action": "rollback",
                "reason": f"Treatment accuracy {relative_accuracy:.1%} of control (threshold: {self.config.auto_rollback_threshold:.1%})",
                "recommendation": f"Rollback {self.config.treatment_model}, keep {self.config.control_model}",
                "metrics": metrics,
            }

        return None

    def export_report(self, output_path: str):
        """Export A/B test report"""
        metrics = self.get_metrics()
        decision = self._check_auto_decision()

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics,
            "auto_decision": decision,
            "log_file": str(self.metrics_file),
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ A/B test report exported to {output_path}")


# Example usage and demo
if __name__ == "__main__":
    print("=" * 80)
    print("A/B TESTING FRAMEWORK DEMO")
    print("=" * 80)

    # Create config
    config = ABTestConfig(
        control_model="v4",
        treatment_model="v5",
        traffic_split=0.20,  # 20% to v5
        metrics_window=100,
        auto_promote_threshold=0.95,
        auto_rollback_threshold=0.90,
        min_samples_for_decision=50,
    )

    print("\nConfiguration:")
    print(f"  Control: {config.control_model}")
    print(f"  Treatment: {config.treatment_model}")
    print(f"  Traffic split: {config.traffic_split:.0%} to treatment")
    print(f"  Metrics window: {config.metrics_window} samples")
    print(f"  Auto-promote threshold: {config.auto_promote_threshold:.0%}")
    print(f"  Auto-rollback threshold: {config.auto_rollback_threshold:.0%}")

    # Simulate A/B test
    print("\n" + "-" * 80)
    print("Simulating A/B Test with 100 Users")
    print("-" * 80)

    # Create classifier (NOTE: This loads real models, may take time)
    print("\nInitializing classifiers...")
    # classifier = ABTestingClassifier(config)  # Uncomment to use real models

    # For demo, simulate results
    print("\nSimulating predictions...")
    control_count = 0
    treatment_count = 0

    for i in range(100):
        user_id = f"user{i}"

        # Determine assignment (simulate hash-based)
        hash_val = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
        bucket = (hash_val % 100) / 100.0
        use_treatment = bucket < config.traffic_split

        if use_treatment:
            treatment_count += 1
        else:
            control_count += 1

    print("\nAssignment Distribution:")
    print(f"  Control (v4): {control_count}/100 ({control_count}%)")
    print(f"  Treatment (v5): {treatment_count}/100 ({treatment_count}%)")
    print(f"  Expected: ~{config.traffic_split:.0%} to treatment")

    # Show consistent assignment
    print("\n" + "-" * 80)
    print("Testing Consistent Assignment")
    print("-" * 80)

    test_users = ["alice", "bob", "charlie"]
    print("\nUser assignments (consistent across requests):")
    for user in test_users:
        assignments = []
        for _ in range(5):  # 5 requests per user
            hash_val = int(hashlib.sha256(user.encode()).hexdigest(), 16)
            bucket = (hash_val % 100) / 100.0
            variant = "treatment" if bucket < config.traffic_split else "control"
            assignments.append(variant)

        # Check consistency
        all_same = len(set(assignments)) == 1
        print(
            f"  {user:10} → {assignments[0]:10} {'✅ consistent' if all_same else '❌ inconsistent'}"
        )

    print("\n" + "=" * 80)
    print("✅ A/B TESTING FRAMEWORK DEMO COMPLETE")
    print("=" * 80)
    print("\nUsage in production:")
    print("  1. Configure traffic split (start with 10%)")
    print("  2. Route predictions through ABTestingClassifier")
    print("  3. Monitor metrics with get_metrics()")
    print("  4. Auto-promote or rollback based on thresholds")
    print("  5. Gradually increase traffic: 10% → 25% → 50% → 100%")
