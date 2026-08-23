#!/usr/bin/env python3
"""Decide PRE-1985 French doctorate types from Sudoc (ABES), by exact IdRef.

THE PROBLEM. Before the 1984 reform France ran several parallel doctorates —
*doctorat d'État*, *doctorat de 3e cycle*, *doctorat d'université*, *doctorat
d'ingénieur* — and a mathematician routinely held TWO of them, years apart,
under DIFFERENT advisors (Brézis: 3e cycle 1966 under Choquet, doctorat d'État
1971/72 under Lions). theses.fr starts at 1985, so nothing we already hold can
tell them apart. That is exactly why 618 French advisor edges sit in REVIEW:
`tools/vetting_risk.py` cannot AFFIRM which doctorate an edge belongs to.

THE JOIN — exact, never by name. Wikidata **P269** is the IdRef/SUDOC
authority PPN, and UNIMARC ``$3`` on 700/701/702 is the same identifier. So a
person we hold a QID for resolves into Sudoc with zero name matching.

WHY NO NAME MATCHING, EVER. On the real French advisor population 9.9% of
surnames map to more than one actual person, covering 23.4% of the target
edges — `lions` is Jacques-Louis AND Pierre-Louis (father and son, same field,
overlapping years); `meyer` and `berger` are eight people each; even
"Surname, Given" is not a function (69 keys map to >1 PPN). A name match here
would mint FALSE independent corroboration, which is the one thing this graph
must never do.

WHAT WE EMIT. Per person PPN: the list of their pre-1985 thesis records, each
with degree type / year / institution / title. The decisive signal for the
risk model is the COUNT:
  * exactly one pre-1985 doctorate -> unambiguous; the advisor edge can only
    refer to that one, so the France multi-degree doubt is RESOLVED for this
    person and `vetting_risk` lifts the edge to TRUST.
  * two or more -> the Brézis pattern. Still not TRUST, but now it is a KNOWN
    multi-degree case rather than an unexplained REVIEW, and it is precisely
    where MGP tends to flatten two sequential advisors into "co-advisors".

R69 — THREE DEFECTS THAT MADE THE EARLIER VERSION UNUSABLE. Each was found by
running the thing against live data, not by reading it.

  1. THE ROLE FILTER NEVER RAN. The old loop claimed to keep only records
     where the person is the AUTHOR ($4 070), but its `if "070" not in text:
     continue` tested elements that are not the role container, so every
     `<ppn>` in the document was collected — including the person's OWN
     authority PPN and every role. Measured: Brézis 39 authored records,
     129 collected; Choquet 97 authored, 182 collected. The junk is not
     random — role **727 is "Directeur de thèse"** (Brézis: 46), so a
     supervisor's SUPERVISED theses were counted as degrees HE held. That
     inverts the decisive signal exactly on the advisors we care most about.
     Now the roles are parsed structurally and only 070 is kept.

  2. A SILENT 40-RECORD CAP. `[:40]` truncated the (already wrong) list with
     no report. J.-L. Lions has 196 authored records; his 1954 thesis is not
     in the first 40 of the mixed list, so he would have been recorded as
     having NO doctorate. Sudoc's SRU accepts batched `ppn=A or ppn=B` CQL —
     measured 90 records in one 4.0 s call — so there is no reason to cap at
     all. Every authored record is now fetched, in batches of 40.

  3. NOTHING CONSUMED THE OUTPUT. The old docstring said "sidecar; the build
     merges it". No code anywhere read `data/sudoc_thesis_types.json`, so
     running the harvest could not have changed a single tier. The build now
     merges it (`apply_sudoc_evidence` in tools/build_genealogy_enrichment.py)
     and `tests/unit/test_sudoc_evidence.py` pins that it stays wired.

  Plus a dedup defect: Choquet's single 1946 thesis has two Sudoc records
  whose titles differ by one character ("Application" / "Applications"), so
  keying on (year, exact title) counted two degrees and destroyed his
  decidability. Records are now clustered on year-proximity + title
  containment, and the merge rule is deliberately CONSERVATIVE: splitting
  leaves an edge at REVIEW (harmless), merging can promote it to TRUST.

TARGETING. The old run probed every French person with a P269 — 1,828 people,
of whom 1,020 (55.8%) were provably useless (873 whose whole era band is
post-1985, already covered by theses.fr, plus 147 not in our graph at all).
The default target set is now the 470 people who can actually change an
outcome: they carry an FR edge at REVIEW, they have a P269, and their era band
can reach pre-1985. `--targets all` restores the old behaviour.

Licence: ABES data under the Etalab Licence Ouverte — cite source + retrieval
date. Be polite: 0.6 s between calls, descriptive User-Agent.

Usage:
    python3 scripts/data/fetch_sudoc_thesis_types.py [--limit N]
    python3 scripts/data/fetch_sudoc_thesis_types.py --targets all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

SRU = "https://www.sudoc.abes.fr/cbs/sru/"
IDREF_BIBLIO = "https://www.idref.fr/services/biblio/{ppn}.xml"
USER_AGENT = "GMNAP/1.0 (mathematician-genealogy research; dylan.possamai@math.ethz.ch)"
OUTPUT = Path("data/sudoc_thesis_types.json")
PROVENANCE = Path("data/wikidata_provenance.json")
ENRICHMENT = Path("data/genealogy_enrichment.json")

# UNIMARC role codes on the IdRef `biblio` service. ONLY 070 means "this
# person wrote it". The others are why the unfiltered list was junk:
#   727 Directeur de thèse      -> theses they SUPERVISED (Brézis: 46)
#   651 Directeur de publication-> volumes they EDITED   (Choquet: 70)
#   555 Membre du jury / 956 Président du jury / 958 Rapporteur -> examined
#   340 Editeur scientifique, 080 Préfacier, 990 Sujet, ...
AUTHOR_ROLE = "070"

# Roles that carry an advisor relation we do NOT yet harvest. Counted and
# reported so the opportunity stays visible instead of being silently dropped.
SUPERVISOR_ROLE = "727"

# UNIMARC non-sorting control characters bracket the sort-ignored article in
# titles ("\x98Les \x9copérateurs monotones"). They must be stripped.
_CTRL = re.compile(r"[\x00-\x1f\x80-\x9f]")

# Degree-type normalisation. Sudoc 328$b is free text with real orthographic
# drift ("Thèse d'Etat" / "Thèse d'état" / "Thèse Etat"), so match on a folded
# form. Order matters: 3e cycle must be tested before the bare "thèse".
DEGREE_PATTERNS: list[tuple[str, str]] = [
    (r"3\s*e?\s*cycle|troisieme cycle", "doctorat_3e_cycle"),
    (r"docteur[- ]ingenieur|doctorat d ingenieur", "doctorat_ingenieur"),
    (r"d\s*etat|d etat", "doctorat_etat"),
    (r"d\s*universite|d universite", "doctorat_universite"),
    (r"habilitation", "habilitation"),
    (r"nouveau regime|doctorat unique", "doctorat_unifie"),
]

# Cataloguing artefacts, not title content. Dropped before the near-duplicate
# comparison so "Problèmes unilatéraux" and "Problèmes unilatéraux : thèse"
# compare as the same work.
_TITLE_STOPWORDS = frozenset(
    """these thesis doctorat tome volume vol partie part fasc fascicule
    et de des du la le les l d a au aux sur en dans pour par avec""".split()
)


def _fold(text: str) -> str:
    """Lowercase, strip accents and punctuation — for pattern matching only."""
    t = unicodedata.normalize("NFD", text or "").lower()
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _title_tokens(title: str) -> frozenset[str]:
    """Content tokens for the near-duplicate test, singular/plural folded.

    The trailing -s matters more than it looks. Choquet's single 1946 thesis
    is catalogued twice as "Application ..." and "Applications ...", and
    treating those as two unrelated tokens put the pair at 0.80 containment —
    just under the 0.85 threshold — so his one degree counted as two and he
    became undecidable. Folding the French plural puts it at 1.00 and takes
    the whole decision off a knife edge, which is the point: a rule that only
    just works is a rule that will stop working on the next name.
    """
    out = set()
    for tok in _fold(title).split():
        if tok in _TITLE_STOPWORDS:
            continue
        if len(tok) > 3 and tok.endswith("s"):
            tok = tok[:-1]
        out.add(tok)
    return frozenset(out)


def classify_degree(raw: str) -> str | None:
    """Map a raw Sudoc 328$b string to our controlled degree token."""
    folded = _fold(raw)
    if not folded:
        return None
    for pattern, token in DEGREE_PATTERNS:
        if re.search(pattern, folded):
            return token
    if "these" in folded or "doctorat" in folded:
        return "doctorat_unspecified"
    return None


def _year(text: str | None) -> int | None:
    m = re.search(r"(1[5-9]\d\d|20\d\d)", text or "")
    return int(m.group(1)) if m else None


# ── near-duplicate collapsing ───────────────────────────────────────────

YEAR_WINDOW = 3
CONTAINMENT = 0.85
MIN_TOKENS_FOR_FUZZY = 3


def _same_work(a: dict, b: dict) -> bool:
    """Is this the same thesis catalogued twice?

    One thesis routinely has several Sudoc records — the deposit copy, a
    microfiche, a commercial reprint — under different PPNs, different years,
    and titles that differ by a character. Counting them separately fakes a
    multi-degree pattern (measured on Choquet: one 1946 thesis, two records,
    "Application"/"Applications").

    DIRECTION MATTERS. Splitting a real duplicate leaves the edge at REVIEW —
    the status quo, harmless. Merging two genuinely different degrees promotes
    the edge to TRUST on a false "only one doctorate". So the rule is
    deliberately conservative: short titles must match exactly.
    """
    ya, yb = a.get("year"), b.get("year")
    if ya is None or yb is None or abs(ya - yb) > YEAR_WINDOW:
        return False
    ta, tb = _title_tokens(a.get("title") or ""), _title_tokens(b.get("title") or "")
    if not ta or not tb:
        return False
    if min(len(ta), len(tb)) < MIN_TOKENS_FOR_FUZZY:
        return ta == tb
    return len(ta & tb) / min(len(ta), len(tb)) >= CONTAINMENT


def _specificity(rec: dict) -> int:
    return 0 if rec.get("degree") in (None, "doctorat_unspecified") else 1


def dedup_theses(records: list[dict]) -> list[dict]:
    """Greedy single-link clustering; keep the most specific record per work."""
    clusters: list[list[dict]] = []
    for rec in records:
        for cl in clusters:
            if any(_same_work(rec, other) for other in cl):
                cl.append(rec)
                break
        else:
            clusters.append([rec])
    return [max(cl, key=_specificity) for cl in clusters]


# ── Sudoc / IdRef access ────────────────────────────────────────────────


def parse_record(rec: ET.Element) -> dict | None:
    """Extract the thesis facts from one UNIMARC record."""
    out: dict = {}
    for df in rec.iter():
        tag = df.get("tag") if df.tag.endswith("datafield") else None
        if tag == "328":
            subs = {
                sf.get("code"): (sf.text or "")
                for sf in df
                if sf.tag.endswith("subfield")
            }
            raw = subs.get("b") or subs.get("a") or ""
            out["degree_raw"] = _CTRL.sub("", raw).strip()
            out["degree"] = classify_degree(raw or subs.get("a", ""))
            out["discipline"] = _CTRL.sub("", subs.get("c", "")).strip() or None
            out["institution"] = _CTRL.sub("", subs.get("e", "")).strip() or None
            out["year"] = _year(subs.get("d") or subs.get("a"))
        elif tag == "200":
            subs = {
                sf.get("code"): (sf.text or "")
                for sf in df
                if sf.tag.endswith("subfield")
            }
            if subs.get("a"):
                out["title"] = _CTRL.sub("", subs["a"]).strip()
    for cf in rec.iter():
        if cf.tag.endswith("controlfield") and cf.get("tag") == "001":
            out["ppn"] = (cf.text or "").strip()
    return out if out.get("degree") or out.get("year") else None


def parse_roles(root: ET.Element) -> dict[str, list[str]]:
    """UNIMARC role code -> record PPNs, parsed STRUCTURALLY.

    The previous version string-matched "070" against arbitrary elements and
    therefore filtered nothing (see defect 1 in the module docstring). Walking
    the <role> containers is the only way to know which records the person
    actually wrote.
    """
    roles: dict[str, list[str]] = {}
    for role in root.iter():
        if not role.tag.endswith("role"):
            continue
        code: str | None = None
        docs: list[str] = []
        for child in role:
            if child.tag.endswith("unimarcCode"):
                code = (child.text or "").strip()
            elif child.tag.endswith("doc"):
                for field in child:
                    if field.tag.endswith("ppn") and field.text:
                        docs.append(field.text.strip())
        if code:
            roles.setdefault(code, []).extend(docs)
    return roles


def authored_ppns(
    client: httpx.Client, ppn: str
) -> tuple[list[str], dict[str, list[str]], bool]:
    """Record PPNs this person AUTHORED ($4 070), the role map, and whether
    the lookup FAILED.

    The third element matters. A transient "Server disconnected" used to be
    indistinguishable from "this person has no Sudoc records": both produced
    an empty list, the person was silently dropped, and the run reported a
    yield as if they had been checked. The failure direction is safe (the edge
    stays at REVIEW) but invisible failures are how a harvest quietly measures
    a smaller population than it claims to.
    """
    try:
        r = client.get(IDREF_BIBLIO.format(ppn=ppn))
        if r.status_code != 200:
            return [], {}, True
        roles = parse_roles(ET.fromstring(r.text))
    except Exception as exc:  # noqa: BLE001
        print(f"  idref {ppn}: {exc}", file=sys.stderr)
        return [], {}, True
    # Exclude the person's own authority PPN — it appears in <query>, and the
    # old parser collected it as if it were one of their works.
    own = [p for p in roles.get(AUTHOR_ROLE, []) if p != ppn]
    return list(dict.fromkeys(own)), roles, False


def fetch_unimarc(
    client: httpx.Client, ppns: list[str], batch: int = 40, pause: float = 0.6
) -> list[dict]:
    """Fetch UNIMARC for every PPN, batched. No cap — see defect 2."""
    out: list[dict] = []
    for i in range(0, len(ppns), batch):
        sub = ppns[i : i + batch]
        query = " or ".join(f"ppn={p}" for p in sub)
        try:
            r = client.get(
                SRU,
                params={
                    "operation": "searchRetrieve",
                    "version": "1.1",
                    "query": query,
                    "recordSchema": "unimarc",
                    "maximumRecords": str(len(sub)),
                },
            )
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.text)
            for rec in root.iter():
                if rec.tag.endswith("record") and any(
                    c.tag.endswith("datafield") for c in rec
                ):
                    parsed = parse_record(rec)
                    if parsed:
                        out.append(parsed)
        except Exception as exc:  # noqa: BLE001
            print(f"  sru batch {i}: {exc}", file=sys.stderr)
        time.sleep(pause)
    return out


def person_theses(client: httpx.Client, ppn: str) -> dict:
    """Everything we can decide about one person's pre-1985 doctorates."""
    docs, roles, failed = authored_ppns(client, ppn)
    records = dedup_theses(fetch_unimarc(client, docs))
    # Count only records Sudoc actually TYPES as a thesis/doctorate. Without
    # this, an early-modern professor's presided disputations are counted as
    # his own degrees: Q122366 (IdRef 031854338) showed SIX "pre-1985
    # doctorates" dated 1721-1777 — "Dissertatio inauguralis physico-medica" —
    # because in that era the *praeses* was catalogued as the author of every
    # disputation he chaired. They all classify to degree=None.
    pre85 = [r for r in records if (r.get("year") or 9999) < 1985 and r.get("degree")]
    return {
        "IdRef": ppn,
        "lookup_failed": failed,
        "authored_records": len(docs),
        "supervised_records": len(roles.get(SUPERVISOR_ROLE, [])),
        "theses": [r for r in records if r.get("degree")],
        "pre1985_count": len(pre85),
        # THE decisive field: exactly one pre-1985 doctorate means the advisor
        # edge is unambiguous, so vetting_risk can lift it out of REVIEW.
        "pre1985_degree": pre85[0].get("degree") if len(pre85) == 1 else None,
        "pre1985_year": pre85[0].get("year") if len(pre85) == 1 else None,
    }


