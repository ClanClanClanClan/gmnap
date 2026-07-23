# Fixture provenance and lawful basis (R57)

Two fixtures pair named mathematicians with a name-origin label and are
deliberately kept in the public repository. This file records why, so the
decision is auditable rather than implicit.

| fixture | records | source |
|---|---|---|
| `name_origin_benchmark.json` | 843 | Wikidata mathematicians (adjudicated) |
| `golden_mathematicians.json` | 500 | Wikidata / MGP notable mathematicians |

**Why these are retained while the adjudicated corpora are not.** The
test is *marginal disclosure*:

- These are **encyclopedia subjects**. Wikidata already publishes their
  nationality and country of citizenship, so our regional label adds
  essentially nothing that is not already public about them, and a large
  share are historical figures — GDPR does not apply to deceased persons
  (Recital 27).
- The adjudicated corpora (`data/eval/`, ~3 000 records) are the
  opposite case: **ordinary working academics** harvested from arXiv and
  OpenAlex author lists, where the origin label is **novel inference**
  published nowhere else. Those are not in this repository, and
  `.gitignore` keeps them out. The build method
  (`tools/build_heldout2_corpus.py`) is public, so the corpus remains
  reproducible without publishing labelled individuals.

**Minimisation applied.** `geo_country` (free-text nationality) was
removed from `name_origin_benchmark.json`: no code reads it, so it was
personal data retained for no purpose. `geo_label` stays because the
accuracy gates score against it.

**If you are in these fixtures and object**, open an issue or contact the
maintainer; entries will be removed on request. See `docs/PRIVACY.md`.

**Enforcement.** `tools/privacy_audit.py` allowlists exactly these two
paths; every other tracked file is checked for living-person/origin-label
pairings, and CI fails on a violation.
