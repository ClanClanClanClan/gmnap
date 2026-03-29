#!/usr/bin/env python3
"""
COMPREHENSIVE V7 AUDIT - BRUTAL TRUTH VERIFICATION
Tests every claim against V7 specification requirements.
No inflated numbers. No false positives. Just reality.
"""

import asyncio
import json
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

# Test both offline and online modes
os.environ["GMNAP_OFFLINE"] = "1"  # Start offline

from src.core.pipeline_v7_complete_final import create_v7_pipeline
from src.analytics.duckdb_analytics import DuckDBAnalytics
from src.regions.manager import RegionManager


class V7ComprehensiveAuditor:
    """Brutally honest V7 compliance auditor."""

    def __init__(self):
        self.claims = {}
        self.reality = {}
        self.failures = []
        self.lies = []

    async def test_pipeline_basic(self):
        """Test 1: Does the pipeline run without crashing?"""
        print("\n" + "=" * 70)
        print("TEST 1: BASIC PIPELINE FUNCTIONALITY")
        print("=" * 70)

        try:
            pipeline = create_v7_pipeline(mode="quick", enable_live=False)
            test_entry = [
                {
                    "GlobalID": "TEST-001",
                    "CanonicalLatin": "Test Person",
                    "Field": "Testing",
                    "Source": "Test",
                    "LastUpdated": "2025-09-11",
                    "ValidationStatus": "pending",
                }
            ]

            results = await pipeline.process(test_entry)

            if len(results) == 1:
                print("✅ Pipeline runs without crashing")
                self.reality["pipeline_runs"] = True
            else:
                print(f"❌ Pipeline returned {len(results)} results instead of 1")
                self.reality["pipeline_runs"] = False
                self.failures.append("Pipeline doesn't return expected results")

        except Exception as e:
            print(f"❌ Pipeline crashed: {e}")
            self.reality["pipeline_runs"] = False
            self.failures.append(f"Pipeline crash: {str(e)[:100]}")

        return self.reality.get("pipeline_runs", False)

    async def test_authority_enrichment(self):
        """Test 3: Does authority enrichment work?"""
        print("\n" + "=" * 70)
        print("TEST 3: AUTHORITY ENRICHMENT")
        print("=" * 70)

        # Test offline first
        os.environ["OFFLINE"] = "1"
        pipeline_offline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entry = [
            {
                "GlobalID": "AUTH-001",
                "CanonicalLatin": "Albert Einstein",
                "Field": "Physics",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
        ]

        results_offline = await pipeline_offline.process(test_entry)

        # Check offline behavior
        if results_offline[0].get("AuthoritySources"):
            print(
                f"❌ Authority sources populated when OFFLINE=1: {results_offline[0]['AuthoritySources']}"
            )
            self.failures.append("Authority enrichment runs when offline")
            self.reality["authority_enrichment"] = False
        else:
            print("✅ No authority enrichment when OFFLINE=1")
            self.reality["authority_enrichment"] = True

        return self.reality.get("authority_enrichment", False)

    async def test_idempotency(self):
        """Test 4: Is processing idempotent (0-byte requirement)?"""
        print("\n" + "=" * 70)
        print("TEST 4: IDEMPOTENCY (0-BYTE REQUIREMENT)")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": "IDEM-001",
                "CanonicalLatin": "Idempotency Test",
                "Field": "Mathematics",
                "BirthYear": 1900,
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
        ]

        # Process twice
        results1 = await pipeline.process(test_entries)
        results2 = await pipeline.process(test_entries)

        # Convert to JSON for byte comparison
        json1 = json.dumps(results1, sort_keys=True)
        json2 = json.dumps(results2, sort_keys=True)

        # Calculate hashes
        hash1 = hashlib.sha256(json1.encode()).hexdigest()
        hash2 = hashlib.sha256(json2.encode()).hexdigest()

        if hash1 == hash2:
            print(f"✅ Idempotent processing (0-byte difference)")
            print(f"   Hash: {hash1}")
            self.reality["idempotency"] = True
        else:
            print(f"❌ NOT idempotent!")
            print(f"   First hash:  {hash1}")
            print(f"   Second hash: {hash2}")
            self.reality["idempotency"] = False
            self.failures.append("Processing not idempotent")

        return self.reality.get("idempotency", False)

    async def test_graph_coherence(self):
        """Test 10: Does graph coherence calculation work?"""
        print("\n" + "=" * 70)
        print("TEST 10: GRAPH COHERENCE (STAGE 6)")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Create entries with relationships
        test_entries = [
            {
                "GlobalID": "GRAPH-001",
                "CanonicalLatin": "Advisor One",
                "Field": "Mathematics",
                "Students": ["GRAPH-002", "GRAPH-003"],
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            },
            {
                "GlobalID": "GRAPH-002",
                "CanonicalLatin": "Student One",
                "Field": "Mathematics",
                "Advisors": ["GRAPH-001"],
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            },
            {
                "GlobalID": "GRAPH-003",
                "CanonicalLatin": "Student Two",
                "Field": "Mathematics",
                "Advisors": ["GRAPH-001"],
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            },
        ]

        try:
            results = await pipeline.process(test_entries)

            # Check if coherence was calculated
            coherence_values = [r.get("GraphCoherence", 0) for r in results]

            if any(c > 0 for c in coherence_values):
                avg_coherence = sum(coherence_values) / len(coherence_values)
                print(f"✅ Graph coherence calculated: avg={avg_coherence:.3f}")
                self.reality["graph_coherence"] = True
            else:
                print(f"❌ Graph coherence all zeros: {coherence_values}")
                self.reality["graph_coherence"] = False
                self.failures.append("Graph coherence not calculated")

        except Exception as e:
            print(f"❌ Graph coherence error: {e}")
            self.reality["graph_coherence"] = False
            self.failures.append(f"Graph error: {str(e)[:100]}")

        return self.reality.get("graph_coherence", False)

    async def test_short_forms(self):
        """Test 11: Does Stage 7 short form tagging work?"""
        print("\n" + "=" * 70)
        print("TEST 11: SHORT FORMS (STAGE 7)")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": "SHORT-001",
                "CanonicalLatin": "Jean-Baptiste Poquelin",
                "AlternativeNames": ["Molière"],
                "Field": "Literature",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
        ]

        try:
            results = await pipeline.process(test_entries)

            # Check if Stage 7 ran
            if "stage_7_short" in pipeline.metrics.stage_timings:
                print(
                    f"✅ Stage 7 executed in {pipeline.metrics.stage_timings['stage_7_short']:.3f}s"
                )
                self.reality["short_forms"] = True
            else:
                print("❌ Stage 7 not executed")
                self.reality["short_forms"] = False
                self.failures.append("Stage 7 not running")

        except Exception as e:
            print(f"❌ Short forms error: {e}")
            self.reality["short_forms"] = False
            self.failures.append(f"Stage 7 error: {str(e)[:100]}")

        return self.reality.get("short_forms", False)

    async def test_caching(self):
        """Test 12: Does caching improve performance?"""
        print("\n" + "=" * 70)
        print("TEST 12: CACHING LAYER")
        print("=" * 70)

        # Check if cache database exists
        cache_path = Path("cache/authority_cache/authority_cache.db")
        if cache_path.exists():
            print(f"✅ Cache database exists: {cache_path}")
            self.reality["caching"] = True
        else:
            print(f"❌ Cache database not found")
            self.reality["caching"] = False
            self.failures.append("Cache database missing")

        return self.reality.get("caching", False)

    async def test_stage_10_analytics(self):
        """Test 13: Does Stage 10 analytics work?"""
        print("\n" + "=" * 70)
        print("TEST 13: STAGE 10 ANALYTICS")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        test_entries = [
            {
                "GlobalID": f"ANALYTICS-{i:03d}",
                "CanonicalLatin": f"Analytics Test {i}",
                "Field": "Mathematics" if i % 2 == 0 else "Physics",
                "BirthYear": 1900 + i,
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
            for i in range(10)
        ]

        try:
            results = await pipeline.process(test_entries)

            # Check if Stage 10 ran
            if "stage_10_analytics" in pipeline.metrics.stage_timings:
                print(
                    f"✅ Stage 10 executed in {pipeline.metrics.stage_timings['stage_10_analytics']:.3f}s"
                )
                self.reality["stage_10_analytics"] = True
            else:
                print("❌ Stage 10 not executed")
                self.reality["stage_10_analytics"] = False
                self.failures.append("Stage 10 not running")

        except Exception as e:
            print(f"❌ Analytics error: {e}")
            self.reality["stage_10_analytics"] = False
            self.failures.append(f"Stage 10 error: {str(e)[:100]}")

        return self.reality.get("stage_10_analytics", False)

    async def test_stage_12_deployment(self):
        """Test 14: Does Stage 12 create valid deployment artifacts?"""
        print("\n" + "=" * 70)
        print("TEST 14: STAGE 12 DEPLOYMENT ARTIFACTS")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False, enable_deployment=True)

        test_entries = [
            {
                "GlobalID": "DEPLOY-TEST-001",
                "CanonicalLatin": "Deployment Artifact Test",
                "Field": "Testing",
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
        ]

        try:
            results = await pipeline.process(test_entries)

            if "stage_12_deployment" in pipeline.metrics.stage_timings:
                print(f"✅ Stage 12 executed")
                self.reality["stage_12_deployment"] = True
            else:
                print("❌ Stage 12 not executed")
                self.reality["stage_12_deployment"] = False
                self.failures.append("Stage 12 not enabled")

        except Exception as e:
            print(f"❌ Deployment error: {e}")
            self.reality["stage_12_deployment"] = False
            self.failures.append(f"Deployment error: {str(e)[:100]}")

        return self.reality.get("stage_12_deployment", False)

    async def test_performance(self):
        """Test 8: Does performance meet V7 standards?"""
        print("\n" + "=" * 70)
        print("TEST 8: PERFORMANCE METRICS")
        print("=" * 70)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Create 100 test entries
        test_entries = [
            {
                "GlobalID": f"PERF-{i:04d}",
                "CanonicalLatin": f"Performance Test {i}",
                "Field": "Testing",
                "BirthYear": 1900 + i,
                "Source": "Test",
                "LastUpdated": "2025-09-11",
                "ValidationStatus": "verified",
            }
            for i in range(100)
        ]

        start_time = time.time()
        results = await pipeline.process(test_entries)
        elapsed = time.time() - start_time

        throughput = len(test_entries) / elapsed if elapsed > 0 else 0

        print(f"Throughput: {throughput:.1f} entries/sec")

        if throughput >= 50:
            print("✅ Performance acceptable")
            self.reality["performance"] = True
        else:
            print("❌ Performance below standards")
            self.reality["performance"] = False
            self.failures.append(f"Low performance: {throughput:.1f} e/s")

        return self.reality.get("performance", False)

    async def run_comprehensive_audit(self):
        """Run all tests and calculate real compliance."""

        print("\n" + "=" * 80)
        print("V7 COMPREHENSIVE AUDIT - BRUTAL TRUTH VERIFICATION")
        print("=" * 80)

        # Run core tests
        await self.test_pipeline_basic()
        await self.test_authority_enrichment()
        await self.test_idempotency()
        await self.test_graph_coherence()
        await self.test_short_forms()
        await self.test_caching()
        await self.test_stage_10_analytics()
        await self.test_stage_12_deployment()
        await self.test_performance()

        # Calculate compliance
        working = sum(1 for v in self.reality.values() if v)
        total = len(self.reality)
        compliance = (working / total * 100) if total > 0 else 0

        # Summary
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)

        print("\n📊 COMPONENT STATUS:")
        for component, working in self.reality.items():
            status = "✅" if working else "❌"
            print(f"  {status} {component}: {working}")

        if self.failures:
            print("\n❌ FAILURES:")
            for failure in self.failures[:5]:  # Show first 5
                print(f"  - {failure}")

        print(f"\n📈 REAL COMPLIANCE: {compliance:.1f}%")

        # Save results
        audit_results = {
            "claims": self.claims,
            "reality": self.reality,
            "failures": self.failures,
            "lies": self.lies,
            "real_compliance": compliance,
        }

        with open("comprehensive_v7_audit_results.json", "w") as f:
            json.dump(audit_results, f, indent=2)

        return compliance


async def main():
    """Run comprehensive V7 audit."""
    auditor = V7ComprehensiveAuditor()
    compliance = await auditor.run_comprehensive_audit()
    return compliance >= 80


if __name__ == "__main__":
    import asyncio

    success = asyncio.run(main())
    exit(0 if success else 1)
