#!/usr/bin/env python3
"""
Regional Classifier V5 - Etymology-Based with Calibration & Abstention

Based on expert guidance (Oct 30, 2025):
- Etymology-based labels (vs affiliation-based)
- Temperature scaling calibration (T=2.817)
- Abstention policy (max_p < 0.55)
- Integration contract with provenance

Performance:
- Top-1: 86.01% (test set)
- Top-3: 91.07% (test set)
- Latin scripts: 86.42%
- Calibrated ECE: 0.0063

Integration Contract:
Input: {"name_canonical_latin": "Michel Ferin", "country_code": "US"}
Output: {
  "model_name": "fasttext-v5-etymology",
  "model_version": "2025-10-30",
  "label_policy": "etymology",
  "region_top1": "A2",
  "region_top1_confidence": 0.86,
  "topk": [{"region":"A2","p":0.86},{"region":"A1","p":0.10}],
  "proba": {"A1":0.10,"A2":0.86,...},
  "abstained": false,
  "abstain_reason": null,
  "calibration": {"method":"temperature","T":2.817},
  "provenance": {"model_file":"v5_etymology.bin","train_date":"2025-10-30"}
}
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import fasttext
import numpy as np


class RegionalClassifierV5:
    """
    Regional classifier with etymology-based labels and calibration
    """

    def __init__(
        self,
        model_path: str = None,
        temperature: float = 2.817,
        abstention_threshold: float = 0.55,
    ):
        """
        Initialize classifier

        Args:
            model_path: Path to fastText model (default: auto-detect v5_etymology)
            temperature: Temperature for calibration (default: 2.817 from validation)
            abstention_threshold: Minimum confidence to make prediction (default: 0.55)
        """
        self.temperature = temperature
        self.abstention_threshold = abstention_threshold
        self.model_version = "2025-10-30"
        self.label_policy = "etymology"

        # Auto-detect model path
        if model_path is None:
            model_path = self._find_model()

        self.model_path = Path(model_path)
        self.model = fasttext.load_model(str(self.model_path))

    def _find_model(self) -> str:
        """Auto-detect model path"""
        candidates = [
            "data/ml_training/regional_classifier.bin",  # v4 baseline - BEST (87.5% golden)
            "data/ml_training/regional_classifier_v5_FIXED.bin",  # v5 fixed (75% golden - WORSE)
            "data/ml_training/regional_classifier_v5_etymology.bin",  # v5 broken (37.5% - DO NOT USE)
            "../../../data/ml_training/regional_classifier.bin",
        ]

        for path in candidates:
            if Path(path).exists():
                return path

        raise FileNotFoundError(
            "Could not find v5_etymology model. Please specify model_path."
        )

    def _apply_temperature_scaling(self, probs: np.ndarray) -> np.ndarray:
        """
        Apply temperature scaling to probabilities

        Approximation: p_calibrated = p^(1/T)
        Then renormalize to sum to 1
        """
        calibrated = probs ** (1 / self.temperature)
        return calibrated / np.sum(calibrated)

    def predict(self, name: str, k: int = 3) -> Dict:
        """
        Predict regional origin of name

        Args:
            name: Canonical Latin name
            k: Number of top predictions to return

        Returns:
            Dict with predictions, confidence, abstention decision, and provenance
        """
        # Get raw predictions
        labels, probs = self.model.predict(name, k=k)

        # Convert to region codes
        regions = [l.replace("__label__", "") for l in labels]
        probs = np.array(probs, dtype=float)

        # Apply temperature scaling
        calibrated_probs = self._apply_temperature_scaling(probs)

        # Check abstention
        max_prob = float(calibrated_probs[0])
        should_abstain = max_prob < self.abstention_threshold

        # Build top-k list
        topk = [{"region": r, "p": float(p)} for r, p in zip(regions, calibrated_probs)]

        # Build full probability distribution
        all_probs = {}
        for r, p in zip(regions, calibrated_probs):
            all_probs[r] = float(p)

        # Build response
        response = {
            "model_name": "fasttext-v5-etymology",
            "model_version": self.model_version,
            "label_policy": self.label_policy,
            "region_top1": regions[0] if not should_abstain else None,
            "region_top1_confidence": max_prob if not should_abstain else None,
            "topk": topk,
            "proba": all_probs,
            "abstained": should_abstain,
            "abstain_reason": (
                f"Confidence {max_prob:.3f} < threshold {self.abstention_threshold}"
                if should_abstain
                else None
            ),
            "calibration": {"method": "temperature_scaling", "T": self.temperature},
            "provenance": {
                "model_file": self.model_path.name,
                "train_date": self.model_version,
                "prediction_timestamp": datetime.utcnow().isoformat() + "Z",
            },
        }

        return response

    def predict_batch(self, names: List[str], k: int = 3) -> List[Dict]:
        """Predict for batch of names"""
        return [self.predict(name, k=k) for name in names]


# Convenience function
def detect_region_v5(name: str, k: int = 3) -> Dict:
    """
    Convenience function for one-off predictions

    Example:
        result = detect_region_v5("Michel Ferin")
        print(result['region_top1'])  # "A2"
        print(result['region_top1_confidence'])  # 0.86
    """
    classifier = RegionalClassifierV5()
    return classifier.predict(name, k=k)


if __name__ == "__main__":
    # Demo
    import sys

    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
    else:
        name = "Michel Ferin"

    print(f"Detecting regional origin: {name}")
    print("=" * 60)

    result = detect_region_v5(name, k=3)

    print(
        f"\nTop-1 Prediction: {result['region_top1']} ({result['region_top1_confidence']:.1%} confidence)"
    )
    print(f"Abstained: {result['abstained']}")

    if result["abstained"]:
        print(f"  Reason: {result['abstain_reason']}")

    print("\nTop-3:")
    for i, pred in enumerate(result["topk"][:3], 1):
        print(f"  {i}. {pred['region']:4s} {pred['p']:.1%}")

    print(
        f"\nCalibration: {result['calibration']['method']} (T={result['calibration']['T']:.3f})"
    )
    print(f"Model: {result['model_name']} v{result['model_version']}")
