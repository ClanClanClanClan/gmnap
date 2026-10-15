"""The GlobalID is an IDENTITY, and it is the id the API hands out.

Three defects, one root cause, in the order they have to be fixed:

1. The id was an equivalence class, not an identity. A GlobalID is a hash of
   {CanonicalLatin, BirthYear, DeathYear}, so several ``by_name`` keys can
   legitimately carry one — the alias design, which lets both "Perelman, G."
   and "Grigori Perelman" resolve. But Wikidata enriched one half of each
   aliased pair and left the other a bare stub, so one id named two
   measurably different records, and ``by_global_id[gid] = key`` chose
   between them by insertion order. Invariant I7 permitted this: it compares
   identifiers to each other and never asks whether the records agree.
   I8 is the missing half.

2. ``/api/v1/query`` minted the id it returned from ``{"CanonicalLatin":
   name}`` BEFORE enrichment attached the dates the real id is derived from.
   For the 26.0% of people who carry dates that id was not the id the graph
   is keyed on, and it 404'd on ``/api/v1/lineage``.

3. A miss was not a miss: any string came back 200 with a well-formed minted
   id, so the web UI rendered a result card for a person who does not exist.

Order matters — returning the corpus id (2) is only safe once the corpus id
identifies one person (1).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "genealogy_enrichment.json"
APP_JS = REPO / "static" / "app.js"


@pytest.fixture(scope="module")
def corpus() -> dict:
    assert DATA.exists(), f"{DATA} not found"
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    by_name = payload.get("by_name") or {}
    if len(by_name) < 1000:
        pytest.skip("enrichment file looks like an LFS stub; run `git lfs pull`")
    return payload


@pytest.fixture
def client():
    from starlette.testclient import TestClient

    from src.api.server import create_app

    return TestClient(create_app())


@pytest.fixture
def auth(monkeypatch):
    """Paid-tier header: /query and /process are hashcash-gated otherwise."""
    import src.api.server as srv

    token = "identity-test-token"
    srv._PAID_TOKENS.add(token)
    yield {"Authorization": f"Bearer {token}"}
    srv._PAID_TOKENS.discard(token)


# ── 1. I8: a shared GlobalID must be lossless ─────────────────────────────


def _validate(by_name: dict, by_gid: dict | None = None) -> list[str]:
    from tools.validate_genealogy_integrity import validate

    if by_gid is None:
        by_gid = {r["GlobalID"]: k for k, r in by_name.items() if r.get("GlobalID")}
    return validate(by_name, by_gid)


def _i8(failures: list[str]) -> list[str]:
    return [f for f in failures if f.startswith("I8")]


def test_i8_fails_when_aliased_keys_disagree_on_substance():
    """The exact shape that shipped: same id, one half enriched, one half not."""
    by_name = {
        "perelman, g.": {
            "CanonicalLatin": "Perelman, G.",
            "GlobalID": "GI55FX22XZTK7LSDFQKAHF",
            "QID": "Q117346",
            "Institution": "St. Petersburg State University",
            "Advisors": [
                {
                    "name": "Burago, Yuri",
                    "source": "Wikidata-P184",
                    "confidence": "high",
                }
            ],
        },
        "perelman, grigori": {
            "CanonicalLatin": "Perelman, G.",
            "GlobalID": "GI55FX22XZTK7LSDFQKAHF",
            "Institution": "Steklov Institute of Mathematics",
        },
        "burago, yuri": {
            "CanonicalLatin": "Burago, Yuri",
            "GlobalID": "BURAGOAAAAAAAAAAAAAAAA",
        },
    }
    failures = _i8(_validate(by_name))
    assert failures, "I8 did not catch a lossy alias pair"
    assert "disagree" in failures[0].lower()


def test_i8_allows_aliasing_that_is_lossless():
    """I7's alias design stays legal — I8 only objects to losing data."""
    record = {
        "CanonicalLatin": "Perelman, G.",
        "GlobalID": "GI55FX22XZTK7LSDFQKAHF",
        "QID": "Q117346",
        "Institution": "St. Petersburg State University",
        "Advisors": [
            {"name": "Burago, Yuri", "source": "Wikidata-P184", "confidence": "high"}
        ],
    }
    by_name = {
        "perelman, g.": dict(record),
        "perelman, grigori": dict(record),
        "burago, yuri": {
            "CanonicalLatin": "Burago, Yuri",
            "GlobalID": "BURAGOAAAAAAAAAAAAAAAA",
        },
    }
    assert _i8(_validate(by_name)) == []


