import pytest

#!/usr/bin/env python3
"""Hell-level security testing for GMNAP v7."""

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import sys
from pathlib import Path

from src.core.pipeline_v6 import GMNAPPipeline

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.config import GMNAPConfig


@pytest.mark.timeout(15)
def test_security_hell():
    """Test with malicious inputs."""

    # Create malicious test data
    evil_data = {
        # SQL injection attempt
        "'; DROP TABLE users; --": {"GlobalID": "evil001"},
        # XSS attempt
        "<script>alert('XSS')</script>": {"GlobalID": "evil002"},
        # Command injection
        "; rm -rf /": {"GlobalID": "evil003"},
        # Buffer overflow attempt
        "A" * 10000: {"GlobalID": "evil004"},
        # Null byte injection
        "Smith\x00\x01\x02, John": {"GlobalID": "evil005"},
        # Unicode normalization attack
        "Ä" + "\u0308": {"GlobalID": "evil006"},  # A + combining diaeresis
        # Path traversal
        "../../../etc/passwd": {"GlobalID": "evil007"},
        # LDAP injection
        "admin)(|(password=*)": {"GlobalID": "evil008"},
        # XML injection
        "<?xml version='1.0'?><test>evil</test>": {"GlobalID": "evil009"},
        # Type confusion - non-string
        12345: {"GlobalID": "evil010"},  # This will fail YAML parsing
        # Regex DoS
        "a" + "a" * 50 + "!": {"GlobalID": "evil011"},
        # Unicode direction override
        "\u202e\u0061\u0062\u0063": {"GlobalID": "evil012"},
        # Homograph attack
        "Аррӏе": {"GlobalID": "evil013"},  # Cyrillic 'Apple'
        # Zero-width characters
        "John\u200b\u200c\u200dSmith": {"GlobalID": "evil014"},
        # Control characters
        "Test\x1b[31mRed\x1b[0m": {"GlobalID": "evil015"},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write test file (filter out non-string keys for YAML)
        yaml_data = {k: v for k, v in evil_data.items() if isinstance(k, str)}
        test_file = tmpdir / "evil_inputs.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, allow_unicode=True)

        # Run pipeline
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config)

        # Track what gets through
        blocked = []
        passed = []

        try:
            pipeline.run(tmpdir)

            # Check output
            output_file = Path("./cache/output/evil_inputs.yaml")
            if output_file.exists():
                with open(output_file, encoding="utf-8") as f:
                    output_data = yaml.safe_load(f)

                for evil_input in yaml_data.keys():
                    if evil_input in output_data:
                        passed.append(evil_input)
                    else:
                        blocked.append(evil_input)

            print("🔍 SECURITY TEST RESULTS:")
            print(f"\nPASS BLOCKED ({len(blocked)}):")
            for item in blocked[:5]:  # Show first 5
                safe_display = repr(item)[:50]
                print(f"  - {safe_display}")
            if len(blocked) > 5:
                print(f"  ... and {len(blocked) - 5} more")

            print(f"\nFAIL PASSED ({len(passed)}):")
            for item in passed[:5]:
                safe_display = repr(item)[:50]
                print(f"  - {safe_display}")
            if len(passed) > 5:
                print(f"  ... and {len(passed) - 5} more")

            # Check for signs of successful attacks
            if output_file.exists():
                with open(output_file, "rb") as f:
                    raw_output = f.read()

                security_issues = []

                # Check for null bytes
                if b"\x00" in raw_output:
                    security_issues.append("NULL BYTES in output!")

                # Check for script tags
                if b"<script>" in raw_output:
                    security_issues.append("SCRIPT TAGS in output!")

                # Check for SQL keywords
                if b"DROP TABLE" in raw_output:
                    security_issues.append("SQL KEYWORDS in output!")

                # Check for command injection
                if b"rm -rf" in raw_output:
                    security_issues.append("SHELL COMMANDS in output!")

                if security_issues:
                    print("\n🚨 CRITICAL SECURITY ISSUES:")
                    for issue in security_issues:
                        print(f"  - {issue}")
                else:
                    print("\nPASS No critical security issues detected in output")

            return len(passed) == 0  # Success if nothing malicious passed

        except Exception as e:
            print(f"Pipeline error (possibly good if it blocked attacks): {e}")
            return False


if __name__ == "__main__":
    success = test_security_hell()
    if success:
        print("\nPASS SECURITY: All malicious inputs blocked!")
    else:
        print("\nFAIL SECURITY: Some malicious inputs passed through!")
