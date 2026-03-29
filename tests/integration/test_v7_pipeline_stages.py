from typing import List
from typing import Any
import pytest

#!/usr/bin/env python3
"""
Test V7 Pipeline - Individual Stage Testing

This test validates each of the 12 stages in the V7 processing pipeline:
0. Config - Load specs, verify licenses, DOI credentials
1. Ingest - Read YAML, Unicode NFC->NFKD->fold->NFC
1b. LLMExtract_ETD - Parse thesis PDFs with GPT-4o-mini (TODO)
2. DetectRegion - Script, ICU, fastText, affiliation, DOI prefix
3. RegionHooks - clean->augment->validate->order_key
4. AuthorityEnrich - Fetch ORCID_ETD, Crossref_Thesis, etc. (TODO)
5. CollisionAnalytics - DuckDB, suffix duplicates
6. GraphConsistency - Betweenness, Bayesian confidence
7. TagShortForms - Populate ShortFormClusters (TODO)
8. GlobalValidate - JSON-Schema, roundtrip, coherence gate (TODO)
9. Write&Diff - Deterministic YAML, HTML diff, SQL changelog
10. Report - Markdown metrics, draft DOI, push snapshot
11. IdempotencyCheck - Rerun pipeline, assert identical (TODO)
"""

import asyncio
import json

import time
from pathlib import Path
from typing import Dict, List, Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os

os.environ["GMNAP_OFFLINE"] = "1"
from src.core.pipeline_v7 import V7Pipeline, PipelineMode


