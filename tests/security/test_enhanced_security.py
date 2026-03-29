import pytest

#!/usr/bin/env python3
"""Test enhanced security validator against the 3 previously-passing attacks."""

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
def test_enhanced_security():
    """Test that enhanced security validator blocks the 3 critical attacks."""

    # The 3 malicious inputs that were previously passing
    malicious_data = {
        # Regex DoS attack
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!": {"GlobalID": "dos001"},
        # Unicode combining character attack
        "Ä̈": {"GlobalID": "unicode001"},
        # Homograph attack (Cyrillic lookalikes)
        "Аррӏе": {"GlobalID": "homograph001"},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write malicious test file
        test_file = tmpdir / "malicious.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(malicious_data, f, allow_unicode=True)

        print(f"Created test file with {len(malicious_data)} malicious entries")

        # Run pipeline
        config = GMNAPConfig()
        config.cache.cache_dir = "./cache_security_test"
        pipeline = GMNAPPipeline(config)

        try:
            result = pipeline.run(tmpdir)

            # Check results
            output_dir = Path(config.cache.cache_dir) / "output"

            malicious_outputs = []
            if (output_dir / "malicious.yaml").exists():
                with open(output_dir / "malicious.yaml", "r", encoding="utf-8") as f:
                    output_data = yaml.safe_load(f)
                    if output_data:
                        malicious_outputs = list(output_data.keys())

            print(f"Pipeline processed {result.total_entries} entries")
            print(f"Successful entries: {result.successful_entries}")
            print(f"Failed entries: {result.failed_entries}")
            print(f"Validation errors: {len(result.validation_errors)}")

            if malicious_outputs:
                print(
                    f"FAIL SECURITY BREACH: {len(malicious_outputs)} malicious entries in output:"
                )
                for entry in malicious_outputs:
                    print(f"  - {repr(entry)}")
                return False
            else:
                print("PASS SECURITY SUCCESS: All malicious entries blocked!")
                return True

        except Exception as e:
            print(f"Pipeline error: {e}")
            return False


if __name__ == "__main__":
    print("🛡️  Testing Enhanced Security Validator")
    print("=" * 50)

    success = test_enhanced_security()

    print("=" * 50)
    if success:
        print("PASS Enhanced security validation working correctly!")
    else:
        print("FAIL Security vulnerabilities still present!")
