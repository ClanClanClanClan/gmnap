#!/usr/bin/env python3
"""R65.3 — stratified risk model for MGP-derived advisor edges.

WHY. ~99% of referenced Wikidata P184 statements cite the Mathematics
Genealogy Project, so 28,195 of our 54,818 advisor edges were flagged
`needs_vetting` — undifferentiated. That is too blunt. The maintainer's rule:

    "I am not saying we can never trust MGP: often for more recent people, and
     in countries where the only thing that exists is basically a PhD, we can
     most likely trust what it says. Specific countries and older degrees need
     to be more careful."

MGP's failure modes are STRUCTURED, not random: they cluster where a second
degree tier exists to be confused with the first (Habilitation, Doktor nauk,
doctorat d'État), where a country had no research doctorate at all in the
period, and where the degree is supervisor-free by design. So the model is a
function of (degree country x era x recorded credential).

FOUR TIERS
  TRUST   no positive reason to doubt AND the regime is unambiguous across the
          whole era band -> the flag is REMOVED. TRUST genuinely means "we do
          not flag this".
  REVIEW  no reason to doubt, but we cannot AFFIRM (era straddles a regime
          change, two-tier country, or era unknown). Absence of evidence.
  SUSPECT a POSITIVE marker that the edge is probably wrong.
  RETYPE  the people are probably right but the RELATION LABEL is wrong (a
          habilitation sponsor, a laurea relatore, a higher-doctorate
          consultant). Needs relabelling, not re-verification — so its
          confidence is NOT demoted.

Design verified against the live graph, then adversarially reviewed; the
review's corrections are applied here and marked `# REVIEW-FIX`.
"""

from __future__ import annotations

TRUST, REVIEW, SUSPECT, RETYPE = "TRUST", "REVIEW", "SUSPECT", "RETYPE"
_ORDER = {TRUST: 0, REVIEW: 1, SUSPECT: 2}


def _worse(a: str, b: str) -> str:
    return a if _ORDER.get(a, 0) >= _ORDER.get(b, 0) else b


# ── Regime table ────────────────────────────────────────────────────────
# country -> [(era_from, era_to, floor_tier), ...]; the FLOOR a country/era
# imposes. Eras are doctorate years. INF = open-ended.
INF = 9999

# The modern research doctorate barely exists before ~1810 (Berlin 1810 is the
# conventional anchor). REVIEW-FIX: the draft used a blanket pre-1900 ->
# SUSPECT rule, which flagged 273 Germanic 19th-century edges — Berlin /
# Göttingen / Jena promotion registers, i.e. MGP's BEST-documented material.
# Cutting at 1810 catches the genuinely pre-modern cases without libelling
# the good ones.
PREMODERN_BEFORE = 1810

