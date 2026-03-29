#!/usr/bin/env python3
"""
ULTRACHECK MANIACAL HELL-LEVEL TESTING
No mercy. No bias. ACTIVELY TRYING TO BREAK THE SYSTEM.
"""

import gc
import json
import random
import sys
import threading
import time
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("🔥 ULTRACHECK MANIACAL HELL-LEVEL TESTING")
print("=" * 80)
print("ASSUMING SYSTEM IS GUILTY UNTIL PROVEN INNOCENT")
print("ACTIVELY TRYING TO BREAK EVERYTHING")
print("=" * 80)

# Hell-level audit results
hell_audit = {
    "timestamp": datetime.now().isoformat(),
    "tests_run": 0,
    "failures_found": 0,
    "critical_breaks": [],
    "performance_breaks": [],
    "memory_leaks": [],
    "race_conditions": [],
    "data_corruption": [],
    "security_breaches": [],
}


def hell_test(test_name, test_func, expected_failure_rate=0):
    """Run a hell test expecting it to find problems"""
    global hell_audit
    print(f"\n💀 HELL TEST: {test_name}")
    print("-" * 60)

    try:
        result = test_func()
        hell_audit["tests_run"] += 1

        if result["broken"]:
            hell_audit["failures_found"] += 1
            hell_audit["critical_breaks"].extend(result["breaks"])
            print(f"💥 SYSTEM BROKEN: Found {len(result['breaks'])} critical issues")
            for issue in result["breaks"]:
                print(f"   🚨 {issue}")
        else:
            success_rate = result.get("success_rate", 100)
            if success_rate < (100 - expected_failure_rate):
                hell_audit["failures_found"] += 1
                print(
                    f"WARN BELOW THRESHOLD: {success_rate:.1f}% (expected >{100-expected_failure_rate}%)"
                )
            else:
                print(f"😈 SURVIVED: {result['summary']} (but we'll keep trying)")

        return result
    except Exception as e:
        hell_audit["failures_found"] += 1
        hell_audit["critical_breaks"].append(
            f"{test_name}: Test framework crashed - {str(e)}"
        )
        print(f"💥 TEST FRAMEWORK CRASHED: {e}")
        traceback.print_exc()
        return {"broken": True, "breaks": [f"Test crashed: {e}"]}


# Initialize the victim system
print("🎯 Loading victim system...")
try:
    from src.regions.manager_optimized import RegionManager

    manager = RegionManager()
    print("PASS Victim loaded and ready for torture")
except Exception as e:
    print(f"💥 VICTIM FAILED TO LOAD: {e}")
    # sys.exit(1)  # MOVED: Was at module level


# HELL TEST 1: Unicode Apocalypse - Every possible Unicode character
def unicode_apocalypse():
    """Throw EVERY Unicode character at the system"""
    breaks = []
    tested = 0
    crashed = 0

    print("Testing all Unicode blocks...")

    # Test every Unicode block
    unicode_ranges = [
        (0x0000, 0x007F, "ASCII"),
        (0x0080, 0x00FF, "Latin-1"),
        (0x0100, 0x017F, "Latin Extended-A"),
        (0x0180, 0x024F, "Latin Extended-B"),
        (0x1E00, 0x1EFF, "Latin Extended Additional"),
        (0x0370, 0x03FF, "Greek"),
        (0x0400, 0x04FF, "Cyrillic"),
        (0x0590, 0x05FF, "Hebrew"),
        (0x0600, 0x06FF, "Arabic"),
        (0x4E00, 0x9FFF, "CJK Unified Ideographs"),
        (0x3040, 0x309F, "Hiragana"),
        (0x30A0, 0x30FF, "Katakana"),
        (0xAC00, 0xD7AF, "Hangul Syllables"),
        (0xFFF0, 0xFFFF, "Specials"),
        (0x10000, 0x1007F, "Linear B"),
        (0x1F600, 0x1F64F, "Emoticons"),
    ]

    for start, end, name in unicode_ranges:
        print(f"  Torturing with {name} block...")

        # Test 100 random chars from each block
        for _ in range(100):
            try:
                char_code = random.randint(start, min(end, 0x10FFFF))
                char = chr(char_code)

                # Skip invalid characters
                if unicodedata.category(char) in ("Cc", "Cs", "Co"):
                    continue

                test_name = f"{char} (U+{char_code:04X})"
                result = manager.detect_region({"name": test_name})
                tested += 1

                # Check for system breaks
                if result is None:
                    breaks.append(f"Unicode {name} U+{char_code:04X} returned None")
                    crashed += 1

            except Exception as e:
                crashed += 1
                if "encoding" not in str(e).lower():  # Encoding errors are expected
                    breaks.append(
                        f"Unicode {name} U+{char_code:04X} crashed: {str(e)[:100]}"
                    )

    crash_rate = (crashed / tested) * 100 if tested > 0 else 100

    return {
        "broken": len(breaks) > 10 or crash_rate > 5,
        "breaks": breaks[:20],  # Limit output
        "summary": f"Tested {tested} Unicode chars, {crashed} crashes ({crash_rate:.1f}%)",
        "success_rate": max(0, 100 - crash_rate),
    }


