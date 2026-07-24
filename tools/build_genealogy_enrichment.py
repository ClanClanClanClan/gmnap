#!/usr/bin/env python3
"""Build data/genealogy_enrichment.json from curated sources.

Seeds from data/mgp_validation_data.json (15 famous mathematicians with
full advisor chains), adds stub entries for transitive advisors so chain
traversal works one level deeper. Best-effort Wikidata SPARQL lookup for
BirthYear on missing entries.

Output format:
  {
    "version": "1.0",
    "source_count": N,
    "by_name": {
      "euler, leonhard": {
        "CanonicalLatin": "Euler, Leonhard",
        "GlobalID": "...",
        "BirthYear": 1707,
        "DeathYear": 1783,
        "Institution": "University of Basel",
        "Country": "Switzerland",
        "Thesis": "...",
        "ThesisYear": 1726,
        "Advisors": [{"name": "Bernoulli, Johann", "year": 1726}],
        "Source": "MGP"
      },
      ...
    },
    "by_global_id": {"...": "euler, leonhard", ...}
  }

Usage:
    PYTHONPATH=. python3 tools/build_genealogy_enrichment.py
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.global_id import generate_global_id


def _strip_diacritics(text: str) -> str:
    if not text:
        return text
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


_NAME_PARTICLES = frozenset(
    (
        "von",
        "van",
        "de",
        "del",
        "della",
        "di",
        "du",
        "da",
        "den",
        "der",
        "le",
        "la",
        "ten",
        "ter",
        "af",
        "av",
        "zu",
        "zum",
        "zur",
    )
)


def _fold_particles(key: str) -> str:
    if "," not in key:
        return key
    surname, given = key.split(",", 1)
    surname_tokens = surname.strip().split()
    particles: list[str] = []
    while surname_tokens and surname_tokens[0] in _NAME_PARTICLES:
        particles.append(surname_tokens.pop(0))
    if not particles or not surname_tokens:
        return key
    new_surname = " ".join(surname_tokens)
    new_given = (given.strip() + " " + " ".join(particles)).strip()
    return f"{new_surname}, {new_given}"


MGP_SOURCE = Path("data/mgp_validation_data.json")
WIKIDATA_GENEALOGY = Path("data/wikidata_genealogy.json")
# theses.fr French math theses — IdRef(PPN)-disambiguated student→advisor
# edges (scripts/data/fetch_theses_fr.py). Etalab-2.0. Merges via IdRef
# identity (SOURCE_META["theses.fr"] = high confidence).
THESES_FR = Path("data/theses_fr_math.json")
# OpenAlex-sourced 15k author affiliations — gives us Institution +
# Country for thousands of mathematicians the Wikidata P184 query
# misses (those without a recorded doctoral advisor). No advisor
# chains here, but a valuable coverage boost.
OPENALEX_AFFILIATIONS = Path("data/ml_training/openalex_10k_mathematicians.json")
# Round-23: bulk MGP harvest from `tools/harvest_mgp.py`.
# JSONL, one record per line. When present, merges authoritative
# MGP advisor chains over Wikidata's (MGP is the curated source for
# mathematicians, Wikidata's P184 derives from MGP for many entries).
# Optional — empty / missing means we use Wikidata + OpenAlex only.
MGP_FULL = Path("data/mgp_full.jsonl")
OUTPUT = Path("data/genealogy_enrichment.json")

# ISO-3166 alpha-2 → English country name. Vendored minimal mapping
# covering ~95% of OpenAlex's 118 country codes. Falls back to the
# raw 2-letter code for unknown entries.
_CC_TO_COUNTRY: dict[str, str] = {
    "AE": "United Arab Emirates",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BR": "Brazil",
    "BY": "Belarus",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HR": "Croatia",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IR": "Iran",
    "IS": "Iceland",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "KW": "Kuwait",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Morocco",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PE": "Peru",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TH": "Thailand",
    "TR": "Turkey",
    "TW": "Taiwan",
    "UA": "Ukraine",
    "US": "United States",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "ZA": "South Africa",
}

# Best-effort hand-curated birth years + countries for advisors we know
# about but who are not in the MGP seed.  All entries use the project's
# normalized key ("surname, given" lowercase, single-spaced).
ADVISOR_STUBS = {
    "bernoulli, johann": {
        "CanonicalLatin": "Bernoulli, Johann",
        "BirthYear": 1667,
        "DeathYear": 1748,
        "Country": "Switzerland",
        "Institution": "University of Basel",
        "Advisors": [{"name": "Bernoulli, Jacob"}],
    },
    "bernoulli, jacob": {
        "CanonicalLatin": "Bernoulli, Jacob",
        "BirthYear": 1655,
        "DeathYear": 1705,
        "Country": "Switzerland",
        "Institution": "University of Basel",
    },
    "gordan, paul albert": {
        "CanonicalLatin": "Gordan, Paul Albert",
        "BirthYear": 1837,
        "DeathYear": 1912,
        "Country": "Germany",
    },
    "lindemann, c. l. ferdinand": {
        "CanonicalLatin": "Lindemann, Ferdinand",
        "BirthYear": 1852,
        "DeathYear": 1939,
        "Country": "Germany",
    },
    "weber, heinrich martin": {
        "CanonicalLatin": "Weber, Heinrich Martin",
        "BirthYear": 1842,
        "DeathYear": 1913,
        "Country": "Germany",
    },
    "gauss, carl friedrich": {
        "CanonicalLatin": "Gauss, Carl Friedrich",
        "BirthYear": 1777,
        "DeathYear": 1855,
        "Country": "Germany",
        "Institution": "Universität Helmstedt",
        "Advisors": [{"name": "Pfaff, Johann Friedrich"}],
    },
    "pfaff, johann friedrich": {
        "CanonicalLatin": "Pfaff, Johann Friedrich",
        "BirthYear": 1765,
        "DeathYear": 1825,
        "Country": "Germany",
    },
    "coates, john henry": {
        "CanonicalLatin": "Coates, John Henry",
        "BirthYear": 1945,
        "DeathYear": 2022,
        "Country": "United Kingdom",
        "Institution": "University of Cambridge",
    },
    "knapp, anthony william": {
        "CanonicalLatin": "Knapp, Anthony William",
        "BirthYear": 1941,
        "Country": "United States",
        "Institution": "Stony Brook University",
    },
    "cartan, henri": {
        "CanonicalLatin": "Cartan, Henri",
        "BirthYear": 1904,
        "DeathYear": 2008,
        "Country": "France",
        "Institution": "École Normale Supérieure",
    },
    "schwartz, laurent": {
        "CanonicalLatin": "Schwartz, Laurent",
        "BirthYear": 1915,
        "DeathYear": 2002,
        "Country": "France",
    },
    "hardy, g. h.": {
        "CanonicalLatin": "Hardy, G. H.",
        "BirthYear": 1877,
        "DeathYear": 1947,
        "Country": "United Kingdom",
        "Institution": "Trinity College, Cambridge",
    },
    "steklov, vladimir andreevich": {
        "CanonicalLatin": "Steklov, Vladimir Andreevich",
        "BirthYear": 1864,
        "DeathYear": 1926,
        "Country": "Russia",
    },
    "kellogg, oliver dimon": {
        "CanonicalLatin": "Kellogg, Oliver Dimon",
        "BirthYear": 1878,
        "DeathYear": 1932,
        "Country": "United States",
    },
    "lojasiewicz, stanislaw": {
        "CanonicalLatin": "Łojasiewicz, Stanisław",
        "BirthYear": 1926,
        "DeathYear": 2002,
        "Country": "Poland",
    },
    "stallings, john robert": {
        "CanonicalLatin": "Stallings, John Robert",
        "BirthYear": 1935,
        "DeathYear": 2008,
        "Country": "United States",
    },
    "hedrick, earle raymond": {
        "CanonicalLatin": "Hedrick, Earle Raymond",
        "BirthYear": 1876,
        "DeathYear": 1943,
        "Country": "United States",
    },
    "lindstedt, anders": {
        "CanonicalLatin": "Lindstedt, Anders",
        "BirthYear": 1854,
        "DeathYear": 1939,
        "Country": "Sweden",
    },
    "hilbert, david": {
        "CanonicalLatin": "Hilbert, David",
        "BirthYear": 1862,
        "DeathYear": 1943,
        "Country": "Germany",
        "Institution": "Universität Königsberg",
    },
    "euler, leonhard": {
        "CanonicalLatin": "Euler, Leonhard",
        "BirthYear": 1707,
        "DeathYear": 1783,
        "Country": "Switzerland",
        "Institution": "University of Basel",
    },
    "riemann, bernhard": {
        "CanonicalLatin": "Riemann, Bernhard",
        "BirthYear": 1826,
        "DeathYear": 1866,
        "Country": "Germany",
    },
    "klein, felix": {
        "CanonicalLatin": "Klein, Felix",
        "BirthYear": 1849,
        "DeathYear": 1925,
        "Country": "Germany",
        "Institution": "Universität Bonn",
    },
    "smale, stephen": {
        "CanonicalLatin": "Smale, Stephen",
        "BirthYear": 1930,
        "Country": "United States",
    },
    "bott, raoul": {
        "CanonicalLatin": "Bott, Raoul",
        "BirthYear": 1923,
        "DeathYear": 2005,
        "Country": "United States",
    },
    "noether, emmy amalie": {
        "CanonicalLatin": "Noether, Emmy",
        "BirthYear": 1882,
        "DeathYear": 1935,
        "Country": "Germany",
        "Institution": "Friedrich-Alexander-Universität Erlangen-Nürnberg",
    },
    "tao, terence chi-shen": {
        "CanonicalLatin": "Tao, T.",
        "BirthYear": 1975,
        "Country": "Australia",
        "Institution": "Princeton University",
    },
    "stein, elias menachem": {
        "CanonicalLatin": "Stein, Elias",
        "BirthYear": 1931,
        "DeathYear": 2018,
        "Country": "United States",
        "Institution": "Princeton University",
    },
    "poincare, henri": {
        "CanonicalLatin": "Poincaré, Henri",
        "BirthYear": 1854,
        "DeathYear": 1912,
        "Country": "France",
        "Institution": "École Polytechnique",
    },
    "hermite, charles": {
        "CanonicalLatin": "Hermite, Charles",
        "BirthYear": 1822,
        "DeathYear": 1901,
        "Country": "France",
    },
    "banach, stefan": {
        "CanonicalLatin": "Banach, Stefan",
        "BirthYear": 1892,
        "DeathYear": 1945,
        "Country": "Poland",
        "Institution": "Lviv Polytechnic",
    },
    "ramanujan, srinivasa aiyangar": {
        "CanonicalLatin": "Ramanujan, Srinivasa",
        "BirthYear": 1887,
        "DeathYear": 1920,
        "Country": "India",
    },
    "perelman, grigorii yakovlevich": {
        "CanonicalLatin": "Perelman, G.",
        "BirthYear": 1966,
        "Country": "Russia",
        "Institution": "Steklov Institute of Mathematics",
    },
    # English-spelling alias so queries like "Perelman, G." resolve
    # (transliteration 'Grigori' does not share tokens with 'Grigorii').
    "perelman, grigori": {
        "CanonicalLatin": "Perelman, G.",
        "BirthYear": 1966,
        "Country": "Russia",
        "Institution": "Steklov Institute of Mathematics",
    },
    "mirzakhani, maryam": {
        "CanonicalLatin": "Mirzakhani, Maryam",
        "BirthYear": 1977,
        "DeathYear": 2017,
        "Country": "Iran",
        "Institution": "Stanford University",
    },
    "grothendieck, alexander": {
        "CanonicalLatin": "Grothendieck, Alexander",
        "BirthYear": 1928,
        "DeathYear": 2014,
        "Country": "France",
        "Institution": "Université de Nancy",
    },
    "serre, jean-pierre": {
        "CanonicalLatin": "Serre, J.-P.",
        "BirthYear": 1926,
        "Country": "France",
        "Institution": "Collège de France",
    },
    "wiles, andrew john": {
        "CanonicalLatin": "Wiles, A.",
        "BirthYear": 1953,
        "Country": "United Kingdom",
        "Institution": "Princeton University",
    },
    "avila, artur": {
        "CanonicalLatin": "Avila, A.",
        "BirthYear": 1979,
        "Country": "Brazil",
        "Institution": "Université Paris Diderot",
    },
}


def normalize_key(name: str) -> str:
    """Normalize a name to its enrichment lookup key.

    Must match src/core/genealogy_lookup.py::_normalize_key — any change
    here requires a matching change there.
    """
    if not name:
        return ""
    # Drop parenthetical aliases: "G. H. (Godfrey Harold) Hardy" → "G. H. Hardy"
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Strip diacritics so 'Erdős' and 'Erdos' normalize to the same key
    name = _strip_diacritics(name)
    name = re.sub(r"\s+", " ", name.strip().lower())
    if "," not in name:
        parts = name.split()
        if len(parts) >= 2:
            name = f"{parts[-1]}, {' '.join(parts[:-1])}"
    name = re.sub(r"\s+,", ",", name).strip(" ,")
    name = _fold_particles(name)
    return name


def to_canonical_latin(name: str) -> str:
    """Convert 'First Last' → 'Last, First' preserving case.

    Strips parenthetical aliases for a cleaner display form.
    """
    # Drop parenthetical aliases for cleaner display
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s+", " ", name.strip())
    if "," in name:
        return name.strip(" ,")
    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def assign_global_id(record: dict) -> str:
    """Deterministic GlobalID for a record."""
    entry = {
        "CanonicalLatin": record.get("CanonicalLatin", ""),
        "CanonicalNative": record.get("CanonicalLatin", ""),
        "BirthYear": record.get("BirthYear"),
        "DeathYear": record.get("DeathYear"),
    }
    return generate_global_id(entry)


# ---------------------------------------------------------------------------
# R62: per-edge identity + provenance + confidence (the safe-ingestion
# backbone). Every advisor edge is stamped with its source, a confidence
# tier, and — when known — the Wikidata QID that makes cross-source fusion
# false-merge-resistant. License is DERIVED from source (SOURCE_META), not
# stored per edge. Verified tiers are FLOOR-LOCKED: automation may fill an
# empty slot or corroborate, but may never override a verified edge. This
# is the contract every future source (P185, theses.fr, MathTree) plugs
# into — see docs/DATA_SOURCES.md and the R62 tasks.
# ---------------------------------------------------------------------------
CONFIDENCE_ORDER = {"verified": 3, "high": 2, "medium": 1, "low": 0}

SOURCE_META = {
    "curated": {"confidence": "verified", "license": "MIT"},
    "MGP validation seed": {"confidence": "verified", "license": "MGP-noncommercial"},
    "MGP": {"confidence": "verified", "license": "MGP-noncommercial"},
    "Wikidata-P184": {"confidence": "high", "license": "CC0"},
    "Wikidata-P185": {"confidence": "high", "license": "CC0"},
    "theses.fr": {"confidence": "high", "license": "Etalab-2.0"},
    "MathTree": {"confidence": "medium", "license": "CC-BY-3.0"},
    "referenced advisor (no metadata)": {"confidence": "low", "license": "n/a"},
}

# Verified, hand-curated tiers — never overridden by an automated source.
FLOOR_LOCKED = {"curated", "MGP", "MGP validation seed"}


def make_edge(name, *, qid=None, idref=None, source, year=None, relation="doctoral"):
    """Construct a typed advisor edge with provenance + confidence.

    Keeps ``name`` so every existing reader (``adv["name"]``) still works;
    ADDS qid/idref/source/confidence/relation/year alongside it. ``qid``
    (Wikidata) and ``idref`` (SUDOC/IdRef, e.g. from theses.fr) are the two
    persistent-identity axes fusion keys on — see ``_same_advisor``.
    """
    meta = SOURCE_META.get(source, {"confidence": "low"})
    edge = {
        "name": name,
        "source": source,
        "confidence": meta["confidence"],
        "relation": relation,
    }
    if qid:
        edge["qid"] = qid
    if idref:
        edge["idref"] = idref
    if year:
        edge["year"] = year
    return edge


def _stamp_edges(advisors, source):
    """Map a raw advisor list (dicts or strings) to typed edges, preserving
    a QID / year / mgp_id when the source carried one."""
    out = []
    for a in advisors or []:
        if isinstance(a, dict):
            name = a.get("name")
            if not name:
                continue
            edge = make_edge(
                name,
                qid=a.get("qid"),
                idref=a.get("idref"),
                source=source,
                year=a.get("year"),
                relation=a.get("relation", "doctoral"),
            )
            if a.get("mgp_id"):
                edge["mgp_id"] = a["mgp_id"]
            out.append(edge)
        elif isinstance(a, str) and a:
            out.append(make_edge(a, source=source))
    return out


def _same_advisor(a, b):
    """Two edges denote the same advisor iff a shared persistent id agrees.

    Precedence: QID first, then IdRef, then normalized name. Two DIFFERENT
    ids of the same kind are different people even under one spelling (a
    Wikidata/IdRef duplicate is not a merge signal). When the two edges
    carry DIFFERENT id kinds (one QID-only, one IdRef-only — the common
    Wikidata-vs-theses.fr case) there is no crosswalk here, so they fall
    back to a normalized-name match — conservative: a spelling difference
    leaves them un-merged (a rare near-dup) rather than risking a false
    merge."""
    qa, qb = a.get("qid"), b.get("qid")
    if qa and qb:
        return qa == qb
    ia, ib = a.get("idref"), b.get("idref")
    if ia and ib:
        return ia == ib
    na = normalize_key(a.get("name", ""))
    nb = normalize_key(b.get("name", ""))
    return bool(na) and na == nb


def merge_advisor_edges(existing, incoming):
    """Fill / corroborate / override-only-lower. Returns the merged list.

    - fill: an advisor not already present is added.
    - corroborate: an incoming edge matching an existing advisor (by QID,
      else by normalized name — see ``_same_advisor``) accumulates its
      source into ``sources`` and upgrades a missing QID.
    - override: only when the incoming edge has STRICTLY higher confidence,
      and never when that would demote a FLOOR_LOCKED verified edge to an
      automated one. Accumulated provenance + QID are always carried across.
    """
    merged: list = []
    for e in existing:
        m = dict(e)
        srcs = list(m.get("sources") or [])
        if m.get("source") and m["source"] not in srcs:
            srcs.append(m["source"])
        m["sources"] = srcs
        merged.append(m)
    for inc in incoming:
        match = next((cur for cur in merged if _same_advisor(cur, inc)), None)
        if match is None:
            m = dict(inc)
            m["sources"] = [inc["source"]] if inc.get("source") else []
            merged.append(m)
            continue
        if inc.get("source") and inc["source"] not in match["sources"]:
            match["sources"].append(inc["source"])
        if not match.get("qid") and inc.get("qid"):
            match["qid"] = inc["qid"]
        if not match.get("idref") and inc.get("idref"):
            match["idref"] = inc["idref"]
        cur_c = CONFIDENCE_ORDER.get(match.get("confidence", "low"), 0)
        inc_c = CONFIDENCE_ORDER.get(inc.get("confidence", "low"), 0)
        cur_locked = match.get("source") in FLOOR_LOCKED
        inc_locked = inc.get("source") in FLOOR_LOCKED
        if inc_c > cur_c and not (cur_locked and not inc_locked):
            keep_sources, keep_qid = match["sources"], match.get("qid")
            match.clear()
            match.update(inc)
            match["sources"] = keep_sources
            if keep_qid:
                match["qid"] = keep_qid
    return merged


def build(no_mgp: bool = False) -> dict:
    """Build the enrichment dict.

    ``no_mgp=True`` (the ``--no-mgp`` CLI flag) skips EVERY MGP input —
    the validation seeds (step 1) and the bulk harvest merge (step 2d) —
    producing a CC0-clean artefact (Wikidata + OpenAlex + MIT-licensed
    curated stubs only). This is the supported path for COMMERCIAL
    deployments: MGP's terms are non-commercial-with-attribution
    (DATA_SOURCES.md), so the default bundled artefact, which contains
    ~490 MGP-derived records, must not be served commercially as-is.
    """
    by_name: dict[str, dict] = {}

    # 1. Seed from MGP validation data (skipped under --no-mgp)
    if no_mgp:
        print("--no-mgp: skipping MGP validation seeds (CC0-clean build)")
    else:
        mgp_path = MGP_SOURCE
        if not mgp_path.exists():
            print(f"ERROR: {mgp_path} not found")
            sys.exit(1)

        mgp_entries = json.loads(mgp_path.read_text())
        print(f"Loaded {len(mgp_entries)} seed entries from {mgp_path}")

        for e in mgp_entries:
            key = normalize_key(e["name"])
            record = {
                "CanonicalLatin": to_canonical_latin(e["name"]),
                "Source": "MGP validation seed",
            }
            if e.get("institution"):
                record["Institution"] = e["institution"]
            if e.get("year"):
                record["ThesisYear"] = e["year"]
            if e.get("thesis"):
                record["Thesis"] = e["thesis"]
            if e.get("advisors"):
                record["Advisors"] = _stamp_edges(
                    [
                        {
                            "name": to_canonical_latin(a["name"]),
                            "mgp_id": a.get("mgp_id"),
                        }
                        for a in e["advisors"]
                        if a.get("name")
                    ],
                    "MGP validation seed",
                )
            by_name[key] = record

    # 2. Merge in hand-curated stubs (birth years, countries, advisor chains)
    for key, stub in ADVISOR_STUBS.items():
        if key in by_name:
            # Merge: existing MGP data wins for overlapping fields,
            # stub fills in the gaps
            for field, value in stub.items():
                if field == "Advisors":
                    # Only add if MGP didn't provide any advisors
                    by_name[key].setdefault("Advisors", _stamp_edges(value, "curated"))
                elif not by_name[key].get(field):
                    by_name[key][field] = value
        else:
            stub_copy = dict(stub)
            stub_copy.setdefault("Source", "curated stub")
            if stub_copy.get("Advisors"):
                stub_copy["Advisors"] = _stamp_edges(stub_copy["Advisors"], "curated")
            by_name[key] = stub_copy

    # 2b. Merge in the Wikidata genealogy dataset (thousands of
    # mathematicians with doctoral advisor chains + birth dates +
    # institutions). MGP + stubs still win for overlapping fields so
    # the curated labels stay authoritative on famous names.
    if WIKIDATA_GENEALOGY.exists():
        wiki_entries = json.loads(WIKIDATA_GENEALOGY.read_text(encoding="utf-8"))
        added = 0
        enriched = 0
        for e in wiki_entries:
            if not e.get("CanonicalLatin"):
                continue
            key = normalize_key(e["CanonicalLatin"])
            if not key:
                continue
            # R62: preserve the Wikidata QID on every advisor edge (it was
            # dropped here — the identity that makes fusion false-merge-safe).
            advisors = _stamp_edges(
                [
                    {"name": a["name"], "qid": a.get("qid")}
                    for a in e.get("Advisors", [])
                    if a.get("name")
                ],
                "Wikidata-P184",
            )
            institutions = e.get("Institutions") or []
            institution = institutions[0] if institutions else None
            if key in by_name:
                rec = by_name[key]
                # R62: fill-empty only. A record that already carries curated/
                # MGP-seed advisors holds them under a different name form and
                # with NO QID, so merging Wikidata's QID-bearing variant here
                # would DUPLICATE the same advisor (name-vs-QID identity
                # mismatch). Cross-source co-advisor reconciliation needs fuzzy
                # name matching and is deferred to the ID-bearing sources
                # (theses.fr/P185), which merge cleanly via merge_advisor_edges.
                if advisors and not rec.get("Advisors"):
                    rec["Advisors"] = advisors
                    enriched += 1
                for field, value in (
                    ("BirthYear", e.get("BirthYear")),
                    ("DeathYear", e.get("DeathYear")),
                    ("Country", e.get("Country")),
                    ("Institution", institution),
                ):
                    if value and not rec.get(field):
                        rec[field] = value
                # Track source so downstream users can see where it came from
                if rec.get("Source") == "MGP validation seed":
                    pass
                else:
                    rec["Source"] = rec.get("Source", "") + "+Wikidata"
            else:
                record = {
                    "CanonicalLatin": e["CanonicalLatin"],
                    "Source": "Wikidata",
                }
                if e.get("BirthYear"):
                    record["BirthYear"] = e["BirthYear"]
                if e.get("DeathYear"):
                    record["DeathYear"] = e["DeathYear"]
                if e.get("Country"):
                    record["Country"] = e["Country"]
                if institution:
                    record["Institution"] = institution
                if advisors:
                    record["Advisors"] = advisors
                by_name[key] = record
                added += 1
        print(
            f"Wikidata merge: +{added} new entries, enriched {enriched} "
            f"existing entries"
        )

    # 2b-fr. Merge in the theses.fr French math theses. Unlike the Wikidata
    # block's fill-empty, these student→advisor edges carry an IdRef (PPN),
    # so merge_advisor_edges fuses them cleanly: an existing advisor is
    # corroborated (its source list accumulates "theses.fr"), a genuinely
    # new advisor is added, and a FLOOR_LOCKED curated/MGP edge is never
    # demoted. The bulk are net-new students — recent French PhDs absent
    # from Wikidata — added outright. See scripts/data/fetch_theses_fr.py.
    if THESES_FR.exists():
        fr_entries = json.loads(THESES_FR.read_text(encoding="utf-8"))
        added = 0
        merged = 0
        for e in fr_entries:
            canonical = e.get("CanonicalLatin")
            if not canonical:
                continue
            key = normalize_key(canonical)
            if not key:
                continue
            # Map the harvest's ``ppn`` → ``idref`` at the ingestion boundary
            # so _stamp_edges / _same_advisor stay generic on 'idref'.
            advisors = _stamp_edges(
                [
                    {"name": a["name"], "idref": a.get("ppn")}
                    for a in e.get("Advisors", [])
                    if a.get("name")
                ],
                "theses.fr",
            )
            if not advisors:
                continue
            institution = e.get("Institution")
            if key in by_name:
                rec = by_name[key]
                rec["Advisors"] = merge_advisor_edges(
                    rec.get("Advisors") or [], advisors
                )
                for field, value in (
                    ("Country", e.get("Country")),
                    ("Institution", institution),
                ):
                    if value and not rec.get(field):
                        rec[field] = value
                if "theses.fr" not in (rec.get("Source") or ""):
                    rec["Source"] = (rec.get("Source", "") + "+theses.fr").lstrip("+")
                merged += 1
            else:
                record = {
                    "CanonicalLatin": canonical,
                    "Source": "theses.fr",
                    "Advisors": advisors,
                }
                if e.get("Country"):
                    record["Country"] = e["Country"]
                if institution:
                    record["Institution"] = institution
                if e.get("DefenseYear"):
                    record["DefenseYear"] = e["DefenseYear"]
                if e.get("person_ppn"):
                    record["IdRef"] = e["person_ppn"]
                by_name[key] = record
                added += 1
        print(
            f"theses.fr merge: +{added} new entries, {merged} existing "
            f"students merged"
        )

    # 2c. Merge in the OpenAlex affiliations dataset (15 k entries).
    # This is Institution + Country only — no advisor chains — but
    # covers thousands of working mathematicians the P184 query
    # skips because they don't have a recorded doctoral advisor on
    # Wikidata. Existing MGP / curated / Wikidata data wins on all
    # overlapping fields.
    if OPENALEX_AFFILIATIONS.exists():
        oa_entries = json.loads(OPENALEX_AFFILIATIONS.read_text(encoding="utf-8"))
        added = 0
        enriched = 0
        for e in oa_entries:
            name = e.get("name")
            if not name:
                continue
            key = normalize_key(name)
            if not key:
                continue
            institution = e.get("institution") or None
            cc = e.get("country_code") or ""
            country = _CC_TO_COUNTRY.get(cc, cc) or None

            if key in by_name:
                rec = by_name[key]
                filled = False
                for field, value in (
                    ("Institution", institution),
                    ("Country", country),
                ):
                    if value and not rec.get(field):
                        rec[field] = value
                        filled = True
                if filled:
                    enriched += 1
                    # Mark as OpenAlex-augmented (idempotent — don't
                    # dedupe-concat, just add the tag once).
                    src = rec.get("Source") or ""
                    if "OpenAlex" not in src:
                        rec["Source"] = (src + "+OpenAlex") if src else "OpenAlex"
            else:
                record: dict = {
                    "CanonicalLatin": to_canonical_latin(name),
                    "Source": "OpenAlex",
                }
                if institution:
                    record["Institution"] = institution
                if country:
                    record["Country"] = country
                by_name[key] = record
                added += 1
        print(
            f"OpenAlex merge: +{added} new entries, enriched {enriched} "
            f"existing entries"
        )

    # 2d. Merge MGP bulk-harvest (round 23). Authoritative for
    # mathematician advisor chains — MGP is hand-curated. When
    # present, MGP advisors override Wikidata's (MGP is upstream of
    # most Wikidata P184 entries anyway). Optional — empty / missing
    # file is fine. Skipped entirely under --no-mgp (CC0-clean build).
    if not no_mgp and MGP_FULL.exists() and MGP_FULL.stat().st_size > 0:
        added = 0
        enriched = 0
        with MGP_FULL.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                name = e.get("name")
                if not name:
                    continue
                key = normalize_key(name)
                if not key:
                    continue
                advisors_raw = e.get("advisors") or []
                advisors = _stamp_edges(
                    [
                        {"name": a[0]}
                        for a in advisors_raw
                        if isinstance(a, (list, tuple)) and a
                    ],
                    "MGP",
                )
                year = e.get("year")
                institution = e.get("institution")
                country = e.get("country")
                if key in by_name:
                    rec = by_name[key]
                    # R62: fill-empty (was blind-replace, which dropped
                    # curated edges). Same name-vs-QID rationale as the
                    # Wikidata block above — cross-source merge is deferred.
                    if advisors and not rec.get("Advisors"):
                        rec["Advisors"] = advisors
                        enriched += 1
                    if institution and not rec.get("Institution"):
                        rec["Institution"] = institution
                    if country and not rec.get("Country"):
                        rec["Country"] = country
                    src = rec.get("Source") or ""
                    if "MGP" not in src:
                        rec["Source"] = (src + "+MGP") if src else "MGP"
                else:
                    record: dict = {
                        "CanonicalLatin": to_canonical_latin(name),
                        "Source": "MGP",
                    }
                    if advisors:
                        record["Advisors"] = advisors
                    if year:
                        # R62: a thesis-year-minus-28 guess is NOT a verified
                        # birth year — keep it clearly labelled so it never
                        # masquerades as fact (was record["BirthYear"]).
                        record["BirthYearEstimated"] = year - 28
                    if institution:
                        record["Institution"] = institution
                    if country:
                        record["Country"] = country
                    by_name[key] = record
                    added += 1
        print(
            f"MGP merge: +{added} new entries, enriched {enriched} " f"existing entries"
        )

    # 3. Ensure every referenced advisor has at least a stub entry so
    # chain traversal can find it (otherwise it becomes a dead end).
    # Preserve proper-case display names when we have them — walk the
    # Advisors lists first to collect the nicest CanonicalLatin we saw
    # for each normalized key.
    referenced_display: dict[str, str] = {}
    for record in list(by_name.values()):
        for adv in record.get("Advisors", []) or []:
            name = adv.get("name") if isinstance(adv, dict) else adv
            if not name:
                continue
            key = normalize_key(name)
            if not key:
                continue
            # Prefer the longest / most-cased display we've seen
            candidate = to_canonical_latin(name)
            current = referenced_display.get(key, "")
            if len(candidate) > len(current):
                referenced_display[key] = candidate

    for adv_key in set(referenced_display) - set(by_name):
        by_name[adv_key] = {
            "CanonicalLatin": referenced_display[adv_key] or adv_key,
            "Source": "referenced advisor (no metadata)",
        }

    # 4. Assign GlobalIDs and build reverse index
    by_gid: dict[str, str] = {}
    for key, record in by_name.items():
        gid = assign_global_id(record)
        record["GlobalID"] = gid
        by_gid[gid] = key

    # 5. Data-subject suppression list (PRIVACY.md, R55).
    apply_suppression_list(by_name, by_gid, Path("data/removal_requests.txt"))

    return {
        "version": "1.0",
        "source_count": len(by_name),
        "by_name": by_name,
        "by_global_id": by_gid,
    }


def apply_suppression_list(
    by_name: dict, by_gid: dict, removal_path: Path
) -> tuple[int, int]:
    """Honour data-subject erasure requests (PRIVACY.md, R55).

    ``removal_path`` holds one canonical name or GlobalID per line ('#'
    comments allowed). Because the enrichment is periodically REBUILT from
    upstream harvests, a one-off deletion would silently reappear on the
    next refresh — this list is consulted on every build so an honoured
    request stays honoured. Removes the person's own record AND their
    appearances in other records' Advisors lists (their name is personal
    data wherever it occurs). Returns (records_removed, refs_scrubbed).
    """
    if not removal_path.exists():
        return (0, 0)
    suppressed_keys: set[str] = set()
    suppressed_gids: set[str] = set()
    for raw in removal_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        # A GlobalID is 22 Base32 chars (optionally --N suffixed); anything
        # else is treated as a name.
        if re.fullmatch(r"[A-Z2-7]{22}(--\d+)?", line):
            suppressed_gids.add(line)
        else:
            key = normalize_key(line)
            if key:
                suppressed_keys.add(key)
    removed = 0
    for key in list(by_name):
        rec = by_name[key]
        if key in suppressed_keys or rec.get("GlobalID") in suppressed_gids:
            by_gid.pop(rec.get("GlobalID"), None)
            del by_name[key]
            removed += 1
    scrubbed_refs = 0
    for rec in by_name.values():
        advisors = rec.get("Advisors")
        if not advisors:
            continue
        kept = [
            a
            for a in advisors
            if normalize_key((a.get("name") if isinstance(a, dict) else a) or "")
            not in suppressed_keys
        ]
        if len(kept) != len(advisors):
            scrubbed_refs += len(advisors) - len(kept)
            if kept:
                rec["Advisors"] = kept
            else:
                rec.pop("Advisors", None)
    if removed or scrubbed_refs:
        print(
            f"Suppression list: removed {removed} record(s), scrubbed "
            f"{scrubbed_refs} advisor reference(s) ({removal_path})"
        )
    return (removed, scrubbed_refs)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--no-mgp",
        action="store_true",
        help=(
            "Exclude every MGP input (validation seeds + bulk harvest), "
            "producing a CC0-clean artefact (Wikidata + OpenAlex + MIT "
            "curated stubs). REQUIRED for commercial deployments: MGP's "
            "terms are non-commercial-with-attribution — see "
            "DATA_SOURCES.md 'Commercial use'."
        ),
    )
    args = ap.parse_args()

    output = build(no_mgp=args.no_mgp)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    n = output["source_count"]
    with_adv = sum(1 for r in output["by_name"].values() if r.get("Advisors"))
    with_birth = sum(1 for r in output["by_name"].values() if r.get("BirthYear"))
    with_inst = sum(1 for r in output["by_name"].values() if r.get("Institution"))
    mgp_n = sum(
        1 for r in output["by_name"].values() if "MGP" in (r.get("Source") or "")
    )
    print(
        f"Wrote {OUTPUT}: {n} entries "
        f"({with_adv} with Advisors, {with_birth} with BirthYear, "
        f"{with_inst} with Institution, {mgp_n} MGP-derived)"
    )
    if args.no_mgp and mgp_n:
        print(
            f"WARNING: --no-mgp build still contains {mgp_n} MGP-tagged "
            f"record(s) — investigate before commercial use."
        )


if __name__ == "__main__":
    main()
