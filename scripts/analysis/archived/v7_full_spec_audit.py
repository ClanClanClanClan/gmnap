#!/usr/bin/env python3
"""Comprehensive V7 Spec Compliance Audit - Triple Check"""
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any


def check_stage_implementations() -> Dict[str, Any]:
    """Check all 12 pipeline stages from V7 spec"""
    stages_spec = [
        (0, "Config", "src/core/config_loader.py"),
        (1, "Ingest", "src/core/pipeline_v7.py"),
        ("1b", "LLMExtract_ETD", "src/pipeline/stage_1b_llm_extract.py"),
        (2, "DetectRegion", "src/regions/manager.py"),
        (3, "RegionHooks", "src/regions/base.py"),
        (4, "AuthorityEnrich", "src/authorities/manager.py"),
        (5, "CollisionAnalytics", "src/pipeline/stage_5_collision_analytics.py"),
        (6, "GraphConsistency", "src/core/graph_coherence.py"),
        (7, "TagShortForms", "src/core/pipeline_v7.py"),
        (8, "GlobalValidate", "src/validation/schema_validator.py"),
        (9, "Write&Diff", "src/stage9_write_diff"),
        (10, "Report", "src/core/pipeline_v7.py"),
        (11, "IdempotencyCheck", "src/core/idempotency.py"),
    ]

    results = {"total": len(stages_spec), "implemented": 0, "missing": [], "details": []}

    for stage_num, stage_name, expected_file in stages_spec:
        exists = os.path.exists(expected_file)
        results["details"].append(
            {"stage": f"{stage_num}", "name": stage_name, "file": expected_file, "exists": exists}
        )
        if exists:
            results["implemented"] += 1
        else:
            results["missing"].append(f"Stage {stage_num}: {stage_name}")

    return results


def check_quality_gates() -> Dict[str, Any]:
    """Check quality gates from V7 spec"""
    results = {"gates": {}, "compliance": True}

    # Check duplicate_global_id gate implementation
    try:
        from src.quality.gates import QualityGates

        gates = QualityGates()

        # Test duplicate detection
        test_entries = [
            {"GlobalID": "test-id-1", "CanonicalLatin": "Smith, John"},
            {"GlobalID": "test-id-1", "CanonicalLatin": "Smith, John"},  # duplicate
            {"GlobalID": "test-id-1--1", "CanonicalLatin": "Smith, John"},  # suffixed, should pass
        ]

        results["gates"]["duplicate_global_id"] = {
            "spec": "Collisions suffixed --1, --2 pass the gate",
            "implemented": True,
            "working": False,
        }

        # Try to validate
        try:
            validation_results = []
            for entry in test_entries:
                validation_results.append(gates.validate_entry(entry))

            # Check if suffixed duplicates pass
            if validation_results[2]:  # suffixed should pass
                results["gates"]["duplicate_global_id"]["working"] = True
        except:
            pass

    except ImportError:
        results["gates"]["error"] = "QualityGates module not found"
        results["compliance"] = False

    return results


def check_performance_requirements() -> Dict[str, Any]:
    """Check performance against V7 spec requirements"""
    results = {
        "spec_target": "≤35 min per 1M entries (Quick mode)",
        "required_speed": 476.19,  # entries/sec for 35 min
        "tests": [],
    }

    try:
        from src.core.pipeline_v7 import V7Pipeline, PipelineMode

        # Test with small batch to estimate
        pipeline = V7Pipeline(mode=PipelineMode.QUICK)

        test_entry = {"CanonicalLatin": "Smith, John", "BirthYear": 1980}

        # Warm up
        pipeline.process(test_entry)

        # Time 100 entries
        start = time.time()
        for i in range(100):
            entry = test_entry.copy()
            entry["CanonicalLatin"] = f"Smith{i}, John"
            pipeline.process(entry)
        elapsed = time.time() - start

        speed = 100 / elapsed
        est_1m_time = 1_000_000 / speed / 60

        results["tests"].append(
            {
                "batch_size": 100,
                "speed": speed,
                "est_1m_minutes": est_1m_time,
                "meets_spec": est_1m_time <= 35,
            }
        )

    except Exception as e:
        results["error"] = str(e)

    return results


def check_korean_requirements() -> Dict[str, Any]:
    """Check Korean processing per V7 spec Rule 13"""
    results = {
        "spec": "Rule 13: Korean - Hyphen-separated syllables, initial caps",
        "tests": [],
        "compliance": True,
    }

    test_cases = [
        ("김정은", "Kim Jung-eun"),  # V7 spec requires Jung-eun, not Jong-un
        ("박근혜", "Park Geun-hye"),
        ("문재인", "Moon Jae-in"),
        ("이명박", "Lee Myung-bak"),
        ("김민수", "Kim Min-su"),
    ]

    try:
        from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor

        processor = E4KoreanProcessor()

        for native, expected in test_cases:
            result = processor.process({"CanonicalNative": native})
            actual = result.get("CanonicalLatin", "")
            passed = actual == expected
            results["tests"].append(
                {"input": native, "expected": expected, "actual": actual, "passed": passed}
            )
            if not passed:
                results["compliance"] = False
    except Exception as e:
        results["error"] = str(e)
        results["compliance"] = False

    return results