hell_test("Unicode Apocalypse", unicode_apocalypse, expected_failure_rate=5)


# HELL TEST 2: Scale Torture - Realistic mathematician database sizes
def scale_torture():
    """Test with 100,000+ entries like real databases"""
    breaks = []

    print("Generating 100,000 realistic mathematician names...")

    # Generate realistic names from different regions
    name_templates = [
        ("John {surname}", ["Smith", "Johnson", "Williams", "Brown", "Jones"]),
        ("Marie {surname}", ["Dupont", "Martin", "Bernard", "Petit", "Robert"]),
        ("{name} Petrov", ["Ivan", "Vladimir", "Sergei", "Dmitri", "Pavel"]),
        ("Ahmed {surname}", ["Hassan", "Ali", "Mohammad", "Ibrahim", "Omar"]),
        ("{name} Singh", ["Raj", "Amit", "Suresh", "Vikram", "Ravi"]),
        ("李{name}", ["明", "华", "伟", "强", "军"]),
        ("田中{name}", ["太郎", "花子", "一郎", "美咲", "健"]),
        ("José {surname}", ["García", "Rodríguez", "González", "Fernández", "López"]),
    ]

    test_names = []
    for _ in range(100000):
        template, options = random.choice(name_templates)
        if "{surname}" in template:
            name = template.format(surname=random.choice(options))
        else:
            name = template.format(name=random.choice(options))
        test_names.append(name)

    print(f"Testing {len(test_names)} names for performance...")

    # Performance test
    start_time = time.time()
    processed = 0
    errors = 0
    timeouts = 0

    for i, name in enumerate(test_names):
        try:
            # Timeout individual operations
            start_op = time.time()
            result = manager.detect_region({"name": name})
            op_time = time.time() - start_op

            if op_time > 1.0:  # 1 second per name is too slow
                timeouts += 1
                if timeouts == 1:
                    breaks.append(
                        f"First timeout at name {i}: {name} took {op_time:.2f}s"
                    )

            if result is None:
                errors += 1
                if errors <= 10:  # Only log first 10 errors
                    breaks.append(f"Name {i} returned None: {name}")

            processed += 1

            # Progress report
            if processed % 10000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(
                    f"    Processed {processed:,}, rate: {rate:.0f}/sec, errors: {errors}, timeouts: {timeouts}"
                )

            # Emergency brake - if too many errors/timeouts
            if errors > 1000 or timeouts > 1000:
                breaks.append(f"Emergency brake: {errors} errors, {timeouts} timeouts")
                break

        except Exception as e:
            errors += 1
            if errors <= 10:
                breaks.append(f"Name {i} crashed: {name} -> {str(e)[:100]}")
            if errors > 10000:  # Too many crashes
                break

    total_time = time.time() - start_time
    final_rate = processed / total_time if total_time > 0 else 0
    error_rate = (errors / processed) * 100 if processed > 0 else 100
    timeout_rate = (timeouts / processed) * 100 if processed > 0 else 100

    # Check if system is broken
    is_broken = (
        error_rate > 1  # More than 1% errors
        or timeout_rate > 0.1  # More than 0.1% timeouts
        or final_rate < 1000  # Less than 1000/sec
        or len(breaks) > 5  # Multiple critical issues
    )

    return {
        "broken": is_broken,
        "breaks": breaks,
        "summary": f"Processed {processed:,}/{len(test_names):,}, {final_rate:.0f}/sec, {error_rate:.2f}% errors",
        "success_rate": max(0, 100 - error_rate - timeout_rate),
    }


hell_test("Scale Torture (100K entries)", scale_torture, expected_failure_rate=1)


