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

import re
from typing import NamedTuple

TRUST, REVIEW, SUSPECT, RETYPE = "TRUST", "REVIEW", "SUSPECT", "RETYPE"
_ORDER = {TRUST: 0, REVIEW: 1, SUSPECT: 2}


def _worse(a: str, b: str) -> str:
    return a if _ORDER.get(a, 0) >= _ORDER.get(b, 0) else b


# ── The sibling-credential test ─────────────────────────────────────────
#
# R71 ADDED THIS BECAUSE ITS ABSENCE WAS THE REAL DEFECT. Every failure this
# model has had — the six wrongly-TRUSTed countries, and the contradictions an
# adversarial review found in R71 — comes from one unwritten decision: when a
# SECOND doctoral-level credential exists in a country, does it disqualify the
# country or merely annotate it? With no stated test, each country was decided
# on its own and the answers stopped agreeing with each other. A reviewer put
# it exactly right: a taxonomy that can be bent either way to reach an answer
# already chosen has stopped doing work.
#
# THE TEST. A second doctoral-level credential DISQUALIFIES a country (no
# TRUST window, ever) if and only if it is BOTH:
#
#   1. UNGATED — obtainable without already holding the supervised doctorate,
#      so it can be somebody's FIRST and only doctorate; and
#   2. A MATERIAL ROUTE — actually used, not a rarity awarded late in a career.
#
# If it is gated on a prior doctorate it is POST-doctoral by construction, a
# person holding it also holds a supervised doctorate, and it is a CAVEAT:
# German Habilitation, Polish dr hab., French HDR, Portuguese agregacao,
# GDR Promotion B, the British/Irish/Indian/South African higher doctorate in
# its modern form (formally gated only on a first degree plus 8-12 years'
# standing, but in practice taken by people who already hold a doctorate).
#
# Worked both ways, so the test is falsifiable rather than decorative:
#   NO  dr.philos.  -> ungated (no doctorate required) + a real route -> DISQUALIFY
#   DK  dr.phil.    -> "requires a master's degree, but not necessarily a
#                       ph.d." -> ungated -> DISQUALIFY
#   PT  art. 33 "regime especial" -> thesis defended "sem inscricao no ciclo de
#                       estudos ... e sem a orientacao", open to anyone meeting
#                       the ENTRY conditions for the doctorate -> ungated ->
#                       DISQUALIFY (found in R71; PT had been TRUSTed since 1930)
#   DE  Habilitation-> "umfassen als Vorbedingung immer die Promotion" -> gated
#                       -> CAVEAT, country stays TRUSTed
#   GB  ScD/LittD   -> published work, no supervisor, but "almost all of those
#                       receiving them have a PhD already" -> not a first
#                       doctorate in practice -> CAVEAT
#
# KNOWN UNRESOLVED CONTRADICTION, recorded rather than quietly settled: by this
# test Poland's dr hab. is GATED ("posiadala stopien doktora") and should be a
# caveat, yet PL is REVIEW open-ended — i.e. the model is probably too harsh on
# 1,330 Polish edges. It is NOT being changed here. Unflagging is the dangerous
# direction and needs far stronger evidence than flagging does; the asymmetry
# is deliberate. Same for NO/DK/JP, where a late supervised-PhD window was
# proposed and REFUTED BY MEASUREMENT: credential names survive in the corpus
# (73 distinct DegreeType values) but on only 5.3% of records, so for 94.7% a
# dr.philos. is indistinguishable from a ph.d. and no name-scoped exclusion can
# rescue those countries.