def test_i8_catches_an_id_absent_from_the_reverse_index():
    """An id a record carries but by_global_id does not resolve is a 404."""
    by_name = {
        "euler, leonhard": {
            "CanonicalLatin": "Euler, Leonhard",
            "GlobalID": "EULERAAAAAAAAAAAAAAAAA",
        }
    }
    failures = _i8(_validate(by_name, by_gid={}))
    assert failures, "I8 did not catch a missing reverse-index entry"
    assert "resolve to nothing" in failures[0]


def test_shipped_corpus_has_no_lossy_aliases(corpus):
    failures = _validate(corpus["by_name"], corpus["by_global_id"])
    assert failures == [], "shipped corpus violates a genealogy invariant"


# ── 2. The merge pass that makes the id an identity ───────────────────────


def test_merge_unions_an_alias_group_and_is_idempotent():
    from tools.build_genealogy_enrichment import merge_alias_groups

    by_name = {
        # Ranked second: a bare stub with no external identifier.
        "wiles, andrew john": {
            "CanonicalLatin": "Wiles, A.",
            "GlobalID": "BNKV6C4T3JECXJMGSGBGP6",
            "BirthYear": 1953,
            "Institution": "Princeton University",
            "Source": "curated stub",
        },
        # Ranked first: carries the QID.
        "wiles, a.": {
            "CanonicalLatin": "Wiles, A.",
            "GlobalID": "BNKV6C4T3JECXJMGSGBGP6",
            "QID": "Q184433",
            "BirthPlace": "Cambridge",
            "Institution": "University of Cambridge",
            "Source": "Wikidata",
            "Advisors": [
                {
                    "name": "Coates, John H",
                    "source": "Wikidata-P184",
                    "confidence": "high",
                }
            ],
        },
    }
    changed, affected = merge_alias_groups(by_name)
    assert (changed, affected) == (1, 2)

    merged = by_name["wiles, a."]
    assert by_name["wiles, andrew john"] == merged, "keys still disagree"
    # The identifier-bearing record wins conflicts...
    assert merged["QID"] == "Q184433"
    # ...the richer Institution survives...
    assert merged["Institution"] == "University of Cambridge"
    # ...fields only the stub had are filled in...
    assert merged["BirthYear"] == 1953
    assert merged["BirthPlace"] == "Cambridge"
    # ...the advisor edge reaches BOTH keys, with provenance intact...
    assert [a["name"] for a in merged["Advisors"]] == ["Coates, John H"]
    assert merged["Advisors"][0]["source"] == "Wikidata-P184"
    # ...and both sources are credited, in the build's '+'-joined idiom.
    assert set(merged["Source"].split("+")) == {"Wikidata", "curated stub"}

    # Idempotent, so the build can run it to a fixed point.
    assert merge_alias_groups(by_name) == (0, 0)


def test_merge_unions_advisor_edges_from_both_sides():
    """Both halves holding edges must end up with the union, not one list."""
    from tools.build_genealogy_enrichment import merge_alias_groups

    by_name = {
        "a, x": {
            "CanonicalLatin": "A, X",
            "GlobalID": "SHAREDAAAAAAAAAAAAAAAA",
            "QID": "Q1",
            "Source": "Wikidata",
            "Advisors": [
                {"name": "First, A", "source": "Wikidata-P184", "confidence": "high"}
            ],
        },
        "a, xavier": {
            "CanonicalLatin": "A, X",
            "GlobalID": "SHAREDAAAAAAAAAAAAAAAA",
            "Source": "theses.fr",
            "Advisors": [
                {"name": "Second, B", "source": "theses.fr", "confidence": "high"}
            ],
        },
    }
    assert merge_alias_groups(by_name)[0] == 1
    names = sorted(a["name"] for a in by_name["a, x"]["Advisors"])
    assert names == ["First, A", "Second, B"]
    assert by_name["a, xavier"] == by_name["a, x"]


