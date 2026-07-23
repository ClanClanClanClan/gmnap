# Data sources & licensing

The code in this repository is MIT-licensed (see [LICENSE](LICENSE)).
The **bundled data artifacts** are derivative works of upstream
academic / open-data sources, each with its own licence and
attribution requirement. This document is the authoritative
breakdown.

## Why this matters

Anyone using `data/genealogy_enrichment.json`, the bundled benchmarks,
or the trained models must respect the upstream licences. The MIT
licence on the code does **not** cascade to the data — a derivative
work's terms inherit the most-restrictive parent licence (in
practice that's CC-BY for some of our sources).

## TL;DR

| Artefact | Path | Source | Licence | Attribution required? |
|---|---|---|---|---|
| Genealogy enrichment | `data/genealogy_enrichment.json` | composite, see below | mixed | yes |
| Adjudicated benchmark | `tests/fixtures/name_origin_benchmark.json` | composite | mixed | yes |
| Region YAML overlays | `config/regions/*.yaml` (none yet) | hand-curated | MIT (this repo) | no |
| Script-switch table | `config/script_switch.yaml` | hand-curated | MIT | no |
| Surname fastText model | `data/ml_training/ft_name_classifier.ftz` | trained on aligned MGP + Wikidata + OpenAlex | CC0 derivative | no |
| Country-code → region map | `data/cc_to_region.json` | composite | MIT | no |

## `data/genealogy_enrichment.json`

The largest bundled artefact (~48,500 entries). Composite:

### Mathematics Genealogy Project (MGP)

