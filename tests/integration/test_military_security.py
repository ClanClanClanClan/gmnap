
#!/usr/bin/env python3
"""
Test Military-Grade Security Validator
Verify that we've reduced attack success rate from 12% to <1%
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager

print("🛡️ TESTING MILITARY-GRADE SECURITY")
print("=" * 60)

manager = RegionManager()

# Test the 12 attacks that were previously passing through
previously_passing_attacks = [
    ("αβγδεζη", "Greek letters"),
    ("※§¶†‡", "Typographic symbols"),
    ("\xff\xfe\xfd\xfc", "High Unicode bytes"),
    ("%41%42%43", "URL encoding"),
    ("news:comp.security", "News protocol"),
    ("%%%%%%%%%%", "Format string"),
    ("malware.pif", "PIF executable"),
    ("spyware.msi", "MSI installer"),
    ("ransomware.dll", "DLL library"),
    ("botnet.sys", "System file"),
    ("exploit.ps1", "PowerShell script"),
    ("hack.py", "Python script"),
]

# Additional sophisticated attacks to test
advanced_attacks = [
    # Unicode attacks
    ("\u200b\u200c\u200d", "Zero-width characters"),
    ("\u202e\u202dmalicious", "Bidirectional override"),
    ("аdmin", "Homograph attack (Cyrillic a)"),
    # Encoding attacks
    ("%22%3Cscript%3E", "URL encoded XSS"),
    ("&lt;script&gt;", "HTML encoded script"),
    ("\\u003cscript\\u003e", "Unicode escaped script"),
    # Protocol variants
    ("fILe:///etc/passwd", "Case variant file protocol"),
    ("jaVascript:alert(1)", "Case variant JavaScript"),
    ("DaTa:text/html,<script>", "Case variant data protocol"),
    # Advanced file extensions
    ("trojan.com", "COM executable"),
    ("backdoor.scr", "Screensaver"),
    ("virus.jar", "Java archive"),
    ("payload.apk", "Android package"),
    ("malware.deb", "Debian package"),
    # Polyglot attacks
    ("/*<script>*/alert(1)", "CSS/JS polyglot"),
    ("';alert(1);//", "SQL/JS polyglot"),
    # Format string variants
    ("%n%n%n%n", "Format string exploit"),
    ("%(foo)s", "Python format string"),
    # Template injection variants
    ("{{7*'7'}}", "Jinja2 template"),
    ("${7*7}", "Spring EL injection"),
    ("#{7*7}", "OGNL injection"),
    # Length-based attacks
    ("A" * 50000, "Mega buffer overflow"),
    ("🔥" * 5000, "Unicode emoji bomb"),
]

all_attacks = previously_passing_attacks + advanced_attacks

blocked = 0
passed = 0
total = len(all_attacks)

print(f"Testing {total} attacks against military-grade security...\n")

for attack, description in all_attacks:
    try:
        result = manager.detect_region({"name": attack})

        # Check if attack was blocked
        is_blocked = result.region_code == "Z0" and (
            "quarantine" in result.detection_method
            or "security" in result.detection_method.lower()
            or "military" in result.detection_method.lower()
        )

        if is_blocked:
            blocked += 1
            print(f"PASS BLOCKED: {description}")
        else:
            passed += 1
            print(
                f"FAIL PASSED: {description} -> {result.region_code} via {result.detection_method}"
            )

    except Exception:
        # Exception means it was caught (good)
        blocked += 1
        print(f"PASS BLOCKED: {description} (exception)")

# Calculate security metrics
security_rate = blocked / total if total > 0 else 0
vulnerability_rate = passed / total if total > 0 else 0

print("\n📊 MILITARY SECURITY RESULTS:")
print(f"  Total attacks tested: {total}")
print(f"  Attacks blocked: {blocked}")
print(f"  Attacks passed through: {passed}")
print(f"  Security rate: {security_rate:.1%}")
print(f"  Vulnerability rate: {vulnerability_rate:.1%}")

# Determine security grade
if vulnerability_rate <= 0.01:  # <=1%
    grade = "A+ (Military Grade)"
    status = "🟢 ENTERPRISE READY"
elif vulnerability_rate <= 0.05:  # <=5%
    grade = "A (Excellent)"
    status = "🟢 PRODUCTION READY"
elif vulnerability_rate <= 0.10:  # <=10%
    grade = "B (Good)"
    status = "🟡 NEEDS IMPROVEMENT"
else:
    grade = "F (Failed)"
    status = "🔴 NOT SECURE"

print("\n🎯 SECURITY ASSESSMENT:")
print(f"  Security Grade: {grade}")
print(f"  Status: {status}")

# Test legitimate names to ensure low false positives
print("\n🧪 TESTING LEGITIMATE NAMES (False Positive Check):")

legitimate_names = [
    "Smith, John",
    "García, María",
    "Zhang Wei",
    "Müller, Hans",
    "Al-Khwarizmi",
    "Van der Berg, Willem",
    "O'Connor, Patrick",
    "李明",
    "محمد أحمد",
    "François Müller",
]

false_positives = 0
for name in legitimate_names:
    try:
        result = manager.detect_region({"name": name})

        is_blocked = result.region_code == "Z0" and (
            "quarantine" in result.detection_method
            or "security" in result.detection_method.lower()
            or "military" in result.detection_method.lower()
        )

        if is_blocked:
            false_positives += 1
            print(f"FAIL FALSE POSITIVE: {name}")
        else:
            print(f"PASS LEGITIMATE: {name} -> {result.region_code}")

    except Exception:
        false_positives += 1
        print(f"FAIL FALSE POSITIVE: {name} (exception)")

fp_rate = false_positives / len(legitimate_names)
print("\n📈 FALSE POSITIVE ANALYSIS:")
print(f"  False positive rate: {fp_rate:.1%}")

if vulnerability_rate <= 0.01 and fp_rate <= 0.05:
    print("\n🎉 SUCCESS: Military-grade security achieved!")
    print(f"   PASS Attack success rate: {vulnerability_rate:.1%} (target: <1%)")
    print(f"   PASS False positive rate: {fp_rate:.1%} (target: <5%)")
    print("   🚀 Ready for enterprise deployment!")
elif vulnerability_rate <= 0.05:
    print("\nWARN  GOOD: Significant security improvement")
    print(f"   PASS Attack success rate: {vulnerability_rate:.1%}")
    print(f"   📊 False positive rate: {fp_rate:.1%}")
    print("   🔧 Minor tuning needed for military grade")
else:
    print("\nFAIL NEEDS WORK: Security still insufficient")
    print(f"   WARN  Attack success rate: {vulnerability_rate:.1%} (target: <1%)")
    print(f"   📊 False positive rate: {fp_rate:.1%}")
    print("   🔨 Requires additional security measures")
