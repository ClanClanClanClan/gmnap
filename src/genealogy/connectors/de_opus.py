"""
genealogy/connectors/de_opus.py
OAI-PMH harvester for German OPUS repositories (mathematics dissertations).
Based on FR connector, adapted for German metadata.
"""

import asyncio, aiohttp, xml.etree.ElementTree as ET
from typing import AsyncIterator, Dict, Any

NS_OAI = "{http://www.openarchives.org/OAI/2.0/}"
NS_DC = "{http://purl.org/dc/elements/1.1/}"


class DeOpusOAI:
    def __init__(self, base_url: str, rate_limit: float = 1.0, set_spec: str = None):
        self.base_url = base_url
        self.sleep = 1.0 / max(rate_limit, 0.1)
        self.set_spec = set_spec  # e.g., mathematics set if available

    async def records(
        self, date_from: str = None, date_to: str = None
    ) -> AsyncIterator[Dict[str, Any]]:
        params = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
        if self.set_spec:
            params["set"] = self.set_spec
        if date_from:
            params["from"] = date_from
        if date_to:
            params["until"] = date_to
        token = None
        async with aiohttp.ClientSession() as s:
            while True:
                p = (
                    params
                    if not token
                    else {"verb": "ListRecords", "resumptionToken": token}
                )
                async with s.get(self.base_url, params=p) as r:
                    r.raise_for_status()
                    xml = await r.text()
                    root = ET.fromstring(xml)
                    for rec in root.iter(f"{NS_OAI}record"):
                        header = rec.find(f"{NS_OAI}header")
                        if header is None or header.get("status") == "deleted":
                            continue
                        meta = rec.find(f"{NS_OAI}metadata")
                        if meta is None:
                            continue
                        dc = meta.find(".//*")
                        if dc is None:
                            continue
                        yield {"raw": ET.tostring(dc, encoding="unicode")}
                    rt = root.find(f".//{NS_OAI}resumptionToken")
                    token = rt.text if rt is not None and rt.text else None
                    if not token:
                        break
                await asyncio.sleep(self.sleep)


def parse_dc(raw_xml: str) -> Dict[str, Any]:
    root = ET.fromstring(raw_xml)

    def first(tag):
        el = root.find(f"{NS_DC}{tag}")
        return el.text.strip() if el is not None and el.text else None

    def allv(tag):
        return [el.text.strip() for el in root.findall(f"{NS_DC}{tag}") if el.text]

    title = first("title")
    creators = allv("creator")
    date = first("date")
    publisher = first("publisher")

    # Extract advisors from dc:contributor fields
    # Pattern: Filter out institutions, keep person names
    contributors = allv("contributor")

    # German institution keywords
    institution_keywords = [
        "universität",
        "university",
        "institut",
        "institute",
        "hochschule",
        "technische",
        "fakultät",
        "fachbereich",
        "lehrstuhl",
        "school",
        "college",
        "akademie",
        "academy",
    ]

    # Filter out institutions, keep person names (likely advisors)
    advisors = []
    for c in contributors:
        is_institution = any(kw in c.lower() for kw in institution_keywords)
        if not is_institution:
            # Looks like a person name
            advisors.append(c)

    return {
        "title": title,
        "creators": creators,
        "date": date,
        "publisher": publisher,
        "advisors_text": advisors,
        "_raw_dc": raw_xml,
    }
