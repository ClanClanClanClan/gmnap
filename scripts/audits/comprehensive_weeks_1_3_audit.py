#!/usr/bin/env python3
"""
BRUTAL AUDIT: Weeks 1-3 V7 Implementation
Tests every claim made during weeks 1-3 to verify real vs false progress.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Disable offline mode for real testing
os.environ["OFFLINE"] = "0"

from src.core.pipeline_v7_complete_final import create_v7_pipeline


class BrutalAuditor:
    """Brutally honest auditor for V7 compliance."""

    def __init__(self):
        self.results = {"claims": {}, "reality": {}, "failures": [], "lies": []}

    async def audit_basic_pipeline(self):
        """Test if pipeline even runs."""
        print("\n" + "=" * 60)
        print("AUDIT 1: Basic Pipeline Functionality")
        print("=" * 60)

        try:
            pipeline = create_v7_pipeline(mode="quick", enable_live=False)
            test_entry = [
                {
                    "GlobalID": "TEST-001",
                    "CanonicalLatin": "Test Person",
                    "Field": "Physics",
                    "Source": "Test",
                    "LastUpdated": "2025-09-10",
                    "ValidationStatus": "pending",
                }
            ]

            result = await pipeline.process(test_entry)

            if result and len(result) == 1:
                print("✅ Pipeline runs without crashing")
                self.results["reality"]["pipeline_runs"] = True
                return True
            else:
                print("❌ Pipeline returns wrong number of results")
                self.results["failures"].append("Pipeline processing error")
                return False

        except Exception as e:
            print(f"❌ Pipeline crashes: {e}")
            self.results["failures"].append(f"Pipeline crash: {str(e)[:100]}")
            self.results["reality"]["pipeline_runs"] = False
            return False

    async def audit_authority_enrichment(self):
        """Test if authority enrichment actually works."""
        print("\n" + "=" * 60)
        print("AUDIT 2: Authority Enrichment")
        print("=" * 60)

        # Test with OFFLINE=1 (should not enrich)
        os.environ["OFFLINE"] = "1"
        pipeline = create_v7_pipeline(mode="quick", enable_live=True)

        test_entry = [
            {
                "GlobalID": "AUTH-001",
                "CanonicalLatin": "Albert Einstein",
                "Field": "Physics",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
        ]

        result = await pipeline.process(test_entry)
        offline_has_authority = bool(result[0].get("AuthoritySources"))

        print(f"Offline mode - Authority sources: {result[0].get('AuthoritySources', [])}")

        # Test with OFFLINE=0 (should enrich)
        os.environ["OFFLINE"] = "0"
        pipeline = create_v7_pipeline(mode="quick", enable_live=True)

        result = await pipeline.process(test_entry)
        online_has_authority = bool(result[0].get("AuthoritySources"))
        has_crossref_data = "CrossrefData" in result[0]

        print(f"Online mode - Authority sources: {result[0].get('AuthoritySources', [])}")
        print(f"CrossrefData present: {has_crossref_data}")

        if not offline_has_authority and online_has_authority and has_crossref_data:
            print("✅ Authority enrichment works correctly")
            self.results["reality"]["authority_enrichment"] = True
            return True
        else:
            print("❌ Authority enrichment not working properly")
            self.results["failures"].append("Authority enrichment inconsistent")
            self.results["reality"]["authority_enrichment"] = False
            return False

    async def audit_graph_coherence(self):
        """Test if graph coherence calculation works."""
        print("\n" + "=" * 60)
        print("AUDIT 3: Graph Coherence")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Test with advisor relationships
        test_entries = [
            {
                "GlobalID": "PROF-001",
                "CanonicalLatin": "Advisor Name",
                "Field": "Mathematics",
                "Students": ["PROF-002"],
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            },
            {
                "GlobalID": "PROF-002",
                "CanonicalLatin": "Student Name",
                "Field": "Mathematics",
                "Advisors": ["PROF-001"],
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            },
        ]

        results = await pipeline.process(test_entries)

        has_coherence = all("GraphCoherence" in r for r in results)
        coherence_values = [r.get("GraphCoherence", 0) for r in results]
        avg_coherence = sum(coherence_values) / len(coherence_values) if coherence_values else 0

        print(f"Graph coherence present: {has_coherence}")
        print(f"Average coherence: {avg_coherence:.3f}")
        print(f"Coherence values: {coherence_values}")

        if has_coherence and avg_coherence > 0:
            print("✅ Graph coherence calculation works")
            self.results["reality"]["graph_coherence"] = True
            return True
        else:
            print("❌ Graph coherence broken")
            self.results["failures"].append(f"Graph coherence avg: {avg_coherence}")
            self.results["reality"]["graph_coherence"] = False
            return False

    async def audit_short_forms(self):
        """Test if Stage 7 short forms generation works."""
        print("\n" + "=" * 60)
        print("AUDIT 4: Short Forms Generation")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entry = [
            {
                "GlobalID": "SHORT-001",
                "CanonicalLatin": "Johann Sebastian Bach",
                "Field": "Music",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
        ]

        result = await pipeline.process(test_entry)

        has_short_forms = "ShortFormClusters" in result[0]
        short_forms = result[0].get("ShortFormClusters", [])

        print(f"ShortFormClusters present: {has_short_forms}")
        print(f"Short forms generated: {short_forms}")

        expected_forms = ["J. S. Bach", "JSB", "J Bach", "JS Bach"]
        has_expected = any(form in short_forms for form in expected_forms)

        if has_short_forms and len(short_forms) > 0:
            print("✅ Short forms generation works")
            self.results["reality"]["short_forms"] = True
            return True
        else:
            print("❌ Short forms generation broken")
            self.results["failures"].append("No short forms generated")
            self.results["reality"]["short_forms"] = False
            return False

    async def audit_caching(self):
        """Test if authority caching actually works."""
        print("\n" + "=" * 60)
        print("AUDIT 5: Authority Caching")
        print("=" * 60)

        # Clear cache first
        cache_db = Path("cache/authority/authority_cache.db")
        if cache_db.exists():
            cache_db.unlink()

        os.environ["OFFLINE"] = "0"
        pipeline = create_v7_pipeline(mode="quick", enable_live=True)

        test_entry = [
            {
                "GlobalID": "CACHE-001",
                "CanonicalLatin": "Marie Curie",
                "Field": "Chemistry",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
        ]

        # First call (should hit API)
        start1 = time.time()
        result1 = await pipeline.process(test_entry)
        time1 = time.time() - start1

        # Second call (should hit cache)
        start2 = time.time()
        result2 = await pipeline.process(test_entry)
        time2 = time.time() - start2

        print(f"First call time: {time1:.3f}s")
        print(f"Second call time: {time2:.3f}s")
        print(f"Speed improvement: {time1/time2:.1f}x")

        # Check cache exists
        cache_exists = cache_db.exists()
        print(f"Cache database exists: {cache_exists}")

        if cache_exists and time2 < time1 * 0.5:  # At least 2x faster
            print("✅ Caching works effectively")
            self.results["reality"]["caching"] = True
            return True
        else:
            print("❌ Caching not effective")
            self.results["failures"].append(f"Cache speedup only {time1/time2:.1f}x")
            self.results["reality"]["caching"] = False
            return False

    async def audit_stage_10_analytics(self):
        """Test if Stage 10 analytics actually generates reports."""
        print("\n" + "=" * 60)
        print("AUDIT 6: Stage 10 Analytics")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": f"ANALYT-{i:03d}",
                "CanonicalLatin": f"Test Person {i}",
                "Field": ["Mathematics", "Physics", "Chemistry"][i % 3],
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
            for i in range(10)
        ]

        results = await pipeline.process(test_entries)

        # Check if analytics ran
        has_analytics = "stage_10_analytics" in pipeline.metrics.stage_timings

        # Check for report file
        output_dir = Path("output")
        if output_dir.exists():
            reports = list(output_dir.glob("analytics_report_*.md"))
            has_report = len(reports) > 0

            if has_report:
                latest_report = max(reports, key=lambda p: p.stat().st_mtime)
                print(f"Latest report: {latest_report.name}")

                # Check report content
                with open(latest_report, "r") as f:
                    content = f.read()
                    has_collision_analysis = "Collision Analysis" in content
                    has_field_dist = "Field Distribution" in content
                    has_authority = "Authority Source Coverage" in content
                    has_coherence = "Graph Coherence Metrics" in content

                print(f"Report has collision analysis: {has_collision_analysis}")
                print(f"Report has field distribution: {has_field_dist}")
                print(f"Report has authority coverage: {has_authority}")
                print(f"Report has coherence metrics: {has_coherence}")

                if all([has_collision_analysis, has_field_dist, has_authority, has_coherence]):
                    print("✅ Stage 10 analytics works completely")
                    self.results["reality"]["stage_10_analytics"] = True
                    return True

        print("❌ Stage 10 analytics incomplete")
        self.results["failures"].append("Analytics report missing or incomplete")
        self.results["reality"]["stage_10_analytics"] = False
        return False

    async def audit_stage_12_deployment(self):
        """Test if Stage 12 deployment actually works."""
        print("\n" + "=" * 60)
        print("AUDIT 7: Stage 12 Deployment")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False, enable_deployment=True)

        test_entries = [
            {
                "GlobalID": "DEPLOY-001",
                "CanonicalLatin": "Deployment Test",
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "verified",
            }
        ]

        results = await pipeline.process(test_entries)

        # Check if deployment ran
        has_deployment = "stage_12_deployment" in pipeline.metrics.stage_timings

        # Check deployment artifacts
        manifest_path = Path("deployments/production/manifest.json")
        data_path = Path("deployments/production/data.json")

        manifest_exists = manifest_path.exists()
        data_exists = data_path.exists()

        print(f"Deployment stage ran: {has_deployment}")
        print(f"Manifest exists: {manifest_exists}")
        print(f"Data file exists: {data_exists}")

        if manifest_exists:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
                version = manifest.get("version")
                entry_count = manifest.get("data", {}).get("entry_count", 0)
                validation_passed = manifest.get("validation", {}).get("passed", False)

                print(f"Deployment version: {version}")
                print(f"Entries deployed: {entry_count}")
                print(f"Validation passed: {validation_passed}")

                if version and entry_count > 0 and validation_passed:
                    print("✅ Stage 12 deployment works")
                    self.results["reality"]["stage_12_deployment"] = True
                    return True

        print("❌ Stage 12 deployment broken")
        self.results["failures"].append("Deployment artifacts missing or invalid")
        self.results["reality"]["stage_12_deployment"] = False
        return False

    async def audit_performance(self):
        """Test actual performance metrics."""
        print("\n" + "=" * 60)
        print("AUDIT 8: Performance Metrics")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Test with 100 entries
        test_entries = [
            {
                "GlobalID": f"PERF-{i:04d}",
                "CanonicalLatin": f"Performance Test {i}",
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
            for i in range(100)
        ]

        start_time = time.time()
        results = await pipeline.process(test_entries)
        total_time = time.time() - start_time

        entries_processed = len(results)
        throughput = entries_processed / total_time if total_time > 0 else 0
        projected_1m = (1000000 / throughput / 60) if throughput > 0 else float("inf")

        print(f"Entries processed: {entries_processed}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.1f} entries/sec")
        print(f"Projected 1M time: {projected_1m:.1f} minutes")

        # V7 requires at least 100 entries/sec
        if throughput >= 100:
            print("✅ Performance meets V7 requirements")
            self.results["reality"]["performance"] = True
            return True
        elif throughput >= 10:
            print("⚠️ Performance below V7 target but acceptable")
            self.results["reality"]["performance"] = "partial"
            return False
        else:
            print("❌ Performance far below requirements")
            self.results["failures"].append(f"Only {throughput:.1f} entries/sec")
            self.results["reality"]["performance"] = False
            return False

    async def audit_idempotency(self):
        """Test if idempotency check actually works."""
        print("\n" + "=" * 60)
        print("AUDIT 9: Idempotency Check")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": "IDEM-001",
                "CanonicalLatin": "Idempotency Test",
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-10",
                "ValidationStatus": "pending",
            }
        ]

        # Process twice
        result1 = await pipeline.process(test_entries)
        result2 = await pipeline.process(test_entries)

        # Check if results are identical
        import json

        json1 = json.dumps(result1, sort_keys=True)
        json2 = json.dumps(result2, sort_keys=True)

        identical = json1 == json2

        print(f"Results identical: {identical}")
        print(f"Result 1 size: {len(json1)} bytes")
        print(f"Result 2 size: {len(json2)} bytes")

        if identical:
            print("✅ Idempotency verified")
            self.results["reality"]["idempotency"] = True
            return True
        else:
            print("❌ Idempotency failed")
            self.results["failures"].append("Results not identical")
            self.results["reality"]["idempotency"] = False
            return False

    async def calculate_real_compliance(self):
        """Calculate the REAL V7 compliance percentage."""
        print("\n" + "=" * 60)
        print("REAL V7 COMPLIANCE CALCULATION")
        print("=" * 60)

        # V7 Requirements and weights
        requirements = {
            "pipeline_runs": 5,  # Basic functionality
            "authority_enrichment": 10,  # Stage 4
            "graph_coherence": 10,  # Stage 6
            "short_forms": 5,  # Stage 7
            "caching": 5,  # Performance optimization
            "stage_10_analytics": 10,  # Stage 10
            "stage_12_deployment": 10,  # Stage 12
            "performance": 15,  # Performance requirements
            "idempotency": 10,  # Stage 11
            "quality_gates": 5,  # Stage 8
            "regional_processing": 10,  # Stages 2-3
            "collision_detection": 5,  # Stage 5
        }

        # Calculate scores
        scores = {}
        for req, weight in requirements.items():
            if req in self.results["reality"]:
                if self.results["reality"][req] == True:
                    scores[req] = weight
                elif self.results["reality"][req] == "partial":
                    scores[req] = weight * 0.5
                else:
                    scores[req] = 0
            else:
                scores[req] = 0  # Not tested = not working

        total_possible = sum(requirements.values())
        total_achieved = sum(scores.values())
        real_compliance = (total_achieved / total_possible) * 100

        print("\nComponent Scores:")
        for req, score in scores.items():
            max_score = requirements[req]
            status = "✅" if score == max_score else "⚠️" if score > 0 else "❌"
            print(f"  {status} {req}: {score}/{max_score}")

        print(f"\nTotal Score: {total_achieved}/{total_possible}")
        print(f"REAL V7 COMPLIANCE: {real_compliance:.1f}%")

        self.results["real_compliance"] = real_compliance

        return real_compliance

    async def run_complete_audit(self):
        """Run all audits and generate report."""
        print("\n" + "=" * 70)
        print("BRUTAL V7 COMPLIANCE AUDIT - WEEKS 1-3")
        print("=" * 70)

        # Run all audits
        await self.audit_basic_pipeline()
        await self.audit_authority_enrichment()
        await self.audit_graph_coherence()
        await self.audit_short_forms()
        await self.audit_caching()
        await self.audit_stage_10_analytics()
        await self.audit_stage_12_deployment()
        await self.audit_performance()
        await self.audit_idempotency()

        # Calculate real compliance
        real_compliance = await self.calculate_real_compliance()

        # Generate report
        print("\n" + "=" * 70)
        print("AUDIT SUMMARY")
        print("=" * 70)

        print(f"\n🔍 Tests Run: {len(self.results['reality'])}")
        print(f"❌ Failures: {len(self.results['failures'])}")

        if self.results["failures"]:
            print("\nFailure Details:")
            for failure in self.results["failures"]:
                print(f"  - {failure}")

        print(f"\n📊 REAL V7 COMPLIANCE: {real_compliance:.1f}%")

        if real_compliance >= 40:
            print("✅ Week 3 target (40%) achieved!")
        else:
            print(f"❌ Week 3 target missed by {40 - real_compliance:.1f}%")

        return self.results


async def main():
    """Run the brutal audit."""
    auditor = BrutalAuditor()
    results = await auditor.run_complete_audit()

    # Save results
    with open("weeks_1_3_audit_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nAudit results saved to weeks_1_3_audit_results.json")

    return results["real_compliance"]


if __name__ == "__main__":
    real_compliance = asyncio.run(main())
    exit(0 if real_compliance >= 40 else 1)
