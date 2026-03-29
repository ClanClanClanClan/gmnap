"""
GMNAP v7.0 Pipeline Stage 3: Regional Processing Hooks
Executes regional processors on assigned data.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.errors import RegionalProcessingError
from ..regions.manager import RegionManager

logger = logging.getLogger(__name__)


class RegionHooksStage:
    """Stage 3: Regional processing hooks and data processing"""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize regional processing stage"""
        self.config_path = config_path or Path("./config")
        self.region_manager = RegionManager(self.config_path)
        self.processing_stats = {}

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute regional processors on assigned data

        Args:
            context: Pipeline execution context with regional assignments

        Returns:
            Updated context with processed regional data
        """
        try:
            raw_data = context.get("raw_data", [])
            regional_assignments = context.get("regional_assignments", [])
            config = context.get("config", {})

            if not regional_assignments:
                raise RegionalProcessingError(
                    "No regional assignments found from Stage 2"
                )

            # Initialize processing statistics
            processing_stats = {
                "total_records": len(raw_data),
                "processed_records": 0,
                "failed_records": 0,
                "regional_processing_time": {},
                "regional_success_rate": {},
                "processing_errors": [],
            }

            # Process records by region
            processed_data = []
            regional_data = self._group_by_region(raw_data, regional_assignments)

            for region_code, region_records in regional_data.items():
                try:
                    region_results = self._process_region_data(
                        region_code, region_records, config
                    )
                    processed_data.extend(region_results)
                    processing_stats["processed_records"] += len(region_results)

                except Exception as e:
                    error_msg = f"Region {region_code} processing failed: {str(e)}"
                    processing_stats["processing_errors"].append(error_msg)
                    processing_stats["failed_records"] += len(region_records)
                    logger.warning(error_msg)

                    # Add records to processed data with error flags
                    for record in region_records:
                        record["processing_error"] = str(e)
                        record["processing_status"] = "failed"
                        processed_data.append(record)

            # Calculate final statistics
            self._calculate_final_stats(processing_stats)

            # Update context
            context["processed_data"] = processed_data
            context["regional_processing_stats"] = processing_stats
            context["stage_3_completed"] = True

            return context

        except Exception as e:
            raise RegionalProcessingError(
                f"Stage 3 regional processing failed: {str(e)}"
            )

    def _group_by_region(
        self, data: List[Dict[str, Any]], assignments: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group records by their primary regional assignment"""
        regional_groups = {}

        for assignment in assignments:
            record_index = assignment["record_index"]
            primary_region = assignment["primary_region"]

            if record_index < len(data):
                record = data[record_index].copy()
                record["_assignment_info"] = assignment

                if primary_region not in regional_groups:
                    regional_groups[primary_region] = []

                regional_groups[primary_region].append(record)

        return regional_groups

    def _process_region_data(
        self, region_code: str, records: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process data for a specific region"""
        start_time = time.time()

        try:
            # Get regional processor
            region_processor = self.region_manager.get_region(region_code)
            if not region_processor:
                raise RegionalProcessingError(
                    f"Regional processor {region_code} not found"
                )

            # Process each record through the regional processor
            processed_records = []
            success_count = 0

            for record in records:
                try:
                    processed_record = self._process_single_record(
                        record, region_processor, region_code
                    )
                    processed_records.append(processed_record)
                    success_count += 1

                except Exception as e:
                    # Add error information but keep the record
                    record["regional_processing_error"] = str(e)
                    record["processing_status"] = "regional_failed"
                    record["assigned_region"] = region_code
                    processed_records.append(record)
                    logger.warning(
                        f"Record processing failed in {region_code}: {str(e)}"
                    )

            # Update processing statistics
            processing_time = time.time() - start_time
            self.processing_stats[region_code] = {
                "processing_time": processing_time,
                "records_processed": len(records),
                "success_count": success_count,
                "success_rate": success_count / len(records) if records else 0,
            }

            return processed_records

        except Exception as e:
            processing_time = time.time() - start_time
            self.processing_stats[region_code] = {
                "processing_time": processing_time,
                "records_processed": len(records),
                "success_count": 0,
                "success_rate": 0,
                "error": str(e),
            }
            raise

    def _process_single_record(
        self, record: Dict[str, Any], region_processor, region_code: str
    ) -> Dict[str, Any]:
        """Process a single record through the regional processor"""
        try:
            # Remove internal assignment info from the record
            processing_record = {
                k: v for k, v in record.items() if not k.startswith("_")
            }

            # Execute the v7.0 regional processing pipeline: clean → augment → validate → order_key

            # Step 1: Clean the record
            region_processor.clean(processing_record)

            # Step 2: Augment the record
            region_processor.augment(processing_record)

            # Step 3: Validate the record
            region_processor.validate(processing_record)

            # Step 4: Generate order key
            order_key = region_processor.order_key(processing_record)

            # Add regional processing metadata
            processing_record["_regional_metadata"] = {
                "assigned_region": region_code,
                "processing_status": "success",
                "order_key": order_key,
                "assignment_info": record.get("_assignment_info", {}),
                "processing_timestamp": time.time(),
            }

            return processing_record

        except Exception as e:
            # Preserve original record with error information
            error_record = record.copy()
            error_record["_regional_metadata"] = {
                "assigned_region": region_code,
                "processing_status": "error",
                "error": str(e),
                "assignment_info": record.get("_assignment_info", {}),
                "processing_timestamp": time.time(),
            }
            raise RegionalProcessingError(
                f"Regional processing failed for record: {str(e)}"
            )

    def _calculate_final_stats(self, processing_stats: Dict[str, Any]) -> None:
        """Calculate final processing statistics"""

        # Calculate per-region statistics
        for region_code, stats in self.processing_stats.items():
            processing_stats["regional_processing_time"][region_code] = stats.get(
                "processing_time", 0
            )
            processing_stats["regional_success_rate"][region_code] = stats.get(
                "success_rate", 0
            )

        # Calculate overall success rate
        total_records = processing_stats["total_records"]
        if total_records > 0:
            processing_stats["overall_success_rate"] = (
                processing_stats["processed_records"] / total_records
            )
        else:
            processing_stats["overall_success_rate"] = 0

        # Calculate total processing time
        processing_stats["total_processing_time"] = sum(
            stats.get("processing_time", 0) for stats in self.processing_stats.values()
        )

        # Add summary information
        processing_stats["regions_used"] = list(self.processing_stats.keys())
        processing_stats["total_regions"] = len(self.processing_stats)

        # Performance metrics
        if processing_stats["total_processing_time"] > 0:
            processing_stats["records_per_second"] = (
                processing_stats["processed_records"]
                / processing_stats["total_processing_time"]
            )
        else:
            processing_stats["records_per_second"] = 0

    def get_regional_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of regional processing performance"""
        if not self.processing_stats:
            return {"message": "No processing statistics available"}

        summary = {
            "total_regions_used": len(self.processing_stats),
            "regional_performance": {},
            "fastest_region": None,
            "slowest_region": None,
            "most_successful_region": None,
        }

        fastest_time = float("inf")
        slowest_time = 0
        highest_success_rate = 0

        for region_code, stats in self.processing_stats.items():
            processing_time = stats.get("processing_time", 0)
            success_rate = stats.get("success_rate", 0)

            summary["regional_performance"][region_code] = {
                "processing_time": processing_time,
                "success_rate": success_rate,
                "records_processed": stats.get("records_processed", 0),
            }

            # Track fastest region
            if processing_time < fastest_time and processing_time > 0:
                fastest_time = processing_time
                summary["fastest_region"] = region_code

            # Track slowest region
            if processing_time > slowest_time:
                slowest_time = processing_time
                summary["slowest_region"] = region_code

            # Track most successful region
            if success_rate > highest_success_rate:
                highest_success_rate = success_rate
                summary["most_successful_region"] = region_code

        return summary
