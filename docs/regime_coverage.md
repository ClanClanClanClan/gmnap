# What the risk model cannot affirm, and why

**Numbers in this document are illustrative of the shape of the problem. For
current figures run the tool — never quote this file as the count:**

```bash
PYTHONPATH=. python3 tools/regime_coverage.py
```

That split is deliberate. The claim this document replaces — *"~1,500 edges
sit in REVIEW purely because their country regime is unresearched"* — was
written from memory and was wrong twice over: the real figure was **756**, and
**369 of those have no usable era at all**, so no amount of country research
can move them. A number that lives only in prose drifts away from the graph
the moment the graph changes.

**Where R70 left it.** Adding the three researched rows below moved exactly
the 171 edges predicted before the work started (78 India, 57 Brazil, 36 South
Africa), every one of them REVIEW to TRUST and none in the other direction.
Parked fell 756 to **413**, and the reachable ceiling 367 to **173** — so what
remains is now majority *undated*, not *unresearched*. The binding constraint
has shifted, which is the point of measuring rather than asserting.

## The ceiling, and why it is lower than it looks

`_regime_tier` returns `regime_unknown_XX` **before** it ever looks at the
era. So for an edge with no era band, adding a country row does not change the
tier — it just relabels the reason `era_unknown` and leaves it at REVIEW.

That is the trap R66 fell into (it added rows for three countries and moved
zero edges) and that R70 nearly repeated. The honest ceiling is therefore not
the parked count but the **dated, solely-parked, REVIEW** subset — roughly
half of it.

The remainder is not a regime problem at all. `era_unknown` is the single
largest reason across the whole classified graph — larger than every country
rule combined. **Date coverage, not country research, is the binding
constraint on this model.** Chasing more regime rows while that is true is
optimising the wrong term.

## Why only three countries were researched

The parked population is extremely skewed: three countries hold roughly half
the edges and about three quarters of everything that could ever flip, while
the tail is ~45 countries holding 1–30 edges each, most of them undated.

Researching the tail buys almost nothing and risks a great deal, because a
wrong `TRUST` row **removes** a flag. Six countries were TRUSTed wrongly in
earlier rounds — Greece ran the *yfigesia* to 1983, Belgium the *agrégation*
to 2010, Norway's *dr.philos* and Denmark's higher doctorate are unsupervised
by design — and each one was caught only because a human fact-check happened
to be run.

So the rows added in R70 are the three that carry the population, and each
follows a precedent **already in the table** rather than a fresh judgement:

| Country | Window opens | Precedent | Structural caveat |
|---|---|---|---|
| Brazil | 1965 — *Parecer* CFE 977/1965 (the "Parecer Sucupira") | DE post-1945 | `livre_docencia_sibling_exists` |
| India | 1956 — UGC Act | GB post-1920 | D.Sc. on published work |
| South Africa | 1922 — first SA PhD | GB post-1920 | D.Sc. on published work |

India's anchor is deliberately **conservative**. The supervised PhD dates to
the 1910s–20s, which would justify a much earlier window; using the UGC Act
leaves the 1920s–50s edges at REVIEW. Erring late costs coverage, erring early
removes flags that should be there.

The distinction that keeps Norway and Denmark at REVIEW is different in kind
and must not be blurred: there the unsupervised doctorate is a **primary
route**, taken *instead of* a supervised one, so an advisor edge is fabricated
by construction. A *post-doctoral* higher degree is not that.

## Turkey, Algeria, Lithuania and the rest stay parked

