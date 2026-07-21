"""R59.4 pins — suffix dimension B (Hellenic/Iranian/Icelandic) + -sson YAML.

Pins the adversarially-verified dimension-B additions
(SIGNATURE_SUFFIXES 29→33):

- Greek -idis/-iadis → B3 (13/13 + 4/4 corpus bearers Greek), with the
  curated exclusion trio davidis/aidis/naidis (Latin-German David-form,
  Lithuanian) applied to BOTH the new STRONG rule and the pre-existing
  bare '-is' medium rule ('Aidis, Ruta' was a live wrong B3@0.75).
- Persian -nezhad → C2 (romanization twin of signature 'nejad').
- Icelandic -dottir (ASCII/folded) + -dóttir (raw) → A3, closing the
  verified gap where ASCII-transliterated and non-s weak-genitive
  patronymics fell to R0; plus the F2 'ola-' prefix no longer fires on
  Óladóttir-type patronymics.
- The live -sson precision bug: non-Nordic -sson surnames no longer emit
  wrong A3. Twelve verified bearers are claimed by curated surname_exact
  YAML entries (a1/a2/b2/g1 — g1.yaml is the first G1 supplement and
  exercises new-file loader pickup); frasson/masson/wasson cannot claim
  a single leaf (cross-region bearers, dual etymology, or no named
  bearer) and abstain via the scorer's curated -sson exclusion.
- Rejected-suffix classes stay abstaining (-akos, -zada/-zade, -poor,
  -kar, -wala as suffix, -appa, -anna): rejection pins below; the four
  verified -wala bearers are exact d1.yaml entries instead.

Every expectation was behaviorally verified against the live detector
before being pinned.
"""

import pytest

from src.regions.manager_optimized import RegionManager


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


def _code(manager, name):
    return manager.detect_region({"CanonicalLatin": name}).region_code


# ---------------------------------------------------------------------------
# Greek -idis / -iadis → B3
# ---------------------------------------------------------------------------

GREEK_IDIS = [
    "Souganidis, Panagiotis",
    "Daniilidis, Aris",
    "Garoufalidis, Stavros",
    "Kevrekidis, Yannis",
    "Michailidis, George",
    "Iliadis, Stavros",
    "Antoniadis, Ioannis",
    "Athanasiadis, Christos",
]


@pytest.mark.parametrize("name", GREEK_IDIS)
def test_greek_idis_iadis_emits_b3(manager, name):
    assert _code(manager, name) == "B3", name


@pytest.mark.parametrize(
    "name",
    ["Davidis, Karl", "Aidis, Ruta", "Naidis, George"],
)
def test_idis_exclusion_trio_abstains(manager, name):
    # 'Aidis, Ruta' (Lithuanian) emitted wrong B3@0.75 via the bare '-is'
    # medium rule before R59.4 — the exclusion covers both rule tiers.
    assert _code(manager, name) == "R0", name


@pytest.mark.parametrize(
    "name",
    ["Davis, Martin", "Harris, Joe", "Curtis, Charles", "Lewis, Adrian"],
)
def test_anglo_is_names_never_b3(manager, name):
    assert _code(manager, name) != "B3", name


# ---------------------------------------------------------------------------
# Persian -nezhad → C2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Hassannezhad, Asma", "Ahmadinezhad, Hamid", "Akbarinezhad, R."],
)
def test_nezhad_emits_c2(manager, name):
    assert _code(manager, name) == "C2", name


# ---------------------------------------------------------------------------
# Icelandic -dottir / -dóttir → A3
# ---------------------------------------------------------------------------

DOTTIR_FORMS = [
    "Gudmundsdottir, Anna",  # ASCII s-genitive (was R0)
    "Halldorsdottir, Anna",  # ASCII s-genitive (was R0)
    "Finnbogadóttir, Vigdís",  # raw, weak genitive (was R0)
    "Helgadóttir, Anna",  # raw, weak genitive (was R0)
    "Sturludóttir, Anna",  # raw, weak genitive (was R0)
    "Helgadottir, Sigrun",  # folded, weak genitive (was R0)
    "Bjarnadottir, Kristin",  # folded, weak genitive (was R0)
    "Oladottir, Berglind",  # folded — collided with the F2 'ola-' prefix
]


