"""ROR institution->country lookup: whole-word matching + importability
(R39).

The geo branch resolves an entry's Institution to a country via
src.collectors.ror_client. Two bugs:
  * the package __init__ eagerly imported the optional `requests`-based
    OpenAlex/ORCID clients, so importing ANYTHING from src.collectors
    (incl. the stdlib-only ror_client) failed when requests is absent —
    silently disabling the geo lookup;
  * the fuzzy fallback used arbitrary substring matching (`known in
    norm`), so "kaist" wrongly matched "kaistville ..." and the first
    dict match won (order-dependent country attribution).
"""


def test_collectors_package_imports_without_requests():
    import src.collectors  # must not raise even if requests is absent
    from src.collectors.ror_client import get_ror_lookup  # noqa: F401


def test_ror_lookup_resolves_real_institution():
    from src.collectors.ror_client import get_ror_lookup

    assert get_ror_lookup().lookup("University of Oxford") == "GB"


def test_ror_lookup_rejects_incidental_substring():
    from src.collectors.ror_client import get_ror_lookup

    r = get_ror_lookup()
    # "kaist"/"oxford" appear only as a substring of a longer unrelated
    # token -> must NOT attribute a country.
    assert r.lookup("the kaistville institute of nowhere") is None
    assert r.lookup("oxfordville college") is None
