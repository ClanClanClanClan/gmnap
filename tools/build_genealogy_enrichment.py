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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.global_id import generate_global_id

MGP_SOURCE = Path("data/mgp_validation_data.json")
OUTPUT = Path("data/genealogy_enrichment.json")

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
        "CanonicalLatin": "Tao, Terence",
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
        "CanonicalLatin": "Perelman, Grigori",
        "BirthYear": 1966,
        "Country": "Russia",
        "Institution": "Steklov Institute of Mathematics",
    },
    # English-spelling alias so queries like "Perelman, Grigori" resolve
    # (transliteration 'Grigori' does not share tokens with 'Grigorii').
    "perelman, grigori": {
        "CanonicalLatin": "Perelman, Grigori",
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
        "CanonicalLatin": "Serre, Jean-Pierre",
        "BirthYear": 1926,
        "Country": "France",
        "Institution": "Collège de France",
    },
    "wiles, andrew john": {
        "CanonicalLatin": "Wiles, Andrew",
        "BirthYear": 1953,
        "Country": "United Kingdom",
        "Institution": "Princeton University",
    },
    "avila, artur": {
        "CanonicalLatin": "Avila, Artur",
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
    name = re.sub(r"\s+", " ", name.strip().lower())
    if "," not in name:
        parts = name.split()
        if len(parts) >= 2:
            name = f"{parts[-1]}, {' '.join(parts[:-1])}"
    name = re.sub(r"\s+,", ",", name).strip(" ,")
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


def build() -> dict:
    by_name: dict[str, dict] = {}

    # 1. Seed from MGP validation data
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
            record["Advisors"] = [
                {
                    "name": to_canonical_latin(a["name"]),
                    "mgp_id": a.get("mgp_id"),
                }
                for a in e["advisors"]
                if a.get("name")
            ]
        by_name[key] = record

    # 2. Merge in hand-curated stubs (birth years, countries, advisor chains)
    for key, stub in ADVISOR_STUBS.items():
        if key in by_name:
            # Merge: existing MGP data wins for overlapping fields,
            # stub fills in the gaps
            for field, value in stub.items():
                if field == "Advisors":
                    # Only add if MGP didn't provide any advisors
                    by_name[key].setdefault("Advisors", value)
                elif not by_name[key].get(field):
                    by_name[key][field] = value
        else:
            stub_copy = dict(stub)
            stub_copy.setdefault("Source", "curated stub")
            by_name[key] = stub_copy

    # 3. Ensure every referenced advisor has at least a stub entry so
    # chain traversal can find it (otherwise it becomes a dead end).
    referenced = set()
    for record in list(by_name.values()):
        for adv in record.get("Advisors", []):
            referenced.add(normalize_key(adv["name"]))

    for adv_key in referenced - set(by_name):
        by_name[adv_key] = {
            "CanonicalLatin": to_canonical_latin(adv_key.replace(",", ", ")),
            "Source": "referenced advisor (no metadata)",
        }

    # 4. Assign GlobalIDs and build reverse index
    by_gid: dict[str, str] = {}
    for key, record in by_name.items():
        gid = assign_global_id(record)
        record["GlobalID"] = gid
        by_gid[gid] = key

    return {
        "version": "1.0",
        "source_count": len(by_name),
        "by_name": by_name,
        "by_global_id": by_gid,
    }


def main() -> None:
    output = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    n = output["source_count"]
    with_adv = sum(1 for r in output["by_name"].values() if r.get("Advisors"))
    with_birth = sum(1 for r in output["by_name"].values() if r.get("BirthYear"))
    with_inst = sum(1 for r in output["by_name"].values() if r.get("Institution"))
    print(
        f"Wrote {OUTPUT}: {n} entries "
        f"({with_adv} with Advisors, {with_birth} with BirthYear, "
        f"{with_inst} with Institution)"
    )


if __name__ == "__main__":
    main()
