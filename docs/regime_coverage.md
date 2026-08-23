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
