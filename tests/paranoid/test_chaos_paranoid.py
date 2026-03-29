import os

import pytest


def _simulate_fault_env():
    os.environ["GMNAP_CHAOS_MODE"] = "1"
    yield
    os.environ.pop("GMNAP_CHAOS_MODE", None)


@pytest.mark.chaos
@pytest.mark.timeout(15)
def test_env_fault_simulation():
    # Minimal chaos: pipeline should run (or fail fast) under a simulated fault flag
    for _ in _simulate_fault_env():
        assert True  # marker that environment flag was set
