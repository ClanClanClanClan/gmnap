#!/usr/bin/env python3
"""BDTD (Brazil theses) scoping probe — RUN FROM A NON-BLOCKED IP (e.g. ETH).

From datacenter/cloud IPs bdtd.ibict.br returns HTTP 429 on everything; from a
residential/university IP it should work. This answers, in one polite run, the
three questions we need before building a harvester:

  1. VOLUME  — how many mathematics theses are in BDTD?
  2. ADVISOR — does the OAI-PMH expose a metadata format (mtd3-br / oai_dc)
               that carries the advisor (orientador) as a real field?
  3. LICENSE — what are the metadata reuse terms (the Diretrizes page)?

It is deliberately gentle: descriptive User-Agent, 4 s between requests,
exponential backoff on 429, and it stops early. Only ~8 requests total.

Usage:   python3 probe_bdtd.py
Needs:   pip install httpx   (nothing else; no repo imports)

Paste the whole printed REPORT back to Claude.
"""

import sys
import time
import xml.etree.ElementTree as ET

import httpx

UA = {
    "User-Agent": "GMNAP-scoping/1.0 (academic mathematician-genealogy "
    "research; dylan.possamai@math.ethz.ch)"
}
OAI = "https://bdtd.ibict.br/vufind/OAI/Server"
API = "https://bdtd.ibict.br/vufind/api/v1/search"
NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def get(client, url, params, label, tries=4):
    """Polite GET with 429-aware exponential backoff."""
    for a in range(tries):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429:
                wait = 10 * (a + 1)
                print(f"  [{label}] 429 — backing off {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            print(f"  [{label}] attempt {a+1}: {exc}", file=sys.stderr)
            time.sleep(5 * (a + 1))
    return None


def main():
    print("=" * 70)
    print("BDTD SCOPING PROBE — paste this whole report back to Claude")
    print("=" * 70)
    with httpx.Client(timeout=60, headers=UA, follow_redirects=True) as c:
        # 1. OAI Identify
        r = get(c, OAI, {"verb": "Identify"}, "Identify")
        if r is None:
            print("\nFATAL: could not reach the OAI server even from here.")
            print("Is bdtd.ibict.br reachable in a browser right now?")
            return
        root = ET.fromstring(r.text)
        name = root.findtext(".//oai:repositoryName", default="?", namespaces=NS)
        print(f"\n[1] OAI repositoryName: {name}")
        time.sleep(4)

        # 2. metadata formats — does mtd3-br (advisor-bearing) exist?
        r = get(c, OAI, {"verb": "ListMetadataFormats"}, "Formats")
        fmts = []
        if r is not None:
            root = ET.fromstring(r.text)
            fmts = [
                e.text
                for e in root.findall(".//oai:metadataPrefix", namespaces=NS)
            ]
        print(f"[2] OAI metadataPrefixes: {fmts}")
        print("    (want mtd3-br / mtd-br / etd_ms — those carry the advisor)")
        time.sleep(4)

        # 3. sets — is there a subject/math set, or only institutional?
        r = get(c, OAI, {"verb": "ListSets"}, "Sets")
        setspecs = []
        if r is not None:
            root = ET.fromstring(r.text)
            setspecs = [
                (
                    s.findtext("oai:setSpec", default="", namespaces=NS),
                    s.findtext("oai:setName", default="", namespaces=NS),
                )
                for s in root.findall(".//oai:set", namespaces=NS)
            ]
        math_sets = [s for s in setspecs if "matem" in (s[1] or "").lower()]
        print(f"[3] OAI sets: {len(setspecs)} total; math-named: {math_sets[:5]}")
        time.sleep(4)

        # 4. VuFind API — math thesis COUNT (the volume number we need)
        r = get(
            c,
            API,
            {"lookfor": "matemática", "type": "Subject", "limit": 1},
            "Count",
        )
        if r is not None and "json" in r.headers.get("content-type", ""):
            d = r.json()
            print(f"[4] VuFind resultCount (Subject=matemática): {d.get('resultCount')}")
        else:
            print("[4] VuFind API count: unavailable (see stderr)")
        time.sleep(4)

        # 5. a real record in the richest format — SHOW the advisor field
        prefix = (
            "mtd3-br"
            if "mtd3-br" in fmts
            else ("mtd-br" if "mtd-br" in fmts else "oai_dc")
        )
        r = get(
            c,
            OAI,
            {"verb": "ListRecords", "metadataPrefix": prefix},
            f"Record({prefix})",
        )
        if r is not None:
            print(f"[5] first record in '{prefix}' — RAW metadata (look for the")
            print("    advisor: 'orientador', contributor role='advisor', etc.):")
            root = ET.fromstring(r.text)
            rec = root.find(".//oai:record", namespaces=NS)
            if rec is not None:
                meta = rec.find(".//oai:metadata", namespaces=NS)
                raw = ET.tostring(meta, encoding="unicode") if meta is not None else ""
                print("    " + raw[:1600].replace("\n", "\n    "))
        time.sleep(4)

        # 6. LICENSE — the Diretrizes/terms page (grep for licence words)
        for path in ("/vufind/Diretrizes/Home", "/vufind/Content/direitos"):
            rr = get(c, "https://bdtd.ibict.br" + path, {}, "License")
            if rr is not None and rr.status_code == 200:
                txt = rr.text.lower()
                hits = [
                    w
                    for w in (
                        "licença",
                        "creative commons",
                        "cc0",
                        "cc by",
                        "domínio público",
                        "reuso",
                        "direitos",
                        "metadados",
                        "livre",
                    )
                    if w in txt
                ]
                print(f"\n[6] {path}: license keywords present: {hits}")
                # print a small window around 'licen' if found
                i = txt.find("licen")
                if i > 0:
                    print("    ..." + rr.text[i - 40 : i + 220].replace("\n", " "))
                break
    print("\n" + "=" * 70)
    print("END OF REPORT — copy everything above back to Claude.")
    print("=" * 70)


if __name__ == "__main__":
    main()
