import pytest
import json, os, pathlib, subprocess, sys
from src.core.stage11_gate import main as stage11


@pytest.mark.timeout(15)
def test_stage11_byte_identical(tmp_path, monkeypatch):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps([{"GlobalID": "A"}], sort_keys=True))
    new.write_text(json.dumps([{"GlobalID": "A"}, {"GlobalID": "B"}], sort_keys=True))
    # Run gate via CLI entry
    import sys

    sys.argv = ["stage11_gate", "--old", str(old), "--new", str(new)]
    try:
        stage11()
    except SystemExit as e:
        assert e.code == 0
