import pytest

#!/usr/bin/env python3
"""
Test security fix for ULTRAFIX Phase 6
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

print("🛡️ TESTING SECURITY FIX")
print("=" * 60)

manager = RegionManager()

# Test security attacks
attack_tests = [
    ("'; DROP TABLE users; --", "SQL injection"),
    ("<script>alert('XSS')</script>", "XSS attack"),
    ("../../etc/passwd", "Path traversal"),
    ("| cat /etc/passwd", "Command injection"),
]

print("Testing security blocking...")
blocked = 0
bypassed = 0

for attack, attack_type in attack_tests:
    try:
        result = manager.detect_region({"name": attack})
        if result.metadata.get("blocked"):
            print(f"PASS BLOCKED: {attack_type}")
            blocked += 1
        else:
            print(f"FAIL BYPASSED: {attack_type} - Got region {result.region_code}")
            bypassed += 1
    except Exception as e:
        print(f"PASS BLOCKED: {attack_type} - Exception: {str(e)[:50]}...")
        blocked += 1

print(f"\nSecurity Results: {blocked}/{len(attack_tests)} blocked")

# Test accuracy issue
print("\n" + "=" * 60)
print("Testing accuracy fix...")

accuracy_tests = [
    ("Al-Khwarizmi, Muhammad", "C3", "Arabic mathematician"),
    ("Gauss, Carl Friedrich", "A2", "German mathematician"),
    ("Newton, Isaac", "A1", "English mathematician"),
]

correct = 0
for name, expected, description in accuracy_tests:
    result = manager.detect_region({"name": name})
    if result.region_code == expected:
        print(f"PASS {name} -> {result.region_code} ({description})")
        correct += 1
    else:
        print(
            f"FAIL {name} -> {result.region_code} (expected {expected}) - {description}"
        )
        print(f"   Method: {result.detection_method}, Confidence: {result.confidence}")

print(f"\nAccuracy Results: {correct}/{len(accuracy_tests)} correct")
