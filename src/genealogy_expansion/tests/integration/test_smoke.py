import pathlib


def test_fixture_pipeline_exists():
    root = pathlib.Path(__file__).resolve().parents[2]
    script = root / "scripts" / "run_pipeline_python3.sh"
    assert script.exists()
