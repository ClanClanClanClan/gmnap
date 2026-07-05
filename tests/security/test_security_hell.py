#!/usr/bin/env python3
"""Hell-level security testing for GMNAP v7.

Migrated 2026-06-28 from V6. The original fed a YAML file of malicious
canonical names through `src.core.pipeline_v6.GMNAPPipeline.run(dir)`
(now deleted) and inspected the written output for leaked payloads. The
live injection gate that the pipeline relies on is
`src.core.security_validator.SecurityValidator` (wired into V7Pipeline's
stage 8 / region detection), so this now exercises that gate directly:
every malicious name MUST raise SecurityError before it can reach any
output sink. This is the same property the old end-to-end test asserted,
without depending on the deleted pipeline or on-disk output files.
"""

import pytest

from src.core.security_validator import SecurityError, SecurityValidator


@pytest.mark.timeout(15)
def test_security_hell():
    """Every malicious canonical name must be blocked by the security gate."""

    # Malicious canonical-name payloads. These were the YAML *keys* in the
    # V6 test (the non-string `12345` key was already filtered out before
    # YAML dump, so it is intentionally excluded here too).
    evil_names = [
        # SQL injection attempt
        "'; DROP TABLE users; --",
        # XSS attempt
        "<script>alert('XSS')</script>",
        # Command injection
        "; rm -rf /",
        # Buffer overflow attempt
        "A" * 10000,
        # Null byte injection
        "Smith\x00\x01\x02, John",
        # Unicode normalization attack (A + combining diaeresis)
        "Ä" + "̈",
        # Path traversal
        "../../../etc/passwd",
        # LDAP injection
        "admin)(|(password=*)",
        # XML injection
        "<?xml version='1.0'?><test>evil</test>",
        # Regex DoS
        "a" + "a" * 50 + "!",
        # Unicode direction override
        "‮abc",
        # Homograph attack (Cyrillic 'Apple')
        "Аррӏе",
        # Zero-width characters
        "John​‌‍Smith",
        # Control characters
        "Test\x1b[31mRed\x1b[0m",
    ]

    validator = SecurityValidator()

    blocked = []
    passed = []

    for name in evil_names:
        try:
            validator.validate_string(name, context="CanonicalLatin")
            # No SecurityError -> the gate let this malicious name through.
            passed.append(name)
        except SecurityError:
            blocked.append(name)

    # Every malicious payload must be blocked; none may pass.
    assert not passed, (
        f"SECURITY BREACH: {len(passed)} malicious name(s) were NOT blocked: "
        + ", ".join(repr(p)[:50] for p in passed)
    )
    assert len(blocked) == len(evil_names)


if __name__ == "__main__":
    test_security_hell()
    print("PASS SECURITY: All malicious inputs blocked!")
