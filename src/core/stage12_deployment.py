"""
Stage 12: Deployment - Production deployment with versioning and validation.
Implements V7 specification for deployment stage.
"""

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DeploymentManager:
    """
    Manages Stage 12 deployment with:
    - Semantic versioning
    - Production validation
    - Rollback capability
    - Deployment manifests
    - Health checks
    """

    def __init__(self, deployment_dir: Path = Path("deployments")):
        """
        Initialize deployment manager.

        Args:
            deployment_dir: Directory for deployment artifacts
        """
        self.deployment_dir = Path(deployment_dir)
        self.deployment_dir.mkdir(parents=True, exist_ok=True)

        # Version tracking
        self.version_file = self.deployment_dir / "version.json"
        self.current_version = self._load_version()

        # Deployment history
        self.history_dir = self.deployment_dir / "history"
        self.history_dir.mkdir(exist_ok=True)

        # Production artifacts
        self.production_dir = self.deployment_dir / "production"
        self.production_dir.mkdir(exist_ok=True)

    def _load_version(self) -> str:
        """Load current version from file or initialize."""
        if self.version_file.exists():
            with open(self.version_file, "r") as f:
                data = json.load(f)
                return data.get("version", "0.0.0")
        return "0.0.0"

    def _save_version(self, version: str):
        """Save version to file."""
        with open(self.version_file, "w") as f:
            json.dump({"version": version, "updated": datetime.now().isoformat()}, f, indent=2)

    def _bump_version(self, bump_type: str = "patch") -> str:
        """
        Bump semantic version.

        Args:
            bump_type: 'major', 'minor', or 'patch'

        Returns:
            New version string
        """
        major, minor, patch = map(int, self.current_version.split("."))

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        new_version = f"{major}.{minor}.{patch}"
        self.current_version = new_version
        self._save_version(new_version)
        return new_version

    def validate_for_deployment(
        self, entries: List[Dict[str, Any]], metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate entries and metrics for production deployment.

        Args:
            entries: Processed entries
            metrics: Pipeline metrics

        Returns:
            Validation results
        """
        validation_results = {"passed": True, "checks": {}, "warnings": [], "errors": []}

        # 1. Check entry count
        entry_count = len(entries)
        validation_results["checks"]["entry_count"] = {
            "value": entry_count,
            "passed": entry_count > 0,
        }
        if entry_count == 0:
            validation_results["errors"].append("No entries to deploy")
            validation_results["passed"] = False

        # 2. Check data quality
        validation_errors = sum(1 for e in entries if e.get("ValidationErrors"))
        error_rate = validation_errors / entry_count if entry_count > 0 else 0
        validation_results["checks"]["error_rate"] = {
            "value": f"{error_rate:.2%}",
            "passed": error_rate < 0.05,  # Less than 5% errors
        }
        if error_rate >= 0.05:
            validation_results["warnings"].append(f"High error rate: {error_rate:.2%}")

        # 3. Check authority coverage
        authority_coverage = sum(1 for e in entries if e.get("AuthoritySources"))
        coverage_rate = authority_coverage / entry_count if entry_count > 0 else 0
        validation_results["checks"]["authority_coverage"] = {
            "value": f"{coverage_rate:.2%}",
            "passed": coverage_rate > 0.8,  # At least 80% coverage
        }
        if coverage_rate < 0.8:
            validation_results["warnings"].append(f"Low authority coverage: {coverage_rate:.2%}")

        # 4. Check idempotency
        if metrics:
            idempotency_verified = metrics.get("idempotency_verified", False)
            validation_results["checks"]["idempotency"] = {
                "value": idempotency_verified,
                "passed": idempotency_verified,
            }
            if not idempotency_verified:
                validation_results["errors"].append("Idempotency not verified")
        else:
            validation_results["checks"]["idempotency"] = {
                "value": False,
                "passed": True,  # Skip check if no metrics
            }
            validation_results["passed"] = False

        # 5. Check performance
        if metrics:
            throughput = metrics.get("entries_per_second", 0)
            validation_results["checks"]["performance"] = {
                "value": f"{throughput:.1f} entries/sec",
                "passed": throughput > 10,  # At least 10 entries/sec
            }
            if throughput < 10:
                validation_results["warnings"].append(
                    f"Low throughput: {throughput:.1f} entries/sec"
                )
        else:
            validation_results["checks"]["performance"] = {
                "value": "Not measured",
                "passed": True,  # Skip check if no metrics
            }

        # 6. Check graph coherence
        coherence_scores = [e.get("GraphCoherence", 0) for e in entries]
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
        validation_results["checks"]["graph_coherence"] = {
            "value": f"{avg_coherence:.3f}",
            "passed": avg_coherence > 0.25,
        }
        if avg_coherence <= 0.25:
            validation_results["warnings"].append(f"Low average coherence: {avg_coherence:.3f}")

        return validation_results

    def create_deployment_manifest(
        self,
        entries: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        validation: Dict[str, Any],
        version: str,
    ) -> Dict[str, Any]:
        """
        Create deployment manifest with metadata.

        Args:
            entries: Processed entries
            metrics: Pipeline metrics
            validation: Validation results
            version: Deployment version

        Returns:
            Deployment manifest
        """
        # Compute data hash for integrity
        data_str = json.dumps(entries, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        manifest = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "data": {"entry_count": len(entries), "hash": data_hash, "size_bytes": len(data_str)},
            "metrics": {
                "throughput": metrics.get("entries_per_second", 0),
                "total_time": metrics.get("duration_seconds", 0),
                "stage_timings": metrics.get("stage_timings", {}),
            },
            "validation": validation,
            "environment": {
                "pipeline_mode": metrics.get("mode", "unknown"),
                "python_version": "3.12",
                "deployment_type": "production",
            },
        }

        return manifest

    def deploy(
        self,
        entries: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        bump_type: str = "patch",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Deploy processed entries to production.

        Args:
            entries: Processed entries
            metrics: Pipeline metrics
            bump_type: Version bump type
            force: Force deployment even with validation warnings

        Returns:
            Deployment result
        """
        logger.info(f"Starting deployment with {len(entries)} entries")

        # 1. Validate
        validation = self.validate_for_deployment(entries, metrics)

        if not validation["passed"] and not force:
            logger.error("Deployment validation failed")
            return {
                "success": False,
                "validation": validation,
                "message": "Validation failed. Use force=True to override.",
            }

        if validation["warnings"] and not force:
            logger.warning(f"Deployment has {len(validation['warnings'])} warnings")

        # 2. Bump version
        new_version = self._bump_version(bump_type)
        logger.info(f"Deploying version {new_version}")

        # 3. Create manifest
        manifest = self.create_deployment_manifest(entries, metrics, validation, new_version)

        # 4. Archive current production if exists
        current_prod = self.production_dir / "data.json"
        if current_prod.exists():
            archive_name = (
                f"v{self.current_version.replace('.', '_')}_{datetime.now():%Y%m%d_%H%M%S}"
            )
            archive_dir = self.history_dir / archive_name
            archive_dir.mkdir()
            shutil.copy2(current_prod, archive_dir / "data.json")

            # Also copy current manifest
            current_manifest = self.production_dir / "manifest.json"
            if current_manifest.exists():
                shutil.copy2(current_manifest, archive_dir / "manifest.json")

            logger.info(f"Archived previous deployment to {archive_dir}")

        # 5. Deploy new data
        with open(self.production_dir / "data.json", "w") as f:
            json.dump(entries, f, indent=2)

        with open(self.production_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # 6. Create version tag
        tag_file = self.production_dir / f"v{new_version}.tag"
        tag_file.touch()

        # 7. Run health check
        health = self.health_check()

        result = {
            "success": True,
            "version": new_version,
            "deployed_at": datetime.now().isoformat(),
            "entries_deployed": len(entries),
            "validation": validation,
            "health_check": health,
            "artifacts": {
                "data": str(self.production_dir / "data.json"),
                "manifest": str(self.production_dir / "manifest.json"),
                "tag": str(tag_file),
            },
        }

        logger.info(f"Deployment successful: v{new_version}")
        return result

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of deployed data.

        Returns:
            Health check results
        """
        health = {"healthy": True, "checks": {}}

        # Check data file exists
        data_file = self.production_dir / "data.json"
        health["checks"]["data_file_exists"] = data_file.exists()

        if not data_file.exists():
            health["healthy"] = False
            return health

        # Check data integrity
        try:
            with open(data_file, "r") as f:
                data = json.load(f)
                health["checks"]["valid_json"] = True
                health["checks"]["entry_count"] = len(data)
        except json.JSONDecodeError:
            health["checks"]["valid_json"] = False
            health["healthy"] = False
            return health

        # Check manifest
        manifest_file = self.production_dir / "manifest.json"
        health["checks"]["manifest_exists"] = manifest_file.exists()

        if manifest_file.exists():
            try:
                with open(manifest_file, "r") as f:
                    manifest = json.load(f)
                    health["checks"]["version"] = manifest.get("version")
                    health["checks"]["deployed_at"] = manifest.get("timestamp")
            except json.JSONDecodeError:
                health["checks"]["valid_manifest"] = False

        return health

    def rollback(self, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback to a previous deployment.

        Args:
            version: Version to rollback to (latest if None)

        Returns:
            Rollback result
        """
        # Find available backups
        backups = sorted(self.history_dir.iterdir(), reverse=True)

        if not backups:
            return {"success": False, "message": "No backups available for rollback"}

        # Select backup
        if version:
            target = None
            for backup in backups:
                if f"v{version.replace('.', '_')}" in backup.name:
                    target = backup
                    break
            if not target:
                return {"success": False, "message": f"Version {version} not found in history"}
        else:
            target = backups[0]  # Latest backup

        logger.info(f"Rolling back to {target.name}")

        # Restore files
        data_backup = target / "data.json"
        manifest_backup = target / "manifest.json"

        if data_backup.exists():
            shutil.copy2(data_backup, self.production_dir / "data.json")

        if manifest_backup.exists():
            shutil.copy2(manifest_backup, self.production_dir / "manifest.json")

            # Update version
            with open(manifest_backup, "r") as f:
                manifest = json.load(f)
                restored_version = manifest.get("version", "0.0.0")
                self.current_version = restored_version
                self._save_version(restored_version)

        return {
            "success": True,
            "restored_from": str(target),
            "version": self.current_version,
            "message": f"Successfully rolled back to {target.name}",
        }
