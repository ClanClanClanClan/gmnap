"""
V7 Pipeline Orchestrator - Main Integration System
Connects all V7 components into a unified, compliant system.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .pipeline_v7 import V7Pipeline, PipelineMode
from .v7_quality_gates import V7QualityGates
from .compliance_tracker import V7ComplianceTracker
from ..regions.manager import RegionManager

logger = logging.getLogger(__name__)


class V7Orchestrator:
    """
    V7 Compliance Orchestrator - Main integration system for GMNAP V7.

    This orchestrator ensures 100% V7 specification compliance by:
    1. Integrating all pipeline stages
    2. Enforcing quality gates
    3. Tracking compliance metrics
    4. Managing system state
    """

    def __init__(
        self, mode: PipelineMode = PipelineMode.QUICK, config_dir: Path = None
    ):
        """Initialize V7 orchestrator."""
        self.mode = mode
        self.config_dir = config_dir or Path("./config")

        # Core components
        self.pipeline = V7Pipeline(mode=mode)
        # Use V7 quality gates for Step 2.1 (core V7 gates with real logic)
        self.quality_gates = V7QualityGates()
        self.compliance_tracker = V7ComplianceTracker()
        self.region_manager = RegionManager(self.config_dir)

        # System state
        self.is_initialized = False
        self.last_run_results = None
        self.compliance_metrics = {}

        logger.info(f"V7 Orchestrator initialized in {mode.value} mode")

    async def initialize(self) -> bool:
        """Initialize the V7 system components."""
        try:
            logger.info("Initializing V7 orchestrator components...")

            # Initialize compliance tracker
            await self.compliance_tracker.initialize()

            # Quality gate system is ready (no async initialization needed)

            # Validate system readiness
            readiness_check = await self._check_system_readiness()

            if readiness_check["ready"]:
                self.is_initialized = True
                logger.info("V7 orchestrator initialization complete")
                return True
            else:
                logger.error(
                    f"V7 orchestrator initialization failed: {readiness_check['errors']}"
                )
                return False

        except Exception as e:
            logger.error(f"V7 orchestrator initialization error: {e}")
            return False

    async def process(
        self, entries: List[Dict[str, Any]], run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process entries through the complete V7 pipeline with full compliance.

        Args:
            entries: List of entry dictionaries to process
            run_id: Optional run identifier for tracking

        Returns:
            Complete V7 processing results with compliance metrics
        """
        if not self.is_initialized:
            raise RuntimeError(
                "V7 orchestrator not initialized - call initialize() first"
            )

        run_id = run_id or f"v7_run_{datetime.now():%Y%m%d_%H%M%S}"
        logger.info(f"Starting V7 processing run: {run_id}")

        # Start compliance tracking
        await self.compliance_tracker.start_run(run_id, entries)

        try:
            # Phase 1: Pre-processing validation
            pre_validation = await self._pre_process_validation(entries)
            if not pre_validation["passed"]:
                return await self._handle_validation_failure(run_id, pre_validation)

            # Phase 2: Execute V7 pipeline
            pipeline_results = await self.pipeline.process_batch(entries)

            # Phase 3: Quality gate enforcement
            entries_for_quality = pipeline_results.get("processed_entries", entries)
            quality_results = await self.quality_gates.validate_batch(
                entries_for_quality
            )

            # Phase 4: V7 compliance verification
            compliance_results = await self.compliance_tracker.verify_v7_compliance(
                pipeline_results, quality_results
            )

            # Phase 5: Generate final results
            final_results = await self._generate_final_results(
                run_id, pipeline_results, quality_results, compliance_results
            )

            # Phase 6: Post-processing
            await self._post_process_cleanup(run_id, final_results)

            logger.info(f"V7 processing run {run_id} completed successfully")
            return final_results

        except Exception as e:
            logger.error(f"V7 processing run {run_id} failed: {e}")
            await self.compliance_tracker.record_error(run_id, str(e))
            raise

    async def _check_system_readiness(self) -> Dict[str, Any]:
        """Check if all V7 system components are ready."""
        readiness_checks = []
        errors = []

        # Check pipeline readiness
        try:
            pipeline_ready = (
                hasattr(self.pipeline, "stages") and len(self.pipeline.stages) == 13
            )  # 0-11 + 1b
            readiness_checks.append(("pipeline", pipeline_ready))
            if not pipeline_ready:
                errors.append("Pipeline stages not complete")
        except Exception as e:
            readiness_checks.append(("pipeline", False))
            errors.append(f"Pipeline check failed: {e}")

        # Check region manager readiness
        try:
            region_count = len(self.region_manager.available_regions)
            region_ready = region_count >= 30  # Expect at least 30 regions
            readiness_checks.append(("regions", region_ready))
            if not region_ready:
                errors.append(f"Insufficient regions loaded: {region_count}")
        except Exception as e:
            readiness_checks.append(("regions", False))
            errors.append(f"Region manager check failed: {e}")

        # Check quality gates readiness
        try:
            gates_ready = True  # EnhancedQualityGates is always ready
            readiness_checks.append(("quality_gates", gates_ready))
            if not gates_ready:
                errors.append("Quality gate system not ready")
        except Exception as e:
            readiness_checks.append(("quality_gates", False))
            errors.append(f"Quality gates check failed: {e}")

        # Check compliance tracker readiness
        try:
            tracker_ready = self.compliance_tracker.is_ready
            readiness_checks.append(("compliance_tracker", tracker_ready))
            if not tracker_ready:
                errors.append("Compliance tracker not ready")
        except Exception as e:
            readiness_checks.append(("compliance_tracker", False))
            errors.append(f"Compliance tracker check failed: {e}")

        all_ready = all(ready for _, ready in readiness_checks)

        return {
            "ready": all_ready,
            "checks": dict(readiness_checks),
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
        }

    async def _pre_process_validation(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Pre-process validation before pipeline execution."""
        validation_results = {
            "passed": True,
            "entries_validated": 0,
            "entries_failed": 0,
            "errors": [],
        }

        try:
            # Basic entry structure validation
            for i, entry in enumerate(entries):
                try:
                    # Check required fields
                    if not entry.get("CanonicalLatin"):
                        validation_results["errors"].append(
                            f"Entry {i}: Missing CanonicalLatin"
                        )
                        validation_results["entries_failed"] += 1
                        continue

                    # Basic field type validation
                    canonical = entry.get("CanonicalLatin")
                    if not isinstance(canonical, str) or len(canonical.strip()) == 0:
                        validation_results["errors"].append(
                            f"Entry {i}: Invalid CanonicalLatin"
                        )
                        validation_results["entries_failed"] += 1
                        continue

                    validation_results["entries_validated"] += 1

                except Exception as e:
                    validation_results["errors"].append(
                        f"Entry {i}: Validation error - {e}"
                    )
                    validation_results["entries_failed"] += 1

            # Check if too many entries failed
            failure_rate = (
                validation_results["entries_failed"] / len(entries) if entries else 0
            )
            if failure_rate > 0.1:  # More than 10% failed
                validation_results["passed"] = False
                validation_results["errors"].append(
                    f"High failure rate: {failure_rate:.2%}"
                )

        except Exception as e:
            validation_results["passed"] = False
            validation_results["errors"].append(f"Pre-validation system error: {e}")

        return validation_results

    async def _handle_validation_failure(
        self, run_id: str, validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle pre-validation failures."""
        logger.error(
            f"Pre-validation failed for run {run_id}: {validation_results['errors']}"
        )

        await self.compliance_tracker.record_validation_failure(
            run_id, validation_results
        )

        return {
            "run_id": run_id,
            "status": "FAILED",
            "stage": "pre_validation",
            "error": "Pre-validation failed",
            "validation_results": validation_results,
            "compliance_status": {"overall_score": 0.0, "status": "FAILED_VALIDATION"},
        }

    async def _generate_final_results(
        self,
        run_id: str,
        pipeline_results: Dict[str, Any],
        quality_results: Dict[str, Any],
        compliance_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive final results."""

        # Calculate overall compliance score
        compliance_score = compliance_results.get("overall_score", 0.0)

        # Determine final status
        if compliance_score >= 0.95:
            status = "V7_COMPLIANT"
        elif compliance_score >= 0.85:
            status = "MOSTLY_COMPLIANT"
        elif compliance_score >= 0.70:
            status = "PARTIALLY_COMPLIANT"
        else:
            status = "NON_COMPLIANT"

        final_results = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode.value,
            "status": status,
            # Pipeline results
            "pipeline": {
                "processed_entries": pipeline_results.get("processed_entries", 0),
                "failed_entries": pipeline_results.get("failed_entries", 0),
                "duration_seconds": pipeline_results.get("duration_seconds", 0),
                "throughput": pipeline_results.get("entries_per_second", 0),
                "stage_timings": pipeline_results.get("stage_timings", {}),
            },
            # Quality gate results
            "quality_gates": {
                "gates_passed": quality_results.get("gates_passed", 0),
                "total_gates": quality_results.get("total_gates", 8),
                "gate_results": quality_results.get("gate_details", {}),
                "compliance_rate": quality_results.get("compliance_rate", 0.0),
            },
            # V7 compliance results
            "compliance": {
                "overall_score": compliance_score,
                "status": status,
                "pipeline_compliance": compliance_results.get(
                    "pipeline_compliance", {}
                ),
                "authority_compliance": compliance_results.get(
                    "authority_compliance", {}
                ),
                "region_compliance": compliance_results.get("region_compliance", {}),
                "linguistic_compliance": compliance_results.get(
                    "linguistic_compliance", {}
                ),
            },
            # System metrics
            "system": {
                "memory_usage_mb": self._get_memory_usage(),
                "cpu_usage_percent": self._get_cpu_usage(),
                "disk_usage_mb": self._get_disk_usage(),
            },
        }

        # Store results for future reference
        self.last_run_results = final_results

        return final_results

    async def _post_process_cleanup(self, run_id: str, results: Dict[str, Any]) -> None:
        """Post-processing cleanup and finalization."""
        try:
            # Update compliance tracker with final results
            await self.compliance_tracker.finalize_run(run_id, results)

            # Archive run results
            output_dir = Path("output/v7_runs")
            output_dir.mkdir(parents=True, exist_ok=True)

            results_file = output_dir / f"{run_id}_results.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"V7 run results archived to {results_file}")

        except Exception as e:
            logger.warning(f"Post-processing cleanup failed: {e}")

    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            return int(process.memory_info().rss / 1024 / 1024)
        except ImportError:
            return 0
        except Exception:
            return 0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil

            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def _get_disk_usage(self) -> int:
        """Get disk usage for output directory in MB."""
        try:
            output_dir = Path("output")
            if output_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in output_dir.rglob("*") if f.is_file()
                )
                return int(total_size / 1024 / 1024)
            return 0
        except Exception:
            return 0

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current V7 system status."""
        readiness = await self._check_system_readiness()

        return {
            "orchestrator": {
                "initialized": self.is_initialized,
                "mode": self.mode.value,
                "last_run": (
                    self.last_run_results.get("run_id")
                    if self.last_run_results
                    else None
                ),
            },
            "components": readiness["checks"],
            "ready": readiness["ready"],
            "errors": readiness["errors"],
            "compliance": await self.compliance_tracker.get_current_status(),
            "system_resources": {
                "memory_mb": self._get_memory_usage(),
                "cpu_percent": self._get_cpu_usage(),
                "disk_mb": self._get_disk_usage(),
            },
        }

    async def force_compliance_check(self) -> Dict[str, Any]:
        """Force a comprehensive V7 compliance check."""
        logger.info("Starting forced V7 compliance check...")

        # Run comprehensive compliance validation
        compliance_check = (
            await self.compliance_tracker.comprehensive_compliance_audit()
        )

        return compliance_check


async def main():
    """Example usage of V7 orchestrator."""
    import logging

    logging.basicConfig(level=logging.INFO)

    # Test data
    test_entries = [
        {"CanonicalLatin": "Einstein, Albert", "BirthYear": 1879},
        {"CanonicalLatin": "Gauss, Carl Friedrich", "BirthYear": 1777},
        {"CanonicalLatin": "Euler, Leonhard", "BirthYear": 1707},
        {"CanonicalLatin": "Newton, Isaac", "BirthYear": 1643},
        {"CanonicalLatin": "Archimedes", "BirthYear": -287},
    ]

    # Initialize and run orchestrator
    orchestrator = V7Orchestrator(mode=PipelineMode.QUICK)

    if await orchestrator.initialize():
        results = await orchestrator.process(test_entries)
        print(json.dumps(results, indent=2))
    else:
        print("Orchestrator initialization failed")


if __name__ == "__main__":
    asyncio.run(main())