def test_merge_refuses_to_fuse_two_different_people():
    """A shared id with DIFFERENT canonical forms is a hash collision.

    Merging it would fuse two humans into one record, so the pass must leave
    it alone and let I7 fail the build instead.
    """
    from tools.build_genealogy_enrichment import merge_alias_groups

    by_name = {
        "one, a": {
            "CanonicalLatin": "One, A",
            "GlobalID": "COLLIDEAAAAAAAAAAAAAAA",
            "QID": "Q1",
        },
        "two, b": {
            "CanonicalLatin": "Two, B",
            "GlobalID": "COLLIDEAAAAAAAAAAAAAAA",
            "QID": "Q2",
        },
    }
    assert merge_alias_groups(by_name) == (0, 0)
    assert by_name["one, a"]["QID"] == "Q1"
    assert by_name["two, b"]["QID"] == "Q2"
    assert any(f.startswith("I7") for f in _validate(by_name))


def test_every_corpus_id_resolves_to_exactly_one_person(corpus):
    by_name, by_gid = corpus["by_name"], corpus["by_global_id"]
    ids = {r["GlobalID"] for r in by_name.values() if r.get("GlobalID")}
    assert len(by_gid) == len(ids), "reverse index is not one entry per id"
    assert ids <= set(by_gid), "a record carries an id the index cannot resolve"
    for gid, key in by_gid.items():
        assert key in by_name, f"{gid} points at a missing key {key!r}"
        assert (
            by_name[key]["GlobalID"] == gid
        ), f"{gid} resolves to {key!r}, which carries a different id"


@pytest.mark.parametrize(
    "spellings,advisor",
    [
        (["Grigori Perelman", "Perelman, G."], "Burago, Yuri"),
        (["Stanislaw Lojasiewicz", "Łojasiewicz, Stanisław"], "Ważewski, Tadeusz"),
    ],
)
def test_every_spelling_of_one_person_returns_the_same_advisors(spellings, advisor):
    """ "Grigori Perelman" returned 0 advisors while "Perelman, G." returned 2."""
    from src.core.genealogy_lookup import GenealogyLookup

    lookup = GenealogyLookup()
    seen = []
    for spelling in spellings:
        record = lookup.lookup_by_name(spelling)
        assert record is not None, f"{spelling!r} resolves to nothing"
        names = sorted(a["name"] for a in record.get("Advisors") or [])
        assert advisor in names, f"{spelling!r} lost its advisors: {names}"
        seen.append((record["GlobalID"], tuple(names)))
    assert len(set(seen)) == 1, f"spellings disagree: {seen}"


def test_an_aliased_person_appears_once_among_their_advisors_students():
    """Both alias keys carry the advisor list, so the reverse index must
    dedupe on identity or the descendants tree shows one student twice."""
    from src.core.genealogy_lookup import GenealogyLookup

    edges = GenealogyLookup().traverse_lineage(
        "Burago, Yuri", 1, direction="descendants"
    )
    students = [e["to"] for e in edges]
    assert "Perelman, G." in students
    assert len(students) == len(set(students)), f"duplicate students: {students}"


# ── 3. The API returns the corpus id, and it resolves ─────────────────────


def test_query_returns_the_corpus_id_not_a_minted_one(client, auth, corpus):
    """The old test asserted /query minted with the pipeline's scheme. That
    guarded the wrong thing: both schemes hash the name alone, so for anyone
    with dates the agreed-upon id still was not the id the graph is keyed on.
    """
    from src.core.global_id import generate_global_id

    name = "Euler, Leonhard"
    expected = corpus["by_name"]["euler, leonhard"]["GlobalID"]
    minted = generate_global_id({"CanonicalLatin": name})
    assert minted != expected, "pick a dated person — this proves nothing"

    body = client.get("/api/v1/query", params={"name": name}, headers=auth).json()
    assert body["GlobalID"] == expected
    assert body["global_id"] == expected
    assert body["found"] is True


