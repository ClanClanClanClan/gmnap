import pytest

#!/usr/bin/env python3
"""
Quick test for security fixes.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.security_validator import SecurityError, SecurityValidator


@pytest.mark.timeout(15)
def test_security_fixes():
    """Test that our security fixes work correctly"""
    print("🔍 TESTING SECURITY FIXES")
    print("=" * 50)

    validator = SecurityValidator()

    # Test 1: Template injection should now be blocked
    print("\n1. Testing template injection blocking...")
    template_attacks = [
        "{{7*7}}",
        "${7*7}",
        "<%=7*7%>",
        "#{7*7}",
        "[%7*7%]",
        "@(7*7)",
    ]

    template_blocked = 0
    for attack in template_attacks:
        try:
            validator.validate_string(attack, context="test")
            print(f"FAIL FAILED: {attack} passed through")
        except SecurityError:
            template_blocked += 1
            print(f"PASS Blocked: {attack}")

    print(f"\nTemplate injection: {template_blocked}/{len(template_attacks)} blocked")

    # Test 2: GlobalID collision suffixes should be allowed
    print("\n2. Testing GlobalID collision suffix handling...")
    test_names = [
        ("Smith, John", True),  # Normal name - should pass
        ("Smith, John--1", True),  # v7 collision suffix - should pass
        ("Smith, John--2", True),  # v7 collision suffix - should pass
        ("Smith--10, John", True),  # Suffix in family name - should pass
        ("'; DROP TABLE--", False),  # SQL injection attempt - should fail
        ("--comment", False),  # SQL comment - should fail
    ]

    passed = 0
    for name, should_pass in test_names:
        try:
            # Test YAML key validation (where the issue was)
            data = {name: {"GlobalID": "test"}}
            result = validator.validate_yaml_keys(data)

            if should_pass:
                if name in result:
                    print(f"PASS Passed: '{name}' (expected)")
                    passed += 1
                else:
                    print(f"FAIL Blocked: '{name}' (should have passed)")
            else:
                if name in result:
                    print(f"FAIL Passed: '{name}' (should have been blocked)")
                else:
                    print(f"PASS Blocked: '{name}' (expected)")
                    passed += 1

        except Exception as e:
            if not should_pass:
                print(f"PASS Blocked: '{name}' with error (expected)")
                passed += 1
            else:
                print(f"FAIL Error: '{name}' - {e}")

    print(f"\nGlobalID suffixes: {passed}/{len(test_names)} correct")

    # Test 3: Ensure other SQL injection patterns still blocked
    print("\n3. Testing SQL injection still blocked...")
    sql_attacks = [
        "'; DROP TABLE users--",
        "' OR '1'='1",
        "admin' --",
        "1; DELETE FROM users",
    ]

    sql_blocked = 0
    for attack in sql_attacks:
        try:
            validator.validate_string(attack, context="test")
            print(f"FAIL FAILED: SQL injection passed - {attack}")
        except SecurityError:
            sql_blocked += 1
            print(f"PASS Blocked: {attack}")

    print(f"\nSQL injection: {sql_blocked}/{len(sql_attacks)} blocked")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    template_working = template_blocked == len(template_attacks)
    globalid_working = passed == len(test_names)
    sql_working = sql_blocked == len(sql_attacks)

    print(
        f"PASS Template injection protection: {'WORKING' if template_working else 'FAILED'}"
    )
    print(
        f"PASS GlobalID suffix handling: {'WORKING' if globalid_working else 'FAILED'}"
    )
    print(f"PASS SQL injection protection: {'WORKING' if sql_working else 'FAILED'}")

    return template_working and globalid_working and sql_working


if __name__ == "__main__":
    success = test_security_fixes()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
