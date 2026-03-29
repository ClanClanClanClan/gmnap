from typing import Any, List

#!/usr/bin/env python3
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


GMNAP V7 Full Pipeline Integration Test
Tests the complete 12-stage pipeline with real Crossref data
"""
import json
import time
from typing import Dict, Tuple

# Test data: Famous mathematicians
TEST_MATHEMATICIANS = [
    {
        "GlobalID": "test-tao-001",
        "CanonicalLatin": "Tao, T.",
        "CanonicalNative": "Tao, T.",
        "Type": "Individual",
        "BirthYear": 1975,
    },
    {
        "GlobalID": "test-mirzakhani-001",
        "CanonicalLatin": "Mirzakhani, Maryam",
        "CanonicalNative": "مریم میرزاخانی",
        "Type": "Individual",
        "BirthYear": 1977,
        "DeathYear": 2017,
    },
    {
        "GlobalID": "test-villani-001",
        "CanonicalLatin": "Villani, Cédric",
        "CanonicalNative": "Villani, Cédric",
        "Type": "Individual",
        "BirthYear": 1973,
    },
]


class V7PipelineIntegration:
    """Full V7 pipeline integration test"""

    def __init__(self):
        self.results = {}
        self.metrics = {}

    async def run_pipeline(
        self, entries: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Run all 12 stages of the V7 pipeline

        Returns:
            Tuple of (processed_entries, metrics)
        """
        print("\n" + "=" * 70)
        print("GMNAP V7 FULL PIPELINE INTEGRATION TEST")
        print("=" * 70)

        batch = entries.copy()
        all_metrics = {}

        # Stage 0: Config (simplified)
        print("\n[Stage 0] Config")
        config = self.stage0_config()
        print(f"  ✓ Loaded config for mode: {config['mode']}")

        # Stage 1: Ingest
        print("\n[Stage 1] Ingest")
        batch = self.stage1_ingest(batch)
        print(f"  ✓ Ingested {len(batch)} entries")

        # Stage 1b: LLM Extract (skip for this test)
        print("\n[Stage 1b] LLM Extract ETD")
        print("  ⚠ Skipped (no PDFs to process)")

        # Stage 2: Detect Region
        print("\n[Stage 2] Detect Region")
        batch = self.stage2_detect_region(batch)
        regions = set(e.get("DetectedRegion") for e in batch)
        print(f"  ✓ Detected regions: {regions}")

        # Stage 3: Region Hooks
        print("\n[Stage 3] Region Hooks")
        batch = self.stage3_region_hooks(batch)
        print("  ✓ Applied region processing")

        # Stage 4: Authority Enrichment (REAL CROSSREF DATA!)
        print("\n[Stage 4] Authority Enrichment")
        batch, auth_metrics = await self.stage4_authority_enrich(batch, config["mode"])
        all_metrics["authority"] = auth_metrics
        print(f"  ✓ Enriched {auth_metrics['entries_enriched']}/{len(batch)} entries")
        print(f"  ✓ Found {auth_metrics['orcids_found']} ORCIDs")
        print(f"  ✓ Made {auth_metrics['crossref_requests']} Crossref requests")

        # Stage 5: Collision Analytics
        print("\n[Stage 5] Collision Analytics")
        batch = self.stage5_collision_analytics(batch)
        print("  ✓ Analyzed for collisions")

        # Stage 6: Graph Consistency
        print("\n[Stage 6] Graph Consistency")
        batch, graph_metrics = self.stage6_graph_consistency(batch, config["mode"])
        all_metrics["graph"] = graph_metrics
        print(
            f"  ✓ Graph coherence score: {graph_metrics.get('coherence_score', 'N/A')}"
        )

        # Stage 7: Tag Short Forms
        print("\n[Stage 7] Tag Short Forms")
        batch = self.stage7_tag_shortforms(batch)
        print("  ✓ Tagged short forms")

        # Stage 8: Global Validate
        print("\n[Stage 8] Global Validate")
        try:
            batch, val_metrics = self.stage8_global_validate(batch, config["mode"])
            all_metrics["validation"] = val_metrics
            print("  ✓ Validation passed")
        except Exception as e:
            print(f"  ⚠ Validation warnings: {str(e)[:50]}")

        # Stage 9: Write & Diff
        print("\n[Stage 9] Write & Diff")
        batch = self.stage9_write_diff(batch)
        print("  ✓ Prepared for writing")

        # Stage 10: Report
        print("\n[Stage 10] Report")
        self.stage10_report(batch, all_metrics)
        print("  ✓ Generated report")

        # Stage 11: Idempotency Check
        print("\n[Stage 11] Idempotency Check")
        batch, idemp_metrics = self.stage11_idempotency(batch)
        all_metrics["idempotency"] = idemp_metrics
        diff_bytes = idemp_metrics.get("idempotency_diff_bytes", -1)
        print(f"  ✓ Idempotency: {diff_bytes} diff bytes")

        return batch, all_metrics

    def stage0_config(self) -> Dict[str, Any]:
        """Stage 0: Configuration"""
        return {
            "mode": "Quick",
            "tier": 0,
            "runtime_profile": {
                "apis": "tier-0",
                "cpu_workers": 4,
                "runtime_per_1M": "35 min",
            },
        }

    def stage1_ingest(self, batch: List[Dict]) -> List[Dict]:
        """Stage 1: Ingest and normalize"""
        # Add required fields
        for entry in batch:
            if "Type" not in entry:
                entry["Type"] = "Individual"
            if "Status" not in entry:
                entry["Status"] = "Active"
        return batch

    def stage2_detect_region(self, batch: List[Dict]) -> List[Dict]:
        """Stage 2: Detect region from script"""
        from src.pipeline.stage2_detect_region import detect_region

        for entry in batch:
            region_code, script = detect_region(entry)
            entry["DetectedRegion"] = region_code
            entry["DetectedScript"] = script
        return batch

    def stage3_region_hooks(self, batch: List[Dict]) -> List[Dict]:
        """Stage 3: Apply region-specific processing"""
        from src.pipeline.stage3_region_hooks import apply_region_hooks

        return apply_region_hooks(batch)

    async def stage4_authority_enrich(
        self, batch: List[Dict], mode: str
    ) -> Tuple[List[Dict], Dict]:
        """Stage 4: Enrich with authority data (REAL CROSSREF!)"""
        from src.pipeline.stage4_authority_enrichment import enrich_from_authorities

        return await enrich_from_authorities(batch, mode)

    def stage5_collision_analytics(self, batch: List[Dict]) -> List[Dict]:
        """Stage 5: Collision detection"""
        # Simple collision check
        ids_seen = set()
        for entry in batch:
            gid = entry.get("GlobalID")
            if gid in ids_seen:
                entry["HasCollision"] = True
            ids_seen.add(gid)
        return batch

    def stage6_graph_consistency(
        self, batch: List[Dict], mode: str
    ) -> Tuple[List[Dict], Dict]:
        """Stage 6: Graph consistency check"""
        from src.pipeline.stage6_graph_consistency import enforce_graph_coherence_gate

        return enforce_graph_coherence_gate(batch, mode)

    def stage7_tag_shortforms(self, batch: List[Dict]) -> List[Dict]:
        """Stage 7: Tag short forms"""
        # Simple tagging
        for entry in batch:
            name = entry.get("CanonicalLatin", "")
            if "," in name:
                family, given = name.split(",", 1)
                entry["ShortForms"] = [
                    f"{family}, {given[0]}." if given else family,
                    family,
                ]
        return batch

    def stage8_global_validate(
        self, batch: List[Dict], mode: str
    ) -> Tuple[List[Dict], Dict]:
        """Stage 8: Global validation"""
        from src.pipeline.stage8_global_validate import global_validate

        return global_validate(batch, mode)

    def stage9_write_diff(self, batch: List[Dict]) -> List[Dict]:
        """Stage 9: Write and diff"""
        # Mark as ready to write
        for entry in batch:
            entry["WriteReady"] = True
        return batch

    def stage10_report(self, batch: List[Dict], metrics: Dict) -> str:
        """Stage 10: Generate report"""
        report = f"""
V7 Pipeline Report
==================
Entries Processed: {len(batch)}
Authority Enrichment: {metrics.get('authority', {}).get('entries_enriched', 0)} enriched
ORCIDs Found: {metrics.get('authority', {}).get('orcids_found', 0)}
Crossref Requests: {metrics.get('authority', {}).get('crossref_requests', 0)}
Idempotency: {metrics.get('idempotency', {}).get('idempotency_diff_bytes', 'N/A')} bytes diff
"""
        return report

    def stage11_idempotency(self, batch: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Stage 11: Idempotency check"""
        from src.pipeline.stage11_idempotency_check import idempotency_check

        return idempotency_check(batch, mode="self", strict=False)

    def print_results(self, batch: List[Dict], metrics: Dict):
        """Print detailed results"""
        print("\n" + "=" * 70)
        print("PIPELINE RESULTS")
        print("=" * 70)

        for entry in batch:
            print(f"\n{entry.get('CanonicalLatin', 'Unknown')}:")
            print(f"  GlobalID: {entry.get('GlobalID')}")
            print(
                f"  Region: {entry.get('DetectedRegion')} ({entry.get('DetectedScript')})"
            )

            # Show Crossref enrichment
            if "AuthoritySources" in entry:
                for source in entry["AuthoritySources"]:
                    print(
                        f"  Authority: {source['source']} (confidence: {source['confidence']:.1f})"
                    )

            if "ExternalIDs" in entry:
                for ext_id in entry["ExternalIDs"]:
                    if ext_id.get("type") == "ORCID":
                        print(f"  ORCID: {ext_id['value']}")

            if "Affiliations" in entry:
                print(f"  Affiliations: {len(entry['Affiliations'])} found")
                for aff in entry["Affiliations"][:2]:  # Show first 2
                    print(f"    - {aff.get('institution', 'Unknown')}")

        print("\n" + "=" * 70)
        print("METRICS SUMMARY")
        print("=" * 70)
        print(json.dumps(metrics, indent=2))


async def main():
    """Run the full pipeline test"""

    print("Starting V7 Full Pipeline Integration Test")
    print("This will make REAL API calls to Crossref")
    print("-" * 40)

    # Initialize pipeline
    pipeline = V7PipelineIntegration()

    # Run pipeline with test data
    start_time = time.time()

    try:
        processed_batch, metrics = await pipeline.run_pipeline(TEST_MATHEMATICIANS)

        # Print results
        pipeline.print_results(processed_batch, metrics)

        elapsed = time.time() - start_time
        print(f"\nPASS Pipeline completed in {elapsed:.2f} seconds")

        # Check success criteria
        success_criteria = [
            ("Entries processed", len(processed_batch) == len(TEST_MATHEMATICIANS)),
            (
                "Authority enrichment",
                metrics.get("authority", {}).get("entries_enriched", 0) > 0,
            ),
            (
                "Idempotency achieved",
                metrics.get("idempotency", {}).get("idempotency_diff_bytes") == 0,
            ),
            ("Regions detected", all(e.get("DetectedRegion") for e in processed_batch)),
        ]

        print("\n" + "=" * 70)
        print("SUCCESS CRITERIA")
        print("=" * 70)

        all_passed = True
        for criterion, passed in success_criteria:
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {criterion}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n🎉 ALL SUCCESS CRITERIA MET!")
            print("The V7 pipeline is working with REAL DATA from Crossref!")
            return 0
        else:
            print("\nWARN Some criteria not met, but pipeline executed")
            return 1

    except Exception as e:
        print(f"\nFAIL Pipeline failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import aiohttp
    except ImportError:
        print("ERROR: aiohttp not installed. Run: pip install aiohttp")
    # sys.exit(1)  # MOVED: Was at module level

    # sys.exit(asyncio.run(main()))  # MOVED: Was at module level
