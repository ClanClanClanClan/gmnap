import pytest
from src.authorities.validators import ensure_orcid, AuthorityInputError, safe_startswith


@pytest.mark.timeout(15)
def test_invalid_orcid_is_caught():
    with pytest.raises(AuthorityInputError):
        ensure_orcid("foo")


@pytest.mark.timeout(15)
def test_safe_startswith_handles_non_strings():
    assert not safe_startswith({"k": "v"}, "http")
