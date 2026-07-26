"""R65.3 pins — the stratified MGP risk model.

The maintainer's rule: trust MGP for recent people in single-tier-PhD
countries; be careful with older degrees and two-tier countries. These pin
that behaviour, and pin the corrections the adversarial review forced.
"""

from tools.vetting_risk import REGIME, classify_edge, degree_country, era_band


def S(**kw):
    return dict(kw)


def tier(student, advisor=None):
    return classify_edge({}, student, advisor)["tier"]


# ── the core intent ─────────────────────────────────────────────────────


def test_recent_us_phd_is_trusted():
    """The maintainer's central case: recent + single-tier country -> TRUST."""
    assert tier(S(DegreeCountries=["US"], BirthYear=1975)) == "TRUST"


def test_modern_germany_is_trusted_not_blanket_flagged():
    """DE is 5,758 edges. Blanket-flagging it would recreate the
    undifferentiated flag; the Doktorvater IS the doctoral advisor."""
    assert tier(S(DegreeCountries=["DE"], BirthYear=1960)) == "TRUST"


def test_soviet_era_is_reviewed():
    assert tier(S(DegreeCountries=["SU"], BirthYear=1940)) == "REVIEW"


def test_pre_1985_france_is_reviewed():
    """3e cycle vs doctorat d'État is undecidable before the 1984 reform."""
    assert tier(S(DegreeCountries=["FR"], BirthYear=1925)) == "REVIEW"
    assert tier(S(DegreeCountries=["FR"], BirthYear=1975)) == "TRUST"


def test_italy_before_1983_is_retype_not_suspect():
    """Italy had no research doctorate before 1983 — an 'advisor' there is a
    laurea relatore. The people are right; the LABEL is wrong."""
    assert tier(S(DegreeCountries=["IT"], BirthYear=1935)) == "RETYPE"
    assert tier(S(DegreeCountries=["IT"], BirthYear=1975)) == "TRUST"


def test_britain_before_1920_is_retype():
    """No British mathematics PhD until ~1920 — tutor/mentor chain."""
    assert tier(S(DegreeCountries=["GB"], BirthYear=1875)) == "RETYPE"
    assert tier(S(DegreeCountries=["GB"], BirthYear=1970)) == "TRUST"


# ── corrections forced by the adversarial fact-check ────────────────────


def test_norway_is_never_blanket_trusted():
    """REVIEW-FIX S2: dr.philos. is still awarded and is UNSUPERVISED by
    design, so an advisor edge there is fabricated by construction. The draft
    TRUSTed post-2003."""
    assert tier(S(DegreeCountries=["NO"], BirthYear=1980)) == "REVIEW"
    assert REGIME["NO"] == [(0, 9999, "REVIEW")]


def test_denmark_and_greece_and_belgium_windows():
    # S3: Danish higher doctorate still exists.
    assert tier(S(DegreeCountries=["DK"], BirthYear=1980)) == "REVIEW"
    # S1: Greek yfigesia habilitation until 1983.
    assert tier(S(DegreeCountries=["GR"], BirthYear=1940)) == "REVIEW"
    assert tier(S(DegreeCountries=["GR"], BirthYear=1975)) == "TRUST"
    # S4: Belgian agrégation until 2010.
    assert tier(S(DegreeCountries=["BE"], BirthYear=1960)) == "REVIEW"


def test_japan_carries_ronbun_hakase_caveat():
    v = classify_edge({}, S(DegreeCountries=["JP"], BirthYear=1970), None)
    assert v["tier"] == "REVIEW"
    assert "ronbun_hakase_unsupervised_exists" in v["caveats"]


def test_germany_caveat_annotates_without_flagging():
    """A caveat is a TRUE 'yes but' — it must never move the tier."""
    v = classify_edge({}, S(DegreeCountries=["DE"], BirthYear=1960), None)
    assert v["tier"] == "TRUST"
    assert v["caveats"] == ["habilitation_sibling_exists"]


# ── credential dominates ────────────────────────────────────────────────


def test_habilitation_credential_forces_retype_even_in_a_trusted_country():
    v = classify_edge(
        {}, S(DegreeCountries=["US"], BirthYear=1975, DegreeType="habilitation"), None
    )
    assert v["tier"] == "RETYPE"
    assert v["proposed_relation"] == "habilitation_sponsor"


def test_doktor_nauk_credential_forces_retype():
    v = classify_edge(
        {},
        S(
            DegreeCountries=["RU"],
            BirthYear=1940,
            DegreeType="Doctor of Sciences in Physics and Mathematics",
        ),
        None,
    )
    assert v["tier"] == "RETYPE"
    assert v["proposed_relation"] == "higher_doctorate_sponsor"


def test_kandidat_is_corroborating_not_suspect():
    """REVIEW-FIX: the kandidat IS the doctoral tier — it must NOT retype."""
    v = classify_edge(
        {},
        S(
            DegreeCountries=["RU"],
            BirthYear=1940,
            DegreeType="candidate of Sciences in Physics and Mathematics",
        ),
        None,
    )
    assert v["tier"] != "RETYPE"