# ── East German doctorates ──────────────────────────────────────────────
#
# GDR doctorates resolve to DE, not DD: Wikidata P69 -> P17 gives modern
# Germany for Leipzig, Humboldt, Jena and the rest, so the DD row written to
# handle Promotion A vs Promotion B holds 13 edges while 202 East German
# doctorates sit inside DE and are TRUSTed by the West German rule. That is the
# Greece/Belgium shape exactly — a second credential inside a TRUST window,
# reached by a code path nobody checked. Institution is present on 84% of
# records, so the era band plus the institution routes them back.
GDR_INSTITUTIONS = re.compile(
    r"leipzig|humboldt|jena|halle-wittenberg|martin luther univ|rostock"
    r"|greifswald|dresden|magdeburg|ilmenau|freiberg|chemnitz|karl-marx"
    r"|akademie der wissenschaften der ddr",
    re.IGNORECASE,
)
GDR_FROM, GDR_TO = 1949, 1990


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
    # R71: was [(0,1861,SUSPECT),(1861,INF,TRUST)]. Yale 1861 is the first US
    # PhD — but that marks when the degree BEGAN, not when it became a
    # reliable supervised credential. The AAU was founded in 1900 precisely
    # because US PhD-granting was unregulated and diploma mills proliferated,
    # so 1861-1900 is REVIEW, not TRUST. Costs 62 of 6,750 US TRUST edges
    # (0.9%) — the anchor was wrong in KIND, and fixing it was nearly free.
    "US": [(0, 1861, SUSPECT), (1861, 1900, REVIEW), (1900, INF, TRUST)],
    "CA": [(0, 1900, REVIEW), (1900, INF, TRUST)],
    "AU": [(0, 1948, REVIEW), (1948, INF, TRUST)],
    "NZ": [(0, 1948, REVIEW), (1948, INF, TRUST)],
    "IE": [(0, 1920, REVIEW), (1920, INF, TRUST)],
    # GB: no mathematics PhD until ~1920 (the DPhil/PhD arrives 1917-1920).
    # Earlier "advisor" edges are tutor/mentor chains -> RETYPE, not SUSPECT.
    # R71: 1920 -> 1921, the first mathematics DPhil (Oxford). The old anchor
    # said "1917-1920", a range rather than a date. Costs 1 edge.
    "GB": [(0, 1921, RETYPE), (1921, INF, TRUST)],
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
    # R71: 1900 -> 1954. From the Ley Moyano (1857) until 1954 ONLY the
    # Universidad Central de Madrid could confer a doctorate, so a
    # mathematician based elsewhere took the degree in Madrid and the recorded
    # director may be the Madrid formality rather than the actual mentor —
    # exactly what REVIEW is for. Costs 38 of 433 (the Spanish population is
    # overwhelmingly modern; median era 1983).
    "ES": [(0, 1954, REVIEW), (1954, INF, TRUST)],
    # R71: was [(0,1930,REVIEW),(1930,INF,TRUST)]. Portuguese law keeps a
    # statutory UNSUPERVISED route to the grau de doutor — art. 33 "regime
    # especial de apresentacao da tese" lets a candidate defend "sem inscricao
    # no ciclo de estudos ... e sem a orientacao", open to anyone meeting the
    # ENTRY conditions for the doctorate rather than to existing doctors. That
    # is ungated and therefore the Norway/Denmark shape, not the habilitation
    # shape. Verified against the statute text, not inferred.
    "PT": [(0, INF, REVIEW)],
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
    # R71: the DE caveat now names the GDR problem too. 202 East German
    # doctorates are coded DE (see GDR_INSTITUTIONS); they are re-routed to the
    # DD regime, but any that lack an Institution string still land here.
    "DE": "habilitation_sibling_plus_gdr_promotion_b_inside_window",
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
    # R71 — two siblings that were documented in this file's own prose but
    # never recorded as caveats, while the SAME credential was recorded for
    # India and South Africa. That inconsistency is the shape of the original
    # six-country error.
    "FR": "hdr_habilitation_since_1984",
    "GB": "higher_doctorate_on_published_work_exists",
    # R71 — siblings surfaced by the adversarial verification pass. All are
    # GATED credentials, so by the sibling-credential test above they annotate
    # and do not disqualify. Recording them is the whole point: the six wrong
    # countries were wrong because nobody had written the sibling down.
    "IE": "higher_doctorate_on_published_work_exists",
    "AU": "higher_doctorate_on_published_work_exists",
    "NZ": "higher_doctorate_on_published_work_exists",
    "US": "honorary_phd_conferred_until_1937",
    "PT": "unsupervised_thesis_route_art33_still_in_force",
    "CA": "quebec_francophone_and_pontifical_doctorates_unverified",
    "CN": "tongdengxueli_non_enrolled_doctorate_route",
    "EE": "research_masters_teadusmagister_until_2002",
    "IT": "abilitazione_scientifica_nazionale",
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
# R71 SPLIT THE BACKLOG IN TWO. R70 recorded every anchor as either sourced or
# "unsourced", which lumped together two completely different situations:
#
#   * an anchor that NAMES A REAL EVENT and simply had not been checked yet
#     (Italy's 1983 research doctorate, Greece's 1983 abolition) — that is a
#     genuine backlog item, and it is what the ratchet now counts; and
#   * an anchor for which NO SINGLE DOCUMENTED EVENT EXISTS, where the year is
#     a deliberate conservative choice (Germany 1945 is the post-war boundary,
#     not a doctorate reform; nothing happened to the German Promotion in
#     1945). Chasing a citation for those is chasing something that does not
#     exist, and leaving them labelled "unsourced" implies a debt that can
#     never be paid.
#
# Conflating the two made the backlog look uniformly like missing homework. It
# is not: some of it is missing homework, and some of it is judgement that
# should be labelled as judgement and argued on its merits.
#
# ENFORCED (tests/unit/test_vetting_risk.py):
#   * `year` MUST equal the year the TRUST window opens in REGIME — the real
#     teeth, catching a date edited without its reason, which is close to how
#     the six wrong rows got in;
#   * basis="document" means a specific datable event, and its `event` must
#     name one;
#   * a `source` URL is only credible if someone actually opened it, so a
#     source MUST carry the `quote` seen there and the `retrieved` date. A URL
#     nobody ever fetched is the same defect class as a sidecar nothing reads;
#   * basis="judgement" MUST NOT carry a source — if there is a document to
#     cite, it is not a judgement;
#   * the count of document-basis anchors still missing a source is pinned, so
#     the real backlog can only shrink.


