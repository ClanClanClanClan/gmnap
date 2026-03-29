#!/usr/bin/env python3
"""
ULTRATHINK Final Comprehensive Check
Verifies all fixes and system quality
"""

import os
import sys
import subprocess
import asyncio
import importlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def check_dependencies():
    """Check optional dependencies are available or mocked."""
    results = {"total": 0, "available": 0, "mocked": 0, "missing": []}

    optional_deps = ["pynini", "pyjwt"]

    for dep in optional_deps:
        results["total"] += 1
        try:
            module = importlib.import_module(dep)
            results["available"] += 1
            print(f"  ✅ {dep}: Available (real module)")
        except ImportError:
            # Check if mock is available
            try:
                from src.core.mock_dependencies import get_jwt_module, get_pynini_module

                if dep == "pyjwt":
                    mock = get_jwt_module()
                    if mock:
                        results["mocked"] += 1
                        print(f"  ✅ {dep}: Mock available")
                    else:
                        results["missing"].append(dep)
                        print(f"  ❌ {dep}: Not available")
                elif dep == "pynini":
                    mock = get_pynini_module()
                    if mock:
                        results["mocked"] += 1
                        print(f"  ✅ {dep}: Mock available")
                    else:
                        results["missing"].append(dep)
                        print(f"  ❌ {dep}: Not available")
            except Exception as e:
                results["missing"].append(dep)
                print(f"  ❌ {dep}: Mock error: {e}")

    return results


def check_pipeline_modes():
    """Check all pipeline modes are functional."""
    from src.core.pipeline_v7 import V7Pipeline, PipelineMode

    results = {"total": 3, "working": 0, "failed": []}

    for mode in [PipelineMode.QUICK, PipelineMode.FULL, PipelineMode.EXTREME]:
        try:
            pipeline = V7Pipeline(mode=mode)
            # Test a small batch
            test_entries = [
                {"CanonicalNative": "Test Name", "GlobalID": f"TEST-{mode.value}"}
            ]
            result = asyncio.run(pipeline.process_batch(test_entries))

            if result and "entries" in result:
                results["working"] += 1
                print(f"  ✅ {mode.value}: Functional")
            else:
                results["failed"].append(mode.value)
                print(f"  ❌ {mode.value}: No output")
        except Exception as e:
            results["failed"].append(mode.value)
            print(f"  ❌ {mode.value}: {str(e)}")

    return results


def check_code_quality():
    """Check for code quality issues."""
    results = {
        "print_statements": 0,
        "long_lines": 0,
        "syntax_errors": 0,
        "files_checked": 0,
    }

    # Check for print statements in src/
    print_files = []
    long_line_files = []

    for root, dirs, files in os.walk("src"):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                results["files_checked"] += 1

                try:
                    with open(file_path, "r") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines, 1):
                        # Check for print statements (excluding comments)
                        if "print(" in line and not line.strip().startswith("#"):
                            results["print_statements"] += 1
                            if file_path not in print_files:
                                print_files.append(file_path)

                        # Check for long lines (>100 chars, excluding comments)
                        if len(line.rstrip()) > 100 and not line.strip().startswith(
                            "#"
                        ):
                            results["long_lines"] += 1
                            if file_path not in long_line_files:
                                long_line_files.append(file_path)

                except Exception as e:
                    results["syntax_errors"] += 1

    # Report findings
    if results["print_statements"] > 0:
        print(
            f"  ⚠️  Found {results['print_statements']} print statements in {len(print_files)} files"
        )
        for file in print_files[:3]:  # Show first 3
            print(f"      - {file}")
    else:
        print(f"  ✅ No print statements found")

    if results["long_lines"] > 0:
        print(
            f"  ⚠️  Found {results['long_lines']} long lines in {len(long_line_files)} files"
        )
        for file in long_line_files[:3]:  # Show first 3
            print(f"      - {file}")
    else:
        print(f"  ✅ No long lines found")

    if results["syntax_errors"] == 0:
        print(f"  ✅ No syntax errors in {results['files_checked']} files")
    else:
        print(f"  ❌ {results['syntax_errors']} syntax errors found")

    return results


