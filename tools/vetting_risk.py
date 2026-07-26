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
    # DELIBERATELY ABSENT (stay `regime_unknown` -> REVIEW):
    #   TR — adopted the GERMAN model in 1933, and the research could not date
    #        when the doçentlik requirement was dropped. TRUSTing it open-ended
    #        would repeat the Greece error exactly (DE is REVIEW to 1945; GR,
    #        the same institution, REVIEW to 1983).
    #   DZ — its stated rationale is identical to France's, and FR is REVIEW
    #        to 1985.
    #   BR/IN/ZA — the proposed rows were all-REVIEW no-ops: real code, zero
    #        edges moved. Left unmodelled until DegreeType coverage grows.
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