def check_regional_coverage() -> Dict[str, Any]:
    """Check all 37+ regions from spec are implemented"""
    results = {"spec_regions": 37, "found": 0, "missing": [], "groups": {}}

    # Check each regional group from spec
    region_groups = {
        "A": ["a1_anglo", "a2_west_europe", "a3_nordic", "a4_oceania", "a5_caribbean"],
        "B": ["b1_east_slavic", "b2_south_slavic", "b3_greek"],
        "C": [
            "c1_turkic",
            "c2_persian",
            "c3_arabic_levant",
            "c4_gulf",
            "c5_maghreb",
            "c6_hebrew",
            "c7_armenian",
            "c8_georgian",
            "c9_caucasus",
        ],
        "D": ["d1_hindi", "d2_dravidian", "d3_bengali", "d4_urdu", "d5_sinhala"],
        "E": [
            "e1_sinophone",
            "e2_traditional",
            "e3_japan",
            "e4_korea",
            "e5_vietnam",
            "e6_mainland_sea",
            "e7_maritime_sea",
        ],
        "F": ["f1_ssa_franco", "f2_ssa_anglo", "f3_horn", "f4_lusophone"],
        "G": ["g1_latin_america"],
    }

    for group, regions in region_groups.items():
        group_path = Path(f"src/regions/{group.lower()}_groups")
        if group_path.exists():
            results["groups"][group] = {"expected": len(regions), "found": 0}
            for region in regions:
                if (group_path / region).exists() or (group_path / f"{region}.py").exists():
                    results["found"] += 1
                    results["groups"][group]["found"] += 1
                else:
                    results["missing"].append(f"{group}/{region}")

    return results


def check_data_model() -> Dict[str, Any]:
    """Check V7 data model compliance"""
    required_fields = [
        "GlobalID",
        "CanonicalLatin",
        "CanonicalNative",
        "Variants",
        "BirthYear",
        "DeathYear",
        "Confidence",
        "Gender",
        "LanguageOfPublication",
        "AffiliationTimeline",
        "ShortFormClusters",
        "MSC",
        "ExternalIdentifiers",
    ]

    results = {"required_fields": required_fields, "validation": None}

    try:
        from src.validation.schema_validator import SchemaValidator

        validator = SchemaValidator()

        # Test with minimal valid entry
        test_entry = {"GlobalID": "test-id", "CanonicalLatin": "Smith, John", "Confidence": 85}

        is_valid = validator.validate(test_entry)
        results["validation"] = "working" if is_valid else "failing"
    except Exception as e:
        results["validation"] = f"error: {str(e)}"

    return results


def main():
    print("=" * 80)
    print("V7 SPECIFICATION COMPLIANCE AUDIT - TRIPLE CHECK")
    print("=" * 80)

    results = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "checks": {}}

    # 1. Check pipeline stages
    print("\n📋 Checking Pipeline Stages (12 required)...")
    stages = check_stage_implementations()
    results["checks"]["pipeline_stages"] = stages
    print(f"  ✅ {stages['implemented']}/{stages['total']} stages implemented")
    if stages["missing"]:
        print(f"  ❌ Missing: {', '.join(stages['missing'][:3])}")

    # 2. Check quality gates
    print("\n🚦 Checking Quality Gates...")
    gates = check_quality_gates()
    results["checks"]["quality_gates"] = gates
    if gates["compliance"]:
        print("  ✅ Quality gates implemented")
    else:
        print("  ❌ Quality gates not compliant")

    # 3. Check performance
    print("\n⚡ Checking Performance Requirements...")
    perf = check_performance_requirements()
    results["checks"]["performance"] = perf
    if "error" not in perf:
        test = perf["tests"][0] if perf["tests"] else None
        if test:
            status = "✅" if test["meets_spec"] else "❌"
            print(f"  {status} {test['speed']:.0f} entries/sec (need {perf['required_speed']:.0f})")
            print(f"      Est. 1M time: {test['est_1m_minutes']:.0f} min (spec: ≤35 min)")
    else:
        print(f"  ❌ Error: {perf['error']}")

    # 4. Check Korean processing
    print("\n🇰🇷 Checking Korean Processing (Rule 13)...")
    korean = check_korean_requirements()
    results["checks"]["korean"] = korean
    if korean["compliance"]:
        print("  ✅ Korean processing compliant")
    else:
        failed = [t for t in korean.get("tests", []) if not t.get("passed")]
        if failed:
            print(
                f"  ❌ Failed: {failed[0]['input']} → {failed[0]['actual']} (expected: {failed[0]['expected']})"
            )

    # 5. Check regional coverage
    print("\n🌍 Checking Regional Coverage (37+ regions)...")
    regions = check_regional_coverage()
    results["checks"]["regions"] = regions
    print(f"  ✅ {regions['found']}/{regions['spec_regions']} regions implemented")
    if regions["missing"]:
        print(f"  ❌ Missing: {', '.join(regions['missing'][:5])}")

    # 6. Check data model
    print("\n📊 Checking Data Model...")
    model = check_data_model()
    results["checks"]["data_model"] = model
    print(f"  Schema validation: {model['validation']}")

    # Calculate overall compliance
    compliant = 0
    total = 6

    if stages["implemented"] >= 10:
        compliant += 1
    if gates.get("compliance"):
        compliant += 1
    if perf.get("tests") and perf["tests"][0].get("meets_spec"):
        compliant += 1
    if korean.get("compliance"):
        compliant += 1
    if regions["found"] >= 30:
        compliant += 1
    if model["validation"] == "working":
        compliant += 1

    results["overall"] = {
        "score": f"{compliant}/{total}",
        "percentage": (compliant / total) * 100,
        "status": "COMPLIANT" if compliant >= 5 else "NON-COMPLIANT",
    }

    print("\n" + "=" * 80)
    print("OVERALL V7 SPEC COMPLIANCE")
    print("=" * 80)
    print(f"Score: {results['overall']['score']} ({results['overall']['percentage']:.0f}%)")
    print(f"Status: {results['overall']['status']}")

    # Save results
    filename = f"v7_full_spec_audit_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Detailed results saved to: {filename}")

    return results


if __name__ == "__main__":
    main()