@pytest.mark.timeout(600)
def test_an_id_from_query_resolves_on_lineage(client, auth, corpus):
    """Several hundred ids, spanning both the with-date and without-date
    populations — the with-date half is where the minted id diverged
    (measured 400/400) and every one of those was a 404 here.

    Sampled from people who HAVE advisor edges: /api/v1/lineage 404s on an
    empty edge list, so a leaf 404s whatever its id, which would make this
    test fail for a reason that has nothing to do with the identifier.
    """
    by_name = corpus["by_name"]
    dated, undated = [], []
    for record in by_name.values():
        if not record.get("Advisors"):
            continue
        bucket = (
            dated if (record.get("BirthYear") or record.get("DeathYear")) else undated
        )
        bucket.append(record["CanonicalLatin"])
    assert (
        len(dated) > 200 and len(undated) > 200
    ), f"thin populations: {len(dated)} dated / {len(undated)} undated"

    rng = random.Random(20261015)
    sample = rng.sample(dated, 200) + rng.sample(undated, 200)

    failures = []
    for name in sample:
        body = client.get("/api/v1/query", params={"name": name}, headers=auth).json()
        gid = body.get("GlobalID")
        if not gid:
            failures.append((name, "query returned no id", None))
            continue
        status = client.get(f"/api/v1/lineage/{gid}", headers=auth).status_code
        if status != 200:
            failures.append((name, gid, status))
    assert not failures, (
        f"{len(failures)}/{len(sample)} ids from /query did not resolve on "
        f"/lineage; first few: {failures[:5]}"
    )


# ── 4. A miss is a miss ───────────────────────────────────────────────────


NONSENSE = "Qxzzvy Blargwint"


def test_query_reports_a_miss_instead_of_minting_an_id(client, auth):
    body = client.get("/api/v1/query", params={"name": NONSENSE}, headers=auth).json()
    assert body["found"] is False
    assert body["GlobalID"] is None, "an id was minted for a nonexistent person"
    assert body["global_id"] is None


def test_a_known_and_an_unknown_name_are_distinguishable(client, auth):
    """The whole point: the two cases must not look alike on the wire."""
    hit = client.get(
        "/api/v1/query", params={"name": "Euler, Leonhard"}, headers=auth
    ).json()
    miss = client.get("/api/v1/query", params={"name": NONSENSE}, headers=auth).json()
    assert hit["found"] != miss["found"]
    assert bool(hit["GlobalID"]) and not miss["GlobalID"]


def test_process_marks_an_unknown_entry_as_not_found(client, auth):
    body = client.post(
        "/api/v1/process",
        json={"entries": [{"CanonicalLatin": NONSENSE}], "mode": "quick"},
        headers=auth,
    ).json()
    entries = body["entries"]
    # The 1:1 per-entry contract is deliberate and stays — which is exactly
    # why `found` has to carry the answer.
    assert len(entries) == 1
    assert entries[0]["found"] is False


def test_process_marks_a_known_entry_as_found(client, auth):
    body = client.post(
        "/api/v1/process",
        json={"entries": [{"CanonicalLatin": "Euler, Leonhard"}], "mode": "quick"},
        headers=auth,
    ).json()
    assert body["entries"][0]["found"] is True


def test_app_js_branches_on_found_not_on_array_length():
    """The zero-results branch was unreachable: /process returns one entry per
    input, so `entries.length === 0` never held and any string rendered a
    card. The real browser assertion lives in tools/browser_smoke.py
    (scenario_unknown_name); this guards the branch condition itself.
    """
    js = APP_JS.read_text(encoding="utf-8")
    assert ".found !== false" in js, "app.js does not filter on `found`"
    assert (
        "if (known.length === 0)" in js
    ), "the no-results branch is not driven by the filtered list"
    assert (
        "if (entries.length === 0)" not in js
    ), "the unreachable array-length branch is still the gate"