REGIME: dict[str, list[tuple[int, int, str]]] = {
    # Single-tier PhD systems — the segment the maintainer expects to trust.
    "US": [(0, 1861, SUSPECT), (1861, INF, TRUST)],  # Yale 1861 = first US PhD
    "CA": [(0, 1900, REVIEW), (1900, INF, TRUST)],
    "AU": [(0, 1948, REVIEW), (1948, INF, TRUST)],
    "NZ": [(0, 1948, REVIEW), (1948, INF, TRUST)],
    "IE": [(0, 1920, REVIEW), (1920, INF, TRUST)],
    # GB: no mathematics PhD until ~1920 (the DPhil/PhD arrives 1917-1920).
    # Earlier "advisor" edges are tutor/mentor chains -> RETYPE, not SUSPECT.
    "GB": [(0, 1920, RETYPE), (1920, INF, TRUST)],
    # Germanic: Promotion is the doctorate and the Doktorvater IS the advisor,
    # so this is NOT blanket-flagged (that would recreate the undifferentiated
    # flag over 5,758 edges). The Habilitation sibling is carried as a caveat
    # and only bites via DegreeType or the DDR window.
    "DE": [(0, 1810, SUSPECT), (1810, 1945, REVIEW), (1945, INF, TRUST)],
    "AT": [(0, 1810, SUSPECT), (1810, 1945, REVIEW), (1945, INF, TRUST)],
    "CH": [(0, 1810, SUSPECT), (1810, INF, TRUST)],
    # DDR: Promotion A (doctorate) vs Promotion B (habilitation-equivalent),
    # 1968/69-1991 — same language, overlapping labels.
    "DD": [
        (0, 1810, SUSPECT),
        (1810, 1969, REVIEW),
        (1969, 1991, REVIEW),
        (1991, INF, TRUST),
    ],
    # Soviet sphere: Kandidat (real doctorate, real supervisor) vs Doktor nauk
    # (higher, consultant not supervisor).
    "SU": [(0, INF, REVIEW)],
    "RU": [(0, 1991, REVIEW), (1991, INF, REVIEW)],
    "UA": [(0, 2014, REVIEW), (2014, INF, REVIEW)],
    "BY": [(0, INF, REVIEW)],
    "PL": [(0, INF, REVIEW)],  # dr hab.
    "CZ": [(0, INF, REVIEW)],
    "SK": [(0, INF, REVIEW)],
    "HU": [(0, INF, REVIEW)],
    "RO": [(0, INF, REVIEW)],
    "BG": [(0, INF, REVIEW)],
    "YU": [(0, INF, REVIEW)],
    "RS": [(0, INF, REVIEW)],
    "HR": [(0, INF, REVIEW)],
    "SI": [(0, INF, REVIEW)],
    # France: doctorat d'État / 3e cycle / d'université coexisted until the
    # 1984 reform; HDR (not a doctorate) from 1984/1988.
    "FR": [(0, 1810, SUSPECT), (1810, 1985, REVIEW), (1985, INF, TRUST)],
    # Italy: NO research doctorate before 1983 — an earlier "advisor" is a
    # laurea relatore. That is a relabel, not a doubt -> RETYPE.
    "IT": [(0, 1983, RETYPE), (1983, INF, TRUST)],
    # REVIEW-FIX (fact-check S1): Greece ran the German-model habilitation
    # (υφηγεσία) until it was abolished in 1983. The draft TRUSTed 1900-now.
    "GR": [(0, 1900, SUSPECT), (1900, 1983, REVIEW), (1983, INF, TRUST)],
    # REVIEW-FIX (S4): Belgium's agrégation de l'enseignement supérieur (its
    # habilitation) ran until 2010; the draft TRUSTed 2008+.
    "BE": [(0, 1930, REVIEW), (1930, 2010, REVIEW), (2010, INF, TRUST)],
    "NL": [(0, 1900, REVIEW), (1900, INF, TRUST)],  # promotor-of-record caveat
    "ES": [(0, 1900, REVIEW), (1900, INF, TRUST)],
    "PT": [(0, 1930, REVIEW), (1930, INF, TRUST)],
    # REVIEW-FIX (S2): Norway's dr.philos. is STILL awarded and is
    # unsupervised BY DESIGN — an advisor edge there is fabricated by
    # construction. The draft TRUSTed post-2003. Never blanket-TRUST NO.
    "NO": [(0, INF, REVIEW)],
    # REVIEW-FIX (S3): Denmark's higher doctorate (dr.phil./dr.scient.) still
    # exists, is not equivalent to the ph.d., and is unsupervised.
    "DK": [(0, INF, REVIEW)],
    "SE": [(0, 1970, REVIEW), (1970, INF, TRUST)],
    "FI": [(0, 1970, REVIEW), (1970, INF, TRUST)],
    # Japan: ronbun hakase (thesis doctorate, no coursework, no formal
    # supervisor) coexists with katei hakase to this day.
    "JP": [(0, INF, REVIEW)],
    # R66 — countries un-parked from `regime_unknown`. Each has ONE researched
    # reform date after which a single supervised research doctorate is the
    # only doctoral credential; everything earlier stays REVIEW (no window
    # matches -> era_out_of_range -> REVIEW), which is the safe default.
    #
    # The research also proposed RETYPE windows for the PRE-reform periods.
    # Every one was REJECTED on adversarial review, because RETYPE asserts
    # "the relation label is wrong" and 27 of 48 such edges had an era band
    # merely STRADDLING the boundary — converting ignorance into a positive
    # claim. Concrete false positives it would have shipped: Estonians who
    # defended in INDEPENDENT Estonia retyped as Soviet; Cheng Shiu-Yuen
    # (PhD Berkeley 1974 under Chern) retyped via a CN tiebreak. RETYPE is
    # reserved for "the first tier did not exist" (Italy pre-1983, Britain
    # pre-1920), NOT for "two routes coexisted" — coexistence is REVIEW.
    "IL": [(0, 1936, REVIEW), (1936, INF, TRUST)],
    "IR": [(0, 1984, REVIEW), (1984, INF, TRUST)],
    "CN": [(0, 1983, REVIEW), (1983, INF, TRUST)],
    "KR": [(0, 1980, REVIEW), (1980, INF, TRUST)],
    "MX": [(0, 1968, REVIEW), (1968, INF, TRUST)],
    "AR": [(0, 1995, REVIEW), (1995, INF, TRUST)],
    "EE": [(0, 1995, REVIEW), (1995, INF, TRUST)],
    # R70 — the three countries that actually held the parked edges. Measured
    # BEFORE deciding: of the 756 edges then parked on `regime_unknown`,
    # BR+IN+ZA held 343 of them and 171 of the 227 that could ever flip. The
    # rest of the tail was 45 countries holding 1-30 edges each, most with no
    # era at all, so researching them buys almost nothing and risks a lot.
    # Measured AFTER: these rows moved exactly the predicted 171 (78 IN,
    # 57 BR, 36 ZA), leaving 413 parked. `make regime-coverage` re-derives it.
    #
    # Each row follows a precedent ALREADY in this table rather than a fresh
    # judgement — that is the check the six wrongly-TRUSTed countries failed:
    #   BR post-1965 :: DE post-1945 — a habilitation-like sibling
    #     (livre-docencia) exists, but it is POST-doctoral and distinct, so it
    #     is a caveat, not a blocker.
    #   IN post-1956 :: GB post-1920 — a higher doctorate on published work
    #     (D.Sc., first awarded in mathematics at Allahabad in 1898) coexists
    #     with the supervised PhD. Britain has exactly this and is TRUSTed
    #     from 1920.
    #   ZA post-1922 :: GB post-1920 — same structure, same reasoning.
    # NOT the NO/DK precedent: there the higher doctorate is a PRIMARY route
    # taken INSTEAD of a supervised doctorate, so an advisor edge is fabricated
    # by construction. A post-doctoral higher degree is not that.
    "BR": [(0, 1965, REVIEW), (1965, INF, TRUST)],
    # India: the conservative anchor. The supervised PhD dates to the 1910s-20s
    # (Calcutta 1909/1921), which would justify a much earlier window; the UGC
    # Act 1956 is used instead because that is when doctoral standards became
    # nationally regulated. It leaves the 1920s-50s edges at REVIEW — the safe
    # direction — and can be loosened later WITH evidence.
    "IN": [(0, 1956, REVIEW), (1956, INF, TRUST)],
    "ZA": [(0, 1922, REVIEW), (1922, INF, TRUST)],
    # DELIBERATELY ABSENT (stay `regime_unknown` -> REVIEW):
    #   TR — adopted the GERMAN model in 1933, and the research could not date
    #        when the doçentlik requirement was dropped. TRUSTing it open-ended
    #        would repeat the Greece error exactly (DE is REVIEW to 1945; GR,
    #        the same institution, REVIEW to 1983).
    #   DZ — its stated rationale is identical to France's, and FR is REVIEW
    #        to 1985.
    #   (BR/IN/ZA sat here until R70. The R66 note called their proposed rows
    #        "all-REVIEW no-ops"; re-measured, they were the three LARGEST
    #        parked populations. They have researched rows above now.)
}

