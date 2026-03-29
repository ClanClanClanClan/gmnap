"""
End-to-End Orchestration Integration - Step 4.2
Complete integration of all V7 components into working orchestration system
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from ..regions.manager import RegionManager
from .authority_source_integration import AuthoritySourceIntegrator
from .pipeline_stage_implementation import PipelineStageImplementor
from .pipeline_v7 import PipelineMode, V7Pipeline
from .v7_quality_gates import V7QualityGates


class EndToEndOrchestrator:
    """
    V7 End-to-End Orchestration System for Step 4.2
    Integrates all components into a complete processing pipeline

    Components integrated:
    - 8/12 Pipeline stages
    - 6 V7 Quality gates
    - 4 Authority sources
    - 34 Regional processors
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize all components
        self.pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        self.quality_gates = V7QualityGates()
        self.authority_integrator = AuthoritySourceIntegrator()
        self.stage_implementor = PipelineStageImplementor()
        self.region_manager = RegionManager()

        # Orchestration metrics
        self.metrics = {
            "entries_processed": 0,
            "entries_failed": 0,
            "stages_executed": 0,
            "gates_passed": 0,
            "gates_failed": 0,
            "authority_enrichments": 0,
            "regional_detections": 0,
        }

        # Processing stages configuration
        self.active_stages = [
            "Stage_0_Config",
            "Stage_1_Ingest",
            "Stage_1b_LLMExtract",
            "Stage_2_DetectRegion",
            "Stage_3_RegionHooks",
            "Stage_4_AuthorityEnrich",
            "Stage_6_GenShortForm",
            "Stage_8_GlobalValidate",
        ]

    async def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single entry through the complete pipeline

        Args:
            entry: Input entry to process

        Returns:
            Fully processed entry with all enrichments
        """

        self.logger.info(f"Processing entry: {entry.get('GlobalID', 'unknown')}")

        # Initialize processing record
        processed_entry = entry.copy()
        processed_entry["ProcessingStartTime"] = datetime.now().isoformat()
        processed_entry["ProcessingStages"] = []

        try:
            # Stage 0: Configuration
            processed_entry["Stage_0_Config"] = True
            processed_entry["ProcessingStages"].append("Stage_0_Config")
            self.metrics["stages_executed"] += 1

            # Stage 1: Ingestion
            processed_entry["Stage_1_Ingest"] = True
            processed_entry["IngestedAt"] = datetime.now().isoformat()
            processed_entry["ProcessingStages"].append("Stage_1_Ingest")
            self.metrics["stages_executed"] += 1

            # Stage 1b: LLM Extraction (simulated)
            if not processed_entry.get("CanonicalLatin"):
                processed_entry["CanonicalLatin"] = entry.get("Name", "Unknown")
            processed_entry["Stage_1b_LLMExtract"] = True
            processed_entry["ProcessingStages"].append("Stage_1b_LLMExtract")
            self.metrics["stages_executed"] += 1

            # Stage 2: Region Detection
            detection = self.region_manager.detect_region(processed_entry)
            if detection:
                processed_entry["DetectedRegion"] = detection.region_code
                processed_entry["DetectionConfidence"] = detection.confidence
                self.metrics["regional_detections"] += 1
            processed_entry["Stage_2_DetectRegion"] = True
            processed_entry["ProcessingStages"].append("Stage_2_DetectRegion")
            self.metrics["stages_executed"] += 1

            # Stage 3: Regional Processing
            if processed_entry.get("DetectedRegion"):
                region_processor = self.region_manager.get_region(
                    processed_entry["DetectedRegion"]
                )
                if region_processor:
                    # Apply regional processing
                    region_processor.clean(processed_entry)
                    processed_entry["Stage_3_RegionHooks"] = True
                    processed_entry["ProcessingStages"].append("Stage_3_RegionHooks")
                    self.metrics["stages_executed"] += 1

            # Stage 4: Authority Enrichment
            enriched_entry = await self.stage_implementor.stage_4_authority_enrich(
                processed_entry
            )
            processed_entry.update(enriched_entry)
            if enriched_entry.get("Stage_4_EnrichmentSources"):
                self.metrics["authority_enrichments"] += 1
            processed_entry["ProcessingStages"].append("Stage_4_AuthorityEnrich")
            self.metrics["stages_executed"] += 1

            # Stage 6: Generate Short Forms
            short_form_entry = await self.stage_implementor.stage_6_gen_short_form(
                processed_entry
            )
            processed_entry.update(short_form_entry)
            processed_entry["ProcessingStages"].append("Stage_6_GenShortForm")
            self.metrics["stages_executed"] += 1

            # Stage 8: Global Validation
            validated_entry = await self.stage_implementor.stage_8_global_validate(
                processed_entry
            )
            processed_entry.update(validated_entry)
            processed_entry["ProcessingStages"].append("Stage_8_GlobalValidate")
            self.metrics["stages_executed"] += 1

            # Mark processing complete
            processed_entry["ProcessingEndTime"] = datetime.now().isoformat()
            processed_entry["ProcessingStatus"] = "SUCCESS"
            self.metrics["entries_processed"] += 1

        except Exception as e:
            self.logger.error(f"Error processing entry: {e}")
            processed_entry["ProcessingStatus"] = "FAILED"
            processed_entry["ProcessingError"] = str(e)
            self.metrics["entries_failed"] += 1

        return processed_entry

    async def process_batch(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of entries through the complete pipeline

        Args:
            entries: List of entries to process

        Returns:
            List of processed entries
        """

        self.logger.info(f"Processing batch of {len(entries)} entries")

        # Process entries
        processed_entries = []
        for entry in entries:
            processed_entry = await self.process_entry(entry)
            processed_entries.append(processed_entry)

        # Apply quality gates to batch
        gate_result = await self.quality_gates.validate_batch(processed_entries)

        # Update metrics
        if gate_result["summary"]["overall_passed"]:
            self.metrics["gates_passed"] += 1
        else:
            self.metrics["gates_failed"] += 1

        # Add gate results to entries
        for entry in processed_entries:
            entry["QualityGateResults"] = {
                "passed": gate_result["summary"]["overall_passed"],
                "validation_rate": gate_result["summary"]["validation_rate"],
                "gates_passed": gate_result["summary"]["gates_passed"],
                "gates_run": gate_result["summary"]["gates_run"],
            }

        return processed_entries

    async def run_end_to_end_orchestration(self) -> Dict[str, Any]:
        """
        Run comprehensive end-to-end orchestration test
        Demonstrates full integration of all V7 components
        """

        self.logger.info("Starting end-to-end orchestration for Step 4.2...")

        # Test dataset
        test_entries = [
            {
                "GlobalID": "E2E_001",
                "Name": "Einstein, Albert",
                "BirthYear": 1879,
                "Country": "Germany",
            },
            {
                "GlobalID": "E2E_002",
                "Name": "Curie, Marie",
                "BirthYear": 1867,
                "Country": "Poland",
            },
            {
                "GlobalID": "E2E_003",
                "Name": "Turing, Alan",
                "BirthYear": 1912,
                "Country": "United Kingdom",
            },
            {
                "GlobalID": "E2E_004",
                "Name": "Ramanujan, Srinivasa",
                "BirthYear": 1887,
                "Country": "India",
            },
            {
                "GlobalID": "E2E_005",
                "Name": "Noether, Emmy",
                "BirthYear": 1882,
                "Country": "Germany",
            },
        ]

        # Start timing
        start_time = time.time()

        # Process batch through orchestrator
        processed_entries = await self.process_batch(test_entries)

        # End timing
        end_time = time.time()
        processing_time = end_time - start_time

        # Analyze results
        successful_entries = [
            e for e in processed_entries if e.get("ProcessingStatus") == "SUCCESS"
        ]
        failed_entries = [
            e for e in processed_entries if e.get("ProcessingStatus") == "FAILED"
        ]

        # Calculate success metrics
        success_rate = (
            (len(successful_entries) / len(test_entries)) * 100 if test_entries else 0
        )
        avg_stages_per_entry = (
            self.metrics["stages_executed"] / len(test_entries) if test_entries else 0
        )

        # Component integration analysis
        component_integration = {
            "pipeline_stages": {
                "total_stages": len(self.active_stages),
                "stages_executed": self.metrics["stages_executed"],
                "average_per_entry": avg_stages_per_entry,
            },
            "quality_gates": {
                "gates_run": self.metrics["gates_passed"]
                + self.metrics["gates_failed"],
                "gates_passed": self.metrics["gates_passed"],
                "gates_failed": self.metrics["gates_failed"],
            },
            "authority_sources": {
                "enrichments_performed": self.metrics["authority_enrichments"],
                "enrichment_rate": (
                    self.metrics["authority_enrichments"] / len(test_entries)
                )
                * 100,
            },
            "regional_processing": {
                "detections_performed": self.metrics["regional_detections"],
                "detection_rate": (
                    self.metrics["regional_detections"] / len(test_entries)
                )
                * 100,
            },
        }

        # Sample processed entry for detailed view
        sample_entry = successful_entries[0] if successful_entries else None

        # Compile comprehensive results
        results = {
            "orchestration_summary": {
                "entries_processed": len(test_entries),
                "successful_entries": len(successful_entries),
                "failed_entries": len(failed_entries),
                "success_rate_percent": success_rate,
                "processing_time_seconds": processing_time,
                "throughput_entries_per_second": (
                    len(test_entries) / processing_time if processing_time > 0 else 0
                ),
            },
            "component_integration": component_integration,
            "orchestration_metrics": self.metrics,
            "sample_processed_entry": (
                self._sanitize_entry_for_display(sample_entry) if sample_entry else None
            ),
            "orchestration_metadata": {
                "test_timestamp": datetime.now().isoformat(),
                "active_stages": self.active_stages,
                "pipeline_mode": "QUICK",
            },
        }

        return results

    def _sanitize_entry_for_display(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize entry for display by removing large fields"""

        display_entry = {}
        important_fields = [
            "GlobalID",
            "CanonicalLatin",
            "ProcessingStatus",
            "ProcessingStages",
            "DetectedRegion",
            "DetectionConfidence",
            "Stage_4_EnrichmentSources",
            "ShortForms",
            "ValidationResults",
            "QualityGateResults",
        ]

        for field in important_fields:
            if field in entry:
                display_entry[field] = entry[field]

        return display_entry

    async def run_production_simulation(self) -> Dict[str, Any]:
        """
        Run production-level simulation with larger dataset
        Tests scalability and real-world performance
        """

        self.logger.info("Running production simulation...")

        # Generate larger test dataset
        production_entries = []
        names = [
            "Smith, John",
            "Johnson, Mary",
            "Williams, Robert",
            "Brown, Patricia",
            "Jones, Michael",
            "Garcia, Maria",
            "Miller, David",
            "Davis, Barbara",
            "Rodriguez, Richard",
            "Martinez, Susan",
            "Hernandez, Thomas",
            "Lopez, Nancy",
            "Gonzalez, Daniel",
            "Wilson, Betty",
            "Anderson, Christopher",
            "Thomas, Helen",
            "Taylor, Mark",
            "Moore, Dorothy",
            "Jackson, Paul",
            "Martin, Lisa",
        ]

        for i, name in enumerate(names):
            production_entries.append(
                {
                    "GlobalID": f"PROD_{i+1:04d}",
                    "Name": name,
                    "BirthYear": 1950 + (i * 2),
                    "Country": "United States" if i % 3 == 0 else "United Kingdom",
                }
            )

        # Start timing
        start_time = time.time()

        # Process in batches
        batch_size = 5
        all_processed = []

        for i in range(0, len(production_entries), batch_size):
            batch = production_entries[i : i + batch_size]
            processed_batch = await self.process_batch(batch)
            all_processed.extend(processed_batch)

        # End timing
        end_time = time.time()
        total_time = end_time - start_time

        # Calculate production metrics
        successful = len(
            [e for e in all_processed if e.get("ProcessingStatus") == "SUCCESS"]
        )

        return {
            "production_simulation": {
                "total_entries": len(production_entries),
                "successful_entries": successful,
                "success_rate_percent": (successful / len(production_entries)) * 100,
                "total_processing_time": total_time,
                "throughput_entries_per_second": (
                    len(production_entries) / total_time if total_time > 0 else 0
                ),
                "average_time_per_entry": (
                    total_time / len(production_entries) if production_entries else 0
                ),
            }
        }