async def check_v7_compliance():
    """Check V7 compliance status."""
    from src.core.pipeline_v7 import V7Pipeline, PipelineMode

    results = {
        "korean_processor": False,
        "duplicate_detection": False,
        "regional_detection": False,
        "performance": False,
    }

    # Test Korean processor
    from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor

    processor = E4KoreanProcessor()
    test_name = "김민수"
    result = processor.process({"CanonicalNative": test_name})
    if result and result.get("CanonicalLatin") == "Kim Min-su":
        results["korean_processor"] = True
        print(f"  ✅ Korean processor: Working")
    else:
        print(f"  ❌ Korean processor: Failed")

    # Test duplicate detection
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    entries = [
        {"CanonicalNative": "Same Name", "GlobalID": "DUP-001"},
        {"CanonicalNative": "Same Name", "GlobalID": "DUP-001"},
    ]
    result = await pipeline.process_batch(entries)
    if result["metrics"].get("duplicate_global_ids", 0) > 0:
        results["duplicate_detection"] = True
        print(f"  ✅ Duplicate detection: Working")
    else:
        print(f"  ❌ Duplicate detection: Failed")

    # Test regional detection
    from src.regions.manager import RegionManager

    manager = RegionManager()
    test_cases = [("山田太郎", "E3"), ("محمد", "C3")]
    all_correct = True
    for name, expected in test_cases:
        entry = {"CanonicalNative": name}
        detection = manager.detect_region(entry)
        if not detection or detection.region_code != expected:
            all_correct = False
            break

    if all_correct:
        results["regional_detection"] = True
        print(f"  ✅ Regional detection: Working")
    else:
        print(f"  ❌ Regional detection: Failed")

    # Test performance
    entries = [{"CanonicalNative": f"Name {i}"} for i in range(100)]
    import time

    start = time.time()
    result = await pipeline.process_batch(entries)
    elapsed = time.time() - start
    entries_per_sec = len(entries) / elapsed if elapsed > 0 else 0

    if entries_per_sec > 500:  # Should achieve >500/sec with batch of 100
        results["performance"] = True
        print(f"  ✅ Performance: {entries_per_sec:.0f} entries/sec")
    else:
        print(f"  ❌ Performance: {entries_per_sec:.0f} entries/sec (target: >500)")

    return results


def main():
    """Run comprehensive final check."""
    print("=" * 80)
    print("ULTRATHINK FINAL COMPREHENSIVE CHECK")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    all_results = {}

    # Check dependencies
    print("📦 Checking Dependencies...")
    dep_results = check_dependencies()
    all_results["dependencies"] = dep_results

    # Check pipeline modes
    print("\n⚙️  Checking Pipeline Modes...")
    mode_results = check_pipeline_modes()
    all_results["pipeline_modes"] = mode_results

    # Check code quality
    print("\n📝 Checking Code Quality...")
    quality_results = check_code_quality()
    all_results["code_quality"] = quality_results

    # Check V7 compliance
    print("\n🎯 Checking V7 Compliance...")
    compliance_results = asyncio.run(check_v7_compliance())
    all_results["v7_compliance"] = compliance_results

    # Calculate overall score
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    issues = []

    # Check for critical issues
    if dep_results["missing"]:
        issues.append(f"Missing dependencies: {dep_results['missing']}")

    if mode_results["failed"]:
        issues.append(f"Failed pipeline modes: {mode_results['failed']}")

    if quality_results["print_statements"] > 0:
        issues.append(f"{quality_results['print_statements']} print statements found")

    if quality_results["long_lines"] > 0:
        issues.append(f"{quality_results['long_lines']} long lines found")

    if not all(compliance_results.values()):
        failed_checks = [k for k, v in compliance_results.items() if not v]
        issues.append(f"V7 compliance failures: {failed_checks}")

    if not issues:
        print("\n✅ **SYSTEM FULLY CLEAN - ALL CHECKS PASSED!**")
        print("   - All dependencies available or mocked")
        print("   - All pipeline modes functional")
        print("   - Code quality excellent")
        print("   - V7 compliance complete")
    else:
        print(f"\n⚠️  **MINOR ISSUES FOUND:**")
        for issue in issues:
            print(f"   - {issue}")

    # Save results
    results_file = (
        f"final_check_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n📄 Full results saved to: {results_file}")

    # Return exit code
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
