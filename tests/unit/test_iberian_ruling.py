"""R60.2 pins — the Iberian maintainer ruling (2026-07-23).

RULING: Iberian-origin surnames — Spanish AND Portuguese alike — resolve
to G1 (Latin America & Iberian Caribbean).

Before this ruling the system was internally inconsistent: Spanish
surnames reached G1 through the curated tables, while Portuguese
surnames resolved A2 because the SAME names were duplicated in A2's
manager table (which won by iteration order) and in a "Portuguese
surnames (PT -> A2)" block in the scorer's A2 set. The 2,307-name
corpus N+2 exposed this as a ~10-name wrong class (Oliveira, Carvalho,
Fernandes, Rodrigues, Almeida, Bezerra de Mello, ... all adjudicated G1
by two independent adjudication rounds).

The fix moved the Lusophone names from A2 to G1 in BOTH tiers rather
than deleting them — deleting would have cost the whole class its
coverage. Measured blast radius at commit time: zero deltas on the 843
benchmark, zero on the 456-name pilot (still 0 wrong), zero on the
450-name held-out corpus (92.0% strict precision unchanged).

See docs/calibration.md (R60.2) for the ruling and its rationale.
"""

import pytest

from src.regions.manager_optimized import RegionManager


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


def _code(manager, name):
    return manager.detect_region({"CanonicalLatin": name}).region_code


# Lusophone surnames that resolved A2 before the ruling — via the
# manager's A2 table (0.95 exact) ...
MANAGER_TIER_LUSOPHONE = [
    "Henrique M. Oliveira",
    "Paula A. A. B. Carvalho",
    "Gabriel Fernandes",
    "Sergio Rodrigues",
    "Rodrigo Nicolau Almeida",
    "Santos, Ana",
    "Gomes, Ana",
    "Almeida, Rui",
    "Pinto, Sofia",
]

# ... and via the scorer's A2 STRONG surname set (script-priority path).
SCORER_TIER_LUSOPHONE = [
    "Ferreira, Joao",
    "Pereira, Maria",
    "Teixeira, Luis",
    "Lopes, Pedro",
    "Coelho, Paulo",
]


@pytest.mark.parametrize("name", MANAGER_TIER_LUSOPHONE + SCORER_TIER_LUSOPHONE)
def test_lusophone_surnames_resolve_g1(manager, name):
    assert _code(manager, name) == "G1", name


@pytest.mark.parametrize(
    "name",
    ["Garcia, Maria", "Mendoza, Diego", "Rodriguez, Juan", "Gonzalez, Ana"],
)
def test_hispanic_surnames_still_g1(manager, name):
    # The ruling unified the two halves; the Spanish half must not move.
    assert _code(manager, name) == "G1", name


@pytest.mark.parametrize(
    "name,expected",
    [
        # Non-Iberian names that DO resolve A2 must keep resolving A2.
        ("Poisson, Siméon", "A2"),
        ("Besson, G.", "A2"),
    ],
)
def test_non_iberian_a2_unaffected(manager, name, expected):
    assert _code(manager, name) == expected, name


@pytest.mark.parametrize(
    "name",
    ["Dietrich, Nicolas", "Trutschnig, Wolfgang", "Driessen, Bob"],
)
def test_non_iberian_names_never_swept_into_g1(manager, name):
    # These abstain today (verified pre- and post-ruling: 'Dietrich,
    # Nicolas' -> R0 at both). The invariant this pin owns is only that
    # moving the Lusophone block did not drag unrelated European names
    # into G1 — abstention stays acceptable.
    assert _code(manager, name) != "G1", name


def test_lusophone_names_are_not_claimed_by_two_tables(manager):
    """The duplicate that caused the bug must not come back.

    'oliveira' living in BOTH the manager's A2 table and G1's is what
    made the outcome depend on iteration order. Any future edit that
    re-adds a Lusophone name to an A-family table should fail here.
    """
    a2 = manager.surname_patterns.get("A2", set())
    g1 = manager.surname_patterns.get("G1", set())
    lusophone = {
        "santos",
        "oliveira",
        "rodrigues",
        "almeida",
        "fernandes",
        "carvalho",
        "gomes",
        "martins",
        "pinto",
        "soares",
        "correia",
        "teixeira",
        "ferreira",
        "lopes",
        "pereira",
        "coelho",
        "nogueira",
        "figueiredo",
        "azevedo",
    }
    leaked = sorted(lusophone & set(a2))
    assert not leaked, f"Lusophone names back in A2: {leaked}"
    # And they are genuinely claimed somewhere (coverage not lost).
    assert lusophone & set(g1), "G1 lost the Lusophone class entirely"
