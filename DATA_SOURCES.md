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
| Adjudicated benchmark | `data/benchmarks/adjudicated_843.json` | composite | mixed | yes |
| Region YAML overlays | `config/regions/*.yaml` (none yet) | hand-curated | MIT (this repo) | no |
| Script-switch table | `config/script_switch.yaml` | hand-curated | MIT | no |
| Surname fastText model | `data/ml_training/regional_classifier.bin` | trained on aligned MGP + Wikidata + OpenAlex | CC0 derivative | no |
| Country-code → region map | `data/cc_to_region.json` | composite | MIT | no |

## `data/genealogy_enrichment.json`

The largest bundled artefact (~39,500 entries). Composite:

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
- **Scope**: ~4,362 advisor edges + ~30 P569 (date of birth)
  fields. Harvested by
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

`data/benchmarks/adjudicated_843.json` — 843 mathematician name
entries with hand-checked ground-truth `name_region` labels, used
by `tests/unit/test_region_detection_accuracy.py`. Source mix:

- 500 entries from the original Wikidata SPARQL pull (CC0).
- 343 entries hand-added during round 5-12 calibration (MIT).

The `region_code` labels themselves are this project's
classification, MIT-licensed.

## Models

`data/ml_training/regional_classifier.bin` (50 MB quantised
fastText model). Trained on:

- ~23 000 aligned (name, region) pairs derived from the genealogy
  enrichment file above.
- Training script: `scripts/ml/train_regional_classifier.py`.

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
