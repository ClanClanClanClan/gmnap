import pytest

try:
    import atheris  # type: ignore
except Exception:
    atheris = None


@pytest.mark.fuzz
@pytest.mark.timeout(15)
def test_atheris_available():
    if atheris is None:
        pytest.skip("atheris not installed")
    assert atheris is not None
