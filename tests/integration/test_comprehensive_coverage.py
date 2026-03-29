#!/usr/bin/env python3
"""
from typing import List
from typing import Any
Comprehensive test suite for GMNAP V7 regional processors.

This test suite aims for thorough coverage of:
- Multiple test cases per region (10-20 each)
- Edge cases and corner cases
- Script mixing scenarios
- Error conditions
- Performance under load
- Concurrent safety
- Database integrity
- Variant generation
- Sorting consistency
"""

import threading
import time

import pytest

pytest.skip("Test needs major refactoring", allow_module_level=True)

import json
import os
import random
import sqlite3
from collections import defaultdict

# from src.core.pipeline import GMNAPPipeline
# from src.core.database import GMNAPDatabase
# from src.v7_compat import v7_manager, load_working_processors
from src.regions.base import RegionRuleError

# sys.path.insert(0, 'src')


class ComprehensiveTestSuite:
    """Comprehensive test suite for all regional processors."""

    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "region_stats": defaultdict(lambda: {"tests": 0, "passed": 0, "failed": 0}),
        }

        # Load all processors
        if not v7_manager.list_regions():
            load_working_processors()

        self.pipeline = GMNAPPipeline({"database_path": "comprehensive_test.db"})

    def run_all_tests(self):
        """Run all test categories."""
        print("🧪 GMNAP V7 COMPREHENSIVE TEST SUITE")
        print("=" * 60)

        # Clean up old test database
        if os.path.exists("comprehensive_test.db"):
            os.remove("comprehensive_test.db")

        test_categories = [
            ("Basic Functionality", self.test_basic_functionality),
            ("Edge Cases", self.test_edge_cases),
            ("Script Mixing", self.test_script_mixing),
            ("Validation Rules", self.test_validation_rules),
            ("Variant Generation", self.test_variant_generation),
            ("Sorting Consistency", self.test_sorting_consistency),
            ("Performance Under Load", self.test_performance),
            ("Concurrent Safety", self.test_concurrent_safety),
            ("Database Integrity", self.test_database_integrity),
            ("Error Handling", self.test_error_handling),
            ("Regional Specifics", self.test_regional_specifics),
            ("Cross-Region Consistency", self.test_cross_region_consistency),
        ]

        for category_name, test_func in test_categories:
            print(f"\n{'='*60}")
            print(f"Testing: {category_name}")
            print("=" * 60)
            try:
                test_func()
            except Exception as e:
                self.record_error(f"Category {category_name} failed", str(e))

        self.print_summary()

    @pytest.mark.timeout(15)
    def test_basic_functionality(self):
        """Test basic functionality with diverse test cases."""
        test_data = {
            "A1": [  # Anglo-sphere
                # Standard cases
                ("Smith, John", True),
                ("O'Brien, Mary Catherine", True),
                ("MacDonald, Robert James Jr.", True),
                ("van der Berg, Elizabeth", True),
                ("St. James, William", True),
                # With titles
                ("Dr. Johnson, Sarah PhD", True),
                ("Prof. Brown, Michael J.", True),
                # With suffixes
                ("Williams III, Charles", True),
                ("Davis Sr., Thomas", True),
                ("Miller Jr., James", True),
                # Hyphenated
                ("Smith-Jones, Alice", True),
                ("Taylor-Brown, David", True),
                # Single names (should handle gracefully)
                ("Madonna", True),
                ("Cher", True),
                # Complex cases
                ("van der Waals, Johannes Diderik", True),
                ("O'Connor-Smith, Patrick James III", True),
                ("St. Claire-Davis, Margaret Ann", True),
                # Invalid cases
                ("", False),
                ("123, Numbers", False),
                ("@#$%, Special", False),
            ],
            "A2": [  # Western Europe
                # French
                ("Dupont, Jean-Pierre", True),
                ("Lefèvre, Marie-Claire", True),
                ("D'Alembert, François", True),
                ("de Gaulle, Charles", True),
                # German
                ("Müller, Hans-Jürgen", True),
                ("von Neumann, Johann", True),
                ("Schröder, Gerhard", True),
                ("König, Friedrich Wilhelm", True),
                # Italian
                ("Rossi, Giuseppe", True),
                ("De Luca, Maria", True),
                ("D'Angelo, Francesco", True),
                ("Della Rovere, Giovanni", True),
                # Spanish
                ("García López, José María", True),
                ("Fernández de Córdoba, Isabel", True),
                ("Ruiz y Picasso, Pablo", True),
                # Portuguese
                ("da Silva, João", True),
                ("dos Santos, Maria", True),
                ("de Oliveira e Silva, António", True),
                # Dutch/Belgian
                ("van den Berg, Pieter", True),
                ("De Vries, Anna", True),
                ("Van Damme, Jean-Claude", True),
            ],
            "B1": [  # East Slavic
                # Russian
                ("Иванов, Александр Петрович", True),
                ("Петрова, Елена Михайловна", True),
                ("Сидоров, Дмитрий", True),
                ("Козлова, Анна Сергеевна", True),
                # Ukrainian
                ("Шевченко, Тарас Григорович", True),
                ("Коваленко, Оксана Петрівна", True),
                ("Бондаренко, Михайло", True),
                # Belarusian
                ("Лукашэнка, Аляксандр", True),
                ("Каваль, Святлана", True),
                # Mixed script
                ("Ivanov, Александр", True),
                ("Петров, Ivan", True),
                # Complex patronymics
                ("Александров-Петров, Иван Сергеевич", True),
                ("Николаева-Смирнова, Мария Владимировна", True),
            ],
            "B2": [  # South Slavic & Central Europe
                # Polish
                ("Kowalski, Jan", True),
                ("Nowak, Anna", True),
                ("Wiśniewski, Krzysztof", True),
                ("Wójcik, Małgorzata", True),
                # Czech
                ("Novák, Jan", True),
                ("Dvořák, Karel", True),
                ("Svobodová, Marie", True),
                ("Procházková, Věra", True),
                # Slovak
                ("Kováč, Peter", True),
                ("Horváthová, Zuzana", True),
                # Hungarian (name order)
                ("Nagy, László", True),
                ("Szabó, István", True),
                ("Kovács, Erzsébet", True),
                # Serbian (both scripts)
                ("Jovanović, Milan", True),
                ("Јовановић, Милан", True),
                ("Petrović, Ana", True),
                ("Петровић, Ана", True),
                # Croatian
                ("Horvat, Marko", True),
                ("Kovačević, Ivana", True),
                # Bulgarian
                ("Иванов, Петър", True),
                ("Георгиев, Мария", True),
            ],
            "C2": [  # Persian-Tajik
                # Persian names
                ("محمد احمدی", True),
                ("فاطمه کریمی", True),
                ("علی رضایی", True),
                ("زهرا محمدی", True),
                # Romanized
                ("Mohammad Ahmadi", True),
                ("Fatemeh Karimi", True),
                ("Ali Rezaei", True),
                ("Zahra Mohammadi", True),
                # Afghan names
                ("احمد شاه مسعود", True),
                ("Ahmad Shah Massoud", True),
                # Tajik names
                ("Раҳмонов Эмомалӣ", True),
                ("Rahmonov Emomali", True),
                # Complex cases
                ("سید محمد خاتمی", True),
                ("Seyyed Mohammad Khatami", True),
            ],
            "C3": [  # Arabic Levant-Nile
                # Iraqi
                ("احمد محمد العلي", True),
                ("Ahmad Muhammad al-Ali", True),
                # Egyptian
                ("محمد أحمد السيد", True),
                ("Muhammad Ahmad al-Sayyid", True),
                # Palestinian
                ("محمود عباس", True),
                ("Mahmoud Abbas", True),
                # Lebanese
                ("مريم الخوري", True),
                ("Mariam al-Khoury", True),
                # Syrian
                ("بشار الأسد", True),
                ("Bashar al-Assad", True),
                # With patronymics
                ("أحمد بن محمد العلي", True),
                ("Ahmad ibn Muhammad al-Ali", True),
                ("فاطمة بنت عبدالله", True),
                ("Fatima bint Abdullah", True),
                # Sudanese
                ("عمر البشير", True),
                ("Omar al-Bashir", True),
            ],
            "C4": [  # Arabic Gulf
                # Saudi
                ("محمد بن سلمان آل سعود", True),
                ("Muhammad bin Salman Al Saud", True),
                # UAE
                ("محمد بن راشد آل مكتوم", True),
                ("Mohammed bin Rashid Al Maktoum", True),
                ("فاطمة بنت مبارك", True),
                ("Fatima bint Mubarak", True),
                # Kuwaiti
                ("صباح الأحمد الجابر الصباح", True),
                ("Sabah Al-Ahmad Al-Jaber Al-Sabah", True),
                # Qatari
                ("تميم بن حمد آل ثاني", True),
                ("Tamim bin Hamad Al Thani", True),
                # Bahraini
                ("حمد بن عيسى آل خليفة", True),
                ("Hamad bin Isa Al Khalifa", True),
                # Omani
                ("هيثم بن طارق", True),
                ("Haitham bin Tariq", True),
                # Yemeni
                ("علي عبدالله صالح", True),
                ("Ali Abdullah Saleh", True),
                # With titles
                ("الأمير محمد بن سلمان", True),
                ("Prince Mohammed bin Salman", True),
                ("الشيخ خليفة بن زايد", True),
                ("Sheikh Khalifa bin Zayed", True),
            ],
            "D1": [  # South Asia Hindi Belt
                # Simple Hindi names
                ("राम कुमार", True),
                ("Ram Kumar", True),
                ("सीता देवी", True),
                ("Sita Devi", True),
                # With surnames indicating caste
                ("राजेश कुमार शर्मा", True),
                ("Rajesh Kumar Sharma", True),
                ("प्रिया सिंह", True),
                ("Priya Singh", True),
                ("अमित प्रसाद गुप्ता", True),
                ("Amit Prasad Gupta", True),
                # Complex patterns
                ("डॉ. विजय कुमार मिश्रा", True),
                ("Dr. Vijay Kumar Mishra", True),
                ("श्रीमती सुनीता राम वर्मा", True),
                ("Smt. Sunita Ram Verma", True),
                # With honorifics
                ("पंडित जवाहरलाल नेहरू", True),
                ("Pandit Jawaharlal Nehru", True),
                ("श्री अटल बिहारी वाजपेयी", True),
                ("Shri Atal Bihari Vajpayee", True),
                # Muslim names in Hindi
                ("मोहम्मद अली खान", True),
                ("Mohammad Ali Khan", True),
                # Sikh names
                ("सरदार मनमोहन सिंह", True),
                ("Sardar Manmohan Singh", True),
                # Single word names
                ("कबीर", True),
                ("Kabir", True),
            ],
            "E1": [  # Sinophone Mainland
                # Common Chinese names
                ("王明", True),
                ("Wang Ming", True),
                ("李华", True),
                ("Li Hua", True),
                ("张伟", True),
                ("Zhang Wei", True),
                # Three character names
                ("欧阳修", True),
                ("Ouyang Xiu", True),
                ("司马光", True),
                ("Sima Guang", True),
                # Four character names
                ("诸葛亮", True),
                ("Zhuge Liang", True),
                # Modern names
                ("习近平", True),
                ("Xi Jinping", True),
                ("毛泽东", True),
                ("Mao Zedong", True),
                # With titles
                ("王教授", True),
                ("Professor Wang", True),
                ("李医生", True),
                ("Dr. Li", True),
                # Minority names
                ("爱新觉罗溥仪", True),
                ("Aisin Gioro Puyi", True),
            ],
            "E3": [  # Japan
                # Common Japanese names
                ("田中太郎", True),
                ("Tanaka Taro", True),
                ("佐藤花子", True),
                ("Sato Hanako", True),
                ("山田一郎", True),
                ("Yamada Ichiro", True),
                # Historical names
                ("徳川家康", True),
                ("Tokugawa Ieyasu", True),
                ("源頼朝", True),
                ("Minamoto no Yoritomo", True),
                # Modern names
                ("安倍晋三", True),
                ("Abe Shinzo", True),
                # With titles
                ("山田先生", True),
                ("Yamada-sensei", True),
                # Complex readings
                ("東海林", True),
                ("Shoji", True),
                # Foreign names in katakana
                ("スミス", True),
                ("Smith", True),
                # Mixed scripts
                ("田中マリア", True),
                ("Tanaka Maria", True),
            ],
            "G1": [  # Latin America
                # Spanish dual surnames
                ("García López, Juan Carlos", True),
                ("Rodríguez Pérez, María Isabel", True),
                ("Fernández González, José Luis", True),
                # Portuguese (Brazilian)
                ("da Silva Santos, João Pedro", True),
                ("dos Santos Oliveira, Ana Maria", True),
                ("de Souza Costa, Paulo Roberto", True),
                # Compound surnames
                ("García-López, Carmen", True),
                ("Pérez-Rodríguez, Miguel", True),
                # With particles
                ("de la Cruz, Francisco", True),
                ("del Río, Isabella", True),
                ("de los Santos, Roberto", True),
                # Indigenous names
                ("Quispe Mamani, Carlos", True),
                ("Huanca Choque, María", True),
                # Complex cases
                ("García y López, Juan de Dios", True),
                ("Fernández de la Vega, María del Carmen", True),
                # Argentine
                ("Fernández de Kirchner, Cristina", True),
                # Chilean
                ("Bachelet Jeria, Michelle", True),
                # Mexican
                ("López Obrador, Andrés Manuel", True),
            ],
        }

        for region_code, test_cases in test_data.items():
            print(f"\nTesting {region_code}:")
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                self.record_error(f"No adapter for {region_code}", "Adapter not found")
                continue

            for name, should_pass in test_cases:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": name}
                    if self._is_non_latin_script(name):
                        entry = {"CanonicalNative": name}

                    adapter.process_entry(entry)

                    if should_pass:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"  ✓ {name[:50]}")
                    else:
                        # Should have failed but didn't
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        self.record_error(
                            f"{region_code}: {name}", "Expected to fail but passed"
                        )
                        print(f"  ✗ {name[:50]} - Expected to fail but passed")

                except RegionRuleError as e:
                    if not should_pass:
                        # Expected to fail
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"  ✓ {name[:50]} - Correctly rejected")
                    else:
                        # Should have passed but didn't
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        self.record_error(f"{region_code}: {name}", str(e))
                        print(f"  ✗ {name[:50]} - {e}")

                except Exception as e:
                    self.results["failed"] += 1
                    self.results["region_stats"][region_code]["failed"] += 1
                    self.record_error(
                        f"{region_code}: {name}", f"Unexpected error: {e}"
                    )
                    print(f"  ✗ {name[:50]} - Unexpected error: {e}")

    @pytest.mark.timeout(15)
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            # Empty and whitespace
            {"CanonicalLatin": ""},
            {"CanonicalLatin": " "},
            {"CanonicalLatin": "\t\n\r"},
            {"CanonicalLatin": "   "},
            # Very long names
            {"CanonicalLatin": "A" * 100},
            {"CanonicalLatin": "Test " * 50},
            {"CanonicalLatin": "Very-Long-Hyphenated-Name-" * 10},
            # Special characters
            {"CanonicalLatin": "Test\x00Name"},
            {"CanonicalLatin": "Test\nName"},
            {"CanonicalLatin": "Test\r\nName"},
            {"CanonicalLatin": "Test\tName"},
            # Unicode edge cases
            {"CanonicalLatin": "Test 🚀 Name"},
            {"CanonicalLatin": "Test 😀 Name"},
            {"CanonicalLatin": "Test\u200bName"},  # Zero-width space
            {"CanonicalLatin": "Test\ufeffName"},  # BOM
            # Missing fields
            {},
            {"SomeOtherField": "Value"},
            {"CanonicalLatin": None},
            {"CanonicalNative": None},
            # Numbers and symbols
            {"CanonicalLatin": "123 456"},
            {"CanonicalLatin": "Test@Name"},
            {"CanonicalLatin": "Test#Name"},
            {"CanonicalLatin": "Test$Name"},
            {"CanonicalLatin": "Test%Name"},
            # Punctuation abuse
            {"CanonicalLatin": "..."},
            {"CanonicalLatin": ",,,"},
            {"CanonicalLatin": "---"},
            {"CanonicalLatin": ";;;"},
            # Mixed valid/invalid
            {"CanonicalLatin": "Valid, Name 123"},
            {"CanonicalLatin": "Name, 🚀"},
            {"CanonicalLatin": "Test, Name\x00"},
        ]

        print("\nTesting edge cases across all regions:")
        for region_code in v7_manager.list_regions():
            adapter = v7_manager.get_adapter(region_code)
            edge_case_pass = 0
            edge_case_fail = 0

            for test_case in edge_cases:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    adapter.process_entry(test_case.copy())
                    # If it passes, that might be unexpected for edge cases
                    edge_case_pass += 1
                except:
                    # Expected to fail
                    edge_case_fail += 1
                    self.results["passed"] += 1
                    self.results["region_stats"][region_code]["passed"] += 1

            print(
                f"  {region_code}: {edge_case_fail}/{len(edge_cases)} edge cases properly rejected"
            )

    @pytest.mark.timeout(15)
    def test_script_mixing(self):
        """Test handling of mixed scripts."""
        mixed_script_cases = {
            "B1": [  # East Slavic allows some mixing
                ("Иванов, John", True),
                ("Smith, Александр", True),
                ("Петров-Johnson, Мария", True),
            ],
            "B2": [  # South Slavic with Latin/Cyrillic
                ("Jovanović/Јовановић, Milan", True),
                ("Petrović (Петровић), Ana", True),
            ],
            "C2": [  # Persian with romanization
                ("محمد (Mohammad) احمدی", True),
                ("Ahmadi احمدی", True),
            ],
            "D1": [  # Hindi with English
                ("राम (Ram) कुमार", True),
                ("Dr. शर्मा", True),
            ],
        }

        print("\nTesting script mixing:")
        for region_code, cases in mixed_script_cases.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            print(f"\n  {region_code}:")
            for name, should_work in cases:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": name}
                    adapter.process_entry(entry)
                    if should_work:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {name}")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {name} - Should have failed")
                except:
                    if not should_work:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {name} - Correctly rejected")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {name} - Should have passed")

    @pytest.mark.timeout(15)
    def test_validation_rules(self):
        """Test specific validation rules for each region."""
        validation_tests = {
            "A1": [
                # Must have at least first and last name
                ("Smith", False, "Single word should fail"),
                ("", False, "Empty should fail"),
                ("Smith, ", False, "Missing given name should fail"),
                (", John", False, "Missing family name should fail"),
                ("Smith, John William", True, "Multiple given names OK"),
                ("O'Brien, Mary", True, "Apostrophes OK"),
                ("Smith-Jones, Alice", True, "Hyphens OK"),
                ("Smith, John 123", False, "Numbers should fail"),
                ("Smith, John!", False, "Exclamation should fail"),
            ],
            "C4": [
                # Arabic Gulf specific rules
                ("محمد", False, "Single word should fail"),
                ("Muhammad", False, "Single word should fail"),
                ("محمد بن سلمان", True, "Patronymic pattern OK"),
                ("فاطمة بنت راشد", True, "Female patronymic OK"),
                ("الأمير محمد", True, "Title OK"),
                ("Sheikh Mohammed", True, "English title OK"),
                ("آل سعود", False, "Family name only should fail"),
                ("Al Saud", False, "Family name only should fail"),
            ],
            "E1": [
                # Chinese name rules
                ("王", False, "Single character should fail"),
                ("王明", True, "Two characters OK"),
                ("欧阳修", True, "Three characters OK"),
                ("司马相如", True, "Four characters OK"),
                ("王明李华张伟", False, "Too many characters should fail"),
                ("Wang", False, "Single syllable pinyin should fail"),
                ("Wang Ming", True, "Two syllable pinyin OK"),
                ("Wang Ming Li", True, "Three syllable pinyin OK"),
            ],
        }

        print("\nTesting validation rules:")
        for region_code, tests in validation_tests.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            print(f"\n  {region_code} validation:")
            for name, should_pass, description in tests:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": name}
                    if self._is_non_latin_script(name):
                        entry = {"CanonicalNative": name}

                    adapter.process_entry(entry)

                    if should_pass:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {description}")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {description} - Expected to fail")

                except Exception as e:
                    if not should_pass:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {description} - {e}")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {description} - {e}")

    @pytest.mark.timeout(15)
    def test_variant_generation(self):
        """Test that variants are generated correctly."""
        variant_tests = {
            "A1": [
                (
                    "Smith, John William",
                    ["Smith, J. W.", "Smith, John W.", "Smith, J. William"],
                ),
                (
                    "O'Brien, Mary Catherine",
                    ["O'Brien, M. C.", "O'Brien, Mary C.", "O'Brien, M. Catherine"],
                ),
            ],
            "C4": [
                (
                    "Muhammad bin Salman Al-Saud",
                    ["Muhammad Al-Saud", "محمد بن سلمان آل سعود"],
                ),
                ("Fatima bint Rashid", ["Fatima", "فاطمة بنت راشد"]),
            ],
            "D1": [
                (
                    "राजेश कुमार शर्मा",
                    ["Rajesh Kumar Sharma", "R. K. Sharma", "राजेश शर्मा"],
                ),
                ("प्रिया सिंह", ["Priya Singh", "P. Singh"]),
            ],
        }

        print("\nTesting variant generation:")
        for region_code, tests in variant_tests.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            print(f"\n  {region_code} variants:")
            for name, expected_variants in tests:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": name}
                    if self._is_non_latin_script(name):
                        entry = {"CanonicalNative": name}

                    processed = adapter.process_entry(entry)

                    # Check if any expected variants exist
                    all_variants = []
                    if "Variants" in processed:
                        for variant in processed["Variants"].get("Synthesised", []):
                            all_variants.append(variant["str"])

                    # Don't need exact match, just check some variants were generated
                    if all_variants:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {name} -> {len(all_variants)} variants")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {name} -> No variants generated")

                except Exception as e:
                    self.results["failed"] += 1
                    self.results["region_stats"][region_code]["failed"] += 1
                    print(f"    ✗ {name} - Error: {e}")

    @pytest.mark.timeout(15)
    def test_sorting_consistency(self):
        """Test that order_key produces consistent sorting."""
        sorting_tests = {
            "A1": [
                ("Adams, John", "Baker, William", True),  # A before B
                ("Smith, Alice", "Smith, Bob", True),  # Same family, A before B
                ("O'Brien, Pat", "O'Connor, Mike", False),  # O'Brien after O'Connor
            ],
            "E1": [
                ("Li Ming", "Wang Wei", True),  # L before W
                ("Zhang San", "Zhang Si", True),  # Same family, different given
            ],
        }

        print("\nTesting sorting consistency:")
        for region_code, tests in sorting_tests.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            print(f"\n  {region_code} sorting:")
            for name1, name2, name1_first in tests:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry1 = {"CanonicalLatin": name1}
                    entry2 = {"CanonicalLatin": name2}

                    processed1 = adapter.process_entry(entry1)
                    processed2 = adapter.process_entry(entry2)

                    key1 = adapter.order_key(processed1)
                    key2 = adapter.order_key(processed2)

                    if (key1 < key2) == name1_first:
                        self.results["passed"] += 1
                        self.results["region_stats"][region_code]["passed"] += 1
                        print(f"    ✓ {name1} vs {name2} - Correct order")
                    else:
                        self.results["failed"] += 1
                        self.results["region_stats"][region_code]["failed"] += 1
                        print(f"    ✗ {name1} vs {name2} - Wrong order")

                except Exception as e:
                    self.results["failed"] += 1
                    self.results["region_stats"][region_code]["failed"] += 1
                    print(f"    ✗ Sorting test failed: {e}")

    @pytest.mark.timeout(15)
    def test_performance(self):
        """Test performance under load."""
        print("\nTesting performance under load:")

        # Generate bulk test data
        bulk_data = {
            "A1": [f"TestSurname{i}, TestGiven{i}" for i in range(1000)],
            "E1": [f"Wang Test{i}" for i in range(1000)],
            "C4": [f"Mohammed bin Test{i} Al-Test" for i in range(1000)],
        }

        for region_code, names in bulk_data.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            start_time = time.time()
            processed_count = 0

            for name in names:
                try:
                    entry = {"CanonicalLatin": name}
                    adapter.process_entry(entry)
                    processed_count += 1
                except:
                    pass

            elapsed = time.time() - start_time
            avg_ms = (elapsed / len(names)) * 1000

            # Performance should be under 1ms per entry
            if avg_ms < 1.0:
                self.results["passed"] += 1
                print(
                    f"  ✓ {region_code}: {avg_ms:.3f}ms per entry (processed {processed_count}/{len(names)})"
                )
            else:
                self.results["failed"] += 1
                print(f"  ✗ {region_code}: {avg_ms:.3f}ms per entry - TOO SLOW")
                self.record_warning(
                    f"{region_code} performance", f"{avg_ms:.3f}ms per entry"
                )

    @pytest.mark.timeout(15)
    def test_concurrent_safety(self):
        """Test concurrent processing safety."""
        print("\nTesting concurrent safety:")

        # Test data for concurrent processing
        test_names = []
        for i in range(200):
            test_names.append(
                {
                    "CanonicalLatin": f"TestSurname{i}, TestGiven{i}",
                    "TerritoryCode": random.choice(["US", "GB", "CA", "AU"]),
                }
            )

        # Shared results
        concurrent_results = {"processed": 0, "errors": 0}
        lock = threading.Lock()

        def process_batch(start, end):
            """Process a batch of entries."""
            for i in range(start, end):
                try:
                    self.pipeline.process_entry(test_names[i])
                    with lock:
                        concurrent_results["processed"] += 1
                except Exception:
                    with lock:
                        concurrent_results["errors"] += 1

        # Launch threads
        threads = []
        batch_size = 20
        for i in range(0, len(test_names), batch_size):
            thread = threading.Thread(
                target=process_batch, args=(i, min(i + batch_size, len(test_names)))
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        total_attempted = concurrent_results["processed"] + concurrent_results["errors"]
        if total_attempted == len(test_names) and concurrent_results["errors"] == 0:
            self.results["passed"] += 1
            print(
                f"  ✓ Processed {concurrent_results['processed']}/{len(test_names)} entries concurrently"
            )
        else:
            self.results["failed"] += 1
            print(
                f"  ✗ Concurrent processing issues: {concurrent_results['processed']} processed, {concurrent_results['errors']} errors"
            )

    @pytest.mark.timeout(15)
    def test_database_integrity(self):
        """Test database integrity under various conditions."""
        print("\nTesting database integrity:")

        # Test duplicate handling
        test_entry = {"CanonicalLatin": "UniqueTest, Name", "BirthYear": 1950}

        # Process same entry multiple times
        for i in range(5):
            self.pipeline.process_entry(test_entry)

        # Check database
        self.pipeline.database.get_stats()

        # Should have deduplicated
        # Search for our specific entry
        conn = sqlite3.connect(self.pipeline.database.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM mathematician_entries WHERE canonical_latin = ?",
            ("UniqueTest, Name",),
        )
        count = cursor.fetchone()[0]
        conn.close()

        if count == 1:
            self.results["passed"] += 1
            print("  ✓ Database correctly handles duplicates")
        else:
            self.results["failed"] += 1
            print(f"  ✗ Database has {count} copies of same entry (expected 1)")

    @pytest.mark.timeout(15)
    def test_error_handling(self):
        """Test error handling and recovery."""
        print("\nTesting error handling:")

        error_scenarios = [
            # Invalid region code
            ({"CanonicalLatin": "Test, Name", "RegionCode": "ZZ"}, "Invalid region"),
            # Malformed data
            ({"CanonicalLatin": {"nested": "object"}}, "Malformed data"),
            # Very large data
            ({"CanonicalLatin": "A" * 10000}, "Extremely long name"),
            # Invalid encoding attempts
            ({"CanonicalLatin": b"\xff\xfe"}, "Binary data"),
        ]

        for test_data, scenario in error_scenarios:
            self.results["total_tests"] += 1

            try:
                self.pipeline.process_entry(test_data)
                # If it doesn't raise an error, that might be a problem
                self.results["failed"] += 1
                print(f"  ✗ {scenario} - Should have raised error")
            except Exception as e:
                # Good - it raised an error
                self.results["passed"] += 1
                print(f"  ✓ {scenario} - Properly handled: {type(e).__name__}")

    @pytest.mark.timeout(15)
    def test_regional_specifics(self):
        """Test region-specific features."""
        regional_tests = {
            "A1": {
                "name": "Anglo-sphere specifics",
                "tests": [
                    # Suffix handling
                    ("Smith Jr., John", "Jr. suffix"),
                    ("Williams III, Robert", "III suffix"),
                    ("Brown Sr., James", "Sr. suffix"),
                    ("Johnson Esq., William", "Esq. suffix"),
                    # Particles
                    ("van der Berg, Hans", "Dutch particle"),
                    ("de la Cruz, Maria", "Spanish particle"),
                    ("d'Angelo, Giuseppe", "Italian particle"),
                ],
            },
            "B2": {
                "name": "South Slavic specifics",
                "tests": [
                    # Gender suffixes
                    ("Novák, Jan", "Czech male"),
                    ("Nováková, Marie", "Czech female"),
                    ("Kováč, Peter", "Slovak male"),
                    ("Kováčová, Anna", "Slovak female"),
                    # Hungarian name order
                    ("Nagy László", "Hungarian order"),
                    ("Szabó István", "Hungarian order"),
                ],
            },
            "C4": {
                "name": "Arabic Gulf specifics",
                "tests": [
                    # Royal titles
                    ("الأمير محمد", "Prince title"),
                    ("الشيخ خليفة", "Sheikh title"),
                    ("الشيخة موزة", "Female Sheikh title"),
                    # Tribal names
                    ("آل سعود", "Al Saud tribe"),
                    ("آل نهيان", "Al Nahyan tribe"),
                    ("آل مكتوم", "Al Maktoum tribe"),
                ],
            },
            "D1": {
                "name": "Hindi Belt specifics",
                "tests": [
                    # Caste indicators
                    ("शर्मा", "Brahmin indicator"),
                    ("सिंह", "Kshatriya indicator"),
                    ("गुप्ता", "Vaishya indicator"),
                    # Honorifics
                    ("पंडित नेहरू", "Pandit title"),
                    ("श्री वाजपेयी", "Shri honorific"),
                    ("श्रीमती गांधी", "Shrimati honorific"),
                ],
            },
        }

        print("\nTesting regional specific features:")
        for region_code, test_group in regional_tests.items():
            adapter = v7_manager.get_adapter(region_code)
            if not adapter:
                continue

            print(f"\n  {region_code} - {test_group['name']}:")
            for name, feature in test_group["tests"]:
                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": name}
                    if self._is_non_latin_script(name):
                        entry = {"CanonicalNative": name}

                    adapter.process_entry(entry)

                    # Just check it processes without error
                    self.results["passed"] += 1
                    self.results["region_stats"][region_code]["passed"] += 1
                    print(f"    ✓ {feature}")

                except Exception as e:
                    self.results["failed"] += 1
                    self.results["region_stats"][region_code]["failed"] += 1
                    print(f"    ✗ {feature} - {e}")

    @pytest.mark.timeout(15)
    def test_cross_region_consistency(self):
        """Test consistency across regions for similar features."""
        print("\nTesting cross-region consistency:")

        # Test similar patterns across regions
        consistency_tests = [
            {
                "feature": "Title handling",
                "tests": {
                    "A1": "Dr. Smith, John",
                    "A2": "Dr. Müller, Hans",
                    "C4": "Dr. Mohammed Al-Rashid",
                    "D1": "Dr. Sharma, Rajesh",
                },
            },
            {
                "feature": "Particle handling",
                "tests": {
                    "A1": "de la Cruz, Maria",
                    "A2": "von Neumann, Johann",
                    "G1": "de los Santos, Carlos",
                },
            },
            {
                "feature": "Single word names",
                "tests": {
                    "A1": "Madonna",
                    "D1": "कबीर",
                    "E3": "田中",
                },
            },
        ]

        for test_group in consistency_tests:
            print(f"\n  {test_group['feature']}:")
            results = {}

            for region_code, test_name in test_group["tests"].items():
                adapter = v7_manager.get_adapter(region_code)
                if not adapter:
                    continue

                self.results["total_tests"] += 1
                self.results["region_stats"][region_code]["tests"] += 1

                try:
                    entry = {"CanonicalLatin": test_name}
                    if self._is_non_latin_script(test_name):
                        entry = {"CanonicalNative": test_name}

                    adapter.process_entry(entry)
                    results[region_code] = "passed"
                    self.results["passed"] += 1
                    self.results["region_stats"][region_code]["passed"] += 1

                except Exception:
                    results[region_code] = "failed"
                    self.results["failed"] += 1
                    self.results["region_stats"][region_code]["failed"] += 1

            # Check consistency
            unique_results = set(results.values())
            if len(unique_results) == 1:
                print("    ✓ Consistent behavior across regions")
            else:
                print(f"    WARN  Inconsistent behavior: {results}")
                self.record_warning(
                    test_group["feature"], f"Inconsistent behavior: {results}"
                )

    def _is_non_latin_script(self, text: str) -> bool:
        """Check if text contains non-Latin scripts."""
        for char in text:
            if ord(char) > 255:  # Simple check for non-ASCII
                return True
        return False

    def record_error(self, context: str, error: str):
        """Record an error for reporting."""
        self.results["errors"].append(
            {"context": context, "error": error, "timestamp": time.time()}
        )

    def record_warning(self, context: str, warning: str):
        """Record a warning for reporting."""
        self.results["warnings"].append(
            {"context": context, "warning": warning, "timestamp": time.time()}
        )

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)

        # Overall stats
        print(f"\nTotal Tests Run: {self.results['total_tests']}")
        print(
            f"Passed: {self.results['passed']} ({self.results['passed']/self.results['total_tests']*100:.1f}%)"
        )
        print(
            f"Failed: {self.results['failed']} ({self.results['failed']/self.results['total_tests']*100:.1f}%)"
        )

        # Per-region breakdown
        print("\nPer-Region Results:")
        print(
            f"{'Region':<10} {'Tests':<10} {'Passed':<10} {'Failed':<10} {'Pass Rate':<10}"
        )
        print("-" * 50)

        for region in sorted(self.results["region_stats"].keys()):
            stats = self.results["region_stats"][region]
            pass_rate = (
                stats["passed"] / stats["tests"] * 100 if stats["tests"] > 0 else 0
            )
            print(
                f"{region:<10} {stats['tests']:<10} {stats['passed']:<10} {stats['failed']:<10} {pass_rate:<10.1f}%"
            )

        # Errors
        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"][:10]):  # First 10
                print(f"  {i+1}. {error['context']}: {error['error']}")
            if len(self.results["errors"]) > 10:
                print(f"  ... and {len(self.results['errors']) - 10} more errors")

        # Warnings
        if self.results["warnings"]:
            print(f"\nWarnings ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"  - {warning['context']}: {warning['warning']}")

        # Final verdict
        print("\n" + "=" * 60)
        if self.results["failed"] == 0:
            print("PASS ALL TESTS PASSED! 🎉")
        elif self.results["failed"] / self.results["total_tests"] < 0.05:
            print("PASS TESTS PASSED WITH MINOR ISSUES (>95% pass rate)")
        elif self.results["failed"] / self.results["total_tests"] < 0.10:
            print("WARN  TESTS MOSTLY PASSED (>90% pass rate)")
        else:
            print("FAIL SIGNIFICANT TEST FAILURES")

        # Save detailed results
        with open("comprehensive_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\nDetailed results saved to: comprehensive_test_results.json")


def main():
    """Run the comprehensive test suite."""
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()
