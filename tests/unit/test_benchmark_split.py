"""Unit tests for ``src/regions/benchmark_split.py``.

The split helper drives every "honest" out-of-sample number we
publish — calibration ECE, leaf precision, etc. Pin its invariants:

  - The split is deterministic (same seed = same assignment).
  - Train + test together cover every benchmark entry exactly once.
  - The proportions are within ±5pp of 80/20 globally.
  - Each group (A-G) has ≥ 1 entry on each side.
"""

from __future__ import annotations

import collections

from src.regions.benchmark_split import (
    BENCHMARK_PATH,
    SEED,
    TEST_FRACTION,
    assignment,
    load_all,
    load_test,
    load_train,
)


def test_benchmark_path_resolves_to_real_file():
    assert BENCHMARK_PATH.exists(), (
        f"benchmark fixture missing at {BENCHMARK_PATH} — split helper "
        f"cannot work without it"
    )


def test_assignment_is_deterministic():
    a = assignment()
    b = assignment()
    assert a == b
    assert id(a) == id(b), "expected lru_cache to return the same dict object"


def test_train_plus_test_equals_all_with_no_overlap():
    all_names = {e["full_name"] for e in load_all()}
    train_names = {e["full_name"] for e in load_train()}
    test_names = {e["full_name"] for e in load_test()}
    assert train_names | test_names == all_names
    assert not (train_names & test_names), "train and test must be disjoint"


def test_overall_split_close_to_target_fraction():
    n_total = len(load_all())
    n_test = len(load_test())
    actual_fraction = n_test / n_total
    delta = abs(actual_fraction - TEST_FRACTION)
    assert delta < 0.05, (
        f"actual test fraction {actual_fraction:.3f} differs from "
        f"target {TEST_FRACTION} by more than 5pp ({delta:.3f})"
    )


def test_each_group_has_train_and_test_representation():
    """Stratification: every group letter that appears in the input
    must appear on BOTH sides of the split."""

    def _groups_in(entries):
        out = collections.Counter()
        for e in entries:
            leaves = e.get("acceptable_leaves") or []
            if leaves:
                out[leaves[0][0]] += 1
        return out

    full_groups = _groups_in(load_all())
    train_groups = _groups_in(load_train())
    test_groups = _groups_in(load_test())

    for g, n in full_groups.items():
        if n >= 2:  # only meaningful for groups with at least 2 entries
            assert train_groups[g] >= 1, f"group {g} (n={n}) has no train entries"
            assert test_groups[g] >= 1, f"group {g} (n={n}) has no test entries"


def test_per_group_test_fraction_within_bounds():
    """Each group's test fraction should land near the target 0.2.

    Tiny groups (G=37, F=43) get more bernoulli noise; allow ±10pp
    locally vs the ±5pp global bound."""

    by_group_all: dict[str, list] = collections.defaultdict(list)
    by_group_test: dict[str, list] = collections.defaultdict(list)
    for e in load_all():
        leaves = e.get("acceptable_leaves") or []
        if leaves:
            by_group_all[leaves[0][0]].append(e)
    for e in load_test():
        leaves = e.get("acceptable_leaves") or []
        if leaves:
            by_group_test[leaves[0][0]].append(e)

    for g, all_entries in by_group_all.items():
        if len(all_entries) < 5:
            continue  # skip tiny groups where the bound isn't meaningful
        actual = len(by_group_test.get(g, [])) / len(all_entries)
        assert abs(actual - TEST_FRACTION) < 0.10, (
            f"group {g}: test fraction {actual:.3f} too far from "
            f"target {TEST_FRACTION}"
        )


def test_seed_constant_is_documented():
    """If someone bumps SEED, every published 'test-set ECE' number
    silently invalidates. This isn't a behavioural test — it's a
    sentinel to make the value visible in test output if it ever
    changes."""
    assert SEED == 42, (
        "SEED must remain 42 unless every consumer of load_test() "
        "is re-run and every published number is updated"
    )
