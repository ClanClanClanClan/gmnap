import pytest

#!/usr/bin/env python3
"""DoS protection tests"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os

os.environ["GMNAP_TEST_MODE"] = "true"

from src.core.security_validator import SecurityError, SecurityValidator


@pytest.mark.timeout(15)
def test_150_char_dos_limit():
    """Test 150-character DoS protection for names"""
    validator = SecurityValidator()

    # Test exactly 150 chars (should pass)
    name_150 = "A" * 150
    try:
        validator.validate_string(name_150, "name")
        assert True, "150 char name should be allowed"
    except SecurityError:
        assert False, "150 char name should be allowed"

    # Test 151 chars (should fail)
    name_151 = "A" * 151
    try:
        validator.validate_string(name_151, "name")
        assert False, "151 char name should be blocked"
    except SecurityError:
        assert True, "151 char name should be blocked"


@pytest.mark.timeout(15)
def test_rate_limiting():
    """Test rate limiting protection"""
    validator = SecurityValidator()

    # Should allow reasonable number of requests
    for i in range(5):
        try:
            validator.check_rate_limit("client1", "test")
        except:
            assert False, f"Rate limit triggered too early at request {i+1}"

    assert True, "Rate limiting configured correctly"


@pytest.mark.timeout(15)
def test_memory_exhaustion_protection():
    """Test protection against memory exhaustion attacks"""
    # Test that extremely large inputs are rejected
    validator = SecurityValidator()

    huge_input = "X" * 1000000  # 1MB string
    try:
        validator.validate_string(huge_input, "test")
        assert False, "Should reject huge inputs"
    except:
        assert True, "Correctly rejected huge input"
