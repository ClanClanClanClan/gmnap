from typing import List
from typing import Any
import pytest

#!/usr/bin/env python3
"""
Comprehensive validation test suite for GMNAP.
Tests security, schema, linguistic, and data quality validation.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.security_validator import security_validator, SecurityError
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.validation.schema import SchemaValidator
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.validation.data_quality import data_quality_validator
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.validation_rules import regional_validator
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.linguistic.rules_engine import LinguisticRulesEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ValidationTestSuite:
    """Comprehensive test suite for all validation components."""

    def __init__(self):
        self.security = security_validator
        self.schema = SchemaValidator()
        self.quality = data_quality_validator
        self.regional = regional_validator
        self.linguistic = LinguisticRulesEngine()
        self.results = {"total_tests": 0, "passed": 0, "failed": 0, "tests": []}

    def run_all_tests(self):
        """Run all validation tests."""
        logger.info("Starting comprehensive validation test suite")

        # Security validation tests
        self.test_security_validation()

        # Schema validation tests
        self.test_schema_validation()

        # Data quality tests
        self.test_data_quality_validation()

        # Regional validation tests
        self.test_regional_validation()

        # Linguistic rules tests
        self.test_linguistic_rules()

        # Integration tests
        self.test_integration()

        # Print summary
        self.print_summary()

    @pytest.mark.timeout(15)
    def test_security_validation(self):
        """Test security validation components."""
        logger.info("\n=== Testing Security Validation ===")

        # Test SQL injection detection
        test_cases = [
            {
                "name": "SQL Injection - UNION",
                "input": {"CanonicalLatin": "Smith'; UNION SELECT * FROM users--"},
                "should_pass": False,
            },
            {
                "name": "SQL Injection - DROP",
                "input": {"CanonicalLatin": "Robert'); DROP TABLE students;--"},
                "should_pass": False,
            },
            {
                "name": "XSS Attack - Script Tag",
                "input": {"CanonicalLatin": "John<script>alert('XSS')</script>Doe"},
                "should_pass": False,
            },
            {
                "name": "Command Injection",
                "input": {"CanonicalLatin": "Smith; rm -rf /"},
                "should_pass": False,
            },
            {
                "name": "Path Traversal",
                "input": {"CanonicalLatin": "../../etc/passwd"},
                "should_pass": False,
            },
            {
                "name": "LDAP Injection",
                "input": {"CanonicalLatin": "Smith)(cn=*)"},
                "should_pass": False,
            },
            {
                "name": "Template Injection",
                "input": {"CanonicalLatin": "{{7*7}}"},
                "should_pass": False,
            },
            {
                "name": "NoSQL Injection",
                "input": {"CanonicalLatin": "Smith', $gt: '"},
                "should_pass": False,
            },
            {
                "name": "SSRF Attack",
                "input": {"Homepage": "http://169.254.169.254/latest/meta-data/"},
                "should_pass": False,
            },
            {
                "name": "CSV Injection",
                "input": {"CanonicalLatin": "=cmd|'/c calc'!A0"},
                "should_pass": False,
            },
            {
                "name": "Unicode Direction Override",
                "input": {"CanonicalLatin": "John\u202eDoe"},
                "should_pass": False,
            },
            {
                "name": "Null Byte Injection",
                "input": {"CanonicalLatin": "file.txt%00.jpg"},
                "should_pass": False,
            },
            {
                "name": "Log Injection",
                "input": {"CanonicalLatin": "User\r\n[ERROR] Fake error message"},
                "should_pass": False,
            },
            {
                "name": "Homograph Attack",
                "input": {"CanonicalLatin": "Аррӏе"},  # Cyrillic lookalikes
                "should_pass": False,
            },
            {
                "name": "Excessive Combining Characters",
                "input": {"CanonicalLatin": "A̸̸̗̘̙̜̝̞̟̠̤̥̦̩̪̫̬̭̮̯̰̱̲̳̹̺̻̼͇͈͉͍͎"},
                "should_pass": False,
            },
            {
                "name": "Valid Name - Latin",
                "input": {"CanonicalLatin": "Smith, John Edward"},
                "should_pass": True,
            },
            {
                "name": "Valid Name - Accented",
                "input": {"CanonicalLatin": "Müller, François"},
                "should_pass": True,
            },
            {
                "name": "Valid Name - Hyphenated",
                "input": {"CanonicalLatin": "Smith-Jones, Mary-Jane"},
                "should_pass": True,
            },
            {
                "name": "Valid Name - Apostrophe",
                "input": {"CanonicalLatin": "O'Brien, Patrick"},
                "should_pass": True,
            },
            {
                "name": "Valid Name with Double Hyphen",
                "input": {"CanonicalLatin": "Lee, Jae--3"},  # GlobalID collision suffix
                "should_pass": True,
            },
        ]

        for test in test_cases:
            self.run_security_test(test)

    @pytest.mark.timeout(15)
    def test_schema_validation(self):
        """Test schema validation."""
        logger.info("\n=== Testing Schema Validation ===")

        test_cases = [
            {
                "name": "Valid Complete Entry",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "BirthYear": 1950,
                    "Confidence": 85,
                    "CountryCodes": ["US", "UK"],
                    "PrimaryMSC": [{"code": "11A05", "source": "zbMATH"}],
                    "AuthorityIDs": {"ORCID": "0000-0000-0000-0000"},
                },
                "should_pass": True,
            },
            {
                "name": "Invalid GlobalID Format",
                "input": {
                    "GlobalID": "ABC123",  # Too short
                    "CanonicalLatin": "Smith, John",
                    "Confidence": 85,
                },
                "should_pass": False,
            },
            {
                "name": "Invalid MSC Code",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "PrimaryMSC": [{"code": "99Z99", "source": "manual"}],
                    "Confidence": 85,
                },
                "should_pass": False,
            },
            {
                "name": "Invalid ORCID Format",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "AuthorityIDs": {"ORCID": "1234-5678"},
                    "Confidence": 85,
                },
                "should_pass": False,
            },
            {
                "name": "Death Before Birth",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "BirthYear": 1950,
                    "DeathYear": 1940,
                    "Confidence": 85,
                },
                "should_pass": False,
            },
            {
                "name": "Invalid Country Code",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "CountryCodes": ["USA"],  # Should be 2-letter
                    "Confidence": 85,
                },
                "should_pass": False,
            },
            {
                "name": "Invalid Confidence Score",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "Confidence": 150,  # > 100
                },
                "should_pass": False,
            },
        ]

        for test in test_cases:
            self.run_schema_test(test)

    @pytest.mark.timeout(15)
    def test_data_quality_validation(self):
        """Test data quality validation."""
        logger.info("\n=== Testing Data Quality Validation ===")

        test_cases = [
            {
                "name": "High Quality Entry",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John Edward",
                    "BirthYear": 1950,
                    "Confidence": 90,
                    "CountryCodes": ["US"],
                    "PrimaryMSC": [{"code": "11A05", "source": "zbMATH"}],
                    "AuthorityIDs": {"ORCID": "0000-0000-0000-0000", "zbMATH": "smith.john-edward"},
                    "LanguageOfPublication": ["eng", "fra"],
                },
                "expected_completeness": 100,
                "expected_errors": 0,
            },
            {
                "name": "Low Completeness Entry",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith",
                    "Confidence": 50,
                },
                "expected_completeness": 50,
                "expected_warnings": ["Missing recommended fields"],
            },
            {
                "name": "Test Data Pattern",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "test_user",
                    "Confidence": 100,
                },
                "expected_warnings": ["Suspicious name pattern"],
            },
            {
                "name": "Future Birth Year",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "BirthYear": 2030,
                    "Confidence": 85,
                },
                "expected_errors": ["Birth year in future"],
            },
            {
                "name": "Inconsistent Timeline",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "AffiliationTimeline": [
                        {"from": 2000, "to": 2010, "institution": "MIT"},
                        {"from": 1990, "to": 1995, "institution": "Harvard"},
                    ],
                    "Confidence": 85,
                },
                "expected_warnings": ["not in chronological order"],
            },
            {
                "name": "High Confidence No Authority",
                "input": {
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "CanonicalLatin": "Smith, John",
                    "Confidence": 95,
                    "AuthorityIDs": {},
                },
                "expected_warnings": ["High confidence"],
            },
        ]

        for test in test_cases:
            self.run_quality_test(test)

    @pytest.mark.timeout(15)
    def test_regional_validation(self):
        """Test regional validation rules."""
        logger.info("\n=== Testing Regional Validation ===")

        test_cases = [
            {
                "name": "A1 - Valid Anglo Name",
                "region": "A1",
                "script": "Latin",
                "input": {"CanonicalLatin": "O'Brien, Patrick Michael", "CountryCodes": ["IE"]},
                "expected_valid": True,
            },
            {
                "name": "A1 - Invalid Mc Prefix",
                "region": "A1",
                "script": "Latin",
                "input": {"CanonicalLatin": "Mcdonald, John"},  # Should be McDonald
                "expected_errors": ["Mac/Mc/O' prefixes"],
            },
            {
                "name": "E1 - Valid Chinese Name",
                "region": "E1",
                "script": "CJK",
                "input": {"CanonicalLatin": "Wang, Wei", "CanonicalNative": "王伟"},
                "expected_valid": True,
            },
            {
                "name": "E1 - Too Short Chinese Name",
                "region": "E1",
                "script": "CJK",
                "input": {"CanonicalLatin": "Li, X", "CanonicalNative": "李"},
                "expected_errors": ["Chinese name too short"],
            },
            {
                "name": "B1 - Cyrillic-Latin Mix",
                "region": "B1",
                "script": "Cyrillic",
                "input": {
                    "CanonicalLatin": "Ivanov, Ivan",
                    "CanonicalNative": "Иванов, Иvаn",  # Mixed scripts
                },
                "expected_errors": ["Cyrillic-Latin character mixing", "Mixed scripts"],
            },
            {
                "name": "C3 - Arabic Patronymic",
                "region": "C3",
                "script": "Arabic",
                "input": {
                    "CanonicalLatin": "Al-Hassan ibn Ahmad ibn Ali ibn Muhammad",
                    "CanonicalNative": "الحسن بن أحمد بن علي بن محمد",
                },
                "expected_warnings": ["Long patronymic chain"],
            },
        ]

        for test in test_cases:
            self.run_regional_test(test)

    @pytest.mark.timeout(15)
    def test_linguistic_rules(self):
        """Test linguistic rules engine."""
        logger.info("\n=== Testing Linguistic Rules ===")

        test_cases = [
            {
                "name": "Unicode Normalization",
                "input": "Müller",  # Combining characters
                "expected_normalized": "Müller",  # NFC normalized
            },
            {
                "name": "Whitespace Normalization",
                "input": "  Smith  ,   John  ",
                "expected_normalized": "Smith, John",
            },
            {
                "name": "Multiple Spaces",
                "input": "Smith    John",
                "expected_normalized": "Smith John",
            },
            {"name": "Comma Spacing", "input": "Smith,John", "expected_normalized": "Smith, John"},
            {
                "name": "Extra Punctuation",
                "input": "Smith,, John",
                "expected_normalized": "Smith, John",
            },
            {
                "name": "Control Characters",
                "input": "Smith\x00John",
                "expected_normalized": "SmithJohn",
            },
        ]

        for test in test_cases:
            self.run_linguistic_test(test)

    @pytest.mark.timeout(15)
    def test_integration(self):
        """Test integration of multiple validation systems."""
        logger.info("\n=== Testing Integration ===")

        # Test a complete entry through all validators
        entry = {
            "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
            "CanonicalLatin": "Müller, Hans-Jürgen",
            "CanonicalNative": "Müller, Hans-Jürgen",
            "BirthYear": 1960,
            "DeathYear": None,
            "Confidence": 85,
            "CountryCodes": ["DE", "CH"],
            "PrimaryMSC": [
                {"code": "14H52", "source": "zbMATH"},
                {"code": "32G15", "source": "MathSciNet"},
            ],
            "AuthorityIDs": {"ORCID": "0000-0002-1234-5678", "zbMATH": "muller.hans-jurgen"},
            "LanguageOfPublication": ["eng", "deu", "fra"],
            "AffiliationTimeline": [
                {
                    "from": 1990,
                    "to": 2000,
                    "institution": "University of Heidelberg",
                    "country": "DE",
                },
                {"from": 2000, "to": None, "institution": "ETH Zurich", "country": "CH"},
            ],
            "Variants": {
                "Published": [
                    {"name": "Mueller, H. J.", "source": "manual"},
                    {"name": "Müller, H.-J.", "source": "manual"},
                ]
            },
        }

        test = {"name": "Complete Valid Entry Integration", "entry": entry}

        self.run_integration_test(test)

    # Test execution methods
    def run_security_test(self, test: Dict[str, Any]):
        """Run a single security test."""
        self.results["total_tests"] += 1

        try:
            # Try to validate the entry
            validated = self.security.validate_entry(test["input"])

            if test["should_pass"]:
                logger.info(f"✓ {test['name']}")
                self.results["passed"] += 1
            else:
                logger.error(f"✗ {test['name']} - Expected to fail but passed")
                self.results["failed"] += 1

        except SecurityError as e:
            if not test["should_pass"]:
                logger.info(f"✓ {test['name']} - Correctly blocked: {e}")
                self.results["passed"] += 1
            else:
                logger.error(f"✗ {test['name']} - Incorrectly blocked: {e}")
                self.results["failed"] += 1

    def run_schema_test(self, test: Dict[str, Any]):
        """Run a single schema test."""
        self.results["total_tests"] += 1

        is_valid, errors = self.schema.validate_entry(test["input"])

        if is_valid == test["should_pass"]:
            logger.info(f"✓ {test['name']}")
            self.results["passed"] += 1
        else:
            logger.error(f"✗ {test['name']} - Validation: {is_valid}, Errors: {errors}")
            self.results["failed"] += 1

    def run_quality_test(self, test: Dict[str, Any]):
        """Run a single data quality test."""
        self.results["total_tests"] += 1

        result = self.quality.validate_entry(test["input"])

        passed = True

        # Check completeness if expected
        if "expected_completeness" in test:
            if abs(result["completeness_score"] - test["expected_completeness"]) > 10:
                passed = False
                logger.error(
                    f"Completeness mismatch: expected {test['expected_completeness']}, got {result['completeness_score']}"
                )

        # Check errors
        if "expected_errors" in test:
            if isinstance(test["expected_errors"], int):
                if len(result["errors"]) != test["expected_errors"]:
                    passed = False
                    logger.error(
                        f"Error count mismatch: expected {test['expected_errors']}, got {len(result['errors'])}"
                    )
            else:
                for expected in test["expected_errors"]:
                    if not any(expected in error for error in result["errors"]):
                        passed = False
                        logger.error(f"Expected error not found: {expected}")

        # Check warnings
        if "expected_warnings" in test:
            for expected in test["expected_warnings"]:
                if not any(expected in warning for warning in result["warnings"]):
                    passed = False
                    logger.error(f"Expected warning not found: {expected}")

        if passed:
            logger.info(f"✓ {test['name']}")
            self.results["passed"] += 1
        else:
            logger.error(f"✗ {test['name']} - Result: {result}")
            self.results["failed"] += 1

    def run_regional_test(self, test: Dict[str, Any]):
        """Run a single regional validation test."""
        self.results["total_tests"] += 1

        results = self.regional.validate_entry(test["input"], test["region"], test["script"])

        errors = []
        for result in results:
            errors.extend(result.errors)

        passed = True

        if "expected_valid" in test and test["expected_valid"]:
            if errors:
                passed = False
                logger.error(f"Unexpected errors: {errors}")

        if "expected_errors" in test:
            for expected in test["expected_errors"]:
                if not any(expected in error for error in errors):
                    passed = False
                    logger.error(f"Expected error not found: {expected}")

        if passed:
            logger.info(f"✓ {test['name']}")
            self.results["passed"] += 1
        else:
            logger.error(f"✗ {test['name']} - Errors: {errors}")
            self.results["failed"] += 1

    def run_linguistic_test(self, test: Dict[str, Any]):
        """Run a single linguistic test."""
        self.results["total_tests"] += 1

        result = self.linguistic.normalize_name(test["input"])
        normalized = result["normalized"]

        if normalized == test["expected_normalized"]:
            logger.info(f"✓ {test['name']}")
            self.results["passed"] += 1
        else:
            logger.error(
                f"✗ {test['name']} - Expected: '{test['expected_normalized']}', Got: '{normalized}'"
            )
            self.results["failed"] += 1

    def run_integration_test(self, test: Dict[str, Any]):
        """Run an integration test."""
        self.results["total_tests"] += 1

        entry = test["entry"]
        passed = True
        errors = []

        # 1. Security validation
        try:
            self.security.validate_entry(entry)
        except SecurityError as e:
            passed = False
            errors.append(f"Security: {e}")

        # 2. Schema validation
        is_valid, schema_errors = self.schema.validate_entry(entry)
        if not is_valid:
            passed = False
            errors.extend(f"Schema: {e}" for e in schema_errors)

        # 3. Data quality validation
        quality_result = self.quality.validate_entry(entry)
        if quality_result["errors"]:
            passed = False
            errors.extend(f"Quality: {e}" for e in quality_result["errors"])

        # 4. Regional validation (assuming A2 for German)
        regional_results = self.regional.validate_entry(entry, "A2", "Latin")
        for result in regional_results:
            if result.errors:
                passed = False
                errors.extend(f"Regional: {e}" for e in result.errors)

        if passed:
            logger.info(f"✓ {test['name']}")
            self.results["passed"] += 1
        else:
            logger.error(f"✗ {test['name']} - Errors: {errors}")
            self.results["failed"] += 1

    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 50)
        logger.info("TEST SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {self.results['total_tests']}")
        logger.info(f"Passed: {self.results['passed']}")
        logger.info(f"Failed: {self.results['failed']}")

        if self.results["total_tests"] > 0:
            pass_rate = (self.results["passed"] / self.results["total_tests"]) * 100
            logger.info(f"Pass Rate: {pass_rate:.1f}%")

        if self.results["failed"] == 0:
            logger.info("\nPASS All tests passed!")
        else:
            logger.error(f"\nFAIL {self.results['failed']} tests failed")

        # Save results to file
        with open("validation_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nResults saved to validation_test_results.json")


if __name__ == "__main__":
    suite = ValidationTestSuite()
    suite.run_all_tests()
