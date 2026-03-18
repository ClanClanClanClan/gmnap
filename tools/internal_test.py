#!/usr/bin/env python3
"""
GMNAP Internal Test — Comprehensive quality validation.

Usage:
    python3 tools/internal_test.py [--mode quick|full] [--live] [--entries N]

This script:
1. Loads all 1500 test fixtures
2. Runs the pipeline
3. Validates output against V7 spec requirements
4. Checks all 8 quality gates
5. Produces a detailed quality report
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REQUIRED_FIELDS = [
    "GlobalID", "UpdatedAt", "CanonicalLatin", "CanonicalNative",
    "LanguageOfPublication", "FamilyNameType", "Gender",
    "CountryCodes", "Confidence", "Historic", "GDPR_DATA",
]

VALID_FAMILY_TYPES = {"surname", "patronymic", "mononym"}
VALID_GENDERS = {"male", "female", "nonbinary", "unspecified"}
GLOBALID_PATTERN = r"^[A-Z2-7]{22}(--\d+)?$"


def load_fixtures(max_entries: int = 0) -> list:
    """Load test fixtures from region_test_data.json."""
    path = Path("tests/fixtures/region_test_data.json")
    if not path.exists():
        print(f"ERROR: Fixtures not found at {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for region_code, region_data in data.items():
        if isinstance(region_data, dict) and "entries" in region_data:
            entries.extend(region_data["entries"])
        elif isinstance(region_data, list):
            entries.extend(region_data)

    if max_entries > 0:
        entries = entries[:max_entries]

    return entries


def validate_entry(entry: dict) -> list:
    """Validate a single entry against V7 spec. Returns list of error strings."""
    import re
    errors = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"missing required field: {field}")

    # GlobalID format
    gid = entry.get("GlobalID", "")
    if gid and not re.match(GLOBALID_PATTERN, gid):
        errors.append(f"invalid GlobalID format: {gid[:30]}")

    # Enum fields
    fnt = entry.get("FamilyNameType", "")
    if fnt and fnt not in VALID_FAMILY_TYPES:
        errors.append(f"invalid FamilyNameType: {fnt}")

    gender = entry.get("Gender", "")
    if gender and gender not in VALID_GENDERS:
        errors.append(f"invalid Gender: {gender}")

    # Confidence range
    conf = entry.get("Confidence")
    if conf is not None and not (0 <= conf <= 100):
        errors.append(f"Confidence out of range: {conf}")

    # CountryCodes format
    cc = entry.get("CountryCodes", [])
    if cc and not isinstance(cc, list):
        errors.append(f"CountryCodes must be list, got {type(cc).__name__}")

    # Birth/death year plausibility
    by = entry.get("BirthYear")
    dy = entry.get("DeathYear")
    if isinstance(by, (int, float)) and isinstance(dy, (int, float)):
        if by and dy:
            # Handle dict-wrapped years from authority sources
            by_val = by if isinstance(by, (int, float)) else 0
            dy_val = dy if isinstance(dy, (int, float)) else 0
            if by_val and dy_val and dy_val < by_val:
                errors.append(f"death year {dy_val} before birth year {by_val}")

    return errors


async def run_internal_test(mode: str = "quick", offline: bool = True, max_entries: int = 0):
    """Run the internal quality test."""
    os.environ["PYTHONPATH"] = "."
    os.environ["OFFLINE"] = "1" if offline else "0"
    os.environ["PIPELINE_MODE"] = mode

    Path("work").mkdir(exist_ok=True)
    Path("cache").mkdir(exist_ok=True)
    Path("out/internal_test").mkdir(parents=True, exist_ok=True)

    entries = load_fixtures(max_entries)
    print(f"\n{'='*70}")
    print(f"GMNAP V7 Internal Test — {len(entries)} entries from fixtures")
    print(f"Mode: {mode} | OFFLINE: {os.environ.get('OFFLINE')} | Max: {max_entries or 'all'}")
    print(f"{'='*70}\n")

    from src.core.pipeline_v7 import V7Pipeline as PipelineV7, PipelineMode

    pipeline = PipelineV7(mode=PipelineMode[mode.upper()])
    start = time.time()

    try:
        report = await pipeline.process_batch(entries)
    except Exception as e:
        print(f"\nPIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    elapsed = time.time() - start
    processed = report.get("entries", [])
    metrics = report.get("metrics", {})
    quality = report.get("quality_gates", {})

    # ---- Validation Pass ----
    print("Running V7 spec validation on output...\n")
    total_errors = 0
    entries_with_errors = 0
    error_types = Counter()
    region_counts = Counter()
    region_errors = defaultdict(int)

    for entry in processed:
        rc = entry.get("RegionCode") or entry.get("DetectedRegion", "??")
        region_counts[rc] += 1

        errors = validate_entry(entry)
        if errors:
            entries_with_errors += 1
            total_errors += len(errors)
            region_errors[rc] += 1
            for e in errors:
                error_types[e.split(":")[0]] += 1

    # ---- GlobalID uniqueness ----
    gids = [e.get("GlobalID", "") for e in processed if e.get("GlobalID")]
    unique_gids = set(gids)
    duplicates = len(gids) - len(unique_gids)

    # ---- Report ----
    print(f"{'='*70}")
    print("INTERNAL TEST RESULTS")
    print(f"{'='*70}")
    print(f"  Input entries:     {len(entries)}")
    print(f"  Processed:         {len(processed)}")
    print(f"  Time:              {elapsed:.1f}s ({elapsed/max(len(entries),1)*1000:.0f}ms/entry)")
    print(f"  Throughput:        {len(entries)/max(elapsed,0.001):.0f} entries/sec")
    proj_1m = (elapsed / max(len(entries), 1)) * 1_000_000 / 60
    print(f"  Projected 1M:      {proj_1m:.0f} min")

    print(f"\n  REGION DISTRIBUTION ({len(region_counts)} regions):")
    for rc in sorted(region_counts.keys()):
        errs = region_errors.get(rc, 0)
        err_str = f"  ({errs} errors)" if errs else ""
        print(f"    {rc}: {region_counts[rc]:4d} entries{err_str}")

    print(f"\n  VALIDATION:")
    print(f"    Entries with errors: {entries_with_errors}/{len(processed)} ({entries_with_errors/max(len(processed),1)*100:.1f}%)")
    print(f"    Total errors:        {total_errors}")
    if error_types:
        print(f"    Error breakdown:")
        for err, count in error_types.most_common(10):
            print(f"      {err}: {count}")

    print(f"\n  GLOBALID INTEGRITY:")
    print(f"    Total:    {len(gids)}")
    print(f"    Unique:   {len(unique_gids)}")
    print(f"    Dupes:    {duplicates}")

    print(f"\n  QUALITY GATES:")
    gates_passed = quality.get("passed", "?")
    print(f"    Overall: {'PASS' if gates_passed else 'FAIL'}")
    for gate, val in quality.items():
        if gate != "passed":
            status = "PASS" if not str(val).startswith("FAIL") else "FAIL"
            print(f"    {gate}: {val} [{status}]")

    # Authority enrichment summary
    enriched = sum(1 for e in processed if e.get("_sources"))
    with_alt = sum(1 for e in processed if e.get("AlternativeLatin"))
    with_timeline = sum(1 for e in processed if e.get("AffiliationTimeline"))
    with_events = sum(1 for e in processed if e.get("NameEvents"))
    with_degree = sum(1 for e in processed if e.get("DegreeDate"))
    print(f"\n  AUTHORITY ENRICHMENT:")
    print(f"    Enriched:           {enriched}/{len(processed)}")
    print(f"    AlternativeLatin:   {with_alt}")
    print(f"    AffiliationTimeline:{with_timeline}")
    print(f"    NameEvents:         {with_events}")
    print(f"    DegreeDate:         {with_degree}")

    # Stage timings
    timings = metrics.get("stage_timings", {})
    if timings:
        print(f"\n  STAGE TIMINGS:")
        for stage, t in sorted(timings.items()):
            pct = t / max(elapsed, 0.001) * 100
            print(f"    {stage:30s} {t:7.3f}s ({pct:5.1f}%)")

    # Write full report
    report_path = Path("out/internal_test/report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "entries_input": len(entries),
                "entries_output": len(processed),
                "elapsed_seconds": elapsed,
                "ms_per_entry": elapsed / max(len(entries), 1) * 1000,
                "projected_1m_minutes": proj_1m,
                "regions_detected": len(region_counts),
                "validation_errors": total_errors,
                "entries_with_errors": entries_with_errors,
                "globalid_duplicates": duplicates,
                "quality_gates_passed": gates_passed,
                "authority_enriched": enriched,
            },
            "region_distribution": dict(region_counts),
            "error_types": dict(error_types),
            "quality_gates": quality,
            "stage_timings": timings,
        }, f, indent=2, default=str)
    print(f"\n  Report: {report_path}")

    # Verdict
    print(f"\n{'='*70}")
    if gates_passed and entries_with_errors == 0 and duplicates == 0:
        print("INTERNAL TEST: ALL CLEAR — READY FOR DEPLOYMENT TESTING")
    elif gates_passed and entries_with_errors < len(processed) * 0.05:
        print(f"INTERNAL TEST: ACCEPTABLE — {entries_with_errors} entries with validation warnings")
    else:
        issues = []
        if not gates_passed:
            issues.append("quality gates failed")
        if entries_with_errors > 0:
            issues.append(f"{entries_with_errors} validation errors")
        if duplicates > 0:
            issues.append(f"{duplicates} GlobalID duplicates")
        print(f"INTERNAL TEST: NEEDS ATTENTION — {', '.join(issues)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GMNAP V7 Internal Test")
    parser.add_argument("--mode", default="quick", choices=["quick", "full", "extreme"])
    parser.add_argument("--live", action="store_true", help="Enable live API calls")
    parser.add_argument("--entries", type=int, default=0, help="Max entries (0=all)")
    args = parser.parse_args()

    asyncio.run(run_internal_test(
        mode=args.mode,
        offline=not args.live,
        max_entries=args.entries,
    ))
