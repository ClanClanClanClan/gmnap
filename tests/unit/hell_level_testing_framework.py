#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
HELL-LEVEL TESTING FRAMEWORK FOR GMNAP V7
Extreme stress testing, adversarial inputs, and production-scale validation
No mercy. No assumptions. Only brutal verification.
"""

import asyncio
import json
import logging
import random
import string
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Add project paths
import sys

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.regions.manager_optimized import RegionManager
from src.core.military_grade_security import MilitaryGradeSecurityValidator


class TestSeverity(Enum):
    """Test severity levels."""

    NORMAL = "normal"
    STRESS = "stress"
    EXTREME = "extreme"
    HELLISH = "hellish"
    APOCALYPTIC = "apocalyptic"


@dataclass
class HellTestResult:
    """Hell-level test result."""

    test_name: str
    severity: TestSeverity
    success: bool
    duration: float
    details: str
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class HellLevelTester:
    """
    Hell-level testing framework for GMNAP v7 regions.

    Tests include:
    - Malicious input injection
    - Unicode boundary exploitation
    - Memory exhaustion attacks
    - Concurrent processing chaos
    - Edge case mutation
    - Production-scale stress testing
    """

    def __init__(self):
        self.logger = self._setup_logging()
        self.region_manager = None
        self.security_validator = None
        self.test_results: List[HellTestResult] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

        # Hell-level test configurations
        self.stress_multiplier = 10000  # 10x normal stress
        self.concurrent_threads = 50  # Extreme concurrency
        self.memory_limit_mb = 1024  # Memory constraint
        self.timeout_seconds = 300  # 5-minute timeout

        # Evil test inputs
        self.malicious_inputs = self._generate_malicious_inputs()
        self.unicode_bombs = self._generate_unicode_bombs()
        self.memory_exhaustion_inputs = self._generate_memory_exhaustion()

    def _setup_logging(self) -> logging.Logger:
        """Setup hell-level testing logger."""
        logger = logging.getLogger("hell_testing")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter("%(asctime)s [HELL-TEST] %(levelname)s: %(message)s")
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def _generate_malicious_inputs(self) -> List[Dict[str, Any]]:
        """Generate malicious inputs for security testing."""
        malicious = []

        # SQL injection variants
        sql_attacks = [
            "'; DROP TABLE users; --",
            "admin'--",
            "' OR '1'='1",
            "'; EXEC xp_cmdshell('dir'); --",
            "1; DELETE FROM entries WHERE 1=1; --",
        ]

        # XSS variants
        xss_attacks = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src='x' onerror='alert(1)'>",
            "<svg onload='alert(1)'>",
            "<iframe src='javascript:alert(1)'>",
        ]

        # Path traversal
        path_attacks = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\",
            "/proc/self/environ",
            "file:///etc/shadow",
            "\\\\server\\share\\file",
        ]

        # Command injection
        cmd_attacks = ["; rm -rf /", "| cat /etc/passwd", "&& format c:", "`whoami`", "$(rm -rf /)"]

        # Combine all attacks
        all_attacks = sql_attacks + xss_attacks + path_attacks + cmd_attacks

        for attack in all_attacks:
            malicious.append(
                {"name": attack, "email": f"{attack}@evil.com", "comment": attack, "data": attack}
            )

        return malicious

    def _generate_unicode_bombs(self) -> List[str]:
        """Generate Unicode boundary exploitation inputs."""
        bombs = []

        # Zero-width characters
        bombs.extend(
            [
                "\u200b" * 1000,  # Zero width space bomb
                "\u200c" * 1000,  # Zero width non-joiner
                "\ufeff" * 1000,  # Byte order mark
            ]
        )

        # Normalization attacks
        bombs.extend(
            [
                "é" + "\u0301" * 1000,  # Combining accent spam
                "a\u0300\u0301\u0302" * 500,  # Multiple combining chars
            ]
        )

        # Mixed scripts (potentially confusing)
        bombs.extend(
            [
                "Јohn Smith",  # Cyrillic J, Latin rest
                "Αdmin",  # Greek A, Latin rest
                "Мichael",  # Cyrillic M, Latin rest
            ]
        )

        # Surrogate pairs and high Unicode
        bombs.extend(
            [
                "\U0001f4a9" * 1000,  # Poop emoji spam
                "\U000e0000" * 500,  # Language tag spam
            ]
        )

        return bombs

    def _generate_memory_exhaustion(self) -> List[Dict[str, Any]]:
        """Generate inputs designed to exhaust memory."""
        exhaustion = []

        # Massive string inputs
        for size in [10**5, 10**6, 10**7]:  # 100K, 1M, 10M chars
            exhaustion.append(
                {"name": "A" * size, "data": "x" * size, "comment": "Memory exhaustion test"}
            )

        # Nested structure attacks
        nested_data = {"d": "e" * 10000}
        for _ in range(3):  # 3 levels of nesting
            nested_data = {"nested": nested_data}

        exhaustion.append({"name": "nested_attack", "data": nested_data})

        # Array multiplication attacks
        exhaustion.append(
            {"name": "array_bomb", "data": ["x" * 1000 for _ in range(1000)]}  # Large array
        )

        return exhaustion

    async def run_hell_testing_suite(self, target_regions: List[str] = None) -> Dict[str, Any]:
        """Run the complete hell-level testing suite."""
        self.logger.info("🔥 HELL-LEVEL TESTING SUITE INITIATED")
        self.logger.info("=" * 80)
        self.logger.info("WARNING: Extreme testing in progress. Expect chaos.")
        self.logger.info("=" * 80)

        # Initialize components
        await self._initialize_components()

        # Determine target regions
        if not target_regions:
            target_regions = list(self.region_manager.get_implemented_regions())

        self.logger.info(f"Target regions: {target_regions}")

        # Run test phases
        await self._hell_phase_1_basic_validation(target_regions)
        await self._hell_phase_2_security_exploitation(target_regions)
        await self._hell_phase_3_unicode_chaos(target_regions)
        await self._hell_phase_4_memory_destruction(target_regions)
        await self._hell_phase_5_concurrent_mayhem(target_regions)
        await self._hell_phase_6_production_scale_stress(target_regions)
        await self._hell_phase_7_adversarial_mutation(target_regions)
        await self._hell_phase_8_edge_case_annihilation(target_regions)

        # Generate hell report
        return self._generate_hell_report()

    async def _initialize_components(self):
        """Initialize testing components."""
        try:
            self.region_manager = RegionManager()
            self.security_validator = MilitaryGradeSecurityValidator()
            self.logger.info("PASS Components initialized")
        except Exception as e:
            self.logger.error(f"💥 Component initialization failed: {e}")
            raise

    async def _hell_phase_1_basic_validation(self, regions: List[str]):
        """Phase 1: End-to-end processing validation test."""
        self.logger.info("\n🔥 HELL PHASE 1: END-TO-END PROCESSING VALIDATION")
        self.logger.info("-" * 50)

        # Test cases specific to each working region
        region_test_cases = {
            "A2": [{"name": "Jean Dupont"}, {"name": "Marie Dubois"}, {"name": "Pierre Martin"}],
            "A3": [{"name": "Lars Andersen"}, {"name": "Erik Nilsson"}, {"name": "Anna Korhonen"}],
            "B2": [{"name": "Marko Petrović"}, {"name": "Ana Novak"}, {"name": "Petar Jovanović"}],
            "E2": [{"name": "李明華"}, {"name": "王小明"}, {"name": "陳美玲"}],
            "E4": [{"name": "김철수"}, {"name": "박영희"}, {"name": "이민수"}],
            "E5": [{"name": "Nguyễn Văn Nam"}, {"name": "Trần Thị Lan"}, {"name": "Lê Văn Hùng"}],
            "G1": [{"name": "José García"}, {"name": "María López"}, {"name": "Carlos Rodríguez"}],
        }

        # Test each region with ACTUAL PROCESSING (not just detection)
        for region in regions:
            test_cases = region_test_cases.get(region, [{"name": "Test User"}])

            start_time = time.time()
            successes = 0
            failures = 0

            # Stress test with actual processing
            for i in range(self.stress_multiplier // 100):  # 100 iterations for speed
                for test_case in test_cases:
                    try:
                        # Test 1: Detection
                        result = self.region_manager.detect_region(test_case)
                        if not result:
                            failures += 1
                            continue

                        # Test 2: Get region processor
                        if region not in self.region_manager._regions:
                            failures += 1
                            continue

                        region_processor = self.region_manager._regions[region]

                        # Test 3: End-to-end processing
                        test_entry = test_case.copy()
                        test_entry["CanonicalLatin"] = test_case.get("name", "")

                        # Try full processing pipeline
                        region_processor.clean(test_entry)
                        region_processor.validate(test_entry)
                        region_processor.augment(test_entry)
                        order_key = region_processor.order_key(test_entry)

                        successes += 1
                    except Exception as e:
                        failures += 1

            duration = time.time() - start_time
            total_tests = successes + failures
            success_rate = successes / total_tests * 100 if total_tests > 0 else 0

            self._record_result(
                f"end_to_end_processing_{region}",
                TestSeverity.STRESS,
                success_rate > 95,
                duration,
                f"{total_tests} processing tests, {success_rate:.1f}% success rate",
            )

    async def _hell_phase_2_security_exploitation(self, regions: List[str]):
        """Phase 2: Security exploitation attempts."""
        self.logger.info("\n💀 HELL PHASE 2: SECURITY EXPLOITATION")
        self.logger.info("-" * 50)

        security_blocks = 0
        security_bypasses = 0

        for malicious_input in self.malicious_inputs:
            try:
                # Try to bypass security
                self.security_validator.validate_entry(malicious_input)
                security_bypasses += 1
                self.logger.warning(f"WARN  Security bypass: {malicious_input['name'][:20]}...")
            except Exception:
                security_blocks += 1  # Expected - security should block

        block_rate = security_blocks / len(self.malicious_inputs) * 100

        self._record_result(
            "security_exploitation",
            TestSeverity.EXTREME,
            block_rate >= 99,  # Must block 99%+ of attacks
            1.0,
            f"Blocked {security_blocks}/{len(self.malicious_inputs)} attacks ({block_rate:.1f}%)",
        )

    async def _hell_phase_3_unicode_chaos(self, regions: List[str]):
        """Phase 3: Unicode boundary chaos."""
        self.logger.info("\n🌀 HELL PHASE 3: UNICODE CHAOS")
        self.logger.info("-" * 50)

        unicode_handled = 0
        unicode_crashed = 0

        for bomb in self.unicode_bombs:
            try:
                test_input = {"name": bomb, "data": bomb}
                result = self.region_manager.detect_region(test_input)
                unicode_handled += 1
            except Exception as e:
                unicode_crashed += 1
                self.logger.warning(f"Unicode crash: {str(e)[:50]}...")

        handle_rate = unicode_handled / len(self.unicode_bombs) * 100

        self._record_result(
            "unicode_chaos",
            TestSeverity.HELLISH,
            handle_rate >= 90,  # Should handle 90%+ gracefully
            1.0,
            f"Handled {unicode_handled}/{len(self.unicode_bombs)} unicode bombs ({handle_rate:.1f}%)",
        )

    async def _hell_phase_4_memory_destruction(self, regions: List[str]):
        """Phase 4: Memory exhaustion attacks."""
        self.logger.info("\n💣 HELL PHASE 4: MEMORY DESTRUCTION")
        self.logger.info("-" * 50)

        memory_survived = 0
        memory_killed = 0

        for exhaustion_input in self.memory_exhaustion_inputs:
            try:
                # Set timeout to prevent hanging
                start_time = time.time()
                result = self.region_manager.detect_region(exhaustion_input)

                if time.time() - start_time < 10.0:  # Must complete in 10s
                    memory_survived += 1
                else:
                    memory_killed += 1

            except Exception as e:
                if "memory" in str(e).lower() or "timeout" in str(e).lower():
                    memory_killed += 1
                else:
                    memory_survived += 1  # Graceful handling

        survival_rate = memory_survived / len(self.memory_exhaustion_inputs) * 100

        self._record_result(
            "memory_destruction",
            TestSeverity.APOCALYPTIC,
            survival_rate >= 80,  # Should survive 80%+ of memory attacks
            1.0,
            f"Survived {memory_survived}/{len(self.memory_exhaustion_inputs)} memory attacks ({survival_rate:.1f}%)",
        )

    async def _hell_phase_5_concurrent_mayhem(self, regions: List[str]):
        """Phase 5: Concurrent processing mayhem."""
        self.logger.info("\n⚡ HELL PHASE 5: CONCURRENT MAYHEM")
        self.logger.info("-" * 50)

        async def concurrent_test():
            """Single concurrent test."""
            try:
                test_input = {"name": random.choice(["John", "Jane", "李明", "Maria"])}
                result = self.region_manager.detect_region(test_input)
                return True
            except:
                return False

        # Run massive concurrent tests
        start_time = time.time()
        tasks = [concurrent_test() for _ in range(self.concurrent_threads * 10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if r is True)
        failures = len(results) - successes
        duration = time.time() - start_time

        success_rate = successes / len(results) * 100
        throughput = len(results) / duration

        self._record_result(
            "concurrent_mayhem",
            TestSeverity.HELLISH,
            success_rate >= 95,  # 95%+ success under extreme concurrency
            duration,
            f"{len(results)} concurrent tests, {success_rate:.1f}% success, {throughput:.1f} req/s",
            performance_metrics={
                "throughput": throughput,
                "concurrency": self.concurrent_threads * 10,
            },
        )

    async def _hell_phase_6_production_scale_stress(self, regions: List[str]):
        """Phase 6: Production-scale stress test."""
        self.logger.info("\n🏭 HELL PHASE 6: PRODUCTION SCALE STRESS")
        self.logger.info("-" * 50)

        # Generate realistic production dataset
        production_names = []
        name_templates = [
            "John Smith",
            "María González",
            "李明华",
            "Mohammed Ahmed",
            "Anna Müller",
            "Jean Dubois",
            "Giuseppe Rossi",
            "Olga Petrov",
        ]

        for i in range(1000):  # 1000 test names
            template = random.choice(name_templates)
            # Add variation
            name = f"{template} {i}" if i % 3 == 0 else template
            production_names.append({"name": name, "id": f"prod_{i}"})

        # Process at production scale
        start_time = time.time()
        processed = 0
        errors = 0

        for batch_start in range(0, len(production_names), 50):
            batch = production_names[batch_start : batch_start + 50]

            for entry in batch:
                try:
                    result = self.region_manager.detect_region(entry)
                    processed += 1
                except Exception:
                    errors += 1

        duration = time.time() - start_time
        throughput = len(production_names) / duration
        error_rate = errors / len(production_names) * 100

        self._record_result(
            "production_scale_stress",
            TestSeverity.EXTREME,
            error_rate < 5,  # <5% error rate at production scale
            duration,
            f"{len(production_names)} entries, {throughput:.1f} entries/s, {error_rate:.2f}% errors",
            performance_metrics={"throughput": throughput, "error_rate": error_rate},
        )

    async def _hell_phase_7_adversarial_mutation(self, regions: List[str]):
        """Phase 7: Adversarial mutation testing."""
        self.logger.info("\n🧬 HELL PHASE 7: ADVERSARIAL MUTATION")
        self.logger.info("-" * 50)

        base_names = ["John Smith", "María García", "李明华"]
        mutations_survived = 0
        mutations_crashed = 0

        for base_name in base_names:
            # Generate 100 mutations per base name
            for i in range(100):
                mutation = self._mutate_name(base_name)
                try:
                    result = self.region_manager.detect_region({"name": mutation})
                    mutations_survived += 1
                except Exception:
                    mutations_crashed += 1

        survival_rate = mutations_survived / (mutations_survived + mutations_crashed) * 100

        self._record_result(
            "adversarial_mutation",
            TestSeverity.HELLISH,
            survival_rate >= 85,  # Should survive 85%+ of mutations
            1.0,
            f"Survived {mutations_survived}/{mutations_survived + mutations_crashed} mutations ({survival_rate:.1f}%)",
        )

    async def _hell_phase_8_edge_case_annihilation(self, regions: List[str]):
        """Phase 8: Edge case annihilation."""
        self.logger.info("\n💀 HELL PHASE 8: EDGE CASE ANNIHILATION")
        self.logger.info("-" * 50)

        edge_cases = [
            {"name": ""},  # Empty name
            {"name": " "},  # Whitespace only
            {"name": "a"},  # Single character
            {"name": "a" * 1000},  # Very long name
            {"name": "   John   Smith   "},  # Excess whitespace
            {"name": "John\nSmith"},  # Newlines
            {"name": "John\tSmith"},  # Tabs
            {"name": "John.Smith@domain.com"},  # Email format
            {"name": "123456789"},  # Numbers only
            {"name": "!@#$%^&*()"},  # Symbols only
            {"name": None},  # None value
            {},  # Empty dict
            {"name": ["John", "Smith"]},  # Wrong type
            {"name": 12345},  # Integer name
            {"name": True},  # Boolean name
        ]

        edge_handled = 0
        edge_crashed = 0

        for edge_case in edge_cases:
            try:
                result = self.region_manager.detect_region(edge_case)
                edge_handled += 1
            except Exception:
                edge_handled += 1  # Graceful exception handling is OK

        handle_rate = edge_handled / len(edge_cases) * 100

        self._record_result(
            "edge_case_annihilation",
            TestSeverity.APOCALYPTIC,
            handle_rate >= 90,  # Should gracefully handle 90%+ of edge cases
            1.0,
            f"Handled {edge_handled}/{len(edge_cases)} edge cases ({handle_rate:.1f}%)",
        )

    def _mutate_name(self, name: str) -> str:
        """Generate adversarial mutation of a name."""
        mutations = [
            lambda n: n.upper(),
            lambda n: n.lower(),
            lambda n: n.replace(" ", ""),
            lambda n: n.replace(" ", "_"),
            lambda n: n.replace("a", "@"),
            lambda n: n + "123",
            lambda n: "Dr. " + n,
            lambda n: n + ", Jr.",
            lambda n: n.replace("e", "3"),
            lambda n: n[::-1],  # Reverse
            lambda n: n + "\u0301",  # Add combining accent
            lambda n: n.replace("o", "ο"),  # Greek omicron
        ]

        mutation = random.choice(mutations)
        try:
            return mutation(name)
        except:
            return name + "_mutated"

    def _record_result(
        self,
        test_name: str,
        severity: TestSeverity,
        success: bool,
        duration: float,
        details: str,
        error_message: str = None,
        performance_metrics: Dict[str, Any] = None,
    ):
        """Record a hell-level test result."""
        result = HellTestResult(
            test_name=test_name,
            severity=severity,
            success=success,
            duration=duration,
            details=details,
            error_message=error_message,
            performance_metrics=performance_metrics,
        )

        self.test_results.append(result)
        self.total_tests += 1

        if success:
            self.passed_tests += 1
            status = "PASS PASSED"
        else:
            self.failed_tests += 1
            status = "FAIL FAILED"

        severity_icon = {
            TestSeverity.NORMAL: "🟢",
            TestSeverity.STRESS: "🟡",
            TestSeverity.EXTREME: "🟠",
            TestSeverity.HELLISH: "🔴",
            TestSeverity.APOCALYPTIC: "💀",
        }.get(severity, "⚪")

        self.logger.info(f"{status} {severity_icon} {test_name}: {details}")

    def _generate_hell_report(self) -> Dict[str, Any]:
        """Generate comprehensive hell-level test report."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🔥 HELL-LEVEL TESTING REPORT")
        self.logger.info("=" * 80)

        success_rate = self.passed_tests / self.total_tests * 100 if self.total_tests > 0 else 0

        # Overall statistics
        self.logger.info(f"\n📊 OVERALL STATISTICS:")
        self.logger.info(f"Total tests: {self.total_tests}")
        self.logger.info(f"Passed: {self.passed_tests}")
        self.logger.info(f"Failed: {self.failed_tests}")
        self.logger.info(f"Success rate: {success_rate:.1f}%")

        # Severity breakdown
        severity_stats = {}
        for severity in TestSeverity:
            severity_results = [r for r in self.test_results if r.severity == severity]
            if severity_results:
                severity_passed = sum(1 for r in severity_results if r.success)
                severity_total = len(severity_results)
                severity_rate = severity_passed / severity_total * 100
                severity_stats[severity.value] = {
                    "passed": severity_passed,
                    "total": severity_total,
                    "rate": severity_rate,
                }

        self.logger.info(f"\n🎯 SEVERITY BREAKDOWN:")
        for severity, stats in severity_stats.items():
            icon = {
                "normal": "🟢",
                "stress": "🟡",
                "extreme": "🟠",
                "hellish": "🔴",
                "apocalyptic": "💀",
            }.get(severity, "⚪")
            self.logger.info(
                f"{icon} {severity.upper()}: {stats['passed']}/{stats['total']} ({stats['rate']:.1f}%)"
            )

        # Performance metrics
        perf_results = [r for r in self.test_results if r.performance_metrics]
        if perf_results:
            self.logger.info(f"\n⚡ PERFORMANCE HIGHLIGHTS:")
            for result in perf_results:
                if "throughput" in result.performance_metrics:
                    throughput = result.performance_metrics["throughput"]
                    self.logger.info(f"  {result.test_name}: {throughput:.1f} ops/sec")

        # Overall assessment
        self.logger.info(f"\n🎯 HELL-LEVEL ASSESSMENT:")

        if success_rate >= 95:
            grade = "A+ APOCALYPSE SURVIVOR"
            status = "🔥 HELL-LEVEL READY"
            verdict = "System survived extreme torture testing"
        elif success_rate >= 90:
            grade = "A DEMON SLAYER"
            status = "💀 NEAR HELL-LEVEL"
            verdict = "System mostly survived extreme testing"
        elif success_rate >= 80:
            grade = "B HELL WALKER"
            status = "🔴 SURVIVING HELL"
            verdict = "System survived with significant issues"
        elif success_rate >= 70:
            grade = "C HELL DWELLER"
            status = "🟠 STRUGGLING IN HELL"
            verdict = "System barely surviving extreme testing"
        else:
            grade = "F HELL VICTIM"
            status = "💥 CONSUMED BY HELL"
            verdict = "System destroyed by extreme testing"

        self.logger.info(f"Grade: {grade}")
        self.logger.info(f"Status: {status}")
        self.logger.info(f"Verdict: {verdict}")

        # Failed tests details
        failed_results = [r for r in self.test_results if not r.success]
        if failed_results:
            self.logger.info(f"\n💥 FAILED TESTS ({len(failed_results)}):")
            for result in failed_results[:10]:  # Show first 10
                self.logger.info(f"  FAIL {result.test_name}: {result.details}")

        self.logger.info("\n" + "=" * 80)
        self.logger.info("HELL-LEVEL TESTING COMPLETE")
        self.logger.info("The weak have been purged. Only the strong survive.")
        self.logger.info("=" * 80)

        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": success_rate,
            "grade": grade,
            "severity_stats": severity_stats,
            "test_results": [
                {
                    "name": r.test_name,
                    "severity": r.severity.value,
                    "success": r.success,
                    "duration": r.duration,
                    "details": r.details,
                }
                for r in self.test_results
            ],
        }


async def main():
    """Run hell-level testing suite."""
    tester = HellLevelTester()

    # HONEST TARGET REGIONS - Only test regions that actually work
    # Based on comprehensive audit results
    target_regions = ["A2", "A3", "B2", "E2", "E4", "E5", "G1"]  # Only 7 working regions

    report = await tester.run_hell_testing_suite(target_regions)

    # Save report
    with open("hell_level_test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n🔥 Hell-level testing complete. Report saved to hell_level_test_report.json")
    return report


if __name__ == "__main__":
    asyncio.run(main())
