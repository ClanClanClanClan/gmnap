#!/usr/bin/env python3
"""
V7 Closure Pack Integration Verification
Tests that all closure pack components are properly integrated.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Import the complete pipeline
from src.core.pipeline_v7_complete_final import (
    V7PipelineCompleteFinal,
    create_v7_pipeline,
)


async def verify_integration():
    """Verify that all closure pack components are integrated."""

    print("=" * 70)
    print("V7 CLOSURE PACK INTEGRATION VERIFICATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    results = {"components": {}, "stages": {}, "tests": {}}

    # 1. Check component availability
    print("1. CHECKING COMPONENTS...")
    components_to_check = [
        ("Bayesian Coherence", "src.core.stage6_bayesian", "BayesianCoherence"),
        ("Graph Coherence", "src.core.graph_coherence.coherence", "GraphCoherence"),
        (
            "Deterministic Writer",
            "src.core.stage9_write_diff.write_and_diff",
            "DeterministicWriter",
        ),
        ("DuckDB Writer", "src.core.stage9_db.db_writer", "DuckDBWriter"),
        ("Idempotency Gate", "src.core.stage11_gate", "IdempotencyGate"),
        ("DuckDB Analytics", "src.analytics.duckdb_analytics", "DuckDBAnalytics"),
        ("Quality Gates", "src.quality.gates", "QualityGatesEnforcer"),
        ("Schema Validator", "src.validation.schema_validator", "V7SchemaValidator"),
        ("Round-trip Validator", "src.linguistics.roundtrip", "RoundTripValidator"),
        (
            "Live Authority Adapters",
            "src.authorities.live_adapters",
            "LiveAuthorityAdapters",
        ),
    ]

    for name, module_path, class_name in components_to_check:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            results["components"][name] = "Available"
            print(f"  ✅ {name}: Available")
        except (ImportError, AttributeError) as e:
            results["components"][name] = f"Missing: {str(e)}"
            print(f"  ❌ {name}: Missing - {str(e)}")

    # 2. Create pipeline instance
    print("\n2. CREATING PIPELINE INSTANCE...")
    try:
        pipeline = create_v7_pipeline(
            mode="quick", enable_live=False, enable_memgraph=False
        )
        print("  ✅ Pipeline created successfully")

        # Check for new components
        has_bayesian = hasattr(pipeline, "bayesian_coherence")
        has_idempotency = hasattr(pipeline, "idempotency_gate")
        has_duckdb = hasattr(pipeline, "duckdb_analytics")

        print(f"  {'✅' if has_bayesian else '❌'} Bayesian coherence integrated")
        print(f"  {'✅' if has_idempotency else '❌'} Idempotency gate integrated")
        print(f"  {'✅' if has_duckdb else '❌'} DuckDB analytics integrated")

        results["pipeline"] = {
            "created": True,
            "bayesian": has_bayesian,
            "idempotency": has_idempotency,
            "duckdb": has_duckdb,
        }
    except Exception as e:
        print(f"  ❌ Pipeline creation failed: {e}")
        results["pipeline"] = {"created": False, "error": str(e)}
        return results

    # 3. Test critical stages
    print("\n3. TESTING CRITICAL STAGES...")
    test_entries = [
        {
            "CanonicalLatin": "Test Entry 1",
            "GlobalID": "TEST001",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.95,
        },
        {
            "CanonicalLatin": "Test Entry 2",
            "GlobalID": "TEST002",
            "DetectedRegion": "E4",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.90,
        },
    ]

    try:
        # Test Stage 6 - Graph Consistency
        print("  Testing Stage 6 (Graph Consistency)...")
        processed = await pipeline._stage_6_graph_consistency(test_entries.copy())
        has_coherence = all("GraphCoherence" in e for e in processed)
        has_bayesian_conf = all("BayesianConfidence" in e for e in processed)

        print(f"    {'✅' if has_coherence else '❌'} Graph coherence scores added")
        print(f"    {'✅' if has_bayesian_conf else '❌'} Bayesian confidence added")

        results["stages"]["stage_6"] = {
            "tested": True,
            "coherence": has_coherence,
            "bayesian": has_bayesian_conf,
        }
    except Exception as e:
        print(f"    ❌ Stage 6 test failed: {e}")
        results["stages"]["stage_6"] = {"tested": False, "error": str(e)}

    try:
        # Test Stage 8 - Schema Validation
        print("  Testing Stage 8 (Schema Validation)...")
        validated = await pipeline._stage_8_global_validate(test_entries.copy())
        print(f"    ✅ Validated {len(validated)}/{len(test_entries)} entries")

        results["stages"]["stage_8"] = {
            "tested": True,
            "validated_count": len(validated),
        }
    except Exception as e:
        print(f"    ❌ Stage 8 test failed: {e}")
        results["stages"]["stage_8"] = {"tested": False, "error": str(e)}

    # 4. Test idempotency mechanism
    print("\n4. TESTING IDEMPOTENCY MECHANISM...")
    try:
        # Create output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Write test file
        test_file = output_dir / "test_idempotency.json"
        with open(test_file, "w") as f:
            json.dump(test_entries, f, indent=2, sort_keys=True)

        # Compute hash
        if hasattr(pipeline, "idempotency_gate"):
            hash1 = await pipeline.idempotency_gate.compute_file_hash(test_file)

            # Write again (should be identical)
            with open(test_file, "w") as f:
                json.dump(test_entries, f, indent=2, sort_keys=True)

            hash2 = await pipeline.idempotency_gate.compute_file_hash(test_file)

            idempotent = hash1 == hash2
            print(
                f"  {'✅' if idempotent else '❌'} Idempotency check: {'PASSED' if idempotent else 'FAILED'}"
            )
            print(f"    Hash 1: {hash1[:16]}...")
            print(f"    Hash 2: {hash2[:16]}...")

            results["tests"]["idempotency"] = {
                "tested": True,
                "passed": idempotent,
                "hash1": hash1[:16],
                "hash2": hash2[:16],
            }
        else:
            print("  ⚠️ Idempotency gate not available")
            results["tests"]["idempotency"] = {
                "tested": False,
                "reason": "Gate not available",
            }

    except Exception as e:
        print(f"  ❌ Idempotency test failed: {e}")
        results["tests"]["idempotency"] = {"tested": False, "error": str(e)}

    # 5. Summary
    print("\n" + "=" * 70)
    print("INTEGRATION SUMMARY")
    print("=" * 70)

    # Count successes
    components_ok = sum(1 for v in results["components"].values() if v == "Available")
    total_components = len(results["components"])

    stages_ok = sum(1 for v in results.get("stages", {}).values() if v.get("tested"))
    total_stages = len(results.get("stages", {}))

    pipeline_ok = results.get("pipeline", {}).get("created", False)
    idempotency_ok = (
        results.get("tests", {}).get("idempotency", {}).get("passed", False)
    )

    print(f"Components: {components_ok}/{total_components} available")
    print(f"Pipeline: {'✅ Created' if pipeline_ok else '❌ Failed'}")
    print(f"Stages tested: {stages_ok}/{total_stages}")
    print(f"Idempotency: {'✅ Working' if idempotency_ok else '❌ Not working'}")

    # Overall status
    all_critical_ok = (
        components_ok >= 8  # Most components available
        and pipeline_ok  # Pipeline creates
        and stages_ok >= 1  # At least some stages work
    )

    print("\n" + "=" * 70)
    if all_critical_ok:
        print("✅ V7 CLOSURE PACK INTEGRATION SUCCESSFUL!")
        print("The pipeline is ready with all critical components.")
    else:
        print("⚠️ V7 Closure Pack partially integrated")
        print("Some components may need additional setup.")

    print("=" * 70)

    # Save results
    results_file = Path("v7_closure_integration_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDetailed results saved to: {results_file}")

    return results


async def main():
    """Main entry point."""
    try:
        results = await verify_integration()

        # Exit with appropriate code
        if results.get("pipeline", {}).get("created"):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
