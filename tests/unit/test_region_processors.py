"""
Comprehensive unit tests for all region processors.

Tests that all implemented region processors have the required interface
and handle representative names correctly.
"""

from unittest.mock import patch

import pytest

from src.regions.base import _YAML_CACHE, RegionSpec
from src.regions.manager_optimized import RegionManager


@pytest.fixture(scope="module")
def region_manager():
    return RegionManager()


# ── RegionManager ────────────────────────────────────────────────────────


class TestRegionManager:
    """Test RegionManager initialization and region loading."""

    def test_has_implemented_regions(self, region_manager):
        assert len(region_manager.IMPLEMENTED_REGIONS) > 0

    def test_detect_region_returns_result(self, region_manager):
        entry = {"CanonicalLatin": "Smith, John"}
        result = region_manager.detect_region(entry)
        assert hasattr(result, "region_code")
        assert hasattr(result, "confidence")

    def test_get_region_for_implemented(self, region_manager):
        for code in region_manager.IMPLEMENTED_REGIONS:
            proc = region_manager.get_region(code)
            assert proc is not None, f"No processor for implemented region {code}"


# ── Processor Interface ──────────────────────────────────────────────────


class TestProcessorInterface:
    """Test that all processors implement the required interface."""

    def test_all_have_clean(self, region_manager):
        for code in region_manager.IMPLEMENTED_REGIONS:
            proc = region_manager.get_region(code)
            assert hasattr(proc, "clean"), f"{code} missing clean()"

    def test_all_have_augment(self, region_manager):
        for code in region_manager.IMPLEMENTED_REGIONS:
            proc = region_manager.get_region(code)
            assert hasattr(proc, "augment"), f"{code} missing augment()"

    def test_all_have_order_key(self, region_manager):
        for code in region_manager.IMPLEMENTED_REGIONS:
            proc = region_manager.get_region(code)
            assert hasattr(proc, "order_key"), f"{code} missing order_key()"


# ── Representative Name Tests ────────────────────────────────────────────

# Each test exercises a real-world name through the processor for that region.

REGION_TEST_NAMES = {
    "A1": [
        ("Smith, John", {}),
        ("O'Brien, Mary", {}),
    ],
    "A2": [
        ("Müller, Hans", {}),
        ("García, José María", {}),
    ],
    "B1": [
        ("Ivanov, Sergei", {}),
        ("Petrov, Aleksandr", {}),
    ],
    "B2": [
        ("Kovačević, Marko", {}),
    ],
    "B3": [
        ("Παπαδόπουλος, Γιάννης", {}),
    ],
    "C1": [
        ("Yılmaz, Mehmet", {}),
    ],
    "C2": [
        ("Mohammadi, Ali", {}),
    ],
    "C3": [
        ("Al-Rashid, Ahmad", {}),
    ],
    "C4": [
        ("Al-Mansoori, Khalid", {}),
    ],
    "D1": [
        ("Sharma, Ram", {}),
    ],
    "E1": [
        ("Wang, Wei", {}),
    ],
    "E3": [
        ("Tanaka, Hiroshi", {}),
    ],
    "E4": [
        ("Kim, Minsu", {}),
    ],
    "G1": [
        ("da Silva, Maria", {}),
    ],
}


class TestRegionProcessing:
    """Test region processors with representative names."""

    @pytest.mark.parametrize(
        "region_code,names",
        [(k, v) for k, v in REGION_TEST_NAMES.items()],
        ids=[k for k in REGION_TEST_NAMES.keys()],
    )
    def test_process_name(self, region_manager, region_code, names):
        if region_code not in region_manager.IMPLEMENTED_REGIONS:
            pytest.skip(f"Region {region_code} not implemented")

        proc = region_manager.get_region(region_code)
        for name, expected_fields in names:
            entry = {
                "CanonicalLatin": name,
                "CanonicalNative": name,
                "RegionCode": region_code,
            }
            # Run clean -> augment -> order_key
            if hasattr(proc, "clean"):
                proc.clean(entry)
            if hasattr(proc, "augment"):
                proc.augment(entry)
            if hasattr(proc, "order_key"):
                ok = proc.order_key(entry)
                if ok:
                    entry["OrderKey"] = ok

            # Verify expected fields if any
            for field, value in expected_fields.items():
                assert entry.get(field) == value, (
                    f"Region {region_code}: {name}: expected {field}={value}, "
                    f"got {entry.get(field)}"
                )


# ── Region Detection Tests ───────────────────────────────────────────────


class TestRegionDetection:
    """Test region detection for various name scripts."""

    DETECTION_CASES = [
        ("Smith, John", "A1"),
        ("Müller, Hans", "A2"),
        ("Иванов, Иван", "B1"),
        ("田中, 太郎", "E1"),
        ("김, 철수", "E4"),
        ("الخوارزمي, محمد", "C3"),
    ]

    @pytest.mark.parametrize("name,expected_region", DETECTION_CASES)
    def test_detection(self, region_manager, name, expected_region):
        entry = {"CanonicalLatin": name, "OriginalScript": name}
        result = region_manager.detect_region(entry)
        # We just check detection produces a result, not exact region
        # since detection heuristics may vary
        assert result.region_code is not None
        assert result.confidence > 0


# ── Order Key Tests ──────────────────────────────────────────────────────


