import os, builtins, pytest


def _no_input(*a, **k):
    raise RuntimeError("input() is not allowed in CI tests")


@pytest.fixture(autouse=True)
def _ban_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", _no_input)


def pytest_collection_modifyitems(config, items):
    if os.getenv("LIVE_AUTH", "0") != "1":
        skip = pytest.mark.skip(reason="LIVE_AUTH=1 not set")
        for it in items:
            if "live" in it.keywords:
                it.add_marker(skip)
    if os.getenv("FORCE_EXTREME", "0") != "1":
        skip = pytest.mark.skip(reason="FORCE_EXTREME=1 not set")
        for it in items:
            if "extreme" in it.keywords:
                it.add_marker(skip)