# ── SUSPECT is narrow ───────────────────────────────────────────────────


def test_advisor_born_after_student_is_suspect():
    assert (
        tier(S(DegreeCountries=["US"], BirthYear=1950), S(BirthYear=1960)) == "SUSPECT"
    )


def test_small_birth_gap_is_NOT_suspect():
    """REVIEW-FIX: the draft flagged gaps under 5 years, but 98% were
    era-consistent and 4 of 5 spot-checks were over-flags on living people.
    A young assistant professor supervising a mature student is ordinary."""
    assert tier(S(DegreeCountries=["US"], BirthYear=1945), S(BirthYear=1944)) == "TRUST"


def test_pre_modern_is_retype_not_suspect():
    """REVIEW-FIX: pre-1900 blanket-SUSPECT libelled 273 Germanic 19th-century
    edges — MGP's best-documented material. Only genuinely pre-modern
    (pre-1810) teacher chains retype."""
    assert tier(S(DegreeCountries=["NL"], BirthYear=1620)) == "RETYPE"
    assert tier(S(DegreeCountries=["DE"], BirthYear=1840)) == "REVIEW"  # not SUSPECT


# ── missing data: never TRUST on absence ────────────────────────────────


def test_unknown_country_is_review_never_trust():
    assert tier(S(BirthYear=1975)) == "REVIEW"


def test_unknown_era_is_review_never_trust():
    assert tier(S(DegreeCountries=["US"])) == "REVIEW"


def test_unmodelled_country_is_review_never_trust():
    """We do not TRUST a regime we have not researched — the fact-check found
    6 countries wrongly TRUSTed during live two-tier periods."""
    assert tier(S(DegreeCountries=["ZZ"], BirthYear=1980)) == "REVIEW"


def test_ambiguous_multi_country_does_not_guess():
    """P69 spanning several countries with no tie-break: refuse to guess.
    Mirzakhani is ['US','IR'] and her CITIZENSHIP is Iran — guessing from
    citizenship would give exactly the wrong regime."""
    cc, basis = degree_country(S(DegreeCountries=["US", "IR"]), None)
    assert cc is None and basis == "P69_ambiguous"


def test_advisor_breaks_the_multi_country_tie():
    cc, basis = degree_country(
        S(DegreeCountries=["US", "IR"]), S(DegreeCountries=["US"])
    )
    assert cc == "US" and basis == "P69_advisor_tiebreak"


# ── R66: un-parked countries, and the rows we REFUSED ───────────────────


def test_unparked_countries_trust_only_after_their_reform():
    """Each un-parked country gets ONE researched reform date; earlier eras
    fall through to REVIEW (no matching window)."""
    for cc, reform in (
        ("IL", 1936),
        ("IR", 1984),
        ("CN", 1983),
        ("KR", 1980),
        ("MX", 1968),
        ("AR", 1995),
        ("EE", 1995),
    ):
        assert tier(S(DegreeCountries=[cc], DefenseYear=reform + 10)) == "TRUST", cc
        assert tier(S(DegreeCountries=[cc], DefenseYear=reform - 30)) == "REVIEW", cc


def test_no_retype_window_was_added_for_the_pre_reform_eras():
    """REVIEW-FIX: the research proposed RETYPE for the pre-reform periods.
    All were rejected — 27 of 48 such edges merely STRADDLED the boundary, so
    RETYPE would convert ignorance into a positive 'the label is wrong' claim.
    Concrete false positives avoided: Estonians who defended in INDEPENDENT
    Estonia; Cheng Shiu-Yuen (PhD Berkeley 1974) retyped via a CN tiebreak."""
    for cc in ("IL", "IR", "CN", "KR", "MX", "AR", "EE"):
        assert not any(t == "RETYPE" for _, _, t in REGIME[cc]), cc


def test_turkey_stays_unmodelled_not_trusted():
    """Turkey adopted the GERMAN model in 1933 and the research could not date
    when doçentlik stopped being required. TRUSTing it open-ended would repeat
    the Greece error exactly."""
    assert "TR" not in REGIME
    assert tier(S(DegreeCountries=["TR"], BirthYear=1970)) == "REVIEW"


def test_estonia_soviet_era_is_review_not_retype():
    """Soviet Estonia WAS the Soviet system, which this file models as REVIEW
    (kandidat is supervised, doktor nauk is not, and they are indistinguishable
    here) — so a RETYPE row there contradicted the file's own SU/RU rows."""
    assert tier(S(DegreeCountries=["EE"], DefenseYear=1975)) == "REVIEW"


# ── era band ────────────────────────────────────────────────────────────


def test_direct_year_beats_birth_year_band():
    assert era_band(S(DefenseYear=1990, BirthYear=1960)) == (1990, 1990, "DefenseYear")


def test_birth_year_yields_a_band_not_a_point():
    lo, hi, basis = era_band(S(BirthYear=1960))
    assert basis == "BirthYear" and lo < hi  # a band, deliberately not b+27
