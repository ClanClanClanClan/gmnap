"""
GMNAP Phase 2 Genealogy Enrichment Module

Provides academic genealogy data integration for the main GMNAP V7 pipeline.
Supports two modes:
- API mode: REST API calls to Phase 2 service (default, production)
- Direct mode: Direct Bolt queries to Memgraph (high performance)

Usage:
    from src.genealogy.enrichment import GenealogyEnricher

    # API mode (default)
    enricher = GenealogyEnricher(mode='api', api_url='http://localhost:8080')
    lineage = enricher.get_lineage('GMN-ABC123', max_depth=10)

    # Direct mode (high performance)
    enricher = GenealogyEnricher(mode='direct', bolt_uri='bolt://localhost:7688')
    lineage = enricher.get_lineage('GMN-ABC123', max_depth=10)
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class GenealogyCache:
    """Simple in-memory cache for genealogy queries"""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, tuple] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Dict):
        self.cache[key] = (value, datetime.now())

    def clear(self):
        self.cache.clear()


class GenealogyEnricher:
    """
    Main class for enriching GMNAP records with academic genealogy data.

    Model 1.5: Supports both API and Direct modes for flexible deployment.
    """

    def __init__(
        self,
        mode: str = "api",
        api_url: Optional[str] = None,
        bolt_uri: Optional[str] = None,
        bolt_user: Optional[str] = None,
        bolt_pass: Optional[str] = None,
        cache_ttl: int = 3600,
        timeout: int = 10,
    ):
        """
        Initialize the genealogy enricher.

        Args:
            mode: 'api' or 'direct'
            api_url: URL for Phase 2 API (default: http://localhost:8080)
            bolt_uri: Bolt URI for direct mode (default: bolt://localhost:7688)
            bolt_user: Bolt username (optional)
            bolt_pass: Bolt password (optional)
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
            timeout: Request timeout in seconds (default: 10)
        """
        self.mode = mode.lower()
        if self.mode not in ["api", "direct"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'api' or 'direct'")

        self.timeout = timeout
        self.cache = GenealogyCache(ttl_seconds=cache_ttl)

        if self.mode == "api":
            self.api_url = api_url or os.environ.get(
                "GENEALOGY_API_URL", "http://localhost:8080"
            )
            logger.info(f"GenealogyEnricher initialized in API mode: {self.api_url}")
            self.driver = None

        else:  # direct mode
            uri = bolt_uri or os.environ.get(
                "GENEALOGY_BOLT_URI", "bolt://localhost:7688"
            )
            user = bolt_user or os.environ.get("GENEALOGY_BOLT_USER", "")
            password = bolt_pass or os.environ.get("GENEALOGY_BOLT_PASS", "")

            auth = (user, password) if user else None
            self.driver = GraphDatabase.driver(uri, auth=auth)
            logger.info(f"GenealogyEnricher initialized in Direct mode: {uri}")

    def get_lineage(
        self, global_id: str, max_depth: int = 10, use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get academic lineage (advisor chain) for a mathematician.

        Args:
            global_id: GMNAP GlobalID (e.g., 'GMN-ABC123...')
            max_depth: Maximum depth to traverse (default: 10)
            use_cache: Whether to use cache (default: True)

        Returns:
            Dict with structure:
            {
                'start': 'GMN-ABC123',
                'depth': 10,
                'paths': [
                    {
                        'length': 3,
                        'nodes': ['GMN-ABC123', 'GMN-DEF456', 'GMN-GHI789', 'GMN-JKL012']
                    },
                    ...
                ]
            }

            Returns None on error or if not found.
        """
        cache_key = f"{global_id}:{max_depth}"

        # Check cache
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {global_id}")
                return cached

        # Fetch data
        try:
            if self.mode == "api":
                result = self._fetch_via_api(global_id, max_depth)
            else:
                result = self._fetch_via_bolt(global_id, max_depth)

            # Cache result
            if result and use_cache:
                self.cache.set(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Error fetching lineage for {global_id}: {e}")
            return None

    def _fetch_via_api(self, global_id: str, max_depth: int) -> Optional[Dict]:
        """Fetch lineage via REST API"""
        url = f"{self.api_url}/genealogy/lineage/{global_id}"
        params = {"max_depth": max_depth}

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.warning(f"API request failed for {global_id}: {e}")
            return None

    def _fetch_via_bolt(self, global_id: str, max_depth: int) -> Optional[Dict]:
        """Fetch lineage via direct Bolt query"""
        if not self.driver:
            logger.error("Direct mode selected but no driver initialized")
            return None

        query = f"""
            MATCH (s)
            WHERE s.global_id = $id
            WITH s
            MATCH p=(s)-[:DOCTORAL_ADVISOR*..{max_depth}]->(a)
            RETURN length(p) as path_length, [n in nodes(p) | n.global_id] as path_nodes
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, id=global_id)

                paths = []
                for record in result:
                    paths.append(
                        {"length": record["path_length"], "nodes": record["path_nodes"]}
                    )

                if not paths:
                    return None

                return {"start": global_id, "depth": max_depth, "paths": paths}

        except Exception as e:
            logger.error(f"Bolt query failed for {global_id}: {e}")
            return None

    def get_advisor_count(self, global_id: str) -> int:
        """
        Get count of known advisors for a mathematician.

        Args:
            global_id: GMNAP GlobalID

        Returns:
            Number of direct advisors (0 if none or error)
        """
        lineage = self.get_lineage(global_id, max_depth=1)
        if not lineage or not lineage.get("paths"):
            return 0

        # Count unique advisors at depth 1
        advisors = set()
        for path in lineage["paths"]:
            if path["length"] == 1 and len(path["nodes"]) >= 2:
                advisors.add(path["nodes"][1])

        return len(advisors)

    def has_genealogy_data(self, global_id: str) -> bool:
        """
        Check if genealogy data exists for a mathematician.

        Args:
            global_id: GMNAP GlobalID

        Returns:
            True if any genealogy data exists, False otherwise
        """
        return self.get_advisor_count(global_id) > 0

    def close(self):
        """Close connections and clean up resources"""
        if self.driver:
            self.driver.close()
            logger.info("Genealogy enricher driver closed")
        self.cache.clear()


# Convenience function for quick usage
def get_lineage(
    global_id: str, max_depth: int = 10, mode: str = "api"
) -> Optional[Dict]:
    """
    Convenience function to get lineage without managing enricher instance.

    Args:
        global_id: GMNAP GlobalID
        max_depth: Maximum depth to traverse
        mode: 'api' or 'direct'

    Returns:
        Lineage dict or None
    """
    enricher = GenealogyEnricher(mode=mode)
    try:
        return enricher.get_lineage(global_id, max_depth)
    finally:
        enricher.close()


if __name__ == "__main__":
    # Example usage and testing
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python enrichment.py <global_id> [max_depth] [mode]")
        print("Example: python enrichment.py GMN-ABC123 10 api")
        sys.exit(1)

    global_id = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    mode = sys.argv[3] if len(sys.argv) > 3 else "api"

    print(f"\nFetching lineage for {global_id} (depth={max_depth}, mode={mode})")
    print("=" * 70)

    enricher = GenealogyEnricher(mode=mode)
    try:
        lineage = enricher.get_lineage(global_id, max_depth)

        if lineage:
            print(f"\n✅ Found {len(lineage['paths'])} genealogy path(s):\n")
            for i, path in enumerate(lineage["paths"], 1):
                print(f"Path {i} (length {path['length']}):")
                print(f"  {' → '.join(path['nodes'])}\n")
        else:
            print("❌ No genealogy data found")

    finally:
        enricher.close()