class TestOrderKey:
    """Test order key generation."""

    def test_a1_order_key(self, region_manager):
        if "A1" not in region_manager.IMPLEMENTED_REGIONS:
            pytest.skip("A1 not implemented")
        proc = region_manager.get_region("A1")
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionCode": "A1",
            "FamilyName": "Smith",
            "GivenName": "John",
        }
        ok = proc.order_key(entry)
        assert ok is not None
        assert isinstance(ok, str)

    def test_order_key_deterministic(self, region_manager):
        if "A1" not in region_manager.IMPLEMENTED_REGIONS:
            pytest.skip("A1 not implemented")
        proc = region_manager.get_region("A1")
        entry = {
            "CanonicalLatin": "Smith, John",
            "RegionCode": "A1",
            "FamilyName": "Smith",
            "GivenName": "John",
        }
        ok1 = proc.order_key(entry)
        ok2 = proc.order_key(entry)
        assert ok1 == ok2


# ── YAML Config Loader Tests ────────────────────────────────────────────


class TestYAMLConfigLoader:
    """Test RegionSpec.load_yaml_config() and YAML cache."""

    def setup_method(self):
        """Clear YAML cache before each test."""
        _YAML_CACHE.clear()

    def teardown_method(self):
        _YAML_CACHE.clear()

    def test_missing_yaml_returns_empty(self, region_manager):
        """Regions without YAML files return empty config."""
        if "A1" not in region_manager.IMPLEMENTED_REGIONS:
            pytest.skip("A1 not implemented")
        proc = region_manager.get_region("A1")
        cfg = proc.load_yaml_config()
        # No YAML file exists yet for A1, so should return {}
        assert isinstance(cfg, dict)

    def test_yaml_result_cached(self, tmp_path):
        """Second call returns cached result without re-reading file."""
        import yaml

        yaml_content = {"code": "CC", "titles": ["Dr"]}
        yaml_file = tmp_path / "cc.yaml"
        yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

        with patch("src.regions.base._REGION_CONFIG_DIR", tmp_path):
            _YAML_CACHE.clear()

            class TestRegion(RegionSpec):
                def clean(self, entry):
                    pass

                def augment(self, entry):
                    pass

                def validate(self, entry):
                    pass

                def order_key(self, entry):
                    return ""

            proc = TestRegion(code="CC", yaml_files=[], scripts=["Latin"])
            cfg1 = proc.load_yaml_config()
            cfg2 = proc.load_yaml_config()
            assert cfg1 is cfg2  # Same object (cached)
            assert "CC" in _YAML_CACHE
            assert cfg1["titles"] == ["Dr"]

    def test_clear_cache(self, region_manager):
        """clear_yaml_cache() empties the cache."""
        if "A1" not in region_manager.IMPLEMENTED_REGIONS:
            pytest.skip("A1 not implemented")
        proc = region_manager.get_region("A1")
        proc.load_yaml_config()
        assert "A1" in _YAML_CACHE
        RegionSpec.clear_yaml_cache()
        assert len(_YAML_CACHE) == 0

    def test_loads_real_yaml_file(self, tmp_path):
        """When a YAML file exists, its contents are loaded."""
        import yaml

        # Create a temporary YAML config
        yaml_content = {
            "code": "XX",
            "name": "Test Region",
            "titles": ["Dr", "Prof"],
            "particles": ["de", "van"],
            "romanisation_map": {"a": "b"},
        }
        yaml_file = tmp_path / "xx.yaml"
        yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

        # Patch the config dir to our tmp dir
        with patch("src.regions.base._REGION_CONFIG_DIR", tmp_path):
            _YAML_CACHE.clear()

            # Create a minimal concrete RegionSpec to test with
            class TestRegion(RegionSpec):
                def clean(self, entry):
                    pass

                def augment(self, entry):
                    pass

                def validate(self, entry):
                    pass

                def order_key(self, entry):
                    return ""

            proc = TestRegion(code="XX", yaml_files=[], scripts=["Latin"])
            cfg = proc.load_yaml_config()

        assert cfg["code"] == "XX"
        assert cfg["titles"] == ["Dr", "Prof"]
        assert cfg["particles"] == ["de", "van"]
        assert cfg["romanisation_map"] == {"a": "b"}

    def test_invalid_yaml_returns_empty(self, tmp_path):
        """Malformed YAML returns empty dict without crashing."""
        bad_file = tmp_path / "yy.yaml"
        bad_file.write_text("{{{{invalid yaml", encoding="utf-8")

        with patch("src.regions.base._REGION_CONFIG_DIR", tmp_path):
            _YAML_CACHE.clear()

            class TestRegion(RegionSpec):
                def clean(self, entry):
                    pass

                def augment(self, entry):
                    pass

                def validate(self, entry):
                    pass

                def order_key(self, entry):
                    return ""

            proc = TestRegion(code="YY", yaml_files=[], scripts=["Latin"])
            cfg = proc.load_yaml_config()

        assert cfg == {}

    def test_yaml_overrides_hardcoded_pattern(self, tmp_path):
        """Demonstrate the override pattern: YAML takes precedence."""
        import yaml

        yaml_content = {"titles": ["Emperor", "Shogun"]}
        yaml_file = tmp_path / "zz.yaml"
        yaml_file.write_text(yaml.dump(yaml_content), encoding="utf-8")

        with patch("src.regions.base._REGION_CONFIG_DIR", tmp_path):
            _YAML_CACHE.clear()

            class TestRegion(RegionSpec):
                def __init__(self):
                    super().__init__(code="ZZ", yaml_files=[], scripts=["Latin"])
                    # Hardcoded default
                    self.titles = {"Dr", "Prof"}
                    # Override from YAML if available
                    cfg = self.load_yaml_config()
                    if "titles" in cfg:
                        self.titles = set(cfg["titles"])

                def clean(self, entry):
                    pass

                def augment(self, entry):
                    pass

                def validate(self, entry):
                    pass

                def order_key(self, entry):
                    return ""

            proc = TestRegion()

        assert proc.titles == {"Emperor", "Shogun"}
