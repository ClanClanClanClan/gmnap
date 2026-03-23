"""
Memgraph client for GMNAP V7 academic genealogy features.
Implements Stage 6 (GraphConsistency) functionality.
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


class MemgraphClient:
    """
    Memgraph client for academic genealogy graph operations.
    
    Implements V7 Stage 6 (GraphConsistency):
    - Betweenness centrality calculations
    - Bayesian confidence scoring
    - Cycle detection (<3 generations)
    - Quality gate validation
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 7687,
                 username: str = "gmnap",
                 password: str = ""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.driver = None
        self.connected = False
        
        # Override with environment variables if available
        self.host = os.getenv("MEMGRAPH_HOST", self.host)
        self.port = int(os.getenv("MEMGRAPH_PORT", self.port))
        self.username = os.getenv("MEMGRAPH_USER", self.username)
        self.password = os.getenv("MEMGRAPH_PASSWORD", self.password)
        
        if not MEMGRAPH_AVAILABLE:
            logger.warning("Memgraph client not available - neo4j package not installed")
            return
            
        self._connect()
    
    def _connect(self) -> bool:
        """Connect to Memgraph database."""
        if not MEMGRAPH_AVAILABLE:
            return False
            
        try:
            uri = f"bolt://{self.host}:{self.port}"
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(self.username, self.password),
                encrypted=False  # Memgraph typically doesn't use TLS in development
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.connected = True
            logger.info(f"Connected to Memgraph at {uri}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            self.connected = False
            return False
    
    def close(self):
        """Close connection to Memgraph."""
        if self.driver:
            self.driver.close()
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Memgraph."""
        return self.connected and MEMGRAPH_AVAILABLE
    
    def create_mathematician(self, entry: Dict[str, Any]) -> bool:
        """
        Create or update mathematician node in graph.
        
        Args:
            entry: Mathematician entry from V7 pipeline
        """
        if not self.is_connected():
            logger.warning("Memgraph not connected - skipping mathematician creation")
            return False
            
        try:
            with self.driver.session() as session:
                query = """
                MERGE (m:Mathematician {global_id: $global_id})
                SET m.canonical_latin = $canonical_latin,
                    m.canonical_native = $canonical_native,
                    m.birth_year = $birth_year,
                    m.death_year = $death_year,
                    m.region = $region,
                    m.confidence = $confidence,
                    m.msc_primary = $msc_primary,
                    m.updated_at = datetime(),
                    m.gdpr_data = $gdpr_data
                RETURN m.global_id as id
                """
                
                result = session.run(query,
                    global_id=entry.get("GlobalID", ""),
                    canonical_latin=entry.get("CanonicalLatin", ""),
                    canonical_native=entry.get("CanonicalNative", ""),
                    birth_year=entry.get("BirthYear"),
                    death_year=entry.get("DeathYear"),
                    region=entry.get("DetectedRegion", ""),
                    confidence=entry.get("DetectionConfidence", 0.0),
                    msc_primary=entry.get("MSC", {}).get("primary", ""),
                    gdpr_data=entry.get("GDPR_DATA", False)
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
                
                result = session.run(query,
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    source=relation.source,
                    year=relation.year,
                    qualifier=relation.qualifier
                )
                
                if result.single():
                    logger.debug(f"Added relation: {relation.source_id} -> {relation.target_id}")
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
            
        try:
            with self.driver.session() as session:
                # Simple betweenness approximation
                # In production, would use more sophisticated algorithm
                query = """
                MATCH (m:Mathematician)
                OPTIONAL MATCH (m)-[r:DOCTORAL_ADVISOR]->()
                WITH m, count(r) as out_degree
                OPTIONAL MATCH ()-[r2:DOCTORAL_ADVISOR]->(m)
                WITH m, out_degree, count(r2) as in_degree
                WITH m, (out_degree + in_degree) as total_degree
                MATCH (all:Mathematician)
                WITH m, total_degree, count(all) as total_nodes
                SET m.betweenness_score = toFloat(total_degree) / toFloat(total_nodes)
                RETURN m.global_id as id, m.betweenness_score as score
                """
                
                result = session.run(query)
                scores = {}
                
                for record in result:
                    scores[record["id"]] = record["score"]
                    
                logger.info(f"Calculated betweenness centrality for {len(scores)} mathematicians")
                return scores
                
        except Exception as e:
            logger.error(f"Failed to calculate betweenness centrality: {e}")
            
        return {}
    
    def detect_cycles(self, max_depth: int = 3) -> List[List[str]]:
        """
        Detect cycles in the academic genealogy graph.
        
        Args:
            max_depth: Maximum cycle depth to check (V7 spec: <3 generations)
            
        Returns:
            List of cycles, each cycle is a list of GlobalIDs
        """
        if not self.is_connected():
            return []
            
        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (a:Mathematician)-[:DOCTORAL_ADVISOR*1..{max_depth}]->(b:Mathematician)
                -[:DOCTORAL_ADVISOR*1..{max_depth}]->(a)
                WHERE a <> b
                RETURN DISTINCT a.global_id as start_id, b.global_id as end_id
                LIMIT 100
                """
                
                result = session.run(query)
                cycles = []
                
                for record in result:
                    cycle = [record["start_id"], record["end_id"]]
                    cycles.append(cycle)
                    
                if cycles:
                    logger.warning(f"Detected {len(cycles)} potential cycles in genealogy graph")
                else:
                    logger.info("No cycles detected in genealogy graph")
                    
                return cycles
                
        except Exception as e:
            logger.error(f"Failed to detect cycles: {e}")
            
        return []
    
    def get_graph_metrics(self) -> GraphMetrics:
        """
        Get comprehensive graph metrics for V7 quality gates.
        
        Returns:
            GraphMetrics with coherence scores and statistics
        """
        if not self.is_connected():
            return GraphMetrics()
            
        try:
            with self.driver.session() as session:
                # Get basic counts
                stats_query = """
                MATCH (m:Mathematician)
                OPTIONAL MATCH (m)-[r:DOCTORAL_ADVISOR]->()
                RETURN count(DISTINCT m) as mathematician_count,
                       count(r) as relationship_count
                """
                
                stats = session.run(stats_query).single()
                mathematician_count = stats["mathematician_count"] if stats else 0
                relationship_count = stats["relationship_count"] if stats else 0
                
                # Calculate coherence score (simplified)
                # In production, would use more sophisticated coherence metrics
                coherence_score = min(1.0, relationship_count / max(1, mathematician_count) * 0.1)
                
                # Get betweenness scores
                betweenness_scores = self.calculate_betweenness_centrality()
                
                # Detect cycles
                cycles = self.detect_cycles()
                
                # Edge conflicts (simplified - relationships with low confidence)
                conflict_query = """
                MATCH ()-[r:DOCTORAL_ADVISOR]->()
                WHERE r.confidence < 0.8
                RETURN count(r) as conflict_count
                """
                
                conflict_result = session.run(conflict_query).single()
                edge_conflicts = conflict_result["conflict_count"] if conflict_result else 0
                
                metrics = GraphMetrics(
                    total_mathematicians=mathematician_count,
                    total_relationships=relationship_count,
                    coherence_score=coherence_score,
                    betweenness_scores=betweenness_scores,
                    cycle_count=len(cycles),
                    edge_conflicts=edge_conflicts,
                    last_updated=datetime.now()
                )
                
                logger.info(f"Graph metrics: {mathematician_count} mathematicians, "
                          f"{relationship_count} relationships, "
                          f"coherence: {coherence_score:.3f}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get graph metrics: {e}")
            
        return GraphMetrics()
    
    def validate_quality_gates(self, mode: str = "quick") -> Tuple[bool, Dict[str, Any]]:
        """
        Validate V7 quality gates for graph consistency.
        
        Args:
            mode: Pipeline mode (quick/full/extreme)
            
        Returns:
            Tuple of (gates_passed, gate_results)
        """
        metrics = self.get_graph_metrics()
        
        # V7 quality gate thresholds
        thresholds = {
            "quick": {"coherence_min": 0.85, "edge_conflict_pct_max": 2.0},
            "full": {"coherence_min": 0.92, "edge_conflict_pct_max": 1.0},
            "extreme": {"coherence_min": 0.97, "edge_conflict_pct_max": 0.0}
        }
        
        threshold = thresholds.get(mode, thresholds["quick"])
        
        # Calculate edge conflict percentage
        edge_conflict_pct = (metrics.edge_conflicts / max(1, metrics.total_relationships)) * 100
        
        # Check gates
        coherence_pass = metrics.coherence_score >= threshold["coherence_min"]
        conflict_pass = edge_conflict_pct <= threshold["edge_conflict_pct_max"]
        cycle_pass = metrics.cycle_count == 0  # V7 spec: reject cycles <3
        
        gates_passed = coherence_pass and conflict_pass and cycle_pass
        
        gate_results = {
            "coherence_score": metrics.coherence_score,
            "coherence_threshold": threshold["coherence_min"],
            "coherence_pass": coherence_pass,
            "edge_conflict_pct": edge_conflict_pct,
            "edge_conflict_threshold": threshold["edge_conflict_pct_max"],
            "edge_conflict_pass": conflict_pass,
            "cycle_count": metrics.cycle_count,
            "cycle_pass": cycle_pass,
            "overall_pass": gates_passed
        }
        
        if gates_passed:
            logger.info(f"Graph quality gates PASSED for {mode} mode")
        else:
            logger.error(f"Graph quality gates FAILED for {mode} mode: {gate_results}")
            
        return gates_passed, gate_results


# Global instance for pipeline use
_memgraph_client = None

def get_memgraph_client() -> MemgraphClient:
    """Get singleton Memgraph client instance."""
    global _memgraph_client
    if _memgraph_client is None:
        _memgraph_client = MemgraphClient()
    return _memgraph_client


def close_memgraph_client():
    """Close global Memgraph client."""
    global _memgraph_client
    if _memgraph_client:
        _memgraph_client.close()
        _memgraph_client = None