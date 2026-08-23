"""R65.3 pins — the stratified MGP risk model.

The maintainer's rule: trust MGP for recent people in single-tier-PhD
countries; be careful with older degrees and two-tier countries. These pin
that behaviour, and pin the corrections the adversarial review forced.
"""

from tools.vetting_risk import (
    REGIME,
    TRUST,
    TRUST_ANCHOR,
    classify_edge,
    degree_country,
    era_band,
)


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


# ── R70: evidence is mandatory exactly where the flag is REMOVED ────────


def _trust_countries():
    return {cc for cc, rows in REGIME.items() if any(t == TRUST for _, _, t in rows)}


def test_every_trust_window_names_the_event_that_opens_it():
    """A TRUST row is the only thing in this model that REMOVES a flag, so it
    is the only direction that can launder a wrong MGP edge into the canonical
    graph. Six countries were TRUSTed wrongly and every one was caught by a
    human fact-check that happened to be run — nothing in the code required a
    row to say what it rested on, so nothing would have caught the seventh.

    REVIEW deliberately needs no anchor: "we cannot affirm this" asserts
    nothing and is the safe default."""
    missing = _trust_countries() - set(TRUST_ANCHOR)
    assert not missing, f"TRUST window with no stated basis: {sorted(missing)}"
    orphan = set(TRUST_ANCHOR) - _trust_countries()
    assert not orphan, f"anchor for a country with no TRUST window: {sorted(orphan)}"


def test_anchor_year_matches_the_window_it_justifies():
    """THE TEETH. Catches a date edited without its reason — close to how the
    six wrong rows got in (a year with no stated basis behind it)."""
    for cc in sorted(_trust_countries()):
        window_opens = next(a for a, _b, t in REGIME[cc] if t == TRUST)
        anchor_year, event, _src = TRUST_ANCHOR[cc]
        assert (
            anchor_year == window_opens
        ), f"{cc}: TRUST opens {window_opens} but its anchor says {anchor_year}"
        assert event.strip(), f"{cc}: empty anchor text"


def test_unsourced_anchors_are_a_ratchet_that_can_only_tighten():
    """26 of the 29 anchors are carried from earlier rounds without an
    external source. That is the honest state, not a passing grade — pinning
    the COUNT means a new TRUST country cannot be added sourceless without
    deliberately editing this number, and the backlog can only shrink."""
    unsourced = sorted(cc for cc, (_y, _e, src) in TRUST_ANCHOR.items() if not src)
    assert len(unsourced) <= 26, f"a new unsourced TRUST window appeared: {unsourced}"


# ── R70: the three researched rows ─────────────────────────────────────


def test_brazil_trusts_after_the_sucupira_reform_only():
    """Parecer CFE 977/1965 structures the doutorado. Before it, Brazilian
    academic credentials were the catedra and the livre-docencia."""
    assert tier(S(DegreeCountries=["BR"], DefenseYear=1990)) == "TRUST"
    assert tier(S(DegreeCountries=["BR"], DefenseYear=1950)) == "REVIEW"


def test_india_uses_the_conservative_anchor():
    """The supervised PhD dates to the 1910s-20s, which would justify a much
    earlier window. 1956 (UGC Act) is chosen deliberately: it leaves the
    1920s-50s edges at REVIEW, the safe direction."""
    assert tier(S(DegreeCountries=["IN"], DefenseYear=1975)) == "TRUST"
    assert tier(S(DegreeCountries=["IN"], DefenseYear=1935)) == "REVIEW"


def test_south_africa_trusts_from_the_first_phd():
    assert tier(S(DegreeCountries=["ZA"], DefenseYear=1990)) == "TRUST"
    assert tier(S(DegreeCountries=["ZA"], DefenseYear=1905)) == "REVIEW"


def test_new_rows_follow_the_GB_precedent_not_the_NO_precedent():
    """BR/IN/ZA each have a higher doctorate or habilitation sibling, and so
    does Britain (DSc on published work) — which is TRUSTed from 1920. What
    keeps NO and DK at REVIEW is different in kind: there the unsupervised
    doctorate is a PRIMARY route taken INSTEAD of a supervised one, so an
    advisor edge is fabricated by construction. If that distinction is ever
    dropped, this test should fail before the tiers move."""
    for cc in ("BR", "IN", "ZA", "GB"):
        assert any(t == TRUST for _, _, t in REGIME[cc]), cc
    for cc in ("NO", "DK"):
        assert not any(t == TRUST for _, _, t in REGIME[cc]), cc


def test_the_researched_rows_carry_their_caveat():
    """TRUST removes the flag; the structural 'yes but' still reaches the
    reader."""
    from tools.vetting_risk import CAVEAT

    assert CAVEAT["BR"] == "livre_docencia_sibling_exists"
    assert "published_work" in CAVEAT["IN"]
    v = classify_edge({}, S(DegreeCountries=["BR"], DefenseYear=1990), None)
    assert v["tier"] == "TRUST" and v["caveats"] == ["livre_docencia_sibling_exists"]


# ── R69: Sudoc registry evidence lifts the France window ───────────────


def test_single_pre1985_doctorate_lifts_france_out_of_review():
    """France is REVIEW 1810-1985 for ONE reason: several doctorates ran in
    parallel and a mathematician routinely held two, under different advisors.
    ABES evidence of exactly one pre-1985 doctorate removes that specific
    doubt."""
    base = S(DegreeCountries=["FR"], DefenseYear=1970)
    assert tier(base) == "REVIEW"
    lifted = classify_edge(
        {}, S(**base, SudocPre1985Count=1, SudocPre1985Year=1970), None
    )
    assert lifted["tier"] == "TRUST"
    assert lifted["reasons"] == ["sudoc_single_pre1985_doctorate_1970"]


def test_two_pre1985_doctorates_stay_review_but_explained():
    """The Brezis pattern: 3e cycle 1966 under Choquet, doctorat d'Etat 1971
    under Lions. Still REVIEW — but a KNOWN multi-degree case, which is
    exactly where MGP flattens two sequential advisors into 'co-advisors'."""
    v = classify_edge(
        {}, S(DegreeCountries=["FR"], DefenseYear=1970, SudocPre1985Count=2), None
    )
    assert v["tier"] == "REVIEW"
    assert "sudoc_multi_pre1985_doctorate_2" in v["reasons"]


def test_sudoc_lift_is_narrow_and_never_overrides_a_real_doubt():
    """It fires ONLY when the France window is the sole reason. A recorded
    habilitation, an impossible birth order, or another country must all
    survive the evidence."""
    # a recorded habilitation still RETYPEs
    v = classify_edge(
        {},
        S(
            DegreeCountries=["FR"],
            DefenseYear=1970,
            DegreeType="Habilitation",
            SudocPre1985Count=1,
        ),
        None,
    )
    assert v["tier"] == "RETYPE"
    # advisor born after the student is still impossible
    v = classify_edge(
        {},
        S(
            DegreeCountries=["FR"],
            DefenseYear=1970,
            BirthYear=1940,
            SudocPre1985Count=1,
        ),
        S(BirthYear=1960),
    )
    assert v["tier"] == "SUSPECT"
    # and it does not leak to other countries
    v = classify_edge(
        {}, S(DegreeCountries=["PL"], DefenseYear=1970, SudocPre1985Count=1), None
    )
    assert v["tier"] == "REVIEW"