# Permanent structural caveats — TRUE but NOT flags. A caveat annotates; it
# never moves the tier. These are exactly the "yes but" facts a reader of the
# edge deserves.
CAVEAT: dict[str, str] = {
    "DE": "habilitation_sibling_exists",
    "AT": "habilitation_sibling_exists",
    "CH": "habilitation_sibling_exists",
    "DD": "promotion_b_habilitation_equivalent",
    "PL": "dr_hab_sibling_exists",
    "NL": "promotor_of_record_may_differ_from_daily_supervisor",
    "NO": "drphilos_unsupervised_by_design",
    "DK": "higher_doctorate_unsupervised_exists",
    "SE": "licentiate_sibling_exists",
    "FI": "licentiate_sibling_exists",
    "JP": "ronbun_hakase_unsupervised_exists",
    "GR": "yfigesia_habilitation_until_1983",
    "BE": "agregation_habilitation_until_2010",
    "BR": "livre_docencia_sibling_exists",
    "IN": "dsc_higher_doctorate_on_published_work_exists",
    "ZA": "dsc_higher_doctorate_on_published_work_exists",
}

# ── Why each TRUST window opens ─────────────────────────────────────────
#
# WHY THIS TABLE EXISTS. A TRUST row REMOVES a flag: it is the only direction
# in this model that can silently launder a wrong MGP edge into the canonical
# graph. Six countries were TRUSTed wrongly (Greece running the yfigesia to
# 1983, Belgium the agregation to 2010, Norway's and Denmark's unsupervised
# higher doctorates, and two more), and every one was caught by a HUMAN
# fact-check pass that happened to be run. Nothing in the code required a row
# to say what it rested on, so nothing would have caught the seventh.
#
# So: evidence is mandatory exactly where the flag is removed. REVIEW needs no
# anchor — "we cannot affirm this" is the safe default and asserts nothing.
#
# `year` MUST equal the year the TRUST window opens in REGIME. That is the
# enforced part, and it is the real teeth: it catches a date edited without
# its reason, which is close to how the six got in. `source` is a URL where
# the claim was checked against a document; "" marks an anchor CARRIED FROM AN
# EARLIER ROUND AND NOT INDEPENDENTLY SOURCED. Those are not silently
# tolerated — tests/unit/test_vetting_risk.py pins how many there are, so the
# number can only go DOWN without a deliberate edit.
TRUST_ANCHOR: dict[str, tuple[int, str, str]] = {
    # (year, the documented event that opens the window, source URL or "")
    "BR": (
        1965,
        "Parecer CFE 977/1965 (the 'Parecer Sucupira', 3 Dec 1965) structures "
        "master's and doctoral courses; still the basis of CAPES regulation.",
        "https://www.gov.br/capes/pt-br/assuntos/noticias/"
        "regulamentacao-da-pos-graduacao-do-pais-completa-60-anos",
    ),
    "IN": (
        1956,
        "UGC Act 1956 puts doctoral standards under a national regulator. "
        "Deliberately later than the first supervised PhDs (Calcutta, 1909/"
        "1921) — the conservative end of the defensible range.",
        "https://en.wikipedia.org/wiki/UGC_India",
    ),
    "ZA": (
        1922,
        "First South African PhD (S. H. Skaife, 1922); doctoral education "
        "surveyed from the 1899 LLD onward by Herman (2017).",
        "https://doi.org/10.1080/03075079.2015.1101756",
    ),
    # ── carried from earlier rounds, not independently sourced ──────────
    "US": (1861, "Yale confers the first US PhD, 1861.", ""),
    "CA": (1900, "Research doctorate established by ~1900.", ""),
    "AU": (1948, "First Australian PhDs conferred from 1948.", ""),
    "NZ": (1948, "First New Zealand PhDs conferred from 1948.", ""),
    "IE": (1920, "PhD adopted alongside the British reform, ~1920.", ""),
    "GB": (1920, "The DPhil/PhD arrives in Britain 1917-1920.", ""),
    "DE": (
        1945,
        "Post-war Promotion is the doctorate; Habilitation is a "
        "separate post-doctoral credential.",
        "",
    ),
    "AT": (1945, "As DE — post-war Promotion is the doctorate.", ""),
    "CH": (1810, "Single Promotion from the modern-university anchor.", ""),
    "DD": (1991, "Reunification ends the Promotion A / Promotion B split.", ""),
    "FR": (
        1985,
        "The 1984 reform replaces doctorat d'Etat / 3e cycle / "
        "d'universite with the single doctorat.",
        "",
    ),
    "IT": (
        1983,
        "Italy's research doctorate is created in 1983; before it "
        "there is only the laurea relatore.",
        "",
    ),
    "GR": (1983, "The yfigesia (Greek habilitation) is abolished in 1983.", ""),
    "BE": (
        2010,
        "The agregation de l'enseignement superieur (Belgium's "
        "habilitation) runs until 2010.",
        "",
    ),
    "NL": (1900, "Single promotie; the promotor-of-record caveat is separate.", ""),
    "ES": (1900, "Single doctorado from ~1900.", ""),
    "PT": (1930, "Single doutoramento from ~1930.", ""),
    "SE": (
        1970,
        "The 1969 reform replaces the old doktorsgrad; licentiate "
        "becomes a separate lesser degree.",
        "",
    ),
    "FI": (1970, "As SE — the parallel Nordic reform.", ""),
    "IL": (1936, "Doctoral studies at the Hebrew University from 1936.", ""),
    "IR": (1984, "Post-revolution reorganisation of doctoral education.", ""),
    "CN": (
        1983,
        "China's first PhDs are conferred in 1983 under the 1981 "
        "Academic Degrees Regulations.",
        "",
    ),
    "KR": (1980, "Single supervised doctorate from ~1980.", ""),
    "MX": (1968, "Single doctorado from ~1968.", ""),
    "AR": (
        1995,
        "Ley de Educacion Superior 24.521 (1995) regulates " "postgraduate degrees.",
        "",
    ),
    "EE": (1995, "Post-Soviet reform replaces the kandidat with the PhD.", ""),
}


