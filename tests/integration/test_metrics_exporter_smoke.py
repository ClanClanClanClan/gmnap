import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.ops.metrics import start_metrics_server


@pytest.mark.timeout(15)
def test_metrics_server_start():
    # Should not raise
    start_metrics_server()
