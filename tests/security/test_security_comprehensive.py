from typing import Dict

import pytest

#!/usr/bin/env python3
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


Comprehensive Security Testing Suite for GMNAP v7

Tests the security filtering system against various attack vectors:
- Script injection (XSS, JavaScript, VBScript)
- SQL injection
- Command injection  
- HTML injection
- Unicode attacks
- Control character attacks
- Buffer overflow attempts
- Path traversal
- Template injection

This test ensures that all regional processors are protected against
malicious input while preserving legitimate multilingual name data.
"""

import traceback
from typing import Any

# Import security components
try:
    from src.regions.base import RegionRuleError
    from src.regions.security import RegionSecurityError as SecurityError
    from src.regions.security import (
        SecurityFilter,
    )

    # Import processors from proper package structure
    try:
        import os

        os.environ["GMNAP_TEST_MODE"] = "true"
        from pathlib import Path

        from src.regions.manager_optimized import RegionManager

        # Create manager instance to get processors
        manager = RegionManager(Path("./config"))
        G1_LatinAmerica = manager.get_region("G1")
        E3_Japan = manager.get_region("E3")
        E1_SinophoneMainland = manager.get_region("E1")
        E4KoreanProcessor = manager.get_region("E4")
    except ImportError as region_error:
        print(f"Warning: Could not load some regions: {region_error}")
        G1_LatinAmerica = None
        E3_Japan = None
        E1_SinophoneMainland = None
        E4KoreanProcessor = None
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory")
    # sys.exit(1)  # MOVED: Was at module level


class SecurityTestSuite:
    """Comprehensive security test suite."""

    def __init__(self):
        self.security_filter = SecurityFilter()
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0

        # Initialize test processors
        self.processors = {
            "E4Korean": E4KoreanProcessor,
            "G1LatinAmerica": G1_LatinAmerica,
            "E3Japan": E3_Japan,
            "E1Chinese": E1_SinophoneMainland,
        }

    @pytest.mark.timeout(15)
    def test_attack_vector(
        self,
        attack_name: str,
        malicious_input: str,
        should_block: bool = True,
        context: str = "test",
    ):
        """Test a specific attack vector."""
        self.total_tests += 1

        try:
            self.security_filter.scan_for_attacks(malicious_input, context)

            if should_block:
                print(f"FAIL FAILED: {attack_name} - Attack was NOT blocked!")
                print(f"   Input: {repr(malicious_input[:100])}")
                self.failed_tests += 1
                return False
            else:
                print(f"PASS PASSED: {attack_name} - Legitimate input allowed")
                self.passed_tests += 1
                return True

        except SecurityError as e:
            if should_block:
                print(f"PASS PASSED: {attack_name} - Attack correctly blocked")
                print(f"   Detected: {str(e)[:80]}...")
                self.passed_tests += 1
                return True
            else:
                print(f"FAIL FAILED: {attack_name} - Legitimate input blocked!")
                print(f"   Error: {str(e)[:80]}...")
                self.failed_tests += 1
                return False
        except Exception as e:
            print(f"FAIL ERROR: {attack_name} - Unexpected exception: {e}")
            self.failed_tests += 1
            return False

    @pytest.mark.timeout(15)
    def test_processor_integration(
        self,
        test_name: str,
        actual_processor_name: str,
        malicious_entry: Dict[str, Any],
    ):
        """Test processor integration with security."""
        self.total_tests += 1

        try:
            processor = self.processors[actual_processor_name]
            if processor is None:
                print(f"FAIL FAILED: {test_name} integration - Processor not loaded")
                self.failed_tests += 1
                return False

            # Use the standard validate() method instead of non-existent security_validate()
            processor.validate(malicious_entry)

            print(f"FAIL FAILED: {test_name} integration - Attack was NOT blocked!")
            print(f"   Entry: {malicious_entry}")
            self.failed_tests += 1
            return False

        except (RegionRuleError, SecurityError) as e:
            # Any RegionRuleError or SecurityError indicates the processor detected the malicious input
            print(f"PASS PASSED: {test_name} integration - Attack correctly blocked")
            print(f"   Detected: {str(e)[:80]}...")
            self.passed_tests += 1
            return True
        except Exception as e:
            print(f"FAIL ERROR: {test_name} integration - Unexpected exception: {e}")
            self.failed_tests += 1
            return False

    def run_all_tests(self):
        """Run comprehensive security test suite."""
        print("🔒 GMNAP v7 Security Test Suite")
        print("=" * 50)

        # 1. Script Injection Tests
        print("\n1. Script Injection Tests")
        print("-" * 25)

        self.test_attack_vector(
            "JavaScript Alert", "Smith<script>alert('XSS')</script>"
        )
        self.test_attack_vector("JavaScript Event Handler", 'Smith" onload="alert(1)"')
        self.test_attack_vector("VBScript Injection", "vbscript:msgbox('attack')")
        self.test_attack_vector("JavaScript Protocol", "javascript:eval('malicious')")
        self.test_attack_vector("SVG XSS", "<svg/onload=alert('xss')>")
        self.test_attack_vector("IMG XSS", "<img/src=x/onerror=alert(1)>")

        # 2. SQL Injection Tests
        print("\n2. SQL Injection Tests")
        print("-" * 20)

        self.test_attack_vector(
            "SQL Union Attack", "Smith' UNION SELECT * FROM users--"
        )
        self.test_attack_vector("SQL Boolean Attack", "Smith' OR '1'='1")
        self.test_attack_vector("SQL Drop Table", "Smith'; DROP TABLE names;--")
        self.test_attack_vector("SQL Comment Injection", "Smith'/**/OR/**/1=1--")

        # 3. Command Injection Tests
        print("\n3. Command Injection Tests")
        print("-" * 23)

        self.test_attack_vector("Shell Command", "Smith; rm -rf /")
        self.test_attack_vector("Windows Command", "Smith & del /f *.*")
        self.test_attack_vector("Pipe Command", "Smith | cat /etc/passwd")
        self.test_attack_vector("Backtick Command", "Smith`whoami`")
        self.test_attack_vector("Variable Expansion", "Smith${IFS}malicious")

        # 4. HTML Injection Tests
        print("\n4. HTML Injection Tests")
        print("-" * 19)

        self.test_attack_vector(
            "Iframe Injection", "<iframe src='malicious.com'></iframe>"
        )
        self.test_attack_vector(
            "Object Injection", "<object data='malicious.swf'></object>"
        )
        self.test_attack_vector(
            "Meta Refresh", "<meta http-equiv='refresh' content='0;url=evil.com'>"
        )
        self.test_attack_vector(
            "Link Injection", "<link rel='stylesheet' href='evil.css'>"
        )

        # 5. Control Character Tests
        print("\n5. Control Character Tests")
        print("-" * 24)

        self.test_attack_vector("Null Byte Injection", "Smith\\x00malicious")
        self.test_attack_vector("Bell Character", "Smith\\x07")
        self.test_attack_vector("Escape Character", "Smith\\x1b[31mRed")
        self.test_attack_vector("Form Feed", "Smith\\x0c")

        # 6. Unicode Attack Tests
        print("\n6. Unicode Attack Tests")
        print("-" * 21)

        self.test_attack_vector("RLO Override", "Smith\\u202ekcatta")
        self.test_attack_vector("LRO Override", "Smith\\u202dmalicious")
        self.test_attack_vector("BOM Injection", "Smith\\ufeffhidden")
        self.test_attack_vector("Soft Hyphen", "Smith\\u00adattack")

        # 7. Path Traversal Tests
        print("\n7. Path Traversal Tests")
        print("-" * 21)

        self.test_attack_vector("Directory Traversal", "../../../etc/passwd")
        self.test_attack_vector(
            "Windows Traversal", "..\\\\..\\\\..\\\\windows\\\\system32"
        )
        self.test_attack_vector("Encoded Traversal", "%2e%2e%2f%2e%2e%2f")

        # 8. Template Injection Tests
        print("\n8. Template Injection Tests")
        print("-" * 24)

        self.test_attack_vector("Django Template", "Smith{{7*7}}")
        self.test_attack_vector("Spring EL", "Smith${7*7}")
        self.test_attack_vector("JSP Expression", "Smith<%=7*7%>")

        # 9. Buffer Overflow Tests
        print("\n9. Buffer Overflow Tests")
        print("-" * 21)

        self.test_attack_vector("Long String", "A" * 1000)
        self.test_attack_vector("Repeated Characters", "Smith" + "X" * 100)

        # 10. Legitimate Input Tests (should NOT be blocked)
        print("\n10. Legitimate Input Tests")
        print("-" * 26)

        legitimate_names = [
            ("English Name", "Smith, John", False),
            ("Spanish Name", "García, María José", False),
            ("Chinese Name", "王小明", False),
            ("Korean Name", "김민수", False),
            ("Japanese Name", "田中太郎", False),
            ("Arabic Name", "محمد الأحمد", False),
            ("Russian Name", "Иванов, Иван", False),
            ("German Name", "Müller, Hans", False),
            ("French Name", "Dubois, Jean-Pierre", False),
            ("Hyphenated Name", "Smith-Jones, Mary", False),
            ("Apostrophe Name", "O'Connor, Patrick", False),
            ("Accented Name", "Café, André", False),
        ]

        for name, input_text, should_block in legitimate_names:
            self.test_attack_vector(name, input_text, should_block)

        # 11. Processor Integration Tests
        print("\n11. Processor Integration Tests")
        print("-" * 31)

        malicious_entries = [
            {"CanonicalLatin": "Smith<script>alert(1)</script>"},
            {"CanonicalNative": "テスト" + "\\x00" + "attack"},
            {"CJK": "王小明" + "; DROP TABLE names;--"},
            {"Variants": {"Observed": [{"str": "Evil<iframe>"}]}},
        ]

        for processor_name in self.processors:
            for i, entry in enumerate(malicious_entries):
                self.test_processor_integration(
                    f"{processor_name}_Entry{i+1}", processor_name, entry
                )

        # 12. Edge Case Tests
        print("\n12. Edge Case Tests")
        print("-" * 17)

        self.test_attack_vector("Empty String", "", False)
        self.test_attack_vector("Only Spaces", "   ", False)
        self.test_attack_vector("Mixed Scripts Safe", "Smith 王", False)
        self.test_attack_vector("Numbers Safe", "Smith123", False)
        self.test_attack_vector("Basic Punctuation", "Smith, Jr.", False)

        # Results Summary
        print("\n" + "=" * 50)
        print("🔒 SECURITY TEST RESULTS")
        print("=" * 50)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {self.passed_tests/self.total_tests*100:.1f}%")

        if self.failed_tests == 0:
            print("\n🎉 ALL SECURITY TESTS PASSED!")
            print("PASS System is protected against all tested attack vectors")
            return True
        else:
            print(f"\nWARN  {self.failed_tests} SECURITY TESTS FAILED!")
            print("FAIL System has security vulnerabilities")
            return False


def main():
    """Run the comprehensive security test suite."""
    test_suite = SecurityTestSuite()

    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"\nFAIL CRITICAL ERROR in security test suite: {e}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    pass  # sys.exit(main())