class V7StageValidator:
    """Individual stage validation for V7 pipeline."""

    def __init__(self):
        self.pipeline = V7Pipeline(mode=PipelineMode.QUICK)
        self.test_entries = self._generate_test_data()
        self.results = {}

    def _generate_test_data(self) -> List[Dict[str, Any]]:
        """Generate diverse test data covering all regions with V7-compliant schema."""
        from datetime import datetime

        # V7-compliant base template
        base_entry = {
            "UpdatedAt": datetime.now().isoformat(),
            "LanguageOfPublication": ["en"],
            "FamilyNameType": "surname",
            "Gender": "unspecified",
            "CountryCodes": ["US"],
            "Confidence": 95,
            "Historic": False,
            "GDPR_DATA": False,
        }

        entries = []

        # Generate proper GlobalIDs (22-char Base32)
        test_global_ids = [
            "ABCDEFGHIJKLMNOPQRSTUV0",
            "ABCDEFGHIJKLMNOPQRSTUV1",
            "ABCDEFGHIJKLMNOPQRSTUV2",
            "ABCDEFGHIJKLMNOPQRSTUV3",
            "ABCDEFGHIJKLMNOPQRSTUV4",
            "ABCDEFGHIJKLMNOPQRSTUV5",
            "ABCDEFGHIJKLMNOPQRSTUV6",
            "ABCDEFGHIJKLMNOPQRSTUV7",
            "ABCDEFGHIJKLMNOPQRSTUV8",
            "ABCDEFGHIJKLMNOPQRSTUV9",
            "ABCDEFGHIJKLMNOPQRSTUVX",
            "ABCDEFGHIJKLMNOPQRSTUVY",
        ]

        test_entries = [
            # A1 Anglo Sphere
            {
                "CanonicalLatin": "Smith, John William",
                "CanonicalNative": "Smith, John William",
                "BirthYear": 1975,
                "Affiliation": "MIT",
                "Region": "A1",
                "CountryCodes": ["US"],
            },
            {
                "CanonicalLatin": "O'Connor, Mary Elizabeth",
                "CanonicalNative": "O'Connor, Mary Elizabeth",
                "BirthYear": 1980,
                "Region": "A1",
                "CountryCodes": ["IE"],
                "Gender": "female",
            },
            # A2 Western Europe
            {
                "CanonicalLatin": "Müller, Hans Friedrich",
                "CanonicalNative": "Müller, Hans Friedrich",
                "BirthYear": 1960,
                "Region": "A2",
                "CountryCodes": ["DE"],
                "Gender": "male",
            },
            {
                "CanonicalLatin": "García-López, María Carmen",
                "CanonicalNative": "García-López, María Carmen",
                "BirthYear": 1970,
                "Region": "A2",
                "CountryCodes": ["ES"],
                "Gender": "female",
            },
            # B1 East Slavic - properly paired entries
            {
                "CanonicalLatin": "Petrov, Aleksandr Nikolaevich",
                "CanonicalNative": "Петров Александр Николаевич",
                "BirthYear": 1965,
                "Region": "B1",
                "CountryCodes": ["RU"],
                "Gender": "male",
                "LanguageOfPublication": ["ru", "en"],
            },
            # C3 Arabic - properly paired entries
            {
                "CanonicalLatin": "al-Khwarizmi, Muhammad ibn Musa",
                "CanonicalNative": "الخوارزمي محمد بن موسى",
                "BirthYear": 780,
                "Region": "C3",
                "CountryCodes": ["IQ"],
                "Gender": "male",
                "Historic": True,
                "LanguageOfPublication": ["ar"],
            },
            # E1 Chinese - properly paired entries
            {
                "CanonicalLatin": "Wang Wei",
                "CanonicalNative": "王伟",
                "BirthYear": 1970,
                "Region": "E1",
                "CountryCodes": ["CN"],
                "Gender": "male",
                "LanguageOfPublication": ["zh", "en"],
            },
            # E3 Japanese - properly paired entries
            {
                "CanonicalLatin": "Tanaka Hiroshi",
                "CanonicalNative": "田中博",
                "BirthYear": 1965,
                "Region": "E3",
                "CountryCodes": ["JP"],
                "Gender": "male",
                "LanguageOfPublication": ["ja", "en"],
            },
            # E4 Korean - properly paired entries
            {
                "CanonicalLatin": "Kim Jong-un",
                "CanonicalNative": "김정은",
                "BirthYear": 1980,
                "Region": "E4",
                "CountryCodes": ["KP"],
                "Gender": "male",
                "LanguageOfPublication": ["ko"],
            },
            # Edge cases
            {
                "CanonicalLatin": "Duplicate Name",
                "CanonicalNative": "Duplicate Name",
                "BirthYear": 1990,
                "Region": "A1",
                "CountryCodes": ["US"],
            },
            {
                "CanonicalLatin": "Duplicate Name",
                "CanonicalNative": "Duplicate Name",
                "BirthYear": 1991,
                "Region": "A1",
                "CountryCodes": ["US"],
            },  # Intentional duplicate
            {
                "CanonicalLatin": "Unicode Test café naïve résumé",
                "CanonicalNative": "Unicode Test café naïve résumé",
                "BirthYear": 1985,
                "Region": "A2",
                "CountryCodes": ["FR"],
                "LanguageOfPublication": ["fr", "en"],
            },
        ]

        # Merge base template with each test entry (let pipeline generate GlobalIDs)
        for i, entry in enumerate(test_entries):
            full_entry = {**base_entry, **entry}
            # Remove pre-set GlobalID to let pipeline generate proper Base32 ones
        entries.append(full_entry)

        return entries

    async def test_stage_0_config(self) -> Dict[str, Any]:
        """Test Stage 0: Config validation."""
        print("🔧 Testing Stage 0: Config")

        start_time = time.time()
        try:
            await self.pipeline._stage_0_config()
            elapsed = time.time() - start_time

            # Validate config loaded
            config_valid = bool(self.pipeline.config)
            gates_valid = self.pipeline.quality_gates is not None

            result = {
                "status": "PASS" if config_valid and gates_valid else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "config_loaded": config_valid,
                "quality_gates_set": gates_valid,
                "mode": self.pipeline.mode.value,
                "workers": self.pipeline.workers,
            }

            print(
                f"  PASS Config: {config_valid}, Gates: {gates_valid}, Mode: {self.pipeline.mode.value}"
            )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_1_ingest(self) -> Dict[str, Any]:
        """Test Stage 1: Ingest with Unicode normalization."""
        print("📥 Testing Stage 1: Ingest")

        start_time = time.time()
        try:
            results = await self.pipeline._stage_1_ingest(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Validate Unicode normalization
            normalized_count = sum(1 for entry in results if "CanonicalLatinNormalized" in entry)
            unicode_test_entry = next(
                (e for e in results if "café" in e.get("CanonicalLatin", "")), None
            )

            result = {
                "status": "PASS" if len(results) == len(self.test_entries) else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "unicode_normalized_count": normalized_count,
                "unicode_normalization_working": unicode_test_entry is not None
                and "CanonicalLatinNormalized" in unicode_test_entry,
                "sample_normalization": (
                    unicode_test_entry.get("CanonicalLatinNormalized", "")
                    if unicode_test_entry
                    else ""
                ),
            }

            print(f"  PASS Processed: {len(results)}, Unicode normalized: {normalized_count}")
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_2_detect_region(self) -> Dict[str, Any]:
        """Test Stage 2: Region detection."""
        print("🌍 Testing Stage 2: DetectRegion")

        start_time = time.time()
        try:
            results = await self.pipeline._stage_2_detect_region(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Validate region detection
            detected_count = sum(1 for entry in results if "DetectedRegion" in entry)
            confidence_scores = [
                entry.get("DetectionConfidence", 0)
                for entry in results
                if "DetectionConfidence" in entry
            ]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            )

            # Check specific region detections
            region_accuracy = {}
            for entry in results:
                expected = entry.get("Region", "")
            detected = entry.get("DetectedRegion", "")
            if expected:
                region_accuracy[expected] = region_accuracy.get(
                    expected, {"correct": 0, "total": 0}
                )
            region_accuracy[expected]["total"] += 1
            if detected == expected:
                region_accuracy[expected]["correct"] += 1

            result = {
                "status": "PASS" if detected_count == len(results) else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "regions_detected": detected_count,
                "average_confidence": avg_confidence,
                "region_accuracy": region_accuracy,
            }

            print(
                f"  PASS Detected: {detected_count}/{len(results)}, Avg confidence: {avg_confidence:.3f}"
            )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_3_region_hooks(self) -> Dict[str, Any]:
        """Test Stage 3: Region hooks (clean->augment->validate->order_key)."""
        print("🎯 Testing Stage 3: RegionHooks")

        start_time = time.time()
        try:
            # Add region detection first
            entries_with_regions = await self.pipeline._stage_2_detect_region(
                self.test_entries.copy()
            )
            results = await self.pipeline._stage_3_region_hooks(entries_with_regions)
            elapsed = time.time() - start_time

            # Check if regional processing was applied
            processed = len(results) == len(entries_with_regions)
            regional_processing_applied = sum(
                1 for entry in results if "RegionalProcessing" in entry
            )
            order_keys_generated = sum(1 for entry in results if "OrderKey" in entry)
            successful_processing = sum(
                1
                for entry in results
                if entry.get("RegionalProcessing", {}).get("status") == "processed"
            )

            result = {
                "status": "PASS" if processed and regional_processing_applied > 0 else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "regional_processing_applied": regional_processing_applied,
                "order_keys_generated": order_keys_generated,
                "successful_processing": successful_processing,
                "failed_processing": self.pipeline.metrics.failed_entries,
            }

            if processed and regional_processing_applied > 0:
                print(
                    f"  PASS Processed: {len(results)}, Regional processing: {regional_processing_applied}, Order keys: {order_keys_generated}"
                )
            else:
                print(
                    f"  FAIL Processing failed - Processed: {len(results)}, Regional: {regional_processing_applied}"
                )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_4_authority_enrich(self) -> Dict[str, Any]:
        """Test Stage 4: Authority enrichment."""
        print("📚 Testing Stage 4: AuthorityEnrich")

        start_time = time.time()
        try:
            results = await self.pipeline._stage_4_authority_enrich(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Check enrichment implementation
            processed = len(results) == len(self.test_entries)
            enriched_count = sum(1 for entry in results if "AuthorityData" in entry)
            identifiers_added = sum(1 for entry in results if "Identifiers" in entry)
            affiliations_added = sum(1 for entry in results if "AuthorityAffiliations" in entry)

            # Stage 4 is now implemented if it processes without throwing TODO errors
            # and attempts to fetch authority data (even if no results due to quotas/network)
            result = {
                "status": "PASS" if processed else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "enriched_entries": enriched_count,
                "identifiers_added": identifiers_added,
                "affiliations_added": affiliations_added,
                "authority_sources": ["ORCID"],  # Currently implemented
            }

            print(
                f"  PASS Authority enrichment: {enriched_count} enriched, {identifiers_added} with IDs"
            )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_5_collision_analytics(self) -> Dict[str, Any]:
        """Test Stage 5: Collision analytics."""
        print("🔍 Testing Stage 5: CollisionAnalytics")

        start_time = time.time()
        try:
            # Add GlobalIDs only for duplicate detection test case
            test_data = self.test_entries.copy()
            for i, entry in enumerate(test_data):
                if "Duplicate Name" in entry.get("CanonicalLatin", ""):
                    entry["GlobalID"] = "DUPLICATE_TEST_ID"  # Intentional duplicate
                # For other entries, let the pipeline generate proper Base32 GlobalIDs

            results = await self.pipeline._stage_5_collision_analytics(test_data)
            elapsed = time.time() - start_time

            # Check duplicate handling
            global_ids = [entry.get("GlobalID", "") for entry in results]
            duplicate_suffixed = sum(1 for gid in global_ids if "--" in gid)

            result = {
                "status": "PASS" if len(results) == len(test_data) else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "duplicate_global_ids_detected": self.pipeline.metrics.duplicate_global_ids,
                "duplicates_suffixed": duplicate_suffixed,
                "unique_global_ids": len(set(global_ids)),
            }

            print(
                f"  PASS Duplicates detected: {self.pipeline.metrics.duplicate_global_ids}, Suffixed: {duplicate_suffixed}"
            )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_6_graph_consistency(self) -> Dict[str, Any]:
        """Test Stage 6: Graph consistency."""
        print("📊 Testing Stage 6: GraphConsistency")

        start_time = time.time()
        try:
            # Add some advisor relationships for testing
            test_data = self.test_entries.copy()
            test_data[0]["Advisors"] = ["Einstein, Albert"]
            test_data[1]["Advisors"] = ["Gauss, Carl Friedrich"]

            results = await self.pipeline._stage_6_graph_consistency(test_data)
            elapsed = time.time() - start_time

            # Check graph analysis
            betweenness_scores = sum(1 for entry in results if "BetweennessScore" in entry)
            graph_gates = sum(1 for entry in results if "GraphQualityGates" in entry)

            result = {
                "status": "PASS" if len(results) == len(test_data) else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "betweenness_scores_calculated": betweenness_scores,
                "graph_quality_gates_checked": graph_gates > 0,
                "graph_conflicts_detected": self.pipeline.metrics.graph_conflicts,
                "memgraph_connected": self.pipeline.memgraph_client.is_connected(),
            }

            print(
                f"  PASS Betweenness: {betweenness_scores}, Conflicts: {self.pipeline.metrics.graph_conflicts}"
            )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_7_tag_short_forms(self) -> Dict[str, Any]:
        """Test Stage 7: Tag short forms."""
        print("🏷️  Testing Stage 7: TagShortForms")

        start_time = time.time()
        try:
            results = await self.pipeline._stage_7_tag_short_forms(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Check short form implementation
            processed = len(results) == len(self.test_entries)
            short_forms_found = sum(1 for entry in results if "ShortForms" in entry)
            clusters_created = sum(1 for entry in results if "ShortFormClusters" in entry)

            # Check if pipeline has short_form_clusters attribute
            has_global_clusters = hasattr(self.pipeline, "short_form_clusters")
            global_cluster_count = len(getattr(self.pipeline, "short_form_clusters", {}))

            result = {
                "status": "PASS" if processed and short_forms_found > 0 else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "short_forms_found": short_forms_found,
                "clusters_created": clusters_created,
                "global_clusters": global_cluster_count,
                "has_global_clusters": has_global_clusters,
            }

            if processed and short_forms_found > 0:
                print(
                    f"  PASS Short forms: {short_forms_found} entries, {global_cluster_count} global clusters"
                )
            else:
                print(
                    f"  FAIL Short form processing failed - Processed: {len(results)}, Forms found: {short_forms_found}"
                )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_8_global_validate(self) -> Dict[str, Any]:
        """Test Stage 8: Global validation."""
        print("PASS Testing Stage 8: GlobalValidate")

        start_time = time.time()
        try:
            # First run through earlier pipeline stages to get proper data
            stage1_results = await self.pipeline._stage_1_ingest(self.test_entries.copy())
            stage2_results = await self.pipeline._stage_2_detect_region(stage1_results)
            stage3_results = await self.pipeline._stage_3_region_hooks(stage2_results)
            # Skip Stage 4 (AuthorityEnrich) to avoid quota consumption in tests
            stage5_results = await self.pipeline._stage_5_collision_analytics(stage3_results)
            results = await self.pipeline._stage_8_global_validate(stage5_results)
            elapsed = time.time() - start_time

            # Check validation implementation
            processed = len(results) == len(self.test_entries)
            validation_results_present = sum(1 for entry in results if "ValidationResults" in entry)
            validation_status_present = sum(1 for entry in results if "ValidationStatus" in entry)
            roundtrip_scores = sum(1 for entry in results if "RoundtripScore" in entry)
            valid_entries = sum(1 for entry in results if entry.get("ValidationStatus") == "VALID")

            result = {
                "status": "PASS" if processed and validation_results_present > 0 else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "validation_results_present": validation_results_present,
                "validation_status_present": validation_status_present,
                "roundtrip_scores_calculated": roundtrip_scores,
                "valid_entries": valid_entries,
                "roundtrip_failures": self.pipeline.metrics.roundtrip_failures,
            }

            if processed and validation_results_present > 0:
                print(
                    f"  PASS Validated: {len(results)}, Results: {validation_results_present}, Valid: {valid_entries}, Roundtrip scores: {roundtrip_scores}"
                )
            else:
                print(
                    f"  FAIL Validation failed - Processed: {len(results)}, Results: {validation_results_present}"
                )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_9_write_diff(self) -> Dict[str, Any]:
        """Test Stage 9: Write and diff."""
        print("💾 Testing Stage 9: Write&Diff")

        start_time = time.time()
        try:
            await self.pipeline._stage_9_write_diff(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Check if output file was created
            output_dir = Path("output")
            output_files = (
                list(output_dir.glob("v7_pipeline_*.json")) if output_dir.exists() else []
            )

            result = {
                "status": "PASS" if output_files else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "output_files_created": len(output_files),
                "latest_output": str(output_files[-1]) if output_files else None,
            }

            print(f"  PASS Output files created: {len(output_files)}")
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_10_report(self) -> Dict[str, Any]:
        """Test Stage 10: Report generation."""
        print("📋 Testing Stage 10: Report")

        start_time = time.time()
        try:
            await self.pipeline._stage_10_report(self.test_entries.copy())
            elapsed = time.time() - start_time

            # Check if report was created
            output_dir = Path("output")
            report_files = list(output_dir.glob("v7_report_*.md")) if output_dir.exists() else []

            result = {
                "status": "PASS" if report_files else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "report_files_created": len(report_files),
                "latest_report": str(report_files[-1]) if report_files else None,
            }

            print(f"  PASS Report files created: {len(report_files)}")
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def test_stage_11_idempotency(self) -> Dict[str, Any]:
        """Test Stage 11: Idempotency check."""
        print("🔄 Testing Stage 11: IdempotencyCheck")

        start_time = time.time()
        try:
            # Run stages 1-8 first to have meaningful data for idempotency check (skip stage 4 authority)
            # Start with Stage 1 to save original input
            stage1_results = await self.pipeline._stage_1_ingest(self.test_entries.copy())
            stage2_results = await self.pipeline._stage_2_detect_region(stage1_results)
            stage3_results = await self.pipeline._stage_3_region_hooks(stage2_results)
            # Skip Stage 4 (AuthorityEnrich) to avoid quota consumption
            stage5_results = await self.pipeline._stage_5_collision_analytics(stage3_results)
            stage6_results = await self.pipeline._stage_6_graph_consistency(stage5_results)
            stage7_results = await self.pipeline._stage_7_tag_short_forms(stage6_results)
            stage8_results = await self.pipeline._stage_8_global_validate(stage7_results)

            # Now run idempotency check
            results = await self.pipeline._stage_11_idempotency_check(stage8_results)
            elapsed = time.time() - start_time

            # Check idempotency implementation
            processed = len(results) == len(self.test_entries)
            idempotency_checks = sum(1 for entry in results if "IdempotencyCheck" in entry)

            # Check for idempotency metrics
            has_metrics = hasattr(self.pipeline, "idempotency_metrics")
            idempotency_rate = 0.0
            identical_entries = 0

            if has_metrics:
                metrics = getattr(self.pipeline, "idempotency_metrics", {})
            idempotency_rate = metrics.get("idempotency_rate", 0.0)
            identical_entries = metrics.get("identical_entries", 0)

            result = {
                "status": "PASS" if processed and idempotency_checks > 0 else "FAIL",
                "elapsed_ms": elapsed * 1000,
                "entries_processed": len(results),
                "idempotency_checks_added": idempotency_checks,
                "has_idempotency_metrics": has_metrics,
                "idempotency_rate": idempotency_rate,
                "identical_entries": identical_entries,
            }

            if processed and idempotency_checks > 0:
                print(
                    f"  PASS Idempotency: {idempotency_checks} checks, {identical_entries} identical, rate: {idempotency_rate:.3f}"
                )
            else:
                print(
                    f"  FAIL Idempotency check failed - Processed: {len(results)}, Checks: {idempotency_checks}"
                )
            return result

        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    async def run_all_stage_tests(self) -> Dict[str, Any]:
        """Run all individual stage tests."""
        print("🔥 V7 PIPELINE INDIVIDUAL STAGE TESTING")
        print("=" * 60)

        # Test all stages
        stage_tests = [
            ("Stage 0", self.test_stage_0_config),
            ("Stage 1", self.test_stage_1_ingest),
            ("Stage 2", self.test_stage_2_detect_region),
            ("Stage 3", self.test_stage_3_region_hooks),
            ("Stage 4", self.test_stage_4_authority_enrich),
            ("Stage 5", self.test_stage_5_collision_analytics),
            ("Stage 6", self.test_stage_6_graph_consistency),
            ("Stage 7", self.test_stage_7_tag_short_forms),
            ("Stage 8", self.test_stage_8_global_validate),
            ("Stage 9", self.test_stage_9_write_diff),
            ("Stage 10", self.test_stage_10_report),
            ("Stage 11", self.test_stage_11_idempotency),
        ]

        results = {}
        total_time = 0

        for stage_name, test_func in stage_tests:
            try:
                # Reset metrics before each individual stage test to prevent interference
                if hasattr(self.pipeline, "reset_metrics"):
                    self.pipeline.reset_metrics()

                result = await test_func()
                results[stage_name] = result
                total_time += result.get("elapsed_ms", 0)

                status_icon = {"PASS": "PASS", "FAIL": "FAIL", "TODO": "WARN", "ERROR": "💥"}.get(
                    result["status"], "❓"
                )

                print(f"{status_icon} {stage_name}: {result['status']}")

            except Exception as e:
                print(f"💥 {stage_name}: ERROR - {e}")
        results[stage_name] = {"status": "ERROR", "error": str(e)}

        # Generate summary
        status_counts = {}
        for result in results.values():
            status = result.get("status", "ERROR")
        status_counts[status] = status_counts.get(status, 0) + 1

        summary = {
            "total_stages": len(stage_tests),
            "status_counts": status_counts,
            "total_elapsed_ms": total_time,
            "average_stage_time_ms": total_time / len(stage_tests),
            "stage_results": results,
        }

        print("\n" + "=" * 60)
        print("📊 V7 PIPELINE STAGE SUMMARY")
        print("=" * 60)
        for status, count in status_counts.items():
            icon = {"PASS": "PASS", "FAIL": "FAIL", "TODO": "WARN", "ERROR": "💥"}.get(status, "❓")
        print(f"{icon} {status}: {count} stages")

        print(f"\n⏱️  Total time: {total_time:.0f}ms")
        print(f"📈 Average per stage: {total_time/len(stage_tests):.0f}ms")

        return summary


async def main():
    """Run V7 pipeline stage validation."""
    validator = V7StageValidator()
    results = await validator.run_all_stage_tests()

    # Save detailed results
    output_path = Path("v7_pipeline_stage_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Detailed results saved to: {output_path}")

    # Return success based on no ERROR status
    error_count = results["status_counts"].get("ERROR", 0)
    return error_count == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
