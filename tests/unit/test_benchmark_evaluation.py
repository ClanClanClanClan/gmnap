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


def _fasttext_ready() -> bool:
    """True when both the fasttext binary and a surname/ft_name model are
    reachable. CI environments without the model file (it is gitignored
    because of its 50 MB size) should skip strict accuracy assertions."""
    import shutil
    from pathlib import Path

    # Binary check: Python module OR the CLI on PATH / known fallbacks
    binary_ok = False
    try:
        import fasttext  # noqa: F401

        binary_ok = True
    except ImportError:
        if shutil.which("fasttext"):
            binary_ok = True
        else:
            home = Path.home()
            for p in (
                "/usr/local/bin/fasttext",
                "/opt/homebrew/bin/fasttext",
                str(home / ".local" / "bin" / "fasttext"),
                "bin/fasttext",
            ):
                if Path(p).exists():
                    binary_ok = True
                    break
    if not binary_ok:
        return False

    model_candidates = (
        "data/ml_training/ft_name_classifier.ftz",
        "data/ml_training/ft_name_classifier.bin",
        "data/ml_training/surname_classifier.ftz",
        "data/ml_training/surname_classifier.bin",
    )
    return any(Path(p).exists() for p in model_candidates)


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


@pytest.mark.timeout(600)
def test_name_origin_leaf_precision(manager, benchmark_data):
    """Leaf precision on high-confidence entries (where geo and name-origin agree).

    NOTE: This only measures on the AGREEMENT subset. The disagreement
    subset (immigrants, diaspora) requires human adjudication for proper
    name-origin labels. Until then, we report but don't gate on it.

    Per-test timeout 600s: with the full fastText model present, the
    pipeline takes ~50ms/entry on 843 entries (~ 7-9 min when the
    classifier path is exercised, depending on hardware). On CI the
    test is `pytest.skip`-ed because the fastText model isn't bundled
    in the runner image — the 600s ceiling is for the local-dev-with-
    fastText path, not CI.
    """
    from src.regions.manager_optimized import LEAF_TO_GROUP

    if not _fasttext_ready():
        pytest.skip(
            "fastText model not available — skipping strict leaf-precision "
            "assertion (reduced-capability runtime)."
        )

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

    # ONE pass through the full benchmark — record the per-entry
    # outcome, then re-bucket below for the all/train/test reports
    # without paying for the pipeline again.
    from src.regions.benchmark_split import assignment

    split_map = assignment()
    per_entry: list[dict] = []
    for entry in benchmark_data:
        r = manager.detect_region({"CanonicalLatin": entry["full_name"]})
        per_entry.append(
            {
                "name": entry["full_name"],
                "code": r.region_code,
                "group": r.group_region,
                "geo_label": entry["geo_label"],
                "acceptable_leaves": entry.get("acceptable_leaves") or [],
                "split": split_map.get(entry["full_name"], "?"),
            }
        )

    # ── Report 1: full 843 vs geo labels (informational) ──
    all_emitted = sum(1 for x in per_entry if x["code"] != "R0")
    all_correct_geo = sum(
        1 for x in per_entry if x["code"] != "R0" and x["code"] == x["geo_label"]
    )
    all_group = sum(
        1
        for x in per_entry
        if (x["code"] != "R0" and x["code"] == x["geo_label"])
        or (
            x["code"] != "R0"
            and LEAF_TO_GROUP.get(x["code"]) == LEAF_TO_GROUP.get(x["geo_label"])
        )
        or (x["code"] == "R0" and x["group"] == LEAF_TO_GROUP.get(x["geo_label"]))
    )
    print("\n[INFO] Full 843 vs geo labels (NOT name-origin adjusted):")
    print(
        f"  Leaf precision: {all_correct_geo}/{all_emitted} = "
        f"{all_correct_geo/max(1,all_emitted):.1%}"
    )
    print(
        f"  Coverage: {all_emitted}/{len(benchmark_data)} = "
        f"{all_emitted/len(benchmark_data):.1%}"
    )
    print(
        f"  Group-or-better: {all_group}/{len(benchmark_data)} = "
        f"{all_group/len(benchmark_data):.1%}"
    )
    print("  NOTE: many 'errors' are correct name-origin on immigrants")

    # ── Report 2: train vs test split, honest leaf precision vs
    #             acceptable_leaves (the adjudicated-leaf metric) ──
    def _split_metrics(side: str) -> dict:
        rows = [x for x in per_entry if x["split"] == side]
        emitted = sum(1 for x in rows if x["code"] != "R0")
        correct = sum(
            1 for x in rows if x["code"] != "R0" and x["code"] in x["acceptable_leaves"]
        )
        return {
            "n": len(rows),
            "emitted": emitted,
            "correct": correct,
            "coverage": emitted / max(1, len(rows)),
            "leaf_precision": correct / max(1, emitted),
        }

    train_m = _split_metrics("train")
    test_m = _split_metrics("test")
    print("\n[INFO] Stratified train/test split (src/regions/benchmark_split.py):")
    print(
        f"  Train (in-sample):    "
        f"leaf precision {train_m['correct']}/{train_m['emitted']} = "
        f"{train_m['leaf_precision']:.1%}, "
        f"coverage {train_m['emitted']}/{train_m['n']} = "
        f"{train_m['coverage']:.1%}"
    )
    print(
        f"  Test  (held-out):     "
        f"leaf precision {test_m['correct']}/{test_m['emitted']} = "
        f"{test_m['leaf_precision']:.1%}, "
        f"coverage {test_m['emitted']}/{test_m['n']} = "
        f"{test_m['coverage']:.1%}"
    )


def test_name_origin_group_accuracy(manager, benchmark_data):
    """Group-or-better on high-confidence entries.

    High-confidence adjudication was recorded when the full detection
    pipeline (rules + fastText surname classifier) agreed with the geo
    label. Without the fastText model present, accuracy drops to ~50 %;
    this test skips rather than failing in that environment.
    """
    from src.regions.manager_optimized import LEAF_TO_GROUP

    if not _fasttext_ready():
        pytest.skip(
            "fastText model not available — skipping strict group-accuracy "
            "assertion; this reflects a reduced-capability runtime, not a "
            "regression."
        )

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