# HELL TEST 3: Concurrent Chaos - Multiple threads hammering the system
def concurrent_chaos():
    """Multiple threads hitting the system simultaneously"""
    breaks = []
    results_lock = threading.Lock()

    def worker_thread(thread_id, iterations=1000):
        thread_errors = []
        thread_results = []

        test_names = [f"Thread{thread_id}User{i}" for i in range(iterations)]

        for i, name in enumerate(test_names):
            try:
                result = manager.detect_region({"name": name})
                if result is None:
                    thread_errors.append(f"T{thread_id}:{i} returned None")
                else:
                    thread_results.append(result.region_code)
            except Exception as e:
                thread_errors.append(f"T{thread_id}:{i} crashed: {str(e)[:50]}")

        with results_lock:
            if len(thread_errors) > 0:
                breaks.extend(thread_errors[:10])  # Limit per thread

    print("Starting 10 concurrent threads...")
    threads = []
    start_time = time.time()

    for i in range(10):
        t = threading.Thread(target=worker_thread, args=(i, 1000))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join(timeout=60)  # 60 second timeout
        if t.is_alive():
            breaks.append("Thread hung and timed out")

    elapsed = time.time() - start_time
    error_rate = (len(breaks) / 10000) * 100  # 10 threads * 1000 operations each

    return {
        "broken": len(breaks) > 50
        or elapsed > 120,  # Should complete in under 2 minutes
        "breaks": breaks,
        "summary": f"10 threads, {10000} total ops, {len(breaks)} errors, {elapsed:.1f}s",
        "success_rate": max(0, 100 - error_rate),
    }


hell_test("Concurrent Chaos (10 threads)", concurrent_chaos, expected_failure_rate=5)


# HELL TEST 4: Memory Destruction - Look for memory leaks
def memory_destruction():
    """Test for memory leaks with massive operations"""
    breaks = []

    import os

    import psutil

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"Initial memory: {initial_memory:.1f} MB")

    # Run 50,000 operations and check memory growth
    test_name = "MemoryTestName" * 10  # 140 char string

    for i in range(50000):
        try:
            manager.detect_region({"name": f"{test_name}{i}"})

            # Check memory every 10,000 operations
            if i % 10000 == 0 and i > 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                growth_rate = memory_growth / (i / 1000)  # MB per 1K operations

                print(
                    f"    {i:,} ops: {current_memory:.1f} MB (+{memory_growth:.1f} MB, {growth_rate:.3f} MB/1K ops)"
                )

                if memory_growth > 500:  # More than 500MB growth is concerning
                    breaks.append(
                        f"Excessive memory growth: {memory_growth:.1f} MB after {i:,} operations"
                    )

                if growth_rate > 0.1:  # More than 0.1MB per 1000 operations
                    breaks.append(
                        f"Memory leak detected: {growth_rate:.3f} MB per 1K operations"
                    )

        except Exception as e:
            breaks.append(f"Memory test crashed at iteration {i}: {str(e)[:50]}")
            break

    final_memory = process.memory_info().rss / 1024 / 1024
    total_growth = final_memory - initial_memory

    return {
        "broken": total_growth > 100
        or len(breaks) > 0,  # More than 100MB growth is bad
        "breaks": breaks,
        "summary": f"50K ops: {initial_memory:.1f} -> {final_memory:.1f} MB (+{total_growth:.1f} MB)",
        "success_rate": 100 if total_growth < 100 and len(breaks) == 0 else 0,
    }


hell_test("Memory Destruction", memory_destruction, expected_failure_rate=0)


