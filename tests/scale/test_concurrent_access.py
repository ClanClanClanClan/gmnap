import pytest
import subprocess, sys


@pytest.mark.timeout(15)
def test_cache_concurrency():
    out = subprocess.check_output(
        [sys.executable, "tools/concurrent_access_test.py"], text=True
    ).strip()
    assert "OK:" in out
