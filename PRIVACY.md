# Privacy notice — GMNAP bundled data & pipeline

*Last updated: 2026-07-07 (R55). This notice exists because the repository
redistributes structured records about real, identifiable people — many of
them living — and anyone doing that owes those people a plain statement of
what is held, why, and how to object.*

## What personal data this repository contains

| Artefact | People | Fields |
|---|---|---|
| `data/genealogy_enrichment.json` | ~39,900 mathematicians (living and deceased) | canonical name, country, institution, birth year / death year (where public), doctoral-advisor names, source tag |
| `data/mgp_full.jsonl` | 475 mathematicians | name, degree, institution, year, dissertation title, advisor/student names |
| `data/benchmarks/adjudicated_843.json` | 843 mathematicians | name, region-of-name-origin label (this project's classification) |
| `data/ml_training/*` corpora | subsets of the above | (surname, region-label) pairs |
| Pipeline outputs (`out/`, `output/`, API responses) | whatever you process | the above plus derived fields (region axes, short forms, confidence) |

**What it deliberately does NOT contain:** contact details, addresses,
emails, photographs, financial data, health data, or any GDPR Art. 9
special-category data. Every field is professional/bibliographic and was
already published by the sources below.

**One derived field deserves honesty:** the pipeline *infers a region of
name origin* (linguistic classification of a surname). That is an
inference about a person, not a fact about them; it is emitted with a
confidence score and an abstention path (`R0`), and it deliberately says
nothing about citizenship, ethnicity, or residence (`GeoRegion` vs
`NameRegion` are split axes precisely so the two are never conflated).

### Correction (R57, 2026-07-23): the Art. 9 claim above was too strong

The sentence "does NOT contain … any GDPR Art. 9 special-category data"
was written about the *fields we collect*, and it is accurate about
those. It was **wrong about the field we derive**. A name-origin label
attached to an identifiable person is capable of *revealing* ethnic or
religious origin, and Art. 9 covers data "revealing" such origin — under
CJEU C-184/20 that includes data from which it can be **inferred**. So
"we only computed it from a public name" is not an exemption, and our
internal framing (we classify the *name form*, not the bearer) is a real
distinction that nonetheless does not survive publication of a
per-person label. The `C6` category, whose label is "Hebrew &
Diaspora", is the clearest case.

Three things follow, and all are implemented:

1. **The adjudicated corpora are not published.** ~3 000 arXiv/OpenAlex
   authors with origin labels (`data/eval/`) are gitignored and absent
   from git history. The *build method*
   (`tools/build_heldout2_corpus.py`) is public, so the corpus stays
   reproducible without publishing labelled individuals. Aggregate
   accuracy figures are in `docs/calibration.md`.
2. **The API does not hand out labels anonymously.** `/api/v1/query`
   returns the genealogy surface (name, advisors, institution, birth
   year — the same class of data MGP and OpenAlex publish) to everyone,
   and the name-origin classification only to authenticated research
   callers. Without that gate the free tier could be walked over the
   ~39.9 k enrichment names to rebuild exactly the corpus we decline to
   publish.
3. **A CI gate enforces it.** `tools/privacy_audit.py` fails the build
   if any tracked file pairs a presumed-living person with a leaf code.
   Two Wikidata-derived fixtures are allowlisted with their rationale
   recorded in `tests/fixtures/PROVENANCE.md`; the test is *marginal
   disclosure* — Wikidata already publishes those subjects'
   nationality, whereas for ordinary working academics our label is
   novel inference published nowhere else.

**If you are in this data and want out**, see "How to object" below.
Removal requests are honoured for the bundled data and the fixtures.

## Where the data comes from

- **Wikidata** (CC0) — names, P184 doctoral-advisor edges, P569 birth
  dates, P69 institutions.
- **OpenAlex** (CC0) — author affiliations and countries for working
  mathematicians.
- **Mathematics Genealogy Project** (non-commercial terms; see
  [DATA_SOURCES.md](DATA_SOURCES.md)) — a small harvested subset
  (advisor chains, dissertation titles), collected respecting the
  site's robots.txt crawl delay.

All three publish this information openly; this project aggregates and
cross-links it. Data subjects were not contacted individually: for a
~40k-person bibliographic aggregation that would be disproportionate
(GDPR Art. 14(5)(b)) — this public notice is the mitigation.

## Why (lawful basis)

Processing rests on **legitimate interest (GDPR Art. 6(1)(f))**: building
open research infrastructure for name disambiguation and academic-
genealogy research, over data the subjects themselves published in a
professional context, with **Art. 89-style safeguards** (data
minimisation to professional fields; the masking machinery below). The
balancing consideration: the records are already public in at least two
open databases; aggregation here adds linkage, not new disclosure.

## Protections built into the pipeline

These run on every batch (`src/core/gdpr.py`, kill-switch documented in
the README):

- **`GDPR_DATA` marking** — records carrying person-level fields are
  flagged so downstream consumers can apply their own policy.
- **Birth-year decade masking** — when fewer than 5 people share a
  (region, birth-decade) cohort in an output batch, the exact year is
  replaced by a decade label and **the exact value is dropped, not
  stashed** (R54 closed a leak where the original year travelled beside
  its mask).
- **ShadowNode conversion** (`--drop-personal` /
  `GMNAP_DROP_PERSONAL=1`) — collapses person records to bracketed
  initials for right-to-be-forgotten serving.
- **ToS-source scrubbing** — fields sourced from services whose terms
  forbid redistribution (Google Scholar, ProQuest, CNKI) are stripped
  before anything is written. (Google Scholar scraping is permanently
  declined in this project.)

## Your rights (erasure, rectification, objection)

If you are in this dataset and want your record corrected or removed:

1. **Open an issue** on this repository titled `data-subject request`
   (or email the maintainer if an address is published on the repo
   profile). State the name as it appears and what you want changed.
   You do not need to justify an objection.
2. Your record will be removed from / corrected in the bundled
   artefacts in the next data refresh and release.

**Honest caveats, so the promise is real:**

- **Git history**: released artefacts are versioned; a removed record
  remains in older commits/releases unless history is rewritten. On
  request we will exclude the record from all future releases; full
  history purging is possible but disruptive and handled case-by-case.
- **Upstream sources**: this project re-harvests from Wikidata, OpenAlex
  and MGP. If your record remains upstream it would reappear on
  re-harvest — the refresh tooling keeps a suppression list
  (`data/removal_requests.txt`, created on first request) so honoured
  requests survive refreshes. For removal at the source you must also
  contact the upstream database.
- **Third-party clones**: we cannot retract copies others have cloned.

## Operational data (API server)

The bundled API server (`gmnap serve`) keeps **in-memory** rate-limit
counters keyed by client IP and (for the paid tier) bearer-token usage
counts. Nothing is written to disk, there are no analytics, no cookies,
and logs default to request lines only. Deployers who put this behind
their own infrastructure are responsible for their own logging policy.

## Contact & accountability

Single-maintainer project; the maintainer is the data controller in
GDPR terms for the bundled artefacts. Requests come in through GitHub
issues (see above). This notice changes only via pull request, so its
history is itself auditable.