# HELL TEST 5: Malicious Data Injection - Advanced attack vectors
def malicious_data_injection():
    """Advanced attack vectors beyond basic injection"""
    breaks = []

    # Advanced attack payloads
    advanced_attacks = [
        # Polyglot attacks (multiple injection types in one)
        "'; DROP TABLE users; --<script>alert(1)</script>${7*7}",
        # Unicode attacks
        "\uff1c\uff53\uff43\uff52\uff49\uff50\uff54\uff1e",  # Fullwidth script tag
        # Double encoding attacks
        "%253Cscript%253Ealert(1)%253C/script%253E",
        # XML/XXE attacks
        "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><root>&xxe;</root>",
        # Server-side template injection
        "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
        "#{7*7}",
        "${T(java.lang.System).getProperty('user.name')}",
        # NoSQL injection
        "'; return db.users.find(); var dummy='",
        "' || '1'=='1",
        # LDAP injection
        "*)(uid=*))(|(uid=*",
        # Command injection variations
        "|whoami",
        "`whoami`",
        "$(whoami)",
        "& ping 127.0.0.1 &",
        # Buffer overflow attempts
        "A" * 10000,
        "A" * 100000,
        # Format string attacks
        "%x%x%x%x%x%x%x%x",
        "%s%s%s%s%s%s%s%s",
        # Zip bombs (compressed)
        "PK\x03\x04" + "0" * 1000,
        # Binary exploits
        "\x90" * 100 + "\x31\xc0\x50\x68",  # NOP sled + shellcode start
        # Timing attacks
        "'; WAITFOR DELAY '00:00:05' --",
        # JSON/YAML bombs
        '{"a": "' + "B" * 10000 + '"}',
        # Regex DoS
        "a" * 1000 + "!",
        "(a+)+$",
        # Unicode normalization attacks
        "\u0041\u030a",  # A + combining ring above
        # Homograph attacks
        "\u0430\u043e\u043c\u0430\u0438\u043d.com",  # Cyrillic chars that look like ASCII
    ]

    print(f"Testing {len(advanced_attacks)} advanced attack vectors...")

    reflected_attacks = 0
    bypassed_security = 0

    for i, attack in enumerate(advanced_attacks):
        try:
            result = manager.detect_region({"name": attack})

            # Check if attack was reflected in output (BAD)
            result_str = str(result.__dict__)
            if any(part in result_str for part in attack.split()[:3] if len(part) > 3):
                reflected_attacks += 1
                breaks.append(f"Attack {i+1} reflected in output: {attack[:30]}...")

            # Check if attack bypassed security (got processed as normal name)
            if (
                result.region_code != "Z0"
                and result.confidence > 0.3
                and "error" not in result.metadata
            ):
                bypassed_security += 1
                breaks.append(
                    f"Attack {i+1} bypassed security: {attack[:30]}... -> {result.region_code}"
                )

        except Exception as e:
            # Some crashes might indicate successful attacks
            error_msg = str(e).lower()
            if any(
                keyword in error_msg
                for keyword in ["eval", "exec", "system", "command"]
            ):
                breaks.append(
                    f"Attack {i+1} caused suspicious crash: {attack[:30]}... -> {str(e)[:50]}"
                )

    reflection_rate = (reflected_attacks / len(advanced_attacks)) * 100
    bypass_rate = (bypassed_security / len(advanced_attacks)) * 100

    return {
        "broken": reflected_attacks > 0 or bypassed_security > 5,
        "breaks": breaks,
        "summary": f"{len(advanced_attacks)} attacks: {reflected_attacks} reflected, {bypassed_security} bypassed",
        "success_rate": max(0, 100 - reflection_rate - bypass_rate),
    }


hell_test("Malicious Data Injection", malicious_data_injection, expected_failure_rate=0)


