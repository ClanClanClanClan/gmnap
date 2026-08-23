"""R69 pins — Sudoc pre-1985 doctorate evidence, harvest to tier.

WHY THIS EXISTS. The harvester's docstring said "sidecar; the build merges
it". Nothing anywhere read `data/sudoc_thesis_types.json`, so running the
harvest could not have moved a single tier — the integration existed only in
prose. That is the same defect class as the three authority fetchers
documented "WORKING" while structurally incapable of returning data, and as
the harvester's own `$4 070` role filter, which was described in a comment and
implemented as a no-op.

So these tests do not check that the code is *reasonable*; they check the
places where a claim and the code can silently diverge:
  * the build still calls the merge (it can be deleted without any test
    failing otherwise),
  * the role filter actually excludes non-authored records,
  * the dedup errs toward SPLITTING, because splitting leaves an edge at
    REVIEW while merging can promote it to TRUST on a false "only one degree".
"""

import ast
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.data.fetch_sudoc_thesis_types import (
    AUTHOR_ROLE,
    classify_degree,
    dedup_theses,
    parse_roles,
)
from tools.build_genealogy_enrichment import apply_sudoc_evidence

BIBLIO = """<?xml version="1.0" encoding="UTF-8"?>
<sudoc service="biblio">
<query><ppn>032438249</ppn></query>
<result>
<role><unimarcCode>070</unimarcCode><roleName>Auteur</roleName>
  <doc><ppn>AAA</ppn></doc><doc><ppn>BBB</ppn></doc></role>
<role><unimarcCode>727</unimarcCode><roleName>Directeur de these</roleName>
  <doc><ppn>SUP1</ppn></doc><doc><ppn>SUP2</ppn></doc></role>
<role><unimarcCode>651</unimarcCode><roleName>Directeur de publication</roleName>
  <doc><ppn>ED1</ppn></doc></role>
</result></sudoc>"""


# ── the role filter (defect 1) ──────────────────────────────────────────


def test_only_authored_records_are_kept():
    """Role 727 is 'Directeur de these' — theses the person SUPERVISED.
    Pooling them with their own work counted a supervisor's students as
    degrees HE held, which inverts the decisive signal exactly on the
    advisors we care most about (Brezis: 39 authored, 46 supervised)."""
    roles = parse_roles(ET.fromstring(BIBLIO))
    assert roles[AUTHOR_ROLE] == ["AAA", "BBB"]
    assert roles["727"] == ["SUP1", "SUP2"]
    assert "SUP1" not in roles[AUTHOR_ROLE]


def test_the_persons_own_authority_ppn_is_not_one_of_their_works():
    """The old parser collected every <ppn> in the document, including the
    <query> echo of the person's own authority record."""
    roles = parse_roles(ET.fromstring(BIBLIO))
    assert "032438249" not in roles.get(AUTHOR_ROLE, [])


# ── the dedup (must err toward SPLITTING) ──────────────────────────────


def _t(year, title, degree="doctorat_unspecified"):
    return {"year": year, "title": title, "degree": degree}


def test_one_thesis_catalogued_twice_collapses():
    """Choquet's single 1946 thesis has two Sudoc records whose titles differ
    by one character ('Application'/'Applications'). Keying on the exact title
    counted two degrees and destroyed his decidability."""
    out = dedup_theses(
        [
            _t(
                1946,
                "Application des proprietes descriptives de la fonction contingent",
            ),
            _t(
                1946,
                "Applications des proprietes descriptives de la fonction contingent",
            ),
        ]
    )
    assert len(out) == 1


def test_two_real_degrees_stay_two():
    """The Brezis pattern must survive: 3e cycle 1966, doctorat d'Etat 1971."""
    out = dedup_theses(
        [
            _t(1966, "Les operateurs monotones", "doctorat_3e_cycle"),
            _t(1971, "Problemes unilateraux"),
        ]
    )
    assert len(out) == 2


def test_short_titles_require_an_exact_match():
    """Containment on a two-token title merges almost anything. Merging is the
    DANGEROUS direction — it promotes an edge to TRUST on a false 'only one
    doctorate' — so short titles fall back to exact equality."""
    out = dedup_theses(
        [_t(1950, "Convergences"), _t(1950, "Convergences et topologie")]
    )
    assert len(out) == 2


def test_cataloguing_words_do_not_create_a_false_second_degree():
    out = dedup_theses(
        [_t(1972, "Problemes unilateraux"), _t(1972, "Problemes unilateraux : these")]
    )
    assert len(out) == 1


def test_presided_disputations_are_not_degrees():
    """Early-modern praeses trap: Q122366 showed SIX 'pre-1985 doctorates'
    dated 1721-1777 because the presiding professor was catalogued as author.
    They carry no classifiable 328$b."""
    assert classify_degree("Positiones medicae tumultuariae") is None
    assert classify_degree("Thèse de 3e cycle") == "doctorat_3e_cycle"


# ── the merge into the build (defect 3) ────────────────────────────────


def test_evidence_lands_on_the_student_record(tmp_path):
    side = tmp_path / "sudoc.json"
    side.write_text(
        json.dumps(
            {
                "_meta": {},
                "people": {
                    "Q1": {
                        "IdRef": "111",
                        "pre1985_count": 1,
                        "pre1985_degree": "doctorat_etat",
                        "pre1985_year": 1970,
                    },
                    "Q2": {"IdRef": "222", "pre1985_count": 2},
                },
            }
        )
    )
    by_name = {"a, a": {"QID": "Q1"}, "b, b": {"QID": "Q2"}, "c, c": {}}
    stats = apply_sudoc_evidence(by_name, side)
    assert stats == {"loaded": 2, "matched": 2, "decidable": 1, "multi": 1}
    assert by_name["a, a"]["SudocPre1985Count"] == 1
    assert by_name["a, a"]["SudocPre1985Year"] == 1970
    assert by_name["b, b"]["SudocPre1985Count"] == 2
    assert "SudocPre1985Degree" not in by_name["b, b"]  # ambiguous: no degree
    assert "SudocPre1985Count" not in by_name["c, c"]


def test_a_missing_sidecar_is_not_an_error(tmp_path):
    """The sidecar is optional — a clone without it must still build."""
    assert apply_sudoc_evidence({}, tmp_path / "nope.json")["loaded"] == 0


def test_build_consumes_the_sudoc_sidecar():
    """THE ONE THAT MATTERS. The previous integration existed only in a
    docstring. If the merge call is ever removed from the build, the harvest
    silently stops affecting any tier again — exactly the failure this round
    fixed. Asserted against the parsed source, not by importing and hoping."""
    src = Path("tools/build_genealogy_enrichment.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert (
        "apply_sudoc_evidence" in called
    ), "the build no longer merges the Sudoc sidecar — the harvest is dead again"
