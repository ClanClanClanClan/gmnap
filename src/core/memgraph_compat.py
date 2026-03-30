"""
Memgraph-compatible client for GMNAP V7 academic genealogy features.
Fixes Neo4j vs Memgraph syntax incompatibilities.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import neo4j
    from neo4j import GraphDatabase

    MEMGRAPH_AVAILABLE = True
except ImportError:
    MEMGRAPH_AVAILABLE = False
    GraphDatabase = None

# Try to import NetworkX as fallback
try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

logger = logging.getLogger(__name__)


@dataclass
class GenealogyRelation:
    """Academic genealogy relationship between mathematicians."""

    source_id: str
    target_id: str
    relation_type: str  # doctoralAdvisor, adviserCommitteeMember, postdocMentor, habilitationAdvisor
    qualifier: Optional[str] = None
    confidence: float = 1.0
    source: str = "GMNAP"
    year: Optional[int] = None


@dataclass
class GraphMetrics:
    """Graph consistency metrics for V7 quality gates."""

    total_mathematicians: int = 0
    total_relationships: int = 0
    coherence_score: float = 0.0
    betweenness_scores: Dict[str, float] = None
    cycle_count: int = 0
    edge_conflicts: int = 0
    last_updated: datetime = None

    def __post_init__(self):
        if self.betweenness_scores is None:
            self.betweenness_scores = {}
        if self.last_updated is None:
            self.last_updated = datetime.now()


class MemgraphCompatibleClient:
    """
    Memgraph-compatible client with fallback to NetworkX.

    Fixes syntax differences between Neo4j and Memgraph:
    - Uses localDateTime() instead of datetime()
    - Handles Memgraph-specific query optimizations
    - Falls back to NetworkX when Memgraph is unavailable
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 7687,
        username: str = "",  # Memgraph default: no auth
        password: str = "",  # Memgraph default: no auth
        use_mock: bool = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.driver = None
        self.connected = False
        self.use_mock = use_mock

        # NetworkX fallback graph
        self.nx_graph = None
        self.nx_data = {}

        # Override with environment variables if available
        self.host = os.getenv("MEMGRAPH_HOST", self.host)
        self.port = int(os.getenv("MEMGRAPH_PORT", self.port))
        self.username = os.getenv("MEMGRAPH_USER", self.username)
        self.password = os.getenv("MEMGRAPH_PASSWORD", self.password)

        # Determine if we should use mock
        if self.use_mock is None:
            self.use_mock = os.getenv("USE_MOCK_MEMGRAPH", "false").lower() == "true"

        if self.use_mock:
            logger.info("Using NetworkX mock for Memgraph")
            self._init_mock()
        elif not MEMGRAPH_AVAILABLE:
            logger.warning("Memgraph client not available - using NetworkX fallback")
            self._init_mock()
        else:
            self._connect()

    def _init_mock(self):
        """Initialize NetworkX fallback."""
        if NETWORKX_AVAILABLE:
            self.nx_graph = nx.DiGraph()
            self.connected = True
            logger.info("Initialized NetworkX fallback for Memgraph")
        else:
            logger.error("Neither Memgraph nor NetworkX available")
            self.connected = False

    def _connect(self) -> bool:
        """Connect to Memgraph database."""
        if not MEMGRAPH_AVAILABLE:
            self._init_mock()
            return self.connected

        try:
            uri = f"bolt://{self.host}:{self.port}"

            # Memgraph typically doesn't require authentication
            if self.username and self.password:
                auth = (self.username, self.password)
            else:
                auth = None

            self.driver = GraphDatabase.driver(
                uri,
                auth=auth,
                encrypted=False,  # Memgraph typically doesn't use TLS in development
            )

            # Test connection with Memgraph-compatible query
            with self.driver.session() as session:
                result = session.run("RETURN 'test' AS test")
                if result.single():
                    self.connected = True
                    logger.info(f"Connected to Memgraph at {uri}")
                    return True

        except Exception as e:
            logger.warning(
                f"Failed to connect to Memgraph, using NetworkX fallback: {e}"
            )
            self._init_mock()

        return self.connected

    def close(self):
        """Close connection to Memgraph."""
        if self.driver:
            self.driver.close()
            self.connected = False

    def is_connected(self) -> bool:
        """Check if connected to Memgraph or mock."""
        return self.connected

    def create_mathematician(self, entry: Dict[str, Any]) -> bool:
        """
        Create or update mathematician node in graph.

        Args:
            entry: Mathematician entry from V7 pipeline
        """
        if not self.is_connected():
            logger.warning("Graph not connected - skipping mathematician creation")
            return False

        # NetworkX fallback
        if self.nx_graph is not None:
            global_id = entry.get("GlobalID", "")
            self.nx_graph.add_node(global_id, **entry)
            self.nx_data[global_id] = entry
            return True

        # Memgraph query (compatible syntax)
        try:
            with self.driver.session() as session:
                # Use localDateTime() for Memgraph instead of datetime()
                query = """
                MERGE (m:Mathematician {global_id: $global_id})
                SET m.canonical_latin = $canonical_latin,
                    m.canonical_native = $canonical_native,
                    m.birth_year = $birth_year,
                    m.death_year = $death_year,
                    m.region = $region,
                    m.confidence = $confidence,
                    m.msc_primary = $msc_primary,
                    m.updated_at = localDateTime(),
                    m.gdpr_data = $gdpr_data
                RETURN m.global_id as id
                """

                result = session.run(
                    query,
                    global_id=entry.get("GlobalID", ""),
                    canonical_latin=entry.get("CanonicalLatin", ""),
                    canonical_native=entry.get("CanonicalNative", ""),
                    birth_year=entry.get("BirthYear"),
                    death_year=entry.get("DeathYear"),
                    region=entry.get("DetectedRegion", ""),
                    confidence=entry.get("DetectionConfidence", 0.0),
                    msc_primary=entry.get("MSC", {}).get("primary", ""),
                    gdpr_data=entry.get("GDPR_DATA", False),
                )

                record = result.single()
                if record:
                    logger.debug(f"Created/updated mathematician: {record['id']}")
                    return True

        except Exception as e:
            logger.error(f"Failed to create mathematician: {e}")

        return False

    def add_genealogy_relation(self, relation: GenealogyRelation) -> bool:
        """
        Add academic genealogy relationship between mathematicians.

        Args:
            relation: Genealogy relationship to add
        """
        if not self.is_connected():
            return False

        # NetworkX fallback
        if self.nx_graph is not None:
            self.nx_graph.add_edge(
                relation.source_id,
                relation.target_id,
                relation_type=relation.relation_type,
                confidence=relation.confidence,
                year=relation.year,
                qualifier=relation.qualifier,
                source=relation.source,
            )
            return True

        # Memgraph query
        try:
            with self.driver.session() as session:
                query = """
                MATCH (source:Mathematician {global_id: $source_id})
                MATCH (target:Mathematician {global_id: $target_id})
                MERGE (source)-[r:DOCTORAL_ADVISOR {
                    relation_type: $relation_type,
                    confidence: $confidence,
                    source: $source,
                    year: $year,
                    qualifier: $qualifier
                }]->(target)
                RETURN r
                """

                result = session.run(
                    query,
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    source=relation.source,
                    year=relation.year,
                    qualifier=relation.qualifier,
                )

                if result.single():
                    logger.debug(
                        f"Added relation: {relation.source_id} -> {relation.target_id}"
                    )
                    return True

        except Exception as e:
            logger.error(f"Failed to add genealogy relation: {e}")

        return False

    def calculate_betweenness_centrality(self) -> Dict[str, float]:
        """
        Calculate betweenness centrality for all mathematicians.

        Returns:
            Dictionary mapping GlobalID to betweenness centrality score
        """
        if not self.is_connected():
            return {}

        # NetworkX fallback
        if self.nx_graph is not None:
            if len(self.nx_graph.nodes) > 0:
                return nx.betweenness_centrality(self.nx_graph)
            return {}

        # Memgraph query (optimized for Memgraph)
        try:
            with self.driver.session() as session:
                # First check if Memgraph has the betweenness centrality algorithm
                try:
                    # Try Memgraph's MAGE algorithm if available
                    query = """
                    CALL mg.betweenness_centrality()
                    YIELD node, betweenness
                    RETURN node.global_id as id, betweenness as score
                    """
                    result = session.run(query)
                    scores = {}
                    for record in result:
                        scores[record["id"]] = record["score"]
                    if scores:
                        return scores
                except Exception:
                    # Fall back to approximation
                    pass

                # Simple betweenness approximation
                query = """
                MATCH (m:Mathematician)
                OPTIONAL MATCH (m)-[r:DOCTORAL_ADVISOR]->()
                WITH m, count(r) as out_degree
                OPTIONAL MATCH ()-[r2:DOCTORAL_ADVISOR]->(m)
                WITH m, out_degree, count(r2) as in_degree
                WITH m, (out_degree + in_degree) as total_degree
                MATCH (all:Mathematician)
                WITH m, total_degree, count(all) as total_nodes
                SET m.betweenness_score = toFloat(total_degree) / toFloat(total_nodes + 1)
                RETURN m.global_id as id, m.betweenness_score as score
                """

                result = session.run(query)
                scores = {}

                for record in result:
                    scores[record["id"]] = record["score"]

                return scores

        except Exception as e:
            logger.error(f"Failed to calculate betweenness centrality: {e}")
            return {}

    def detect_cycles(self, max_length: int = 3) -> List[List[str]]:
        """
        Detect cycles in the genealogy graph.

        Args:
            max_length: Maximum cycle length to detect (default 3)

        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        if not self.is_connected():
            return []

        # NetworkX fallback
        if self.nx_graph is not None:
            try:
                cycles = list(nx.simple_cycles(self.nx_graph))
                return [c for c in cycles if len(c) <= max_length]
            except Exception:
                return []

        # Memgraph query
        try:
            with self.driver.session() as session:
                # Detect short cycles
                query = f"""
                MATCH path=(m:Mathematician)-[:DOCTORAL_ADVISOR*1..{max_length}]->(m)
                RETURN [n in nodes(path) | n.global_id] as cycle
                """

                result = session.run(query)
                cycles = []

                for record in result:
                    cycle = record["cycle"]
                    if cycle and len(cycle) <= max_length + 1:
                        cycles.append(cycle)

                return cycles

        except Exception as e:
            logger.error(f"Failed to detect cycles: {e}")
            return []

    def get_graph_metrics(self) -> GraphMetrics:
        """
        Get comprehensive graph metrics for quality gates.

        Returns:
            GraphMetrics object with current statistics
        """
        metrics = GraphMetrics()

        if not self.is_connected():
            return metrics

        # NetworkX fallback
        if self.nx_graph is not None:
            metrics.total_mathematicians = self.nx_graph.number_of_nodes()
            metrics.total_relationships = self.nx_graph.number_of_edges()

            if metrics.total_mathematicians > 0:
                metrics.betweenness_scores = self.calculate_betweenness_centrality()
                metrics.coherence_score = min(
                    1.0,
                    metrics.total_relationships / (metrics.total_mathematicians * 2),
                )
                cycles = self.detect_cycles()
                metrics.cycle_count = len(cycles)

            return metrics

        # Memgraph query
        try:
            with self.driver.session() as session:
                # Count mathematicians
                result = session.run("MATCH (m:Mathematician) RETURN count(m) as count")
                record = result.single()
                if record:
                    metrics.total_mathematicians = record["count"]

                # Count relationships
                result = session.run(
                    "MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) as count"
                )
                record = result.single()
                if record:
                    metrics.total_relationships = record["count"]

                # Calculate coherence score
                if metrics.total_mathematicians > 0:
                    metrics.coherence_score = min(
                        1.0,
                        metrics.total_relationships
                        / (metrics.total_mathematicians * 2),
                    )

                # Get betweenness scores
                metrics.betweenness_scores = self.calculate_betweenness_centrality()

                # Detect cycles
                cycles = self.detect_cycles()
                metrics.cycle_count = len(cycles)

                # Check for edge conflicts (simplified)
                query = """
                MATCH (a)-[r1:DOCTORAL_ADVISOR]->(b)
                MATCH (a)-[r2:DOCTORAL_ADVISOR]->(b)
                WHERE id(r1) < id(r2)
                RETURN count(*) as conflicts
                """
                result = session.run(query)
                record = result.single()
                if record:
                    metrics.edge_conflicts = record["conflicts"]

        except Exception as e:
            logger.error(f"Failed to get graph metrics: {e}")

        return metrics

    def validate_quality_gates(
        self, mode: str = "quick"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate V7 quality gates for graph consistency.

        Args:
            mode: Validation mode ("quick", "standard", "paranoid")

        Returns:
            Tuple of (pass/fail, detailed results)
        """
        metrics = self.get_graph_metrics()

        # Define thresholds based on mode
        thresholds = {
            "quick": {
                "coherence": 0.3,
                "max_edge_conflicts": 0.05,  # 5% of edges
                "max_cycles": 10,
            },
            "standard": {
                "coherence": 0.5,
                "max_edge_conflicts": 0.02,  # 2% of edges
                "max_cycles": 5,
            },
            "paranoid": {
                "coherence": 0.7,
                "max_edge_conflicts": 0.01,  # 1% of edges
                "max_cycles": 0,
            },
        }

        threshold = thresholds.get(mode, thresholds["standard"])

        # Calculate percentages
        edge_conflict_pct = 0.0
        if metrics.total_relationships > 0:
            edge_conflict_pct = (
                metrics.edge_conflicts / metrics.total_relationships
            ) * 100

        # Validate
        results = {
            "coherence_score": metrics.coherence_score,
            "coherence_threshold": threshold["coherence"],
            "coherence_pass": metrics.coherence_score >= threshold["coherence"],
            "edge_conflict_pct": edge_conflict_pct,
            "edge_conflict_threshold": threshold["max_edge_conflicts"] * 100,
            "edge_conflict_pass": edge_conflict_pct
            <= threshold["max_edge_conflicts"] * 100,
            "cycle_count": metrics.cycle_count,
            "cycle_threshold": threshold["max_cycles"],
            "cycle_pass": metrics.cycle_count <= threshold["max_cycles"],
            "total_mathematicians": metrics.total_mathematicians,
            "total_relationships": metrics.total_relationships,
        }

        # Overall pass/fail
        passed = (
            results["coherence_pass"]
            and results["edge_conflict_pass"]
            and results["cycle_pass"]
        )

        return passed, results


# Alias for compatibility
MemgraphClient = MemgraphCompatibleClient