# HELL TEST 6: Data Corruption Scenarios
def data_corruption_scenarios():
    """Test with corrupted, malformed, and impossible data"""
    breaks = []

    corrupted_data = [
        # Truncated data
        {"name": "John"[:-1]},  # Empty string
        {"name": "A"},  # Single char
        {"name": "AB"},  # Two chars
        # Mixed encodings (impossible in Python strings, but simulate)
        {"name": "John\udcffSmith"},  # Surrogate escape
        # Impossible Unicode sequences
        {"name": "\ud800"},  # Lone high surrogate
        {"name": "\udfff"},  # Lone low surrogate
        # Control characters
        {"name": "John\x00Smith"},  # Null byte
        {"name": "John\x01\x02\x03Smith"},  # Control chars
        {"name": "John\x7fSmith"},  # DEL character
        # Normalization hell
        {"name": "e\u0301"},  # Combining acute accent
        {"name": "e\u0301\u0300\u0302"},  # Multiple combining chars
        # Bidirectional text attacks
        {"name": "John\u202esmithSmith\u202d"},  # RTL override
        # Zero-width characters
        {"name": "Jo\u200bhn"},  # Zero-width space
        {"name": "John\ufeff"},  # Zero-width no-break space
        # Deeply nested structures (if JSON processing is involved)
        {"name": "John", "nested": {"deep": {"deeper": {"deepest": "attack"}}}},
        # Extremely long fields
        {"name": "A", "other_field": "B" * 1000000},
        # Type confusion
        {"name": ["John", "Smith"]},  # Array instead of string
        {"name": {"first": "John", "last": "Smith"}},  # Object instead of string
        {"name": 42.0},  # Float that looks like int
        {"name": float("inf")},  # Infinity
        {"name": float("nan")},  # NaN
        # Encoding edge cases
        {"name": "\U0010ffff"},  # Highest Unicode codepoint
        {"name": "\U0001f4a9"},  # Pile of poo emoji
        # Empty/null variations
        {"name": ""},
        {"name": None},
        {},
        None,
    ]

    print(f"Testing {len(corrupted_data)} data corruption scenarios...")

    crashes = 0
    hangs = 0
    corruption_detected = 0

    for i, corrupt_data in enumerate(corrupted_data):
        try:
            start_time = time.time()
            result = manager.detect_region(corrupt_data)
            elapsed = time.time() - start_time

            if elapsed > 5.0:  # Took more than 5 seconds
                hangs += 1
                breaks.append(
                    f"Corruption {i+1} caused hang ({elapsed:.1f}s): {str(corrupt_data)[:50]}"
                )

            # Check for unexpected behavior
            if result is not None and hasattr(result, "region_code"):
                if result.region_code not in [
                    "A1",
                    "A2",
                    "B1",
                    "B2",
                    "C1",
                    "C2",
                    "C3",
                    "C4",
                    "D1",
                    "E1",
                    "E3",
                    "E4",
                    "G1",
                    "Z0",
                ]:
                    corruption_detected += 1
                    breaks.append(
                        f"Corruption {i+1} caused invalid region: {result.region_code}"
                    )

        except Exception as e:
            crashes += 1
            # Some crashes are expected for corrupted data
            if not any(
                expected in str(e).lower()
                for expected in ["invalid", "error", "bad", "malformed"]
            ):
                breaks.append(
                    f"Corruption {i+1} caused unexpected crash: {str(e)[:50]}"
                )

    crash_rate = (crashes / len(corrupted_data)) * 100
    hang_rate = (hangs / len(corrupted_data)) * 100

    return {
        "broken": hangs > 0 or corruption_detected > 0 or crash_rate > 50,
        "breaks": breaks,
        "summary": f"{len(corrupted_data)} corrupted inputs: {crashes} crashes ({crash_rate:.1f}%), {hangs} hangs",
        "success_rate": max(0, 100 - hang_rate - (corruption_detected * 10)),
    }


hell_test(
    "Data Corruption Scenarios", data_corruption_scenarios, expected_failure_rate=30
)

# FINAL HELL ASSESSMENT
print("\n" + "=" * 80)
print("💀 FINAL HELL-LEVEL ASSESSMENT")
print("=" * 80)

total_tests = hell_audit["tests_run"]
total_failures = hell_audit["failures_found"]
survival_rate = (
    ((total_tests - total_failures) / total_tests * 100) if total_tests > 0 else 0
)

print(
    f"\n🔥 HELL SURVIVAL RATE: {survival_rate:.1f}% ({total_tests - total_failures}/{total_tests} tests survived)"
)
print(f"💀 CRITICAL BREAKS FOUND: {len(hell_audit['critical_breaks'])}")

if len(hell_audit["critical_breaks"]) > 0:
    print("\n🚨 CRITICAL SYSTEM BREAKS:")
    for i, break_desc in enumerate(hell_audit["critical_breaks"][:20]):  # Show first 20
        print(f"   {i+1}. {break_desc}")
    if len(hell_audit["critical_breaks"]) > 20:
        print(f"   ... and {len(hell_audit['critical_breaks']) - 20} more breaks")

# Maniacal verdict
if survival_rate >= 95 and len(hell_audit["critical_breaks"]) == 0:
    verdict = "🔥 SURVIVED THE HELL - TRULY PRODUCTION READY"
    emoji = "🔥PASS"
elif survival_rate >= 90:
    verdict = "😈 MOSTLY SURVIVED - SOME ISSUES FOUND"
    emoji = "WARN"
elif survival_rate >= 80:
    verdict = "💀 BADLY DAMAGED - MAJOR ISSUES"
    emoji = "FAIL"
else:
    verdict = "🏴‍☠️ COMPLETELY DESTROYED - SYSTEM IS BROKEN"
    emoji = "💥"

print(f"\n{emoji} MANIACAL HELL VERDICT: {verdict}")

# Save the brutal truth
with open("ultracheck_maniacal_hell_results.json", "w") as f:
    json.dump(hell_audit, f, indent=2)

print("\n📄 Maniacal hell results saved to: ultracheck_maniacal_hell_results.json")
print("\n" + "=" * 80)
print("MANIACAL HELL TESTING COMPLETE")
print("THE TRUTH HAS BEEN REVEALED")
print("=" * 80)
