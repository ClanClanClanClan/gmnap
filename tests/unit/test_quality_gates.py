"""
Comprehensive unit tests for V7 quality gates.

Tests all 8 gates with mode-specific thresholds (Quick, Full, Extreme)
and verifies correct pass/fail behavior.
"""

import pytest

from src.quality.gates import QualityGateChecker, dice

# ── Dice coefficient ─────────────────────────────────────────────────────


class TestDiceCoefficient:
    """Test Sørensen-Dice coefficient."""

    def test_identical_strings(self):
        assert dice("hello", "hello") == 1.0

    def test_completely_different(self):
        assert dice("abc", "xyz") == 0.0

    def test_partial_overlap(self):
        score = dice("night", "nacht")
        assert 0.0 < score < 1.0

    def test_case_insensitive(self):
        assert dice("Hello", "hello") == 1.0

    def test_empty_strings(self):
        assert dice("", "") == 1.0

    def test_single_char(self):
        assert dice("a", "a") == 1.0


# ── Gate 1: duplicate_global_id ──────────────────────────────────────────


class TestDuplicateGlobalId:
    """Gate 1: duplicate_global_id must be 0 in all modes."""

    def test_no_duplicates(self):
        checker = QualityGateChecker(mode="quick")
        entries = [
            {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"},
            {"GlobalID": "BBBBBBBBBBBBBBBBBBBBBB"},
        ]
        ok, count = checker.check_duplicate_global_ids(entries)
        assert ok
        assert count == 0

    def test_with_duplicates(self):
        checker = QualityGateChecker(mode="quick")
        entries = [
            {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"},
            {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"},
        ]
        ok, count = checker.check_duplicate_global_ids(entries)
        assert not ok
        assert count == 1

    @pytest.mark.parametrize("mode", ["quick", "full", "extreme"])
    def test_zero_tolerance_all_modes(self, mode):
        checker = QualityGateChecker(mode=mode)
        entries = [
            {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"},
            {"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"},
        ]
        ok, count = checker.check_duplicate_global_ids(entries)
        assert not ok


# ── Gate 2: duplicate_external_id_pct ────────────────────────────────────


class TestDuplicateExternalId:
    """Gate 2: duplicate_external_id_pct varies by mode."""

    def test_no_external_ids(self):
        checker = QualityGateChecker(mode="quick")
        entries = [{"GlobalID": "AAAAAAAAAAAAAAAAAAAAAA"}]
        ok, pct = checker.check_duplicate_external_ids(entries)
        assert ok
        assert pct == 0.0

    def test_no_duplicates(self):
        checker = QualityGateChecker(mode="quick")
        entries = [
            {"GlobalID": "A" * 22, "AuthorityIDs": {"ORCID": "0000-0001-0000-0001"}},
            {"GlobalID": "B" * 22, "AuthorityIDs": {"ORCID": "0000-0001-0000-0002"}},
        ]
        ok, pct = checker.check_duplicate_external_ids(entries)
        assert ok

    def test_extreme_mode_zero_tolerance(self):
        checker = QualityGateChecker(mode="extreme")
        entries = [
            {"GlobalID": "A" * 22, "AuthorityIDs": {"ORCID": "0000-0001-0000-0001"}},
            {"GlobalID": "B" * 22, "AuthorityIDs": {"ORCID": "0000-0001-0000-0001"}},
        ]
        ok, pct = checker.check_duplicate_external_ids(entries)
        assert not ok


# ── Gate 3: roundtrip_script_rate_min ────────────────────────────────────


class TestRoundtripScriptRate:
    """Gate 3: roundtrip_script_rate_min >= 0.97."""

    def test_all_identical(self):
        checker = QualityGateChecker(mode="quick")
        pairs = [("Smith", "Smith"), ("García", "García")]
        ok, rate = checker.check_roundtrip_rate(pairs)
        assert ok
        assert rate == 1.0

    def test_empty_pairs(self):
        checker = QualityGateChecker(mode="quick")
        ok, rate = checker.check_roundtrip_rate([])
        assert ok
        assert rate == 1.0

    def test_low_roundtrip_fails(self):
        checker = QualityGateChecker(mode="quick")
        # Many mismatches should fail
        pairs = [("abc", "xyz")] * 100
        ok, rate = checker.check_roundtrip_rate(pairs)
        assert not ok


# ── Gate 4: genealogy_edge_conflict_pct ──────────────────────────────────


class TestGenealogyEdgeConflicts:
    """Gate 4: genealogy_edge_conflict_pct varies by mode."""

    def test_no_conflicts(self):
        checker = QualityGateChecker(mode="quick")
        ok, pct = checker.check_genealogy_edge_conflicts(0, 100)
        assert ok
        assert pct == 0.0

    def test_no_edges(self):
        checker = QualityGateChecker(mode="quick")
        ok, pct = checker.check_genealogy_edge_conflicts(0, 0)
        assert ok

    def test_quick_mode_2pct_threshold(self):
        checker = QualityGateChecker(mode="quick")
        # 1.5% conflicts should pass in quick mode
        ok, pct = checker.check_genealogy_edge_conflicts(15, 1000)
        assert ok

    def test_full_mode_1pct_threshold(self):
        checker = QualityGateChecker(mode="full")
        # 1.5% conflicts should fail in full mode (limit 1%)
        ok, pct = checker.check_genealogy_edge_conflicts(15, 1000)
        assert not ok

    def test_extreme_mode_zero_tolerance(self):
        checker = QualityGateChecker(mode="extreme")
        ok, pct = checker.check_genealogy_edge_conflicts(1, 1000)
        assert not ok


# ── Gate 5: graph_coherence_score_min ────────────────────────────────────


class TestGraphCoherence:
    """Gate 5: graph_coherence_score_min varies by mode."""

    @pytest.mark.parametrize(
        "mode,score,expected",
        [
            ("quick", 0.85, True),
            ("quick", 0.80, False),
            ("full", 0.92, True),
            ("full", 0.90, False),
            ("extreme", 0.97, True),
            ("extreme", 0.95, False),
        ],
    )
    def test_mode_specific_thresholds(self, mode, score, expected):
        checker = QualityGateChecker(mode=mode)
        ok, val = checker.check_graph_coherence(score)
        assert ok == expected
        assert val == score


# ── Gate 6: peak_rss_gb_on_2M ───────────────────────────────────────────


class TestMemoryLimit:
    """Gate 6: peak_rss_gb_on_2M <= 6GB."""

    def test_memory_check_runs(self):
        checker = QualityGateChecker(mode="quick")
        ok, rss = checker.check_memory_limit()
        assert ok  # In tests, should be well under 6GB
        assert rss >= 0

    def test_custom_limit(self):
        checker = QualityGateChecker(mode="quick")
        ok, rss = checker.check_memory_limit(rss_gb_limit=0.001)
        # 1MB limit - likely exceeded
        assert not ok or rss < 0.001


# ── Gate 7: warm_cache_runtime_per_1M_min ────────────────────────────────


class TestRuntime:
    """Gate 7: warm_cache_runtime_per_1M_min (Quick <=35, Full <=70)."""

    def test_quick_mode_within_limit(self):
        checker = QualityGateChecker(mode="quick")
        ok, val = checker.check_runtime(30)
        assert ok

    def test_quick_mode_over_limit(self):
        checker = QualityGateChecker(mode="quick")
        ok, val = checker.check_runtime(40)
        assert not ok

    def test_full_mode_within_limit(self):
        checker = QualityGateChecker(mode="full")
        ok, val = checker.check_runtime(60)
        assert ok

    def test_full_mode_over_limit(self):
        checker = QualityGateChecker(mode="full")
        ok, val = checker.check_runtime(80)
        assert not ok


# ── Gate 8: idempotent_diff_bytes_max ────────────────────────────────────


class TestIdempotency:
    """Gate 8: idempotent_diff_bytes_max must be 0."""

    def test_zero_diff(self):
        checker = QualityGateChecker(mode="quick")
        ok, val = checker.check_idempotency(0)
        assert ok

    def test_nonzero_diff(self):
        checker = QualityGateChecker(mode="quick")
        ok, val = checker.check_idempotency(100)
        assert not ok


# ── check_all integration ────────────────────────────────────────────────


class TestCheckAll:
    """Test check_all runs all 8 gates."""

    def test_all_pass(self):
        checker = QualityGateChecker(mode="quick")
        entries = [
            {
                "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
            }
        ]
        metrics = {
            "graph_conflicts": 0,
            "edges": 10,
            "graph_coherence": 0.95,
            "projected_time_per_million": 20,
            "idempotency_diff_bytes": 0,
        }
        all_ok, results = checker.check_all(entries, metrics)
        assert all_ok
        assert len(results) == 8

    def test_duplicate_fails_all(self):
        checker = QualityGateChecker(mode="quick")
        entries = [
            {
                "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
                "CanonicalLatin": "Smith",
                "CanonicalNative": "Smith",
            },
            {
                "GlobalID": "AAAAAAAAAAAAAAAAAAAAAA",
                "CanonicalLatin": "Jones",
                "CanonicalNative": "Jones",
            },
        ]
        metrics = {
            "graph_conflicts": 0,
            "edges": 0,
            "graph_coherence": 0.95,
            "projected_time_per_million": 20,
            "idempotency_diff_bytes": 0,
        }
        all_ok, results = checker.check_all(entries, metrics)
        assert not all_ok
        assert not results["duplicate_global_id"][0]