@pytest.mark.parametrize("name", DOTTIR_FORMS)
def test_dottir_emits_a3(manager, name):
    assert _code(manager, name) == "A3", name


def test_yoruba_ola_prefix_still_fires(manager):
    # The -dottir carve-out must not break the real F2 prefix class.
    assert _code(manager, "Oladipo, Ayodele") == "F2"


# ---------------------------------------------------------------------------
# -sson: YAML-claimed non-Nordic bearers + curated abstentions + Nordic intact
# ---------------------------------------------------------------------------

SSON_YAML_CLAIMS = [
    ("Besson, G.", "A2"),
    ("Buisson, O.", "A2"),
    ("Cusson, P.", "A2"),
    ("Gosson, Maurice de", "A2"),
    ("Hermisson, J.", "A2"),
    ("Casson, Andrew", "A1"),
    ("Sisson, Scott", "A1"),
    ("Whisson, S.", "A1"),
    ("Mathisson, Myron", "B2"),
    ("Malbouisson, J. M. C.", "G1"),  # exercises new-file g1.yaml pickup
]


@pytest.mark.parametrize("name,expected", SSON_YAML_CLAIMS)
def test_non_nordic_sson_yaml_claims(manager, name, expected):
    assert _code(manager, name) == expected, name


@pytest.mark.parametrize(
    "name",
    ["Frasson, Miguel", "Masson, Etienne", "Wasson, R."],
)
def test_sson_curated_exclusions_abstain(manager, name):
    assert _code(manager, name) == "R0", name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Andersson, Lars", "A3"),
        ("Thorsteinsson, Jon", "A3"),
        ("Johnson, David", "A1"),  # single-s Anglo -son untouched
        ("Poisson, Siméon", "A2"),  # hardcoded exact entry, pre-existing
    ],
)
def test_sson_regression_pins(manager, name, expected):
    assert _code(manager, name) == expected, name


# ---------------------------------------------------------------------------
# Rejected suffix classes: abstention is the correct, pinned behavior
# ---------------------------------------------------------------------------

REJECTED_ABSTAIN = [
    "Strakos, Zdenek",  # -akos: Czech Strakoš (diacritic lost by folding)
    "Bakos, Gaspar",  # -akos: Hungarian collision class
    "Grafakos, Loukas",  # -akos rejected even for real Greek bearers
    "Alikakos, Nicholas",
    "Quezada, Maria",  # -zada: Hispanic
    "Gusein-Zade, S.",  # -zade: Azeri C1-vs-C2 cross-group
    "Abubakar, Ibrahim",  # -kar spans 8 regions
]


@pytest.mark.parametrize("name", REJECTED_ABSTAIN)
def test_rejected_suffix_classes_abstain(manager, name):
    assert _code(manager, name) == "R0", name


def test_kapoor_stays_d1(manager):
    # -poor was rejected as a C2 suffix precisely because its only corpus
    # bearer is Indian.
    assert _code(manager, "Kapoor, Apoorva") == "D1"


@pytest.mark.parametrize(
    "name",
    ["Rangwala, S. A.", "Kagalwala, Kumel", "Raniwala, Hamza", "Fruitwala, Neelay"],
)
def test_wala_bearers_via_d1_yaml(manager, name):
    # -wala as a SUFFIX was rejected (4 bearers < 8 attestation floor);
    # the four verified bearers are exact d1.yaml entries.
    assert _code(manager, name) == "D1", name


# ---------------------------------------------------------------------------
# Cross-family regression pins (unchanged by dimension B)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Papadopoulos, A.", "B3"),
        ("Hassanzadeh, Sara", "C2"),
        ("Nguyen, Van", "E5"),
        ("Novak, Jan", "B2"),
        ("Tanaka, Kazuo", "E3"),
    ],
)
def test_cross_family_regression_pins(manager, name, expected):
    assert _code(manager, name) == expected, name
