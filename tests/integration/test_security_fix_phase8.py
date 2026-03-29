
#!/usr/bin/env python3
"""
Test ULTRAFIX Phase 8 security fixes
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

print("🔒 TESTING SECURITY FIXES")
print("=" * 60)

manager = RegionManager()

# Test cases that were passing through
security_test_cases = [
    # Windows paths
    ("C:\\Windows\\System32\\drivers\\etc\\hosts", "Windows absolute path"),
    ("D:/Users/Admin/passwords.txt", "Windows path with forward slash"),
    ("C:\\Program Files\\malware.exe", "Windows path with exe"),
    # Unix paths (attacks)
    ("/etc/passwd", "Unix path attack"),
    ("/home/user/.ssh/id_rsa", "Unix path attack"),
    ("/var/log/secure", "Unix path attack"),
    # Emoji/symbol attacks
    ("㊗️🈲🈯️🈳🈵🈴🈲🈱", "Pure emoji string"),
    ("💣💥🔥", "Emoji bomb"),
    ("👤👤👤", "Symbol only"),
    # Mixed attacks
    ("John/../../etc/passwd", "Name with path traversal"),
    ("test.exe", "Name with executable extension"),
    ("javascript:alert(1)", "JavaScript protocol"),
    ("<script>alert('xss')</script>", "Script tag"),
    # Valid names that should pass
    ("John Smith", "Normal name"),
    ("François Müller", "Name with diacritics"),
    ("李明", "Chinese name"),
    ("محمد", "Arabic name"),
]

blocked = 0
passed = 0

for test_input, description in security_test_cases:
    result = manager.detect_region({"name": test_input})

    # Check if this is an attack that should be blocked
    should_block = any(
        keyword in description.lower()
        for keyword in [
            "path",
            "emoji",
            "symbol",
            "exe",
            "script",
            "javascript",
            "traversal",
        ]
    )

    is_blocked = result.region_code == "Z0" and (
        "quarantine" in result.detection_method
        or "security-blocked" in result.detection_method
    )

    if should_block:
        # These should be blocked
        if is_blocked:
            print(
                f"PASS {description}: BLOCKED - {result.metadata.get('quarantine_reason', result.metadata.get('error'))}"
            )
            blocked += 1
        else:
            print(f"FAIL {description}: PASSED through as {result.region_code}")
            passed += 1
    else:
        # Valid names should not be blocked
        if not is_blocked:
            print(f"PASS {description}: Allowed - {result.region_code}")
            blocked += 1  # Count as success
        else:
            print(f"FAIL {description}: Wrongly blocked - {result.metadata}")
            passed += 1

total = len(security_test_cases)
print("\n📊 Security Results:")
print(f"  Correctly handled: {blocked}/{total}")
print(f"  Security issues: {passed}/{total}")

if passed == 0:
    print("PASS SECURITY FIXED! All attacks blocked, valid names allowed.")
else:
    print(f"FAIL {passed} security issues remain")
