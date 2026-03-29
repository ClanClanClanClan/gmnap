#!/usr/bin/env python3
"""
ML Model Registry and Versioning System

Tracks all deployed ML models with:
- Version metadata
- Performance metrics
- Deployment history
- A/B testing support

Usage:
    registry = ModelRegistry("models/registry.json")

    # Register new model
    registry.register_model(
        model_id="v5_etymology_20251030",
        model_file="regional_classifier_v5_etymology.bin",
        version="2025-10-30",
        label_policy="etymology",
        accuracy=0.8601,
        calibration_T=2.817
    )

    # Get active model
    active = registry.get_active_model()
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ModelRegistry:
    """
    ML Model Registry for version tracking and deployment management
    """

    def __init__(self, registry_path: str = "models/registry.json"):
        """
        Initialize registry

        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create registry
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "models": {},
                "active_model_id": None,
                "deployment_history": [],
            }
            self._save()

    def _save(self):
        """Save registry to disk"""
        with open(self.registry_path, "w") as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)

    def _compute_model_hash(self, model_file: Path) -> str:
        """Compute SHA256 hash of model file"""
        if not model_file.exists():
            return "MISSING"

        sha256 = hashlib.sha256()
        with open(model_file, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_model(
        self,
        model_id: str,
        model_file: str,
        version: str,
        label_policy: str,
        accuracy: float,
        calibration_T: float,
        top3_accuracy: Optional[float] = None,
        abstention_rate: Optional[float] = None,
        ece: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Dict:
        """
        Register a new model version

        Args:
            model_id: Unique identifier (e.g., "v5_etymology_20251030")
            model_file: Path to model binary
            version: Training date (YYYY-MM-DD)
            label_policy: "etymology" or "affiliation"
            accuracy: Test set accuracy (0.0-1.0)
            calibration_T: Temperature scaling parameter
            top3_accuracy: Optional top-3 accuracy
            abstention_rate: Optional abstention rate
            ece: Optional Expected Calibration Error
            notes: Optional description

        Returns:
            Model metadata dict
        """
        model_path = Path(model_file)

        # Compute model hash
        model_hash = self._compute_model_hash(model_path)

        # Create model metadata
        model_metadata = {
            "model_id": model_id,
            "model_file": str(model_path),
            "model_hash": model_hash,
            "version": version,
            "label_policy": label_policy,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "accuracy": accuracy,
                "top3_accuracy": top3_accuracy,
                "abstention_rate": abstention_rate,
                "ece": ece,
            },
            "calibration": {
                "method": "temperature_scaling",
                "T": calibration_T,
            },
            "deployment_status": "registered",  # registered | active | deprecated
            "deployed_at": None,
            "deprecated_at": None,
            "notes": notes or f"Registered on {datetime.utcnow().strftime('%Y-%m-%d')}",
        }

        # Add to registry
        self.registry["models"][model_id] = model_metadata
        self._save()

        print(f"✅ Registered model: {model_id}")
        print(f"   File: {model_file}")
        print(f"   Hash: {model_hash[:16]}...")
        print(f"   Accuracy: {accuracy:.1%}")
        print(f"   Label policy: {label_policy}")

        return model_metadata

    def activate_model(self, model_id: str, notes: Optional[str] = None):
        """
        Set a model as active (deployed to production)

        Args:
            model_id: Model to activate
            notes: Optional deployment notes
        """
        if model_id not in self.registry["models"]:
            raise ValueError(f"Model {model_id} not found in registry")

        # Deprecate current active model
        current_active = self.registry.get("active_model_id")
        if current_active and current_active in self.registry["models"]:
            self.registry["models"][current_active]["deployment_status"] = "deprecated"
            self.registry["models"][current_active]["deprecated_at"] = (
                datetime.utcnow().isoformat() + "Z"
            )

        # Activate new model
        self.registry["models"][model_id]["deployment_status"] = "active"
        self.registry["models"][model_id]["deployed_at"] = (
            datetime.utcnow().isoformat() + "Z"
        )
        self.registry["active_model_id"] = model_id

        # Log deployment
        deployment_record = {
            "model_id": model_id,
            "deployed_at": datetime.utcnow().isoformat() + "Z",
            "previous_model_id": current_active,
            "notes": notes or f"Activated {model_id}",
        }
        self.registry["deployment_history"].append(deployment_record)

        self._save()

        print(f"✅ Activated model: {model_id}")
        if current_active:
            print(f"   Replaced: {current_active}")

    def get_active_model(self) -> Optional[Dict]:
        """Get currently active model metadata"""
        active_id = self.registry.get("active_model_id")
        if active_id and active_id in self.registry["models"]:
            return self.registry["models"][active_id]
        return None

    def list_models(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all models

        Args:
            status: Optional filter ("registered", "active", "deprecated")

        Returns:
            List of model metadata dicts
        """
        models = list(self.registry["models"].values())

        if status:
            models = [m for m in models if m["deployment_status"] == status]

        # Sort by registration date (newest first)
        models.sort(key=lambda m: m["registered_at"], reverse=True)

        return models

    def get_deployment_history(self) -> List[Dict]:
        """Get deployment history"""
        return self.registry["deployment_history"]

    def compare_models(self, model_id_1: str, model_id_2: str) -> Dict:
        """
        Compare two models

        Args:
            model_id_1: First model
            model_id_2: Second model

        Returns:
            Comparison dict
        """
        if model_id_1 not in self.registry["models"]:
            raise ValueError(f"Model {model_id_1} not found")
        if model_id_2 not in self.registry["models"]:
            raise ValueError(f"Model {model_id_2} not found")

        m1 = self.registry["models"][model_id_1]
        m2 = self.registry["models"][model_id_2]

        comparison = {
            "model_1": {
                "id": model_id_1,
                "version": m1["version"],
                "label_policy": m1["label_policy"],
                "accuracy": m1["metrics"]["accuracy"],
            },
            "model_2": {
                "id": model_id_2,
                "version": m2["version"],
                "label_policy": m2["label_policy"],
                "accuracy": m2["metrics"]["accuracy"],
            },
            "improvements": {},
        }

        # Compare metrics
        if m1["metrics"]["accuracy"] and m2["metrics"]["accuracy"]:
            diff = m2["metrics"]["accuracy"] - m1["metrics"]["accuracy"]
            comparison["improvements"]["accuracy"] = {
                "delta": diff,
                "delta_pp": diff * 100,
                "better": model_id_2 if diff > 0 else model_id_1,
            }

        return comparison

    def export_report(self, output_path: str):
        """Export registry report"""
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "active_model": self.get_active_model(),
            "total_models": len(self.registry["models"]),
            "registered_models": len(
                [
                    m
                    for m in self.registry["models"].values()
                    if m["deployment_status"] == "registered"
                ]
            ),
            "active_models": len(
                [
                    m
                    for m in self.registry["models"].values()
                    if m["deployment_status"] == "active"
                ]
            ),
            "deprecated_models": len(
                [
                    m
                    for m in self.registry["models"].values()
                    if m["deployment_status"] == "deprecated"
                ]
            ),
            "deployment_history": self.registry["deployment_history"],
            "all_models": list(self.registry["models"].values()),
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Exported report to {output_path}")


if __name__ == "__main__":
    # Demo usage
    print("=" * 80)
    print("MODEL REGISTRY DEMO")
    print("=" * 80)

    registry = ModelRegistry("models/demo_registry.json")

    # Register v4 model (baseline)
    print("\n1. Registering v4 model (baseline)...")
    registry.register_model(
        model_id="v4_affiliation_20251027",
        model_file="data/ml_training/regional_classifier_v4_optimized.bin",
        version="2025-10-27",
        label_policy="affiliation",
        accuracy=0.6814,
        calibration_T=1.0,
        notes="Baseline model with affiliation-based labels",
    )

    # Register v5 model (current)
    print("\n2. Registering v5 model (etymology)...")
    registry.register_model(
        model_id="v5_etymology_20251030",
        model_file="data/ml_training/regional_classifier_v5_etymology.bin",
        version="2025-10-30",
        label_policy="etymology",
        accuracy=0.8601,
        calibration_T=2.817,
        top3_accuracy=0.9107,
        abstention_rate=0.005,
        ece=0.0063,
        notes="Production model with etymology labels and calibration",
    )

    # Activate v5
    print("\n3. Activating v5 model...")
    registry.activate_model(
        "v5_etymology_20251030", notes="Deploy v5 to production - 86.01% accuracy"
    )

    # List models
    print("\n4. Listing all models...")
    models = registry.list_models()
    for model in models:
        status_icon = "✅" if model["deployment_status"] == "active" else "📝"
        print(f"\n  {status_icon} {model['model_id']}")
        print(f"     Status: {model['deployment_status']}")
        print(f"     Accuracy: {model['metrics']['accuracy']:.1%}")
        print(f"     Label policy: {model['label_policy']}")

    # Compare models
    print("\n5. Comparing v4 vs v5...")
    comparison = registry.compare_models(
        "v4_affiliation_20251027", "v5_etymology_20251030"
    )
    print(
        f"\n  Model 1: {comparison['model_1']['id']} ({comparison['model_1']['accuracy']:.1%})"
    )
    print(
        f"  Model 2: {comparison['model_2']['id']} ({comparison['model_2']['accuracy']:.1%})"
    )
    if "accuracy" in comparison["improvements"]:
        imp = comparison["improvements"]["accuracy"]
        print(f"  Improvement: +{imp['delta_pp']:.2f}pp")
        print(f"  Better model: {imp['better']}")

    # Get active model
    print("\n6. Getting active model...")
    active = registry.get_active_model()
    if active:
        print(f"\n  Active: {active['model_id']}")
        print(f"  Deployed: {active['deployed_at']}")
        print(f"  Accuracy: {active['metrics']['accuracy']:.1%}")

    # Export report
    print("\n7. Exporting report...")
    registry.export_report("models/demo_registry_report.json")

    print("\n" + "=" * 80)
    print("✅ MODEL REGISTRY DEMO COMPLETE")
    print("=" * 80)