class Anchor(NamedTuple):
    """The documented event (or stated judgement) that opens a TRUST window."""

    year: int
    event: str
    basis: str = "judgement"  # "document" | "judgement"
    source: str = ""
    quote: str = ""  # text actually read on that page
    retrieved: str = ""  # ISO date it was read


TRUST_ANCHOR: dict[str, Anchor] = {
    # ── verified against a fetched page ─────────────────────────────────
    "US": Anchor(
        1900,
        "The AAU is founded (28 Feb 1900) by fourteen doctoral-granting "
        "universities to standardise American doctoral programmes. R71 moved "
        "this from 1861: Yale's first PhD marks when the degree BEGAN, not "
        "when it became a reliable supervised credential — before the AAU, "
        "US PhD-granting was unregulated and diploma mills proliferated.",
        "document",
        "https://en.wikipedia.org/wiki/Association_of_American_Universities",
        "strengthen and standardize American doctoral programs",
        "2026-08-23",
    ),
    "GB": Anchor(
        1921,
        "First mathematics DPhil awarded (Oxford, 1921); British universities "
        "resolved to create the PhD in 1917 and Cambridge's first "
        "mathematics PhD followed in 1924. R71 replaced the range "
        "'1917-1920' with the dated first award in this discipline.",
        "document",
        "https://www.economics.soton.ac.uk/staff/aldrich/Doc1.htm",
        "In 1917 British universities resolved to create a PhD degree",
        "2026-08-23",
    ),
    "ES": Anchor(
        1954,
        "Madrid's monopoly on conferring the doctorate ends. From the Ley "
        "Moyano (1857) until 1954 ONLY the Universidad Central de Madrid "
        "could award a doctorate, so a mathematician based anywhere else took "
        "the degree in Madrid and the recorded director may be the Madrid "
        "formality rather than the actual mentor. R71 moved this from 1900.",
        "document",
        "https://www.ucm.es/la-universidad-en-el-franquismo",
        "sólo en Madrid se alcanzaría, hasta 1954, el título de doctor",
        "2026-08-23",
    ),
    "BR": Anchor(
        1965,
        "Parecer CFE 977/1965 (the 'Parecer Sucupira', 3 Dec 1965) structures "
        "master's and doctoral courses; still the basis of CAPES regulation.",
        "document",
        "https://www.gov.br/capes/pt-br/assuntos/noticias/"
        "regulamentacao-da-pos-graduacao-do-pais-completa-60-anos",
        "estruturou os cursos de mestrado e doutorado",
        "2026-08-23",
    ),
    "IN": Anchor(
        1956,
        "UGC Act 1956 puts doctoral standards under a national regulator. "
        "Deliberately later than the first supervised PhDs (Calcutta, 1909/"
        "1921) — the conservative end of the defensible range.",
        "document",
        "https://en.wikipedia.org/wiki/UGC_India",
        "University Grants Commission Act, 1956",
        "2026-08-23",
    ),
    "ZA": Anchor(
        1922,
        "First South African PhD (S. H. Skaife, 1922); doctoral education "
        "surveyed from the 1899 LLD onward by Herman (2017).",
        "document",
        "https://doi.org/10.1080/03075079.2015.1101756",
        "Looking back at doctoral education in South Africa",
        "2026-08-23",
    ),
    # ── document-basis, NOT YET SOURCED — this is the real backlog ───────
    "FR": Anchor(
        1985,
        "The 1984 Savary law replaces doctorat d'Etat / 3e cycle / "
        "d'universite with a single doctorat, and creates the HDR as a "
        "POST-doctoral qualification (see the FR caveat).",
        "document",
    ),
    "IT": Anchor(
        1983,
        "Italy's research doctorate (dottorato di ricerca) is created; before "
        "it an 'advisor' is a laurea relatore.",
        "document",
    ),
    "GR": Anchor(
        1983, "The yfigesia (Greek habilitation) is abolished in 1983.", "document"
    ),
    "BE": Anchor(
        2010,
        "The agregation de l'enseignement superieur (Belgium's habilitation) "
        "runs until 2010.",
        "document",
    ),
    "DD": Anchor(
        1991, "Reunification ends the Promotion A / Promotion B split.", "document"
    ),
    "SE": Anchor(
        1970,
        "The 1969 reform replaces the old doktorsgrad; the licentiate becomes "
        "a separate lesser degree.",
        "document",
    ),
    "FI": Anchor(1970, "The parallel Nordic reform, as SE.", "document"),
    "AU": Anchor(1948, "First Australian PhDs conferred from 1948.", "document"),
    "NZ": Anchor(1948, "First New Zealand PhDs conferred from 1948.", "document"),
    "IL": Anchor(
        1936,
        "Doctoral studies begin at the Hebrew University of Jerusalem.",
        "document",
    ),
    "CN": Anchor(
        1983,
        "China's first PhDs are conferred in 1983 under the Academic Degrees "
        "Regulations (in force 1981). Art. 6 also opens the doctorate to "
        "non-enrolled candidates of 'equivalent academic ability' — recorded "
        "as the CN caveat.",
        "document",
        "https://zh.wikisource.org/wiki/中华人民共和国学位条例",
        "高等学校和科学研究机构的研究生，或具有研究生毕业同等学力的人员，"
        "通过博士学位的课程考试和论文答辩",
        "2026-08-23",
    ),
    "AR": Anchor(
        1995,
        "Ley de Educacion Superior 24.521 (1995), art. 39: postgraduate "
        "education runs exclusively in university institutions, and doctoral "
        "programmes must be accredited by CONEAU.",
        "document",
        "http://servicios.infoleg.gob.ar/infolegInternet/anexos/25000-29999/"
        "25394/texact.htm",
        "La formación de posgrado se desarrollará exclusivamente en "
        "instituciones universitarias",
        "2026-08-23",
    ),
    # ── judgement: NO single documented event exists ─────────────────────
    # These are deliberate conservative choices, not missing homework. Marking
    # them "unsourced" implied a debt that can never be paid; the honest thing
    # is to label the judgement and argue it. Each must still be a SAFE
    # choice — later than the earliest defensible date, never earlier.
    "DE": Anchor(
        1945,
        "No doctorate reform happened in 1945; the German Promotion is "
        "continuous. This is the conservative post-war boundary, chosen "
        "because the Habilitation's much stronger role in the earlier period "
        "makes the recorded advisor less determinate. Earlier would be the "
        "unsafe direction.",
    ),
    "AT": Anchor(1945, "As DE — the same conservative post-war boundary."),
    "CH": Anchor(
        1810,
        "1810 is the Berlin/Humboldt anchor for the modern research "
        "university, not a Swiss event; Switzerland follows the German "
        "Promotion + Habilitation model. Pre-1810 doctorates are caught by "
        "PREMODERN_BEFORE regardless.",
    ),
    "CA": Anchor(1900, "Research doctorate established around 1900; no single reform."),
    "IE": Anchor(
        1920, "PhD adopted alongside the British reform; no separate statute."
    ),
    "NL": Anchor(
        1900,
        "The Dutch promotie is continuous; 1900 is a conservative modern "
        "boundary. The promotor-of-record caveat is the real issue here.",
    ),
    "IR": Anchor(1984, "Post-revolution reorganisation of doctoral education."),
    "KR": Anchor(1980, "Single supervised doctorate from around 1980."),
    "MX": Anchor(1968, "Single doctorado from around 1968."),
    "EE": Anchor(1995, "Post-Soviet reform replaces the kandidat with the PhD."),
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

    # R71 — East German doctorates arrive here labelled DE (Wikidata P69->P17
    # returns modern Germany for Leipzig, Humboldt, Jena...), so the DD row
    # written to handle Promotion A vs Promotion B was covering 13 edges while
    # 202 GDR doctorates were being TRUSTed by the West German rule. Route them
    # back using the era band plus the institution. Both conditions are
    # required: the band must sit ENTIRELY inside the GDR's existence, so a
    # career straddling reunification is never mislabelled.
    if (
        cc == "DE"
        and lo is not None
        and hi is not None
        and lo >= GDR_FROM
        and hi <= GDR_TO
        and GDR_INSTITUTIONS.search(student.get("Institution") or "")
    ):
        cc, cc_basis = "DD", "gdr_institution_in_gdr_era"

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