- **Source**: [genealogy.math.ndsu.nodak.edu](https://www.genealogy.math.ndsu.nodak.edu/)
- **Scope**: ~15 seed mathematicians + 25 curated stubs + transitive
  advisors fetched via `tools/harvest_mgp.py` (which honours the
  site's `Crawl-delay: 10` in robots.txt).
- **Licence**: The MGP terms are **non-commercial use** with
  attribution. Their data export ("API") is not formally licensed
  CC0; we treat the harvested subset as fair use for research-tool
  development, with attribution in every API response that surfaces
  an MGP-derived `mgp_id`.
- **Attribution**: any downstream user that surfaces advisor chains
  drawn from MGP must credit "Mathematics Genealogy Project,
  © North Dakota State University" — the API response carries the
  `mgp_id` so downstream consumers can construct backlinks.

### Wikidata SPARQL (P184 = doctoral advisor)

- **Source**: [Wikidata Query Service](https://query.wikidata.org/)
- **Scope**: 28,179 mathematicians carrying ~33,773 P184 advisor
  edges, with 17,357 P569 (date of birth) and 20,224 P69
  (institution) fields. Harvested by
  `scripts/data/fetch_wikidata_genealogy.py` using decade-
  partitioned queries (52 buckets 1500–2020).
- **Licence**: **CC0** (Creative Commons Public Domain Dedication).
- **Attribution**: not legally required but politely included
  ("data from Wikidata, CC0").

### OpenAlex (affiliations + concepts)

- **Source**: [openalex.org](https://openalex.org/)
- **Scope**: ~14,432 author records — mostly Country + Institution
  for living mathematicians the MGP doesn't cover. Harvested via
  the polite-pool endpoint.
- **Licence**: **CC0**.
- **Attribution**: not required.

## Adjudicated benchmark

`tests/fixtures/name_origin_benchmark.json` — 843 mathematician name
entries with hand-checked ground-truth `name_region` labels, used
by `tests/unit/test_region_detection_accuracy.py`. Source mix:

- 500 entries from the original Wikidata SPARQL pull (CC0).
- 343 entries hand-added during round 5-12 calibration (MIT).

The `region_code` labels themselves are this project's
classification, MIT-licensed.

## Models

`data/ml_training/ft_name_classifier.ftz` (50 MB quantised
fastText model). Trained on:

- ~23 000 aligned (name, region) pairs derived from the genealogy
  enrichment file above.
- Training script: `scripts/ml/build_name_classifier.py`.

Since the training corpus is itself derivative of CC0 Wikidata +
OpenAlex + the non-commercial MGP subset, the model inherits the
union: **non-commercial use, with attribution**, until the MGP-
sourced rows are isolated and replaced.

## Authority-source API responses

When `OFFLINE=0`, the pipeline hits live APIs (OpenAlex, Crossref,
ORCID, GND, HAL, OAI, zbMATH Open, Wikidata). Cached responses
land in `./cache/authority/` (zlib-compressed JSON, keyed by SHA-
256 of the canonical query payload).

| Source | Licence | Attribution |
|---|---|---|
| OpenAlex | CC0 | not required |
| Crossref | CC0 (metadata) | not required |
| ORCID public API | [ORCID Public Data File terms](https://info.orcid.org/orcid-public-data-file/) (free for research) | yes — ORCID iDs are personal identifiers |
| GND (DNB) | CC0 | not required |
| HAL | CC-BY | yes |
| OAI-PMH (universities) | varies per institution | check per-source |
| zbMATH Open | CC-BY-SA | yes |
| Wikidata SPARQL | CC0 | polite-required |
| Crossref Thesis | CC0 metadata | not required |

## What about the screenshots in `docs/screenshots/`?

Self-captured renderings of this project's own web UI; MIT.

## GDPR

The bundled data contains only **publicly-published academic
records**: names, institutions, advisor relationships, birth/death
years (where Wikidata has them), thesis titles. No private contact
data, no addresses. The `--drop-personal` CLI flag and
`GMNAP_DROP_PERSONAL=1` env var convert personal nodes to
`ShadowNode`s (round-bracketed initials only) per
`src/core/gdpr.py`; use that mode when serving EU users who exercise
the right-to-be-forgotten and the underlying upstream source has
also removed the record.

The full data-protection notice — data categories, lawful basis,
pipeline protections, and the erasure-request process (including the
`data/removal_requests.txt` suppression list that
`tools/build_genealogy_enrichment.py` honours on every rebuild, so a
granted request survives future re-harvests) — is
**[PRIVACY.md](PRIVACY.md)**.

## Commercial use

The code is MIT — commercially usable. The **default bundled dataset is
not**: ~490 of its ~48,500 records (and the advisor chains they carry,
plus `data/mgp_full.jsonl` in its entirety) derive from the Mathematics
Genealogy Project, whose terms are **non-commercial with attribution**.
The API's paid tier (`GMNAP_API_TOKENS`) gates *rate limits*; it does
not — and cannot — grant data rights the upstream licence withholds.

A commercial deployment therefore has exactly two clean options:

1. **Serve the CC0-clean dataset** — rebuild without any MGP input:

   ```bash
   PYTHONPATH=. python3 tools/build_genealogy_enrichment.py --no-mgp
   ```

   This skips the MGP seeds and the bulk-harvest merge, yielding a
   Wikidata (CC0) + OpenAlex (CC0) + MIT-curated-stub artefact —
   ~48,100 entries, zero MGP-tagged records (the build prints the
   MGP-derived count so you can verify it is 0). Do not ship
   `data/mgp_full.jsonl` with a commercial deployment either.

2. **Obtain permission from MGP / NDSU** to serve their data
   commercially, and keep the attribution their terms require.

Runtime records whose provenance actually includes an MGP-class source
are conservatively tagged `LicenceTier: non-redistributable` by the
spec-§10 tier machinery (`src/ops/licence_tiers.py`) — unknown sources
deliberately fall to the most restrictive tier.

## Updating these sources

To re-harvest from upstream:

```bash
# Wikidata (decade-partitioned, 52 buckets, ~30 min)
python3 scripts/data/fetch_wikidata_genealogy.py

# MGP (10 s crawl-delay → slow; respect robots.txt)
python3 tools/harvest_mgp.py

# Re-merge into the single enrichment file
PYTHONPATH=. python3 tools/build_genealogy_enrichment.py
```

The D4 audit check (`tools/audit_repo.py`) gates the file size at
36k–43k entries to catch accidental truncation or stale stubs.

## Reporting incorrect data

If you find an inaccurate advisor edge, wrong birth year, or
mis-classified region in the bundled data:

- For Wikidata-sourced data: fix it on Wikidata
  (the pipeline picks up the change next harvest).
- For MGP-sourced data: report to the MGP via their submission form.
- For this project's adjudication (i.e. wrong `region_code`): open
  an issue or PR; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Authority fetcher roster (spec §9: 14 sources — the repo ships more)

Beyond-spec working code is a feature (see `docs/MASTERPLAN.md` §0). The
spec's 14 sources are wired through `src/authorities/manager_tier01.py`
(9 live HTTP, 2 API-key-gated, 3 deferred — see CLAUDE.md's authority
table). On top of those, `src/authorities/tier0..2/` carries bonus
fetchers, all construction-guarded by
`tests/unit/test_authority_fetchstatus.py` (AST kwarg validity,
FetchStatus members, ABC concreteness):

| Fetcher | Status |
|---|---|
| ACM, IEEE, PubMed, Springer, VIAF, Wiley (tier1) | fixed + tested in R40.1 (were TypeError-on-call); available, not wired into the tier orchestrator |
| DBLP, arXiv (tier1) | statically valid; construction-guarded; behavioral tests pending |
| ResearchGate (tier1) | mock-mode by design — not a live source |
| CNKI, JSTOR, EThOS, J-Stage, NARCIS, SciELO, TEL, CERN-CDS, Dimensions, MathSciNet-HTML, ProQuest (tier2) | template-engine stubs; package importable since R49 (`__init__` used to import 3 never-existing modules) |

The live enrichment path only calls the spec'd 14; the bonus roster is
kept + documented per the maintainer's beyond-spec rule.
