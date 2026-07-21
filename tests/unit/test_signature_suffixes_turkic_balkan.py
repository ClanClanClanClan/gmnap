"""R59.3 pins — Turkic/Balkan signature-suffix dimension (design dim-3).

Pins the adversarially-verified behavior of the seven suffixes added in
R59 (maz, mez, oglu, escu, eanu, ovic, evic — SIGNATURE_SUFFIXES 22→29):

- Turkish negative-aorist surnames (-maz/-mez) emit C1 alone, including
  the dotless-ı diacritic form (tokenizer folds U+0131 before splitting).
- The Hispanic/Portuguese -ez/-az/-maz collision class must NEVER reach
  C1: guards are token length ≥ 6, consonant before the suffix, and the
  curated exclusion 'gormaz' (San Esteban de Gormaz, Spanish toponymic).
- Bare ASCII -oglu requires Turkic corroboration (ı/ş/ğ/ö/ü/ç in the raw
  name, or a C1 STRONG given): 'Papasoglu, P.' is an adjudicated
  Anatolian-GREEK bearer on the 843 benchmark and must abstain, while
  Çavuşoğlu-with-diacritics and Cavusoglu+Mehmet emit C1.
- Romanian -escu/-eanu → B2 (RO→B2 per codebase taxonomy, R51 ruling
  family), excluding the Corsican given name 'Francescu' and 'Ludovic'.
- ASCII South-Slavic -ovic/-evic → B2; raw-diacritic ović/ević tokens
  are handled by the raw-token rules and must not double-fire.
- Existing East-Slavic -ovich → B1 unchanged (Abramovich).

Every expectation below was behaviorally verified against the live
detector before being pinned (R59 discipline: pin what is, after
adjudicating that what-is is right).
"""

import pytest

from src.regions.manager_optimized import RegionManager


@pytest.fixture(scope="module")
def manager():
    return RegionManager()


def _detect(manager, name):
    return manager.detect_region({"CanonicalLatin": name})


# ---------------------------------------------------------------------------
# Turkish -maz/-mez → C1 (leaf, alone)
# ---------------------------------------------------------------------------

TURKISH_MAZ_MEZ = [
    "Yılmaz, Ayşe",  # diacritic form — needs the U+0131 tokenizer fold
    "Yilmaz, D.",
    "Korkmaz, E.",
    "Sonmez, F.",
    "Donmez, G.",
    "Durmaz, H.",
    "Solmaz, I.",
    "Yorulmaz, J.",
    "Kacmaz, K.",
    "Kaymaz, L.",
]


@pytest.mark.parametrize("name", TURKISH_MAZ_MEZ)
def test_turkish_negative_aorist_emits_c1(manager, name):
    r = _detect(manager, name)
    assert r.region_code == "C1", f"{name}: {r.region_code} (want C1)"
    assert r.resolution_level == "leaf"
    assert r.group_region == "TURKIC"


# ---------------------------------------------------------------------------
# Hispanic/Portuguese/other -ez/-az/-maz collision class: NEVER C1
# ---------------------------------------------------------------------------

# Gomez resolves via a pre-existing surname table (not this rule); the
# invariant this suite owns is only that no -maz/-mez guard leaks it to C1.
NOT_C1_NEGATIVES = [
    "Gomez, Maria",
    "Gamez, Pedro",
    "Gormaz, Luis",  # curated exclusion — Spanish toponymic
    "Tomaz, Joao",
    "Grumaz, Ana",
    "Jaimez, Carlos",
    "Almaz, N.",  # 5 chars — under the length guard
    "Elmaz, O.",  # Albanian collision class — under the length guard
    "Soylemez, P.",  # vowel stem — sacrificed to abstention by design
]


@pytest.mark.parametrize("name", NOT_C1_NEGATIVES)
def test_ez_az_collision_class_never_c1(manager, name):
    r = _detect(manager, name)
    assert r.region_code != "C1", f"{name}: leaked to C1"


@pytest.mark.parametrize(
    "name",
    [n for n in NOT_C1_NEGATIVES if not n.startswith("Gomez")],
)
def test_ez_az_collision_class_abstains(manager, name):
    r = _detect(manager, name)
    assert r.region_code == "R0", f"{name}: {r.region_code} (want abstention)"


# ---------------------------------------------------------------------------
# -oglu: Turkic corroboration gate
# ---------------------------------------------------------------------------


def test_papasoglu_anatolian_greek_abstains(manager):
    # Adjudicated counterexample on the 843 benchmark: 'Papasoglu, P.'
    # is Greek (B3). Bare ASCII -oglu without Turkic corroboration must
    # therefore abstain rather than emit C1.
    r = _detect(manager, "Papasoglu, P.")
    assert r.region_code == "R0", f"got {r.region_code}"


def test_cavusoglu_with_turkish_given_emits_c1(manager):
    r = _detect(manager, "Cavusoglu, Mehmet")
    assert r.region_code == "C1"
    assert r.resolution_level == "leaf"


def test_cavusoglu_without_corroboration_abstains(manager):
    r = _detect(manager, "Cavusoglu, John")
    assert r.region_code == "R0", f"got {r.region_code}"


def test_terzioglu_diacritic_emits_c1(manager):
    r = _detect(manager, "Terzioğlu, Tosun")
    assert r.region_code == "C1"


# ---------------------------------------------------------------------------
# Romanian -escu/-eanu → B2; South-Slavic ASCII -ovic/-evic → B2;
# East-Slavic -ovich → B1 (unchanged)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Popescu, Ion", "Munteanu, Radu"],
)
def test_romanian_signature_suffixes_emit_b2(manager, name):
    r = _detect(manager, name)
    assert r.region_code == "B2", f"{name}: {r.region_code}"
    assert r.group_region == "SLAVIC_CENTRAL"


def test_petrovic_ascii_emits_b2(manager):
    r = _detect(manager, "Petrovic, Milan")
    assert r.region_code == "B2"


def test_abramovich_stays_b1(manager):
    r = _detect(manager, "Abramovich, Yuri")
    assert r.region_code == "B1"
    assert r.group_region == "SLAVIC_EAST"


def test_jacobovic_decision_explicit_b2(manager):
    # DECISION (R59.3, explicit per the design-review judge): -ovic
    # attributes the SURNAME FORM, which is South-Slavic patronymic
    # (Jakobović); bearers elsewhere (e.g. Israeli families of Balkan
    # origin) carry a South-Slavic-form name, and the name-origin axis
    # classifies the name, not the bearer's citizenship — same logic as
    # Abramovich→B1. No adjudicated counterexample exists on the 843
    # benchmark, the 456-name pilot, or the 450-name held-out corpus.
    r = _detect(manager, "Jacobovic, R.")
    assert r.region_code == "B2"


@pytest.mark.parametrize("name", ["Francescu, Antone", "Ludovic, Jean"])
def test_escu_ovic_exclusions_abstain(manager, name):
    r = _detect(manager, name)
    assert r.region_code == "R0", f"{name}: {r.region_code}"
