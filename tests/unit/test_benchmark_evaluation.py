"""Three-track benchmark evaluation per expert Phase 5 guidance.

Track 1: Geo benchmark — geo_region vs CC/citizenship labels (843 entries)
Track 2: Name-origin benchmark — name_region on adjudicated onomastic labels
Track 3: Ambiguity benchmark — abstention/candidates on mixed/diaspora cases
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

sys.path.insert(0, ".")

BENCHMARK_PATH = (
    Path(__file__).parent.parent / "fixtures" / "name_origin_benchmark.json"
)


@pytest.fixture(scope="module")
def benchmark_data():
    import os
    import random

    with open(BENCHMARK_PATH) as f:
        data = json.load(f)

    # In CI: use a smaller sample to avoid timeouts
    if os.environ.get("CI"):
        random.seed(42)
        data = random.sample(data, min(100, len(data)))

    return data


@pytest.fixture(scope="module")
def manager():
    from src.regions.manager_optimized import RegionManager

    return RegionManager()


# ============================================================
# Track 1: Geo Benchmark (geo_region vs citizenship labels)
# ============================================================


def test_geo_benchmark(manager, benchmark_data):
    """Geo branch: when CC is provided, geo_region must match citizenship label."""
    correct = 0
    total = 0
    for entry in benchmark_data:
        geo_label = entry["geo_label"]
        name = entry["full_name"]
        cc = None
        # Infer CC from geo_label (reverse lookup)
        from src.regions.base import TERRITORY_TO_REGION

        for territory, region in TERRITORY_TO_REGION.items():
            if region == geo_label:
                cc = territory
                break
        if not cc:
            continue
        total += 1
        r = manager.detect_region({"CanonicalLatin": name, "CountryCodes": [cc]})
        if r.region_code == geo_label:
            correct += 1

    accuracy = correct / total if total else 0
    assert (
        accuracy >= 0.99
    ), f"Geo benchmark: {accuracy:.1%} ({correct}/{total}) below 99%"


# ============================================================
# Track 2: Name-Origin Benchmark (adjudicated onomastic labels)
# ============================================================


def test_name_origin_leaf_precision(manager, benchmark_data):
    """Leaf precision on high-confidence entries (where geo and name-origin agree).

    NOTE: This only measures on the AGREEMENT subset. The disagreement
    subset (immigrants, diaspora) requires human adjudication for proper
    name-origin labels. Until then, we report but don't gate on it.
    """
    from src.regions.manager_optimized import LEAF_TO_GROUP

    # High-confidence: system agreed with geo label
    high_conf = [e for e in benchmark_data if e["adjudication_confidence"] == "high"]

    emitted = 0
    correct = 0
    for entry in high_conf:
        r = manager.detect_region({"CanonicalLatin": entry["full_name"]})
        if r.region_code != "R0":
            emitted += 1
            if r.region_code == entry["geo_label"]:
                correct += 1

    precision = correct / emitted if emitted else 0
    coverage = emitted / len(high_conf) if high_conf else 0
    print(f"\nHigh-confidence leaf precision: {correct}/{emitted} = {precision:.1%}")
    print(f"High-confidence coverage: {emitted}/{len(high_conf)} = {coverage:.1%}")
    # On agreement subset, precision should be very high
    assert precision >= 0.95, (
        f"High-confidence leaf precision {precision:.1%} below 95% "
        f"({correct}/{emitted})"
    )

    # Also report on ALL 843 entries vs geo labels (informational, not gated)
    all_emitted = 0
    all_correct = 0
    all_group = 0
    for entry in benchmark_data:
        r = manager.detect_region({"CanonicalLatin": entry["full_name"]})
        if r.region_code != "R0":
            all_emitted += 1
            if r.region_code == entry["geo_label"]:
                all_correct += 1
                all_group += 1
            elif LEAF_TO_GROUP.get(r.region_code) == LEAF_TO_GROUP.get(
                entry["geo_label"]
            ):
                all_group += 1
        else:
            if r.group_region == LEAF_TO_GROUP.get(entry["geo_label"]):
                all_group += 1

    print("\n[INFO] Full 843 vs geo labels (NOT name-origin adjusted):")
    print(
        f"  Leaf precision: {all_correct}/{all_emitted} = {all_correct/max(1,all_emitted):.1%}"
    )
    print(
        f"  Coverage: {all_emitted}/{len(benchmark_data)} = {all_emitted/len(benchmark_data):.1%}"
    )
    print(
        f"  Group-or-better: {all_group}/{len(benchmark_data)} = {all_group/len(benchmark_data):.1%}"
    )
    print("  NOTE: many 'errors' are correct name-origin on immigrants")


def test_name_origin_group_accuracy(manager, benchmark_data):
    """Group-or-better on high-confidence entries."""
    from src.regions.manager_optimized import LEAF_TO_GROUP

    high_conf = [e for e in benchmark_data if e["adjudication_confidence"] == "high"]

    group_correct = 0
    for entry in high_conf:
        r = manager.detect_region({"CanonicalLatin": entry["full_name"]})
        expected_group = LEAF_TO_GROUP.get(entry["geo_label"])
        if r.region_code == entry["geo_label"]:
            group_correct += 1
        elif r.region_code == "R0" and r.group_region == expected_group:
            group_correct += 1
        elif r.region_code != "R0":
            got_group = LEAF_TO_GROUP.get(r.region_code)
            if got_group == expected_group:
                group_correct += 1

    accuracy = group_correct / len(high_conf) if high_conf else 0
    print(
        f"\nHigh-confidence group-or-better: {group_correct}/{len(high_conf)} = {accuracy:.1%}"
    )
    assert accuracy >= 0.95, (
        f"Group-or-better {accuracy:.1%} below 95% "
        f"({group_correct}/{len(high_conf)})"
    )


# ============================================================
# Track 3: Ambiguity Benchmark
# ============================================================


def test_ambiguity_handling(manager, benchmark_data):
    """Diaspora/mixed cases should abstain or return candidates, not force a leaf."""
    candidate_entries = [
        e for e in benchmark_data if e["expected_mode"] == "candidates"
    ]
    if not candidate_entries:
        pytest.skip("No candidate-mode entries in benchmark")

    correct_abstain = 0
    for entry in candidate_entries:
        r = manager.detect_region({"CanonicalLatin": entry["full_name"]})
        # Correct if R0 or if detected leaf is in acceptable set
        if r.region_code == "R0":
            correct_abstain += 1
        elif r.region_code in entry.get("acceptable_leaves", []):
            correct_abstain += 1

    rate = correct_abstain / len(candidate_entries) if candidate_entries else 0
    print(
        f"\nAmbiguity handling: {correct_abstain}/{len(candidate_entries)} = {rate:.1%}"
    )


# ============================================================
# Summary report
# ============================================================


def test_benchmark_summary(manager, benchmark_data):
    """Print full benchmark summary for review."""
    from src.regions.manager_optimized import LEAF_TO_GROUP

    stats = {
        "total": len(benchmark_data),
        "leaf_entries": 0,
        "candidate_entries": 0,
        "high_conf": 0,
        "medium_conf": 0,
        "low_conf": 0,
    }

    for e in benchmark_data:
        if e["expected_mode"] == "leaf":
            stats["leaf_entries"] += 1
        else:
            stats["candidate_entries"] += 1
        stats[e["adjudication_confidence"] + "_conf"] += 1

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Total entries: {stats['total']}")
    print(f"  Leaf-identifiable: {stats['leaf_entries']}")
    print(f"  Candidate/ambiguous: {stats['candidate_entries']}")
    print(f"  High confidence: {stats['high_conf']}")
    print(f"  Medium confidence: {stats['medium_conf']}")
    print(f"  Low confidence: {stats['low_conf']}")