`TR` was re-checked in R70 and deliberately left parked. Law 2547 (6 Nov 1981)
established YÖK and the modern rank structure, and *doçentlik* turns out to be
a **professorship qualification awarded by national jury — not a doctorate and
not supervised**, so it is closer to Germany's habilitation than to a rival
doctoral tier. That is suggestive but it is not the claim a TRUST row needs
("after date D a single supervised research doctorate is the only doctoral
credential"), and no source consulted established it. It would move **8
edges**. Turkey adopted the German model in 1933, and Germany itself is REVIEW
until 1945; TRUSTing Turkey open-ended on weaker evidence than we hold for
Germany would repeat the Greece error exactly.

`DZ` shares France's structure, and France is REVIEW to 1985. `LT` was
searched and no reliable date for the retirement of the *habilituotas
daktaras* was found — it would move 3 edges. **"I could not find the date" is
a reason to leave the flag on, not to guess**, and a small prize is a reason
not to spend the risk.

Countries still running a two-tier system (`MD`, `GE`, `AZ`, `UZ`, `AM`, `TJ`,
…) have no TRUST window to add at all.

## The guard

Evidence is mandatory exactly where a flag is **removed**:

* every country with a `TRUST` window must appear in `TRUST_ANCHOR`,
* its anchor year must **equal** the year the window opens — this is the
  enforced part, and it catches a date edited without its reason, which is
  close to how the six wrong rows got in,
* `REVIEW` needs no anchor: "we cannot affirm this" asserts nothing and is the
  safe default,
* the number of anchors with no external source is **pinned**, so a new
  sourceless TRUST row cannot be added without deliberately editing that
  number, and the backlog can only shrink.

Pinned by `tests/unit/test_vetting_risk.py`.

---

# R71 — verifying the anchors themselves

R70 left 26 anchors carried from earlier rounds with no external source. That
looked like bookkeeping. It was not: **those 26 anchors were unflagging 15,419
edges — 98.9% of the entire TRUST tier.** The three sourced in R70 covered 171.
Essentially the whole trusted graph rested on claims nobody had checked.

A 25-agent verification pass ran each country twice and independently — one
agent re-deriving the anchor year **blind to the current value**, another told
the current value and tasked only with breaking it — then adjudicated the pair
and fetched the citations. 877 tool calls, ~2.7M tokens.

## The backlog was never one thing

R70's "26 unsourced" conflated two situations needing opposite responses:

* **document basis** — the anchor names a real datable event that simply had
  not been checked. That is genuine backlog.
* **judgement basis** — no such event exists. Nothing happened to the German
  *Promotion* in 1945; that year is a conservative post-war boundary. Chasing
  a citation for it is chasing something that does not exist, and calling it
  "unsourced" implies a debt that can never be paid.

`TRUST_ANCHOR` now records which kind each is. A `source` is only accepted
together with **the quote actually read on the page and the retrieval date** —
a URL nobody opened is the same defect class as a sidecar nothing reads, and
worse than an honest blank, because it looks like evidence.

## What was actually wrong

| | was | now | why |
|---|---|---|---|
| **DE→DD routing** | 202 GDR doctorates TRUSTed as West German | routed to the DD regime | Wikidata P69→P17 returns *modern Germany* for Leipzig, Humboldt, Jena, so the DD row written for Promotion A vs B covered **13 edges** while the real GDR population sat inside DE |
| **PT** | TRUST from 1930 | **no TRUST window** | art. 33 lets a thesis be defended *"sem inscrição no ciclo de estudos… e sem a orientação"* — a statutory **unsupervised** route to the first doctorate |
| **US** | 1861 (first-ever PhD) | **1900** | 1861 marks when the degree *began*; the AAU formed in 1900 because PhD-granting was unregulated and diploma mills proliferated |
| **ES** | ~1900 | **1954** | until then only Madrid could confer a doctorate, so the recorded director may be a formality |
| **GB** | "1917-1920" (a range) | **1921** | first mathematics DPhil, Oxford |
| **FR, GB, IE, AU, NZ, US, CA, CN, EE, IT** | no caveat | caveat recorded | siblings that existed all along, several described in this module's own prose |

315 edges left TRUST. **Every single movement was toward more flagging** —
nothing was unflagged on the strength of an agent's say-so.

## The real defect was a missing rule

The adversarial pass produced 13 year-moves, and most of them were wrong in the
same way: `GB`, `IE`, `AU` and `NZ` were all moved to 1970 because a higher
doctorate on published work exists — while the *identical* credential is a mere
caveat for India and South Africa. A reviewer put it exactly right: **a
taxonomy that can be bent either way to reach an answer already chosen has
stopped doing work.**

So the sibling-credential test is now written down. A second doctoral
credential disqualifies a country only if it is **ungated** (obtainable without
already holding the supervised doctorate) **and a material route**. Gated
credentials — German *Habilitation*, French HDR, Polish *dr hab.*, the British
higher doctorate — are post-doctoral by construction and only annotate.

That test is what makes Portugal a real find rather than an arbitrary one, and
it is why the four 1970 moves were rejected.

## Recorded, not quietly settled

* **Poland may be too harsh.** By this test the *dr hab.* is gated
  (*"posiadała stopień doktora"*) and should be a caveat, yet PL is REVIEW
  open-ended — 1,330 edges possibly over-flagged. **Not changed.** Unflagging
  is the dangerous direction and needs far stronger evidence than flagging;
  the asymmetry is deliberate.
* **Norway / Denmark / Japan cannot be rescued.** A late supervised-PhD window
  with a name-scoped credential exclusion was proposed, and **refuted by
  measurement**: credential names do survive in the corpus (73 distinct
  `DegreeType` values) but on only **5.3%** of records, so for 94.7% a
  *dr.philos.* is indistinguishable from a *ph.d.*
* **The US anchor is a judgement between two defensible years.** The
  verification pass argued 1920 (the Doctorate Records File is complete from
  then); 1900 was chosen because 1920 would flag the founding era of American
  mathematics — E. H. Moore's Chicago school, Bôcher and Osgood's Harvard
  students — which is among the best-documented material in the corpus. A flag
  that fires on the highest-quality data teaches users to ignore flags. The
  residual honorary-PhD hazard is recorded as a caveat instead.
* **Citations were spot-checked, not fully re-verified.** 3 of the 15 adopted
  (Portugal's statute via local `pdftotext`, Argentina's InfoLeg, China's
  Wikisource) were re-read by hand; all three matched exactly, including two
  non-English primary sources. The other 12 rest on the agents' fetches.
