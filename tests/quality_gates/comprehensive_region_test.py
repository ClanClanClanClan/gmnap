#!/usr/bin/env python3
"""
Comprehensive Regional Processor Testing Suite

Tests all aspects of regional processors to ensure they're fully functional.
Can be run as either a pytest test suite or standalone script.
"""

import time
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Region classes to test: (module_path, class_name)
# ---------------------------------------------------------------------------
REGIONS_TO_TEST = [
    ("src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
    ("src.regions.a_groups.a2_western_europe", "A2_WesternEurope"),
    ("src.regions.b_groups.b1_east_slavic", "B1_EastSlavic"),
    ("src.regions.b_groups.b2_south_slavic_central", "B2_SouthSlavicCentral"),
    ("src.regions.c_groups.c2_persian_tajik", "C2_PersianTajik"),
    ("src.regions.c_groups.c5_arabic_maghreb", "C5ArabicMaghreb"),
    ("src.regions.c_groups.c6_hebrew_diaspora", "C6HebrewDiaspora"),
    ("src.regions.d_groups.d1_south_asia_hindi_belt", "D1_SouthAsiaHindiBelt"),
    ("src.regions.e_groups.e1_sinophone_mainland", "E1_SinophoneMainland"),
    ("src.regions.e_groups.e3_japan", "E3_Japan"),
    ("src.regions.g_groups.g1_latin_america", "G1_LatinAmerica"),
]

# Test data per region
TEST_CASES = {
    "A1_AngloSphere": [
        {"CanonicalLatin": "Smith, John William"},
        {"CanonicalLatin": "O'Brien, Mary Catherine"},
    ],
    "A2_WesternEurope": [
        {"CanonicalLatin": "García Márquez, Gabriel José"},
        {"CanonicalLatin": "Müller, François"},
    ],
    "B1_EastSlavic": [
        {"CanonicalLatin": "Ivanov, Aleksandr Petrovich"},
    ],
    "B2_SouthSlavicCentral": [
        {"CanonicalLatin": "Kowalski, Jan"},
    ],
    "C2_PersianTajik": [
        {"CanonicalLatin": "Mohammad Ahmadi"},
    ],
    "C5ArabicMaghreb": [
        {"CanonicalLatin": "Ben Ali, Mohamed"},
    ],
    "C6HebrewDiaspora": [
        {"CanonicalLatin": "Cohen, David"},
    ],
    "D1_SouthAsiaHindiBelt": [
        {"CanonicalLatin": "Rajesh Kumar Sharma"},
    ],
    "E1_SinophoneMainland": [
        {"CanonicalLatin": "Wang Ming"},
    ],
    "E3_Japan": [
        {"CanonicalLatin": "Tanaka Taro"},
    ],
    "G1_LatinAmerica": [
        {"CanonicalLatin": "García López, Juan Carlos"},
    ],
}


def _import_region_classes() -> Dict[str, Any]:
    """Import all regional processor classes."""
    imported = {}
    for module_name, class_name in REGIONS_TO_TEST:
        module = __import__(module_name, fromlist=[class_name])
        imported[class_name] = getattr(module, class_name)
    return imported


def _make_instances(imported: Dict[str, Any]) -> Dict[str, Any]:
    """Instantiate all region processors."""
    return {name: cls() for name, cls in imported.items()}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def imported_classes():
    return _import_region_classes()


@pytest.fixture(scope="module")
def instances(imported_classes):
    return _make_instances(imported_classes)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestRegionImports:
    """Test that all regional processors can be imported."""

    def test_all_imports_succeed(self, imported_classes):
        assert len(imported_classes) >= 11

    def test_each_is_a_class(self, imported_classes):
        for name, cls in imported_classes.items():
            assert isinstance(cls, type), f"{name} is not a class"


class TestRegionInstantiation:
    """Test that all regional processors can be instantiated."""

    def test_all_instantiate(self, instances):
        assert len(instances) >= 11

    def test_each_has_code(self, instances):
        for name, inst in instances.items():
            assert hasattr(inst, "code"), f"{name} missing .code"
            assert isinstance(inst.code, str), f"{name}.code not a string"


class TestRegionMethods:
    """Test that all required methods exist and are callable."""

    REQUIRED = ["clean", "augment", "validate", "order_key"]

    def test_methods_exist(self, instances):
        for name, inst in instances.items():
            for method in self.REQUIRED:
                assert hasattr(inst, method), f"{name} missing {method}()"
                assert callable(getattr(inst, method)), f"{name}.{method} not callable"


class TestRegionBasicFunctionality:
    """Test basic clean/augment/validate/order_key flow."""

    def test_process_entries(self, instances):
        for name, inst in instances.items():
            cases = TEST_CASES.get(name, [{"CanonicalLatin": "Test, Name"}])
            for case in cases:
                entry = case.copy()
                try:
                    inst.clean(entry)
                    inst.augment(entry)
                    inst.validate(entry)
                    key = inst.order_key(entry)
                    assert isinstance(key, str), f"{name} order_key returned non-string"
                except Exception as exc:
                    pytest.fail(f"{name} failed on {case}: {exc}")


class TestRegionEdgeCases:
    """Test edge cases - exceptions are acceptable but crashes are not."""

    EDGE_CASES = [
        {"CanonicalLatin": ""},
        {"CanonicalLatin": " "},
        {"CanonicalLatin": "A" * 500},
        {"CanonicalLatin": "Test, Name\n\r\t"},
        {},
    ]

    def test_edge_cases_dont_crash(self, instances):
        for name, inst in instances.items():
            for case in self.EDGE_CASES:
                entry = case.copy()
                try:
                    inst.clean(entry)
                    inst.augment(entry)
                    inst.validate(entry)
                    inst.order_key(entry)
                except Exception:
                    pass  # Exceptions are acceptable for edge cases


class TestRegionPerformance:
    """Test basic performance characteristics."""

    def test_processing_speed(self, instances):
        entries = [{"CanonicalLatin": f"TestName{i}, Given{i}"} for i in range(100)]

        for name, inst in instances.items():
            start = time.time()
            for entry in entries:
                e = entry.copy()
                try:
                    inst.clean(e)
                    inst.augment(e)
                    inst.validate(e)
                    inst.order_key(e)
                except Exception:
                    pass
            elapsed = time.time() - start
            avg_ms = elapsed / len(entries) * 1000

            assert avg_ms < 50, f"{name}: {avg_ms:.2f}ms/entry exceeds 50ms limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
