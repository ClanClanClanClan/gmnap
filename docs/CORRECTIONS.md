# Corrections — how a fix actually reaches the graph

The Mathematics Genealogy Project's core weakness is not that it has errors;
every large dataset does. It is that a correction takes **months and dozens of
emails**, because there is no visible path from "this is wrong" to "the graph
changed". This document is that path.

## Why a ledger, and not just an edit

`data/genealogy_enrichment.json` is **rebuilt** from upstream harvests
(Wikidata, theses.fr, MGP, OpenAlex). Editing it directly is useless: the next
build overwrites the edit. Worse, `merge_advisor_edges()` is **monotone** — it
fills, corroborates, or overrides upward, but never removes — so there is no
in-band way to express *"this edge is wrong"*. And since **~99% of our Wikidata
advisor statements cite MGP**, the next harvest re-asserts the very error you
just removed.

So corrections live in an append-only ledger, `data/adjudicated_corrections.json`,
which the build consults **on every run**. That is the same durability trick
`apply_suppression_list()` already uses to keep GDPR erasure requests honoured
across rebuilds.

## The ledger format

A JSON array. Each entry:

```json
{
  "ticket": "GMNAP-C-0001",
  "action": "retract",
  "student": { "name": "Aardal, Karen" },
  "advisor": { "name": "Wolsey, Laurence", "qid": "Q15825378" },
  "evidence": "https://…  (what convinced the adjudicator)",
  "adjudicated_on": "2026-08-22",
  "note": "Belgian agrégation, not a doctoral supervision"
}
```

### `retract` — remove an edge
Matching follows the same identity precedence as `_same_advisor`: **QID, then
IdRef, then normalized name**. Name matching is permitted here because
retraction *removes*: the failure mode is a missing edge, which is visible and
reversible.

### `assert` — add or affirm an edge
Enters at the `curated` tier, which is the only `FLOOR_LOCKED` source — no
automated harvest can dislodge it. Because of that, an `assert` **requires a
`qid` or `idref` on the advisor**. Entries with only a name are **refused and
reported**, never silently downgraded.

The reason is measured, not theoretical: **9.9% of French advisor surnames map
to more than one real person**, covering 23.4% of the edges we care about.
`lions` is Jacques-Louis *and* Pierre-Louis — father and son, same field,
overlapping years. A floor-locked edge minted on a bare name would be a
permanently unremovable error.

## Where it runs, and why there

`apply_corrections()` runs in `tools/build_genealogy_enrichment.py`:

- **after** every harvest merge — otherwise the next merge re-adds what you retracted;
- **before** `apply_edge_integrity()` — so the corrected graph is the one checked for cycles and self-loops;
- **before** `mark_vetting_status()` — so vetting sees corrected edges;
- **before** `apply_suppression_list()`, which stays last — **erasure beats correction**. If someone has exercised their right to be forgotten, no correction can reinstate them.

## Operating it (single maintainer)

1. A suggestion arrives at `POST /api/v1/suggest` and lands in `data/corrections/`.
2. Adjudicate it: is there evidence? Does the advisor have a persistent identifier?
3. Append an entry to `data/adjudicated_corrections.json` with a ticket id and the evidence.
4. Rebuild: `PYTHONPATH=. python3 tools/build_genealogy_enrichment.py`
5. The build prints what it did (`Corrections: N retracted, N asserted, N refused, N unmatched`).

The correction is now durable: it is re-applied on every future build, including
builds where the upstream still carries the original error.

## Privacy

The ledger is a tracked `.json` file, so `tools/privacy_audit.py` scans it like
any other. Do not put a name-origin/region claim about a living person in a
`note`. Erasure requests belong in `data/removal_requests.txt`, not here — they
are a different mechanism with stronger precedence.
