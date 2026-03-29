#!/usr/bin/env python3
"""
ML Classifier Production Monitoring and Logging

Based on expert guidance and integration contract:
- Log all predictions with provenance
- Track accuracy metrics
- Alert on degradation
- Support multiple log formats (JSON, structured)

Usage:
    from src.monitoring.ml_classifier_logger import MLClassifierLogger

    logger = MLClassifierLogger("logs/ml_predictions.jsonl")
    logger.log_prediction(input_data, result, ground_truth=None)
"""

import json
import logging
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class MLClassifierLogger:
    """
    Production logger for ML regional classifier

    Features:
    - JSON lines format for easy parsing
    - Rolling statistics (last 1000 predictions)
    - Automatic alerting on degradation
    - Provenance tracking
    """

    def __init__(
        self,
        log_path: str = "logs/ml_predictions.jsonl",
        alert_abstention_threshold: float = 0.10,
        alert_confidence_threshold: float = 0.70,
        rolling_window: int = 1000,
    ):
        """
        Initialize logger

        Args:
            log_path: Path to log file (JSONL format)
            alert_abstention_threshold: Alert if abstention rate > this
            alert_confidence_threshold: Alert if avg confidence < this
            rolling_window: Size of rolling statistics window
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.alert_abstention_threshold = alert_abstention_threshold
        self.alert_confidence_threshold = alert_confidence_threshold
        self.rolling_window = rolling_window

        # Rolling statistics
        self.recent_predictions = deque(maxlen=rolling_window)
        self.stats = {
            "total_predictions": 0,
            "abstained_count": 0,
            "confidence_sum": 0.0,
            "correct_count": 0,  # Only if ground truth provided
            "accuracy_count": 0,  # Denominator for accuracy
        }

        # Set up Python logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("MLClassifierLogger")

    def log_prediction(
        self,
        input_data: Dict,
        prediction_result: Dict,
        ground_truth: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Log a single prediction

        Args:
            input_data: Input to classifier (e.g., {"name_canonical_latin": "..."}
            prediction_result: Output from classifier (full contract)
            ground_truth: True region (if known, for accuracy tracking)
            metadata: Additional context (user_id, request_id, etc.)
        """
        # Create log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "input": input_data,
            "prediction": {
                "model_name": prediction_result.get("model_name"),
                "model_version": prediction_result.get("model_version"),
                "label_policy": prediction_result.get("label_policy"),
                "region_top1": prediction_result.get("region_top1"),
                "confidence": prediction_result.get("region_top1_confidence"),
                "abstained": prediction_result.get("abstained"),
                "topk": prediction_result.get("topk", [])[:3],  # Store top-3
            },
            "ground_truth": ground_truth,
            "metadata": metadata or {},
        }

        # Write to log file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # Update statistics
        self._update_stats(prediction_result, ground_truth)

        # Check for alerts
        self._check_alerts()

    def _update_stats(self, prediction: Dict, ground_truth: Optional[str]):
        """Update rolling statistics"""
        self.stats["total_predictions"] += 1

        abstained = prediction.get("abstained", False)
        if abstained:
            self.stats["abstained_count"] += 1

        confidence = prediction.get("region_top1_confidence")
        if confidence is not None:
            self.stats["confidence_sum"] += confidence

        # Track accuracy if ground truth provided
        if ground_truth is not None and not abstained:
            self.stats["accuracy_count"] += 1
            predicted = prediction.get("region_top1")
            if predicted == ground_truth:
                self.stats["correct_count"] += 1

        # Add to rolling window
        self.recent_predictions.append(
            {
                "abstained": abstained,
                "confidence": confidence,
                "correct": (
                    (prediction.get("region_top1") == ground_truth)
                    if ground_truth and not abstained
                    else None
                ),
            }
        )

    def _check_alerts(self):
        """Check for degradation and alert"""
        if len(self.recent_predictions) < 100:
            # Need at least 100 predictions for reliable statistics
            return

        # Compute rolling metrics
        abstention_rate = sum(
            1 for p in self.recent_predictions if p["abstained"]
        ) / len(self.recent_predictions)

        confidences = [
            p["confidence"]
            for p in self.recent_predictions
            if p["confidence"] is not None and not p["abstained"]
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Alert on abstention rate
        if abstention_rate > self.alert_abstention_threshold:
            self.logger.warning(
                f"⚠️  HIGH ABSTENTION RATE: {abstention_rate:.1%} "
                f"(threshold: {self.alert_abstention_threshold:.1%})"
            )

        # Alert on low confidence
        if avg_confidence < self.alert_confidence_threshold:
            self.logger.warning(
                f"⚠️  LOW CONFIDENCE: {avg_confidence:.3f} "
                f"(threshold: {self.alert_confidence_threshold:.3f})"
            )

        # Alert on accuracy (if ground truth available)
        correct_predictions = [
            p for p in self.recent_predictions if p["correct"] is not None
        ]
        if len(correct_predictions) >= 50:
            accuracy = sum(1 for p in correct_predictions if p["correct"]) / len(
                correct_predictions
            )
            if accuracy < 0.75:  # Alert if accuracy drops below 75%
                self.logger.warning(
                    f"⚠️  LOW ACCURACY: {accuracy:.1%} "
                    f"(rolling window: {len(correct_predictions)} predictions)"
                )

    def get_statistics(self) -> Dict:
        """Get current statistics"""
        total = self.stats["total_predictions"]
        if total == 0:
            return {"total_predictions": 0}

        abstention_rate = self.stats["abstained_count"] / total
        avg_confidence = (
            self.stats["confidence_sum"] / (total - self.stats["abstained_count"])
            if total > self.stats["abstained_count"]
            else 0.0
        )

        stats = {
            "total_predictions": total,
            "abstention_rate": abstention_rate,
            "avg_confidence": avg_confidence,
        }

        # Add accuracy if available
        if self.stats["accuracy_count"] > 0:
            stats["accuracy"] = (
                self.stats["correct_count"] / self.stats["accuracy_count"]
            )
            stats["accuracy_sample_size"] = self.stats["accuracy_count"]

        # Rolling window stats
        if len(self.recent_predictions) > 0:
            recent_abstained = sum(1 for p in self.recent_predictions if p["abstained"])
            recent_confidences = [
                p["confidence"]
                for p in self.recent_predictions
                if p["confidence"] is not None and not p["abstained"]
            ]

            stats["rolling_abstention_rate"] = recent_abstained / len(
                self.recent_predictions
            )
            stats["rolling_avg_confidence"] = (
                sum(recent_confidences) / len(recent_confidences)
                if recent_confidences
                else 0.0
            )
            stats["rolling_window_size"] = len(self.recent_predictions)

        return stats

    def export_report(self, output_path: str):
        """Export statistics report to JSON"""
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "log_file": str(self.log_path),
            "statistics": self.get_statistics(),
            "thresholds": {
                "abstention_alert": self.alert_abstention_threshold,
                "confidence_alert": self.alert_confidence_threshold,
            },
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Exported report to {output_path}")


class MLClassifierMonitor:
    """
    Real-time monitoring dashboard (for production)

    Reads from log file and provides metrics
    """

    def __init__(self, log_path: str):
        """Initialize monitor"""
        self.log_path = Path(log_path)

    def analyze_logs(self, last_n: Optional[int] = None) -> Dict:
        """
        Analyze prediction logs

        Args:
            last_n: Analyze only last N predictions (None = all)

        Returns:
            Dict with analysis results
        """
        if not self.log_path.exists():
            return {"error": "Log file not found"}

        # Read logs
        predictions = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    predictions.append(json.loads(line))

        if last_n:
            predictions = predictions[-last_n:]

        if not predictions:
            return {"error": "No predictions found"}

        # Analyze
        analysis = {
            "total_predictions": len(predictions),
            "date_range": {
                "first": predictions[0]["timestamp"],
                "last": predictions[-1]["timestamp"],
            },
            "model_versions": defaultdict(int),
            "label_policies": defaultdict(int),
            "abstention_rate": 0.0,
            "avg_confidence": 0.0,
            "accuracy": None,
            "region_distribution": defaultdict(int),
        }

        abstained_count = 0
        confidence_sum = 0.0
        confidence_count = 0
        correct_count = 0
        total_with_gt = 0

        for pred in predictions:
            # Model version
            model_version = pred["prediction"].get("model_version", "unknown")
            analysis["model_versions"][model_version] += 1

            # Label policy
            label_policy = pred["prediction"].get("label_policy", "unknown")
            analysis["label_policies"][label_policy] += 1

            # Abstention
            if pred["prediction"].get("abstained"):
                abstained_count += 1

            # Confidence
            confidence = pred["prediction"].get("confidence")
            if confidence is not None:
                confidence_sum += confidence
                confidence_count += 1

            # Region distribution
            region = pred["prediction"].get("region_top1")
            if region:
                analysis["region_distribution"][region] += 1

            # Accuracy (if ground truth available)
            ground_truth = pred.get("ground_truth")
            if ground_truth and not pred["prediction"].get("abstained"):
                total_with_gt += 1
                if region == ground_truth:
                    correct_count += 1

        analysis["abstention_rate"] = abstained_count / len(predictions)
        analysis["avg_confidence"] = (
            confidence_sum / confidence_count if confidence_count > 0 else 0.0
        )

        if total_with_gt > 0:
            analysis["accuracy"] = correct_count / total_with_gt
            analysis["accuracy_sample_size"] = total_with_gt

        # Convert defaultdicts to regular dicts
        analysis["model_versions"] = dict(analysis["model_versions"])
        analysis["label_policies"] = dict(analysis["label_policies"])
        analysis["region_distribution"] = dict(
            sorted(
                analysis["region_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        )  # Top 10 regions

        return analysis


if __name__ == "__main__":
    # Demo usage
    print("=" * 80)
    print("ML CLASSIFIER PRODUCTION LOGGING DEMO")
    print("=" * 80)

    # Create logger
    logger = MLClassifierLogger("logs/demo_predictions.jsonl")

    # Simulate predictions
    test_cases = [
        ("John Smith", "A1", "A1", 0.95, False),
        ("José García", "G1", "A1", 0.85, False),  # Misclassification
        ("Zhang Wei", "A1", "E1", 0.92, False),  # Romanized CJK
        ("Michel Ferin", "A2", "A2", 0.86, False),
        ("Ambiguous Name", None, "A1", 0.45, True),  # Abstained
    ]

    print("\nSimulating predictions...")
    for name, ground_truth, predicted, confidence, abstained in test_cases:
        input_data = {"name_canonical_latin": name}

        prediction_result = {
            "model_name": "fasttext-v5-etymology",
            "model_version": "2025-10-30",
            "label_policy": "etymology",
            "region_top1": predicted if not abstained else None,
            "region_top1_confidence": confidence if not abstained else None,
            "abstained": abstained,
            "topk": (
                [
                    {"region": predicted or "A1", "p": confidence},
                    {"region": "A2", "p": 0.10},
                    {"region": "G1", "p": 0.05},
                ]
                if not abstained
                else []
            ),
        }

        logger.log_prediction(input_data, prediction_result, ground_truth)

        status = (
            "✅"
            if (predicted == ground_truth and not abstained)
            else ("⚠️ ABSTAINED" if abstained else "❌")
        )
        print(
            f"  {status} {name:20} → {predicted or 'ABSTAINED':4} (gt: {ground_truth}, conf: {confidence:.2f})"
        )

    # Get statistics
    print("\nCurrent Statistics:")
    stats = logger.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")

    # Export report
    logger.export_report("logs/demo_report.json")
    print("\n✅ Report exported to logs/demo_report.json")

    # Analyze logs
    print("\n" + "=" * 80)
    print("LOG ANALYSIS")
    print("=" * 80)

    monitor = MLClassifierMonitor("logs/demo_predictions.jsonl")
    analysis = monitor.analyze_logs()

    print(f"\nTotal predictions: {analysis['total_predictions']}")
    print(f"Abstention rate: {analysis['abstention_rate']:.1%}")
    print(f"Avg confidence: {analysis['avg_confidence']:.3f}")
    if analysis["accuracy"] is not None:
        print(
            f"Accuracy: {analysis['accuracy']:.1%} (n={analysis['accuracy_sample_size']})"
        )

    print("\nModel versions:")
    for version, count in analysis["model_versions"].items():
        print(f"  {version}: {count}")

    print("\nLabel policies:")
    for policy, count in analysis["label_policies"].items():
        print(f"  {policy}: {count}")

    print("\n" + "=" * 80)