# ── target selection ────────────────────────────────────────────────────


def _era_band(rec: dict) -> tuple[int | None, int | None]:
    for field in ("DefenseYear", "ThesisYear"):
        y = rec.get(field)
        if isinstance(y, int):
            return y, y
    by = rec.get("BirthYear")
    if isinstance(by, int):
        return by + 23, by + 40
    return None, None


def select_targets(mode: str) -> tuple[dict[str, str], dict]:
    """QID -> IdRef for the people worth probing, plus a provenance report.

    `narrowed` (default) keeps only people who can change an outcome: an FR
    advisor edge at REVIEW, an exact P269, and an era band that can reach
    pre-1985. `all` restores the old every-French-person behaviour, which
    measured 55.8% provably useless calls.
    """
    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    idref_of = {q: v["IdRef"] for q, v in prov.items() if v.get("IdRef")}
    fr_all = {
        q: p
        for q, p in idref_of.items()
        if "FR" in (prov[q].get("DegreeCountries") or [])
    }
    if mode == "all":
        return fr_all, {"mode": "all", "targets": len(fr_all)}

    enr = json.loads(ENRICHMENT.read_text(encoding="utf-8"))["by_name"]
    targets: dict[str, str] = {}
    stats = {"mode": "narrowed", "fr_review_students": 0, "no_qid": 0, "no_idref": 0}
    for rec in enr.values():
        edges = [
            a
            for a in (rec.get("Advisors") or [])
            if isinstance(a, dict)
            and isinstance(a.get("vetting"), dict)
            and a["vetting"].get("degree_country") == "FR"
            and a["vetting"].get("tier") == "REVIEW"
        ]
        if not edges:
            continue
        stats["fr_review_students"] += 1
        qid = rec.get("QID")
        if not qid:
            stats["no_qid"] += 1
            continue
        ppn = idref_of.get(qid)
        if not ppn:
            stats["no_idref"] += 1
            continue
        lo, _hi = _era_band(rec)
        # An unknown era cannot be excluded — probe it.
        if lo is not None and lo >= 1985:
            continue
        targets[qid] = ppn
    stats["targets"] = len(targets)
    stats["skipped_vs_all"] = len(fr_all) - len(targets)
    return targets, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--targets", choices=("narrowed", "all"), default="narrowed")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()

    targets, stats = select_targets(args.targets)
    print(json.dumps(stats, indent=2))
    if args.limit:
        targets = dict(list(targets.items())[: args.limit])
    print(f"probing {len(targets):,} people\n")

    collected: dict[str, dict] = {}
    failures = 0
    headers = {"User-Agent": USER_AGENT}
    t0 = time.time()
    with httpx.Client(timeout=90, headers=headers, follow_redirects=True) as client:
        for i, (qid, ppn) in enumerate(targets.items(), 1):
            info = person_theses(client, ppn)
            if info["lookup_failed"]:
                failures += 1
            elif info["theses"] or info["authored_records"]:
                collected[qid] = info
            if i % 25 == 0:
                rate = i / max(time.time() - t0, 1e-6)
                eta = (len(targets) - i) / max(rate, 1e-6) / 60
                print(
                    f"  {i}/{len(targets)}  decided="
                    f"{sum(1 for v in collected.values() if v['pre1985_count'] == 1)}"
                    f"  eta={eta:.0f}min",
                    flush=True,
                )
            time.sleep(0.6)

    single = sum(1 for v in collected.values() if v["pre1985_count"] == 1)
    multi = sum(1 for v in collected.values() if v["pre1985_count"] > 1)
    none_ = sum(1 for v in collected.values() if v["pre1985_count"] == 0)
    print(f"\nprobed {len(targets):,} in {(time.time()-t0)/60:.1f} min")
    print(f"  people with any Sudoc record      : {len(collected):,}")
    print(f"  exactly ONE pre-1985 doctorate    : {single:,}  <- decidable")
    print(f"  TWO OR MORE (the Brezis pattern)  : {multi:,}")
    print(f"  none typed pre-1985               : {none_:,}")
    print(f"  LOOKUP FAILED (not evidence of absence): {failures:,}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "source": "Sudoc (ABES) via IdRef biblio + SRU",
            "licence": "Etalab Licence Ouverte 2.0",
            "retrieved": time.strftime("%Y-%m-%d"),
            "targets": stats,
            "probed": len(targets),
            "decidable": single,
            "multi_degree": multi,
            "lookup_failures": failures,
        },
        "people": collected,
    }
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
