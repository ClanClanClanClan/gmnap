from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp

from .base import BaseConnector

NS_OAI = "{http://www.openarchives.org/OAI/2.0/}"


class OaiPmhConnector(BaseConnector):
    async def records(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        if not self._tos_allowed():
            return
        base = self.cfg["base_url"]
        metadata_prefix = self.cfg.get("metadata_prefix", "oai_dc")
        set_spec = self.cfg.get("set")
        params = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
        if set_spec:
            params["set"] = set_spec
        if date_from:
            params["from"] = date_from
        if date_to:
            params["until"] = date_to

        async with aiohttp.ClientSession() as s:
            token = None
            while True:
                await self.rate.wait()
                p = (
                    {"verb": "ListRecords", "resumptionToken": token}
                    if token
                    else params
                )
                async with s.get(base, params=p, timeout=60) as r:
                    r.raise_for_status()
                    xml_txt = await r.text()
                    root = ET.fromstring(xml_txt)
                    for rec in root.iter(f"{NS_OAI}record"):
                        yield {"_raw_xml": ET.tostring(rec, encoding="unicode")}
                    token_elem = root.find(f".//{NS_OAI}resumptionToken")
                    token = (
                        token_elem.text
                        if token_elem is not None and token_elem.text
                        else None
                    )
                    if not token:
                        break

    def to_thesis(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": None,
            "degree_type": None,
            "discipline": "Mathematics",
            "author_name": None,
            "author_birth_year": None,
            "defense_date": None,
            "institution": None,
            "country": self.cfg.get("country"),
            "advisors": [],
            "committee": [],
            "pdf_url": None,
            "source_id": None,
            "source_name": self.cfg.get("country") + "_OAI",
            "raw": raw,
        }
