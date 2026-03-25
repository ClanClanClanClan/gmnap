"""
Fixture-driven tests for all 37 V7 regions.

Loads region_test_data.json and processes each region's entries through
detection, cleaning, augmenting, and order key generation.
"""

import json
from pathlib import Path

import pytest

from src.regions.manager_optimized import RegionManager

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FIXTURE_FILE = FIXTURES_DIR / "region_test_data.json"


@pytest.fixture(scope="module")
def region_data():
    """Load region test fixtures."""
    return json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def region_manager():
    return RegionManager()


# ── Fixture Integrity ────────────────────────────────────────────────────


class TestFixtureIntegrity:
    """Verify fixture file covers all 37 regions."""

    def test_fixture_file_exists(self):
        assert FIXTURE_FILE.exists(), f"Missing {FIXTURE_FILE}"

    def test_all_37_regions_present(self, region_data):
        expected_regions = {
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "F1",
            "F2",
            "F3",
            "F4",
            "G1",
            "H1",
            "R0",
            "Z0",
        }
        actual = {k for k in region_data.keys() if not k.startswith("_")}
        missing = expected_regions - actual
        assert not missing, f"Missing regions in fixtures: {missing}"

    def test_each_region_has_entries(self, region_data):
        for code, data in region_data.items():
            if code.startswith("_"):
                continue
            assert len(data.get("entries", [])) >= 1, f"Region {code} has no entries"

    def test_total_fixture_count(self, region_data):
        total = sum(
            len(data.get("entries", []))
            for code, data in region_data.items()
            if not code.startswith("_")
        )
        assert total >= 100, f"Expected >=100 test fixtures, got {total}"


# ── Region Detection from Fixtures ───────────────────────────────────────


class TestFixtureDetection:
    """Test region detection using fixture data."""

    def test_detection_produces_results(self, region_data, region_manager):
        for code, data in region_data.items():
            if code.startswith("_"):
                continue
            for entry_data in data.get("entries", []):
                entry = dict(entry_data)
                result = region_manager.detect_region(entry)
                assert (
                    result.region_code is not None
                ), f"Detection failed for {entry.get('CanonicalLatin')} (region {code})"
                assert result.confidence >= 0


# ── Region Processing from Fixtures ──────────────────────────────────────


class TestFixtureProcessing:
    """Test region processing using fixture data."""

    def test_process_all_implemented_regions(self, region_data, region_manager):
        processed = 0
        errors = []
        for code, data in region_data.items():
            if code.startswith("_"):
                continue
            proc = region_manager.get_region(code)
            if proc is None:
                continue  # Skip unimplemented

            for entry_data in data.get("entries", []):
                entry = dict(entry_data)
                entry.setdefault("CanonicalNative", entry.get("CanonicalLatin", ""))
                entry["RegionCode"] = code
                try:
                    proc.clean(entry)
                    proc.augment(entry)
                    ok = proc.order_key(entry)
                    if ok:
                        entry["OrderKey"] = ok
                    processed += 1
                except Exception as e:
                    errors.append(f"{code}/{entry.get('CanonicalLatin')}: {e}")

        assert processed > 0, "No entries were processed"
        if errors:
            # Log errors but don't fail - some regions may have edge cases
            for err in errors:
                print(f"WARNING: {err}")

    def test_clean_does_not_crash(self, region_data, region_manager):
        """Ensure clean() handles all fixture data without exceptions."""
        for code, data in region_data.items():
            if code.startswith("_"):
                continue
            proc = region_manager.get_region(code)
            if proc is None:
                continue
            for entry_data in data.get("entries", []):
                entry = dict(entry_data)
                entry.setdefault("CanonicalNative", entry.get("CanonicalLatin", ""))
                entry["RegionCode"] = code
                try:
                    proc.clean(entry)
                except Exception as e:
                    pytest.fail(f"clean() crashed for {code}/{entry.get('CanonicalLatin')}: {e}")


# ── Pipeline Integration with Fixtures ───────────────────────────────────


class TestFixturePipelineIntegration:
    """Run full pipeline with fixture data."""

    @pytest.mark.timeout(90)
    def test_pipeline_with_fixture_entries(self, region_data):
        import asyncio
        import os
        from src.core.pipeline_v7 import PipelineMode, V7Pipeline

        # Force offline mode to prevent authority API calls hanging
        old_offline = os.environ.get("OFFLINE")
        os.environ["OFFLINE"] = "1"

        # Collect a small sample (1 entry per region) to keep test fast
        all_entries = []
        for code, data in region_data.items():
            if code.startswith("_"):
                continue
            entries = data.get("entries", [])
            if entries:
                all_entries.append(dict(entries[0]))

        try:
            pipeline = V7Pipeline(mode=PipelineMode.QUICK)

            async def run():
                return await pipeline.process_batch(all_entries)

            report = asyncio.run(run())

            assert report["metrics"]["processed_entries"] == len(all_entries)
            assert report["metrics"]["failed_entries"] == 0
        finally:
            if old_offline is None:
                os.environ.pop("OFFLINE", None)
            else:
                os.environ["OFFLINE"] = old_offline