# A recorded credential that is NOT a first doctorate. This DOMINATES the
# country/era logic: it is direct evidence about what the edge is.
# NOTE: "candidate of Sciences" is deliberately absent — the kandidat IS the
# doctoral tier, so it CORROBORATES rather than warns (REVIEW-FIX).
RETYPE_CREDENTIAL: list[tuple[str, str]] = [
    ("habilitation", "habilitation_sponsor"),
    ("doctor of sciences", "higher_doctorate_sponsor"),
    ("doktor nauk", "higher_doctorate_sponsor"),
    ("professor", "not_a_degree"),
    ("docent", "not_a_degree"),
    ("emeritus", "not_a_degree"),
    ("honorary", "honorary_not_doctoral"),
    ("master", "not_a_doctorate"),
    ("bachelor", "not_a_doctorate"),
    ("magister", "not_a_doctorate"),
    ("laurea", "laurea_relatore"),
    ("licentiate", "licentiate_supervisor"),
]

# Doctorate-era band from a birth year. The review measured that band WIDTH
# moves the answer by only ~3.4pp across a wide sweep — so this is a band, not
# a tuned parameter, and must not be over-fitted.
ERA_LO_OFFSET, ERA_HI_OFFSET = 23, 40


def era_band(rec: dict) -> tuple[int | None, int | None, str]:
    """(lo, hi, basis) for the doctorate year. Direct year if we have one."""
    for field in ("DefenseYear", "ThesisYear"):
        y = rec.get(field)
        if isinstance(y, int):
            return y, y, field
    by = rec.get("BirthYear")
    if isinstance(by, int):
        return by + ERA_LO_OFFSET, by + ERA_HI_OFFSET, "BirthYear"
    return None, None, "none"


