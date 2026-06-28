#!/usr/bin/env python3
"""
GMNAP V7 Memgraph Integration
Provides graph database operations for Stage 6 Graph Consistency
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a mathematician node in the graph"""

    global_id: str
    canonical_latin: str
    canonical_native: Optional[str] = None
    region_code: Optional[str] = None
    external_ids: Dict[str, str] = None

    def to_cypher_props(self) -> Dict[str, Any]:
        """Convert to Cypher properties"""
        props = {"global_id": self.global_id, "canonical_latin": self.canonical_latin}
        if self.canonical_native:
            props["canonical_native"] = self.canonical_native
        if self.region_code:
            props["region_code"] = self.region_code
        if self.external_ids:
            props["external_ids"] = json.dumps(self.external_ids)
        return props


class MemgraphIntegrationClient:
    """
    Memgraph client for V7 graph operations
    Implements Stage 6: Graph Consistency requirements
    """

    def __init__(
        self, uri: str = "bolt://localhost:7687", user: str = None, password: str = None
    ):
        """
        Initialize Memgraph connection

        Args:
            uri: Bolt protocol URI
            user: Optional username
            password: Optional password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Establish connection to Memgraph"""
        try:
            if self.user and self.password:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
            else:
                self._driver = AsyncGraphDatabase.driver(self.uri)

            # Test connection
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                test = await result.single()
                if test["test"] == 1:
                    logger.info(f"Connected to Memgraph at {self.uri}")
                    return True
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise

    async def disconnect(self):
        """Close Memgraph connection"""
        if self._driver:
            await self._driver.close()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def create_schema(self):
        """Create graph schema and indexes"""
        async with self._driver.session() as session:
            # Create indexes for performance
            queries = [
                "CREATE INDEX ON :Mathematician(global_id);",
                "CREATE INDEX ON :Mathematician(canonical_latin);",
                "CREATE INDEX ON :Mathematician(region_code);",
                "CREATE INDEX ON :Institution(name);",
                "CREATE INDEX ON :Subject(name);",
            ]

            for query in queries:
                try:
                    await session.run(query)
                    logger.info(f"Created index: {query}")
                except Exception as e:
                    # Index might already exist
                    logger.debug(f"Index creation skipped: {e}")

    async def upsert_mathematician(self, node: GraphNode) -> bool:
        """
        Insert or update a mathematician node

        Args:
            node: GraphNode object

        Returns:
            Success status
        """
        async with self._driver.session() as session:
            query = """
            MERGE (m:Mathematician {global_id: $global_id})
            SET m += $properties
            RETURN m
            """

            try:
                result = await session.run(
                    query, global_id=node.global_id, properties=node.to_cypher_props()
                )
                record = await result.single()
                return record is not None
            except Exception as e:
                logger.error(f"Failed to upsert mathematician {node.global_id}: {e}")
                return False

    async def batch_upsert(self, nodes: List[GraphNode]) -> Tuple[int, int]:
        """
        Batch insert/update mathematician nodes

        Args:
            nodes: List of GraphNode objects

        Returns:
            Tuple of (successful, failed) counts
        """
        success = 0
        failed = 0

        async with self._driver.session() as session:
            for node in nodes:
                query = """
                MERGE (m:Mathematician {global_id: $global_id})
                SET m += $properties
                """

                try:
                    await session.run(
                        query,
                        global_id=node.global_id,
                        properties=node.to_cypher_props(),
                    )
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to upsert {node.global_id}: {e}")
                    failed += 1

        logger.info(f"Batch upsert: {success} successful, {failed} failed")
        return success, failed

    async def create_coauthor_relationship(
        self, source_id: str, target_id: str, properties: Dict[str, Any] = None
    ) -> bool:
        """
        Create a coauthor relationship between two mathematicians

        Args:
            source_id: Source mathematician GlobalID
            target_id: Target mathematician GlobalID
            properties: Relationship properties (e.g., paper_count, years)

        Returns:
            Success status
        """
        async with self._driver.session() as session:
            query = """
            MATCH (a:Mathematician {global_id: $source_id})
            MATCH (b:Mathematician {global_id: $target_id})
            MERGE (a)-[r:COAUTHOR]-(b)
            SET r += $properties
            RETURN r
            """

            try:
                props = properties or {}
                result = await session.run(
                    query, source_id=source_id, target_id=target_id, properties=props
                )
                record = await result.single()
                return record is not None
            except Exception as e:
                logger.error(f"Failed to create coauthor relationship: {e}")
                return False

    async def find_duplicates(
        self, threshold: float = 0.95
    ) -> List[Tuple[str, str, float]]:
        """
        Find potential duplicate entries using graph analysis

        Args:
            threshold: Similarity threshold for duplicate detection

        Returns:
            List of (id1, id2, similarity_score) tuples
        """
        async with self._driver.session() as session:
            # Use Memgraph's graph algorithms for duplicate detection
            query = """
            MATCH (a:Mathematician), (b:Mathematician)
            WHERE a.global_id < b.global_id
            AND (
                a.canonical_latin = b.canonical_latin
                OR similarity(a.canonical_latin, b.canonical_latin) > $threshold
            )
            RETURN a.global_id as id1, b.global_id as id2, 
                   similarity(a.canonical_latin, b.canonical_latin) as score
            ORDER BY score DESC
            LIMIT 100
            """

            duplicates = []
            try:
                result = await session.run(query, threshold=threshold)
                async for record in result:
                    duplicates.append((record["id1"], record["id2"], record["score"]))
            except Exception as e:
                logger.error(f"Failed to find duplicates: {e}")

            return duplicates

    async def calculate_consistency_metrics(self) -> Dict[str, Any]:
        """
        Calculate graph consistency metrics for Stage 6

        Returns:
            Dictionary of consistency metrics
        """
        metrics = {
            "total_nodes": 0,
            "total_edges": 0,
            "isolated_nodes": 0,
            "duplicate_candidates": 0,
            "avg_degree": 0.0,
            "max_degree": 0,
            "components": 0,
        }

        async with self._driver.session() as session:
            try:
                # Count nodes
                result = await session.run(
                    "MATCH (n:Mathematician) RETURN count(n) as count"
                )
                record = await result.single()
                metrics["total_nodes"] = record["count"]

                # Count edges
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                record = await result.single()
                metrics["total_edges"] = record["count"]

                # Find isolated nodes
                result = await session.run("""
                    MATCH (n:Mathematician)
                    WHERE NOT (n)-[]-()
                    RETURN count(n) as count
                """)
                record = await result.single()
                metrics["isolated_nodes"] = record["count"]

                # Calculate average degree
                if metrics["total_nodes"] > 0:
                    metrics["avg_degree"] = (2 * metrics["total_edges"]) / metrics[
                        "total_nodes"
                    ]

                # Find max degree
                result = await session.run("""
                    MATCH (n:Mathematician)
                    RETURN n.global_id as id, size((n)-[]-()) as degree
                    ORDER BY degree DESC
                    LIMIT 1
                """)
                record = await result.single()
                if record:
                    metrics["max_degree"] = record["degree"]

            except Exception as e:
                logger.error(f"Failed to calculate metrics: {e}")

        return metrics

    async def run_consistency_checks(
        self, batch: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run Stage 6 consistency checks on a batch

        Args:
            batch: List of entry dictionaries

        Returns:
            Consistency check results
        """
        results = {
            "entries_processed": len(batch),
            "nodes_created": 0,
            "relationships_created": 0,
            "duplicates_found": 0,
            "consistency_score": 0.0,
            "errors": [],
        }

        # Convert batch to graph nodes
        nodes = []
        for entry in batch:
            try:
                node = GraphNode(
                    global_id=entry.get("GlobalID"),
                    canonical_latin=entry.get("CanonicalLatin"),
                    canonical_native=entry.get("CanonicalNative"),
                    region_code=entry.get("RegionCode"),
                    external_ids=entry.get("ExternalIDs", {}),
                )
                nodes.append(node)
            except Exception as e:
                results["errors"].append(f"Failed to create node: {e}")

        # Batch upsert nodes
        if nodes:
            success, failed = await self.batch_upsert(nodes)
            results["nodes_created"] = success

        # Find duplicates
        duplicates = await self.find_duplicates()
        results["duplicates_found"] = len(duplicates)

        # Calculate consistency score
        metrics = await self.calculate_consistency_metrics()
        if metrics["total_nodes"] > 0:
            # Simple consistency score based on isolated nodes and duplicates
            isolated_ratio = metrics["isolated_nodes"] / metrics["total_nodes"]
            duplicate_ratio = results["duplicates_found"] / metrics["total_nodes"]
            results["consistency_score"] = max(
                0, 1.0 - isolated_ratio - duplicate_ratio
            )

        results["graph_metrics"] = metrics

        return results


# Stage 6 Integration Function
async def stage6_graph_consistency(
    batch: List[Dict[str, Any]], memgraph_uri: str = "bolt://localhost:7687"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Stage 6: Graph Consistency
    Process batch through Memgraph for consistency checking

    Args:
        batch: List of entries
        memgraph_uri: Memgraph connection URI

    Returns:
        Tuple of (processed_batch, metrics)
    """
    metrics = {"stage": 6, "entries_processed": len(batch), "graph_operations": {}}

    try:
        async with MemgraphIntegrationClient(memgraph_uri) as client:
            # Ensure schema exists
            await client.create_schema()

            # Run consistency checks
            results = await client.run_consistency_checks(batch)
            metrics["graph_operations"] = results

            # Mark entries with consistency issues
            if results["duplicates_found"] > 0:
                duplicates = await client.find_duplicates()
                duplicate_ids = set()
                for id1, id2, score in duplicates:
                    duplicate_ids.add(id1)
                    duplicate_ids.add(id2)

                for entry in batch:
                    if entry.get("GlobalID") in duplicate_ids:
                        entry["_consistency_warning"] = "potential_duplicate"

            logger.info(
                f"Stage 6 completed: {results['nodes_created']} nodes, "
                f"{results['duplicates_found']} duplicates, "
                f"consistency score: {results['consistency_score']:.2f}"
            )

    except Exception as e:
        logger.error(f"Stage 6 failed: {e}")
        metrics["error"] = str(e)
        # Fall back to pass-through

    return batch, metrics


# Test function
async def test_memgraph_connection():
    """Test Memgraph connectivity and basic operations"""
    print("Testing Memgraph connection...")

    try:
        async with MemgraphIntegrationClient() as client:
            print("✓ Connected to Memgraph")

            # Create test node
            test_node = GraphNode(
                global_id="test-memgraph-001",
                canonical_latin="Test, Mathematician",
                region_code="A1",
            )

            success = await client.upsert_mathematician(test_node)
            if success:
                print("✓ Created test node")

            # Get metrics
            metrics = await client.calculate_consistency_metrics()
            print(f"✓ Graph metrics: {json.dumps(metrics, indent=2)}")

            return True

    except Exception as e:
        print(f"✗ Memgraph test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test
    asyncio.run(test_memgraph_connection())
