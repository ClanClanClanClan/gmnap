#!/usr/bin/env python3
"""Fetch mathematicians from Wikidata via SPARQL.

Queries for instances of mathematician (Q170790) with country of citizenship.
Targets 2,000+ entries across all nationalities and historical periods.

Output: data/wikidata_mathematicians.json

Usage: python3 scripts/data/fetch_wikidata_mathematicians.py
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ENDPOINT = "https://query.wikidata.org/sparql"

# Wikidata QID → ISO 3166-1 alpha-2
QID_TO_CC = {
    # Major countries
    "Q30": "US",
    "Q145": "GB",
    "Q142": "FR",
    "Q183": "DE",
    "Q38": "IT",
    "Q29": "ES",
    "Q45": "PT",
    "Q55": "NL",
    "Q31": "BE",
    "Q39": "CH",
    "Q40": "AT",
    "Q159": "RU",
    "Q36": "PL",
    "Q28": "HU",
    "Q213": "CZ",
    "Q218": "RO",
    "Q34": "SE",
    "Q20": "NO",
    "Q35": "DK",
    "Q33": "FI",
    "Q41": "GR",
    "Q43": "TR",
    "Q794": "IR",
    "Q668": "IN",
    "Q148": "CN",
    "Q17": "JP",
    "Q884": "KR",
    "Q155": "BR",
    "Q96": "MX",
    "Q801": "IL",
    "Q79": "EG",
    "Q16": "CA",
    "Q408": "AU",
    "Q664": "NZ",
    "Q27": "IE",
    "Q37": "LT",
    "Q211": "LV",
    "Q191": "EE",
    "Q219": "BG",
    "Q403": "RS",
    "Q224": "HR",
    "Q215": "SI",
    "Q217": "MD",
    "Q212": "UA",
    "Q184": "BY",
    "Q227": "AZ",
    "Q230": "GE",
    "Q399": "AM",
    "Q232": "KZ",
    "Q265": "UZ",
    "Q889": "AF",
    "Q851": "SA",
    "Q796": "IQ",
    "Q858": "SY",
    "Q822": "LB",
    "Q810": "JO",
    "Q846": "QA",
    "Q878": "AE",
    "Q842": "OM",
    "Q1028": "MA",
    "Q262": "DZ",
    "Q948": "TN",
    "Q1029": "LY",
    "Q115": "ET",
    "Q114": "KE",
    "Q117": "GH",
    "Q1033": "NG",
    "Q1030": "TZ",
    "Q258": "ZA",
    "Q953": "ZW",
    "Q1032": "UG",
    "Q334": "SG",
    "Q869": "TH",
    "Q252": "ID",
    "Q833": "MY",
    "Q928": "PH",
    "Q881": "VN",
    "Q902": "BD",
    "Q843": "PK",
    "Q854": "LK",
    "Q837": "NP",
    "Q736": "EC",
    "Q298": "CL",
    "Q414": "AR",
    "Q419": "PE",
    "Q733": "PY",
    "Q717": "VE",
    "Q750": "BO",
    "Q739": "CO",
    "Q241": "CU",
    # Historical polities → modern CC
    "Q7318": "DE",  # German Empire
    "Q27306": "DE",  # Kingdom of Prussia
    "Q153136": "DE",  # Electorate of Saxony
    "Q164079": "DE",  # Grand Duchy of Baden
    "Q43287": "DE",  # German Reich
    "Q41304": "DE",  # Weimar Republic
    "Q713750": "DE",  # Duchy of Brunswick
    "Q151624": "DE",  # Electorate of Hanover
    "Q154741": "DE",  # Saxe-Weimar-Eisenach
    "Q131964": "AT",  # Austrian Empire
    "Q533534": "AT",  # Austria-Hungary
    "Q34266": "RU",  # Russian Empire
    "Q15180": "RU",  # Soviet Union
    "Q174193": "FR",  # Kingdom of France
    "Q71084": "IT",  # Kingdom of Italy
    "Q172579": "IT",  # Republic of Venice
    "Q12548": "GB",  # Holy Roman Empire (rough)
    "Q12560": "PL",  # Second Polish Republic
    "Q5765": "TR",  # Ottoman Empire
    "Q8733": "CN",  # Qing dynasty
    "Q9903": "GB",  # Kingdom of England
    "Q179876": "GB",  # Kingdom of Scotland
    "Q161885": "NL",  # Dutch Republic
    "Q29520": "CN",  # Republic of China (→ Taiwan)
}

SPARQL_TEMPLATE = """
SELECT ?person ?personLabel ?country ?countryLabel WHERE {{
  ?person wdt:P106 wd:Q170790 .
  ?person wdt:P27 ?country .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT {limit}
OFFSET {offset}
"""

BATCH_SIZE = 2000


def fetch_wikidata():
    """Fetch mathematicians from Wikidata SPARQL endpoint with pagination."""
    print("Fetching mathematicians from Wikidata...")

    headers = {
        "User-Agent": "GMNAP/1.0 (mathematician-name-project; dylan@example.com)",
        "Accept": "application/json",
    }

    all_results = []
    offset = 0

    with httpx.Client(timeout=120) as client:
        while True:
            query = SPARQL_TEMPLATE.format(limit=BATCH_SIZE, offset=offset)
            print(f"  Fetching offset={offset}...")

            try:
                resp = client.get(
                    ENDPOINT,
                    params={"query": query, "format": "json"},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  Error at offset {offset}: {e}")
                break

            results = data.get("results", {}).get("bindings", [])
            if not results:
                break

            all_results.extend(results)
            print(f"  Got {len(results)} rows (total: {len(all_results)})")

            if len(results) < BATCH_SIZE:
                break

            offset += BATCH_SIZE
            time.sleep(2)  # Be polite to Wikidata

    results = all_results
    print(f"Raw results: {len(results)} rows")

    # Process results
    entries = []
    seen = set()

    for row in results:
        name = row.get("personLabel", {}).get("value", "")
        country_name = row.get("countryLabel", {}).get("value", "")
        country_uri = row.get("country", {}).get("value", "")

        if not name or not country_name:
            continue

        # Skip QID labels (unresolved entities)
        if name.startswith("Q") and name[1:].isdigit():
            continue
        if country_name.startswith("Q") and country_name[1:].isdigit():
            continue

        # Extract country QID from URI and map to CC
        country_qid = country_uri.split("/")[-1] if country_uri else ""
        cc = QID_TO_CC.get(country_qid)

        # Deduplicate by name+country
        name_key = (name.lower().strip(), country_name)
        if name_key in seen:
            continue
        seen.add(name_key)

        # Convert name to "Surname, Given" format
        canonical = _to_canonical(name)

        entry = {
            "CanonicalLatin": canonical,
            "WikidataName": name,
            "Country": country_name,
            "CountryCode": cc,
            "BirthYear": None,
        }

        entries.append(entry)

    print(f"Unique entries: {len(entries)}")
    return entries


def _to_canonical(name):
    """Convert 'Given Surname' to 'Surname, Given' format."""
    # Handle names with titles
    name = name.strip()

    # If already has comma, keep as-is
    if "," in name:
        return name

    parts = name.split()
    if len(parts) < 2:
        return name

    # Last part is surname for Western names
    surname = parts[-1]
    given = " ".join(parts[:-1])
    return f"{surname}, {given}"


def main():
    entries = fetch_wikidata()

    # Save
    out_path = Path("data/wikidata_mathematicians.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(entries)} entries to {out_path}")

    # Print country distribution
    from collections import Counter

    countries = Counter(e["Country"] for e in entries)
    print(f"\nTop 20 countries:")
    for country, count in countries.most_common(20):
        print(f"  {country}: {count}")


if __name__ == "__main__":
    main()