def degree_country(rec: dict, advisor_rec: dict | None) -> tuple[str | None, str]:
    """Where the doctorate was taken, and on what basis.

    Priority: the student's own study countries (Wikidata P69 "educated at" ->
    P17, authoritative — NOT a gazetteer over institution name strings, which
    mis-filed New York University as British). P69 is multi-valued and picking
    [0] is arbitrary, so when the values span several countries we break the
    tie with the ADVISOR's study country — near-conclusive, because the
    doctorate was taken with that advisor (REVIEW-FIX: 295 TRUST edges rested
    on the arbitrary pick; e.g. Hurwitz->Hilbert keyed US via Harvard when the
    doctorate was Göttingen).
    """
    ccs = [c for c in (rec.get("DegreeCountries") or []) if c]
    if len(ccs) == 1:
        return ccs[0], "P69_institution"
    if len(ccs) > 1:
        adv_ccs = set((advisor_rec or {}).get("DegreeCountries") or [])
        overlap = [c for c in ccs if c in adv_ccs]
        if len(overlap) == 1:
            return overlap[0], "P69_advisor_tiebreak"
        return None, "P69_ambiguous"  # never guess
    for src, basis in (
        (rec.get("CountryCode"), "P27_citizenship"),
        ((advisor_rec or {}).get("DegreeCountries") or [None], "advisor_institution"),
    ):
        v = src[0] if isinstance(src, list) else src
        if v:
            return v, basis
    return None, "none"


def _regime_tier(
    cc: str | None, lo: int | None, hi: int | None
) -> tuple[str, list[str]]:
    """Floor tier imposed by (country, era band), plus reasons.

    A band that STRADDLES a regime change cannot be affirmed, so it takes the
    worst tier it touches — that is the whole point of using a band.
    """
    if not cc:
        return REVIEW, ["country_unknown"]
    rows = REGIME.get(cc)
    if not rows:
        return REVIEW, [f"regime_unknown_{cc}"]
    if lo is None:
        return REVIEW, ["era_unknown"]
    tiers, reasons = [], []
    for a, b, t in rows:
        if lo < b and hi >= a:  # band overlaps this window
            tiers.append(t)
            if t != TRUST:
                reasons.append(f"regime_{cc}_{a}_{b}_{t.lower()}")
    if not tiers:
        return REVIEW, [f"regime_{cc}_era_out_of_range"]
    if RETYPE in tiers:
        return RETYPE, reasons
    worst = TRUST
    for t in tiers:
        worst = _worse(worst, t)
    return worst, reasons


