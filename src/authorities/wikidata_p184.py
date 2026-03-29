#!/usr/bin/env python3
"""
Wikidata P184 Authority Source
Fetches doctoral advisor relationships from Wikidata.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class WikidataAuthorityData:
    """Data from Wikidata authority source."""

    wikidata_id: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    doctoral_advisors: List[Dict[str, str]] = field(default_factory=list)
    doctoral_students: List[Dict[str, str]] = field(default_factory=list)
    field_of_work: List[str] = field(default_factory=list)
    institutions: List[Dict[str, Any]] = field(default_factory=list)
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    identifiers: Dict[str, str] = field(default_factory=dict)


class WikidataP184Fetcher:
    """
    Wikidata P184 (doctoral advisor) relationship fetcher.
    Implements V7 spec requirement for Wikidata_P184 authority source.
    """

    def __init__(self):
        """Initialize Wikidata fetcher."""
        self.endpoint = "https://query.wikidata.org/sparql"
        self.api_url = "https://www.wikidata.org/w/api.php"
        self.session = None
        self.cache = {}
        self.cache_ttl = timedelta(hours=24)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def search_by_name(self, name: str, limit: int = 5) -> List[Tuple[str, str]]:
        """
        Search Wikidata for entities by name.

        Args:
            name: Person's name to search
            limit: Maximum results to return

        Returns:
            List of (wikidata_id, label) tuples
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        params = {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "limit": limit,
            "format": "json",
        }

        try:
            async with self.session.get(self.api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []

                    for item in data.get("search", []):
                        # Filter to persons (check description)
                        desc = item.get("description", "").lower()
                        if any(
                            term in desc
                            for term in [
                                "mathematician",
                                "scientist",
                                "professor",
                                "researcher",
                                "academic",
                            ]
                        ):
                            results.append((item["id"], item["label"]))

                    return results
                else:
                    logger.warning(f"Wikidata search failed: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Wikidata search error: {e}")
            return []

    async def fetch_entity(self, wikidata_id: str) -> Optional[WikidataAuthorityData]:
        """
        Fetch Wikidata entity with P184 relationships.

        Args:
            wikidata_id: Wikidata Q-identifier

        Returns:
            Wikidata authority data
        """
        # Check cache
        cache_key = f"wikidata:{wikidata_id}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data

        if not self.session:
            self.session = aiohttp.ClientSession()

        # SPARQL query for P184 (doctoral advisor) and P185 (doctoral student)
        query = f"""
        SELECT ?item ?itemLabel ?itemDescription 
               ?advisor ?advisorLabel 
               ?student ?studentLabel
               ?field ?fieldLabel
               ?institution ?institutionLabel
               ?birthYear ?deathYear
               ?orcid ?isni ?viaf
        WHERE {{
          VALUES ?item {{ wd:{wikidata_id} }}
          
          OPTIONAL {{ ?item wdt:P184 ?advisor. }}
          OPTIONAL {{ ?item wdt:P185 ?student. }}
          OPTIONAL {{ ?item wdt:P101 ?field. }}
          OPTIONAL {{ ?item wdt:P108 ?institution. }}
          OPTIONAL {{ ?item wdt:P569 ?birthDate. BIND(YEAR(?birthDate) AS ?birthYear) }}
          OPTIONAL {{ ?item wdt:P570 ?deathDate. BIND(YEAR(?deathDate) AS ?deathYear) }}
          OPTIONAL {{ ?item wdt:P496 ?orcid. }}
          OPTIONAL {{ ?item wdt:P213 ?isni. }}
          OPTIONAL {{ ?item wdt:P214 ?viaf. }}
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "GMNAP/1.0 (https://github.com/gmnap)",
        }

        try:
            async with self.session.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                headers=headers,
            ) as response:
                if response.status != 200:
                    logger.warning(f"SPARQL query failed: {response.status}")
                    return None

                data = await response.json()

                # Parse results
                authority_data = WikidataAuthorityData(wikidata_id=wikidata_id)

                advisors = {}
                students = {}
                fields = set()
                institutions = {}

                for binding in data.get("results", {}).get("bindings", []):
                    # Basic info
                    if "itemLabel" in binding:
                        authority_data.label = binding["itemLabel"]["value"]
                    if "itemDescription" in binding:
                        authority_data.description = binding["itemDescription"]["value"]

                    # Advisors
                    if "advisor" in binding:
                        advisor_id = binding["advisor"]["value"].split("/")[-1]
                        advisor_label = binding.get("advisorLabel", {}).get(
                            "value", advisor_id
                        )
                        advisors[advisor_id] = advisor_label

                    # Students
                    if "student" in binding:
                        student_id = binding["student"]["value"].split("/")[-1]
                        student_label = binding.get("studentLabel", {}).get(
                            "value", student_id
                        )
                        students[student_id] = student_label

                    # Fields
                    if "fieldLabel" in binding:
                        fields.add(binding["fieldLabel"]["value"])

                    # Institutions
                    if "institution" in binding:
                        inst_id = binding["institution"]["value"].split("/")[-1]
                        inst_label = binding.get("institutionLabel", {}).get(
                            "value", inst_id
                        )
                        institutions[inst_id] = inst_label

                    # Dates
                    if "birthYear" in binding:
                        try:
                            authority_data.birth_year = int(
                                float(binding["birthYear"]["value"])
                            )
                        except:
                            pass
                    if "deathYear" in binding:
                        try:
                            authority_data.death_year = int(
                                float(binding["deathYear"]["value"])
                            )
                        except:
                            pass

                    # Identifiers
                    if "orcid" in binding:
                        authority_data.identifiers["ORCID"] = binding["orcid"]["value"]
                    if "isni" in binding:
                        authority_data.identifiers["ISNI"] = binding["isni"]["value"]
                    if "viaf" in binding:
                        authority_data.identifiers["VIAF"] = binding["viaf"]["value"]

                # Convert to lists
                authority_data.doctoral_advisors = [
                    {"id": k, "name": v} for k, v in advisors.items()
                ]
                authority_data.doctoral_students = [
                    {"id": k, "name": v} for k, v in students.items()
                ]
                authority_data.field_of_work = list(fields)
                authority_data.institutions = [
                    {"id": k, "name": v} for k, v in institutions.items()
                ]

                # Fetch aliases
                await self._fetch_aliases(wikidata_id, authority_data)

                # Cache result
                self.cache[cache_key] = (datetime.now(), authority_data)

                return authority_data

        except Exception as e:
            logger.error(f"Error fetching Wikidata entity {wikidata_id}: {e}")
            return None

    async def _fetch_aliases(
        self, wikidata_id: str, authority_data: WikidataAuthorityData
    ):
        """Fetch entity aliases/alternative names."""
        if not self.session:
            return

        params = {
            "action": "wbgetentities",
            "ids": wikidata_id,
            "props": "aliases",
            "languages": "en|de|fr|es|it|pt|ru|zh|ja|ko",
            "format": "json",
        }

        try:
            async with self.session.get(self.api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    entity = data.get("entities", {}).get(wikidata_id, {})

                    aliases = []
                    for lang, alias_list in entity.get("aliases", {}).items():
                        for alias_item in alias_list:
                            aliases.append(alias_item["value"])

                    authority_data.aliases = aliases

        except Exception as e:
            logger.error(f"Error fetching aliases for {wikidata_id}: {e}")

    async def fetch_advisor_network(
        self, wikidata_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """
        Fetch advisor network (genealogy tree) to specified depth.

        Args:
            wikidata_id: Starting entity
            depth: How many generations to traverse

        Returns:
            Network dictionary with nodes and edges
        """
        if depth <= 0:
            return {"nodes": [], "edges": []}

        nodes = {}
        edges = []
        to_process = [(wikidata_id, 0)]
        processed = set()

        while to_process:
            current_id, current_depth = to_process.pop(0)

            if current_id in processed or current_depth >= depth:
                continue

            processed.add(current_id)

            # Fetch entity
            entity = await self.fetch_entity(current_id)
            if entity:
                # Add node
                nodes[current_id] = {
                    "id": current_id,
                    "label": entity.label,
                    "depth": current_depth,
                    "birth_year": entity.birth_year,
                    "field": entity.field_of_work[0] if entity.field_of_work else None,
                }

                # Add advisor edges and queue for processing
                for advisor in entity.doctoral_advisors:
                    edges.append(
                        {
                            "source": advisor["id"],
                            "target": current_id,
                            "type": "advisor",
                        }
                    )
                    if current_depth + 1 < depth:
                        to_process.append((advisor["id"], current_depth + 1))

                # Add student edges and queue for processing
                for student in entity.doctoral_students:
                    edges.append(
                        {
                            "source": current_id,
                            "target": student["id"],
                            "type": "advisor",
                        }
                    )
                    if current_depth + 1 < depth:
                        to_process.append((student["id"], current_depth + 1))

        return {"nodes": list(nodes.values()), "edges": edges}

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an entry with Wikidata P184 data.

        Args:
            entry: Entry dictionary with name information

        Returns:
            Enriched entry with Wikidata advisor relationships
        """
        name = entry.get("CanonicalLatin", "")
        if not name:
            return entry

        # Search for Wikidata entities
        results = await self.search_by_name(name, limit=3)

        if not results:
            return entry

        # Try to find best match
        for wikidata_id, label in results:
            entity = await self.fetch_entity(wikidata_id)
            if entity:
                # Add Wikidata ID
                entry["WikidataID"] = wikidata_id

                # Add advisor relationships
                if entity.doctoral_advisors:
                    entry["Advisors"] = [
                        advisor["name"] for advisor in entity.doctoral_advisors
                    ]
                    entry["AdvisorIDs"] = [
                        advisor["id"] for advisor in entity.doctoral_advisors
                    ]

                # Add student relationships
                if entity.doctoral_students:
                    entry["Students"] = [
                        student["name"] for student in entity.doctoral_students
                    ]
                    entry["StudentIDs"] = [
                        student["id"] for student in entity.doctoral_students
                    ]

                # Add other identifiers
                if entity.identifiers:
                    for key, value in entity.identifiers.items():
                        entry[key] = value

                # Add birth/death years
                if entity.birth_year:
                    entry["BirthYear"] = entity.birth_year
                if entity.death_year:
                    entry["DeathYear"] = entity.death_year

                # Add fields
                if entity.field_of_work:
                    entry["FieldsOfWork"] = entity.field_of_work

                # Update authority sources
                if "AuthoritySources" not in entry:
                    entry["AuthoritySources"] = []
                entry["AuthoritySources"].append("Wikidata_P184")

                break

        return entry
