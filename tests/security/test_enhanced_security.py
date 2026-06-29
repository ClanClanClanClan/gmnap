#!/usr/bin/env python3
"""Test the enhanced security validator against the 3 attacks that once slipped through.

Migrated 2026-06-28 from V6. The original wrote these 3 payloads to YAML
and ran `src.core.pipeline_v6.GMNAPPipeline.run(dir)` (now deleted),
checking the on-disk output for survivors. The live gate behind that
behavior is `src.core.security_validator.SecurityValidator`, so this now
asserts the gate blocks each payload directly — the regression these
three cases guard against (ReDoS, combining-character stacking, Cyrillic
homograph) lives entirely in the validator.
"""

import pytest

from src.core.security_validator import SecurityError, SecurityValidator


@pytest.mark.timeout(15)
def test_enhanced_security():
    """The 3 critical attacks that previously passed must now be blocked."""

    malicious_names = [
        # Regex DoS attack
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!",
        # Unicode combining character attack
        "Ä̈",
        # Homograph attack (Cyrillic lookalikes)
        "Аррӏе",
    ]

    validator = SecurityValidator()

    for name in malicious_names:
        with pytest.raises(SecurityError):
            validator.validate_string(name, context="CanonicalLatin")


if __name__ == "__main__":
    test_enhanced_security()
    print("PASS Enhanced security validation working correctly!")