def classify_edge(edge: dict, student: dict, advisor_rec: dict | None) -> dict:
    """Return the vetting verdict for one MGP-derived edge."""
    lo, hi, era_basis = era_band(student)
    if lo is None and advisor_rec:  # inherit the advisor's era as a floor
        a_lo, a_hi, a_basis = era_band(advisor_rec)
        if a_lo is not None:
            lo, hi, era_basis = a_lo + 20, a_hi + 40, f"advisor_{a_basis}"
    cc, cc_basis = degree_country(student, advisor_rec)

    tier, reasons = _regime_tier(cc, lo, hi)
    caveats = [CAVEAT[cc]] if cc in CAVEAT else []

    # R69 — REGISTRY EVIDENCE LIFTS THE FRANCE WINDOW.
    #
    # France is REVIEW for 1810-1985 for ONE reason: several doctorates ran in
    # parallel (d'Etat, 3e cycle, d'universite, d'ingenieur) and a
    # mathematician routinely held two of them, years apart, under DIFFERENT
    # advisors. We could not AFFIRM which degree an edge belonged to.
    #
    # Sudoc answers exactly that question. When ABES records exactly ONE
    # pre-1985 doctorate for this person, there is no second degree for the
    # edge to be confused with, so the specific doubt that put it in REVIEW is
    # resolved and the edge is TRUSTed. This is person-level registry evidence
    # overriding a country-level prior — the direction the maintainer asked
    # for ("do not throw away MGP data"), and the only kind of lift in this
    # model.
    #
    # NARROW BY CONSTRUCTION. It fires only when the France window is the SOLE
    # reason. Every other reason (a straddled regime change, an unknown era, a
    # recorded habilitation) leaves the edge exactly where it was, and the
    # SUSPECT / RETYPE rules below still run and still override downward.
    sudoc_n = student.get("SudocPre1985Count")
    if isinstance(sudoc_n, int) and cc == "FR":
        if (
            sudoc_n == 1
            and tier == REVIEW
            and reasons == ["regime_FR_1810_1985_review"]
        ):
            tier = TRUST
            reasons = [
                f"sudoc_single_pre1985_doctorate_{student.get('SudocPre1985Year')}"
            ]
        elif sudoc_n > 1:
            # The Brezis pattern. Still REVIEW — but now a KNOWN multi-degree
            # case rather than an unexplained flag, which is precisely where
            # MGP tends to flatten two sequential advisors into "co-advisors".
            reasons = reasons + [f"sudoc_multi_pre1985_doctorate_{sudoc_n}"]

    # Pre-modern: no research doctorate existed to supervise.
    if hi is not None and hi < PREMODERN_BEFORE:
        tier, reasons = RETYPE, reasons + ["pre_modern_doctorate_teacher_chain"]

    # A recorded non-first-doctorate credential DOMINATES: it is direct
    # evidence about what this edge is.
    deg = (student.get("DegreeType") or "").lower()
    proposed = None
    for needle, label in RETYPE_CREDENTIAL:
        if needle in deg:
            tier, proposed = RETYPE, label
            reasons = reasons + [f"credential_{label}"]
            break

    # SUSPECT is reserved for a hard impossibility. REVIEW-FIX: the draft
    # flagged an advisor/student birth gap under 5 years, but 98% of those
    # were era-consistent and 4 of 5 spot-checks were over-flags on LIVING
    # people (a young assistant professor supervising a mature student is
    # ordinary academia). Only "the advisor was born AFTER the student"
    # survives — that one is genuinely impossible.
    s_by = student.get("BirthYear")
    a_by = (advisor_rec or {}).get("BirthYear")
    if isinstance(s_by, int) and isinstance(a_by, int) and a_by > s_by:
        if tier != RETYPE:  # RETYPE is a label claim; it is not "worse"-able
            tier = _worse(tier, SUSPECT)
        reasons = reasons + ["advisor_born_after_student"]

    out = {
        "tier": tier,
        "degree_country": cc,
        "country_basis": cc_basis,
        "era_lo": lo,
        "era_hi": hi,
        "era_basis": era_basis,
        "reasons": reasons,
        "caveats": caveats,
    }
    if proposed:
        out["proposed_relation"] = proposed
    return out
