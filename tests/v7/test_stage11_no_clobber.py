"""R56: the stage-11 idempotency re-run must not clobber output artifacts.

Caught by the first successful 1M benchmark: a 1,000,000-entry run left a
20-entry output/stage9.yaml on disk, because the stage-11 TRUE re-run
(fresh pipeline over a 20-row sample) ran its own stage 9 into the SAME
output dir, overwriting the main run's artifacts. The re-run's comparison
is in-memory canonical bytes; its writes were pure collateral damage.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("OFFLINE", "1")
os.environ.setdefault("GMNAP_NO_PARALLEL", "1")

from src.core.pipeline_v7 import PipelineMode, V7Pipeline


@pytest.mark.timeout(180)
def test_main_run_artifacts_survive_the_idempotency_rerun(tmp_path, monkeypatch):
    # Run from a scratch cwd so output/ is isolated from other tests.
    monkeypatch.chdir(tmp_path)
    n = 25  # > the 20-entry re-run sample, so a clobber is detectable
    batch = [
        {"CanonicalLatin": f"Distinct{i}, Person{i}", "CountryCodes": ["FR"]}
        for i in range(n)
    ]
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    out = asyncio.run(pipeline.process_batch(batch))
    assert len(out) == n

    yaml_path = Path("output/stage9.yaml")
    assert yaml_path.exists(), "main run wrote no stage9.yaml"
    written = json.loads(yaml_path.read_text(encoding="utf-8"))
    assert len(written) == n, (
        f"output/stage9.yaml holds {len(written)} entries, expected {n} — "
        f"the stage-11 re-run clobbered the main run's artifact again"
    )
    # The idempotency check itself must still have run and recorded a result.
    assert getattr(pipeline.metrics, "idempotency_diff_bytes", None) is not None
