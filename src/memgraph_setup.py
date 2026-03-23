#!/usr/bin/env python3
"""
Memgraph setup for V7 compliance - Academic genealogy graph database.
"""

import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import docker
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


@dataclass
class MathematicianNode:
    """Mathematician node for graph database."""
    global_id: str
    canonical_latin: str
    canonical_native: Optional[str]
    birth_year: Optional[int]
    death_year: Optional[int]
    region_code: str
    msc_codes: List[str] = None
    
    def __post_init__(self):
        if self.msc_codes is None:
            self.msc_codes = []


@dataclass
class AdvisorshipEdge:
    """Doctoral advisorship relationship."""
    student_id: str
    advisor_id: str
    year: Optional[int]
    institution: Optional[str]
    thesis_title: Optional[str]
    confidence: float = 1.0


class MemgraphManager:
    """Manager for Memgraph graph database operations."""
    
    def __init__(self, 
                 bolt_uri: str = "bolt://localhost:7687",
                 auth: tuple = ("", "")):
        """Initialize Memgraph connection."""
        self.bolt_uri = bolt_uri
        self.auth = auth
        self.driver = None
        
    def connect(self):
        """Connect to Memgraph."""
        try:
            self.driver = GraphDatabase.driver(self.bolt_uri, auth=self.auth)
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 'Connected' AS status")
                status = result.single()["status"]
                logger.info(f"Memgraph connection: {status}")
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise
    
    def close(self):
        """Close connection."""
        if self.driver:
            self.driver.close()
    
    def create_schema(self):
        """Create indexes and constraints for optimal performance."""
        with self.driver.session() as session:
            # Create index on GlobalID for fast lookups
            session.run("""
                CREATE INDEX ON :Mathematician(global_id);
            """)
            
            # Create index on CanonicalLatin for name searches
            session.run("""
                CREATE INDEX ON :Mathematician(canonical_latin);
            """)
            
            # Create index on region for regional queries
            session.run("""
                CREATE INDEX ON :Mathematician(region_code);
            """)
            
            logger.info("Created Memgraph schema indexes")
    
    def create_mathematician(self, mathematician: MathematicianNode):
        """Create or update a mathematician node."""
        with self.driver.session() as session:
            session.run("""
                MERGE (m:Mathematician {global_id: $global_id})
                SET m.canonical_latin = $canonical_latin,
                    m.canonical_native = $canonical_native,
                    m.birth_year = $birth_year,
                    m.death_year = $death_year,
                    m.region_code = $region_code,
                    m.msc_codes = $msc_codes
            """, **mathematician.__dict__)
    
    def create_advisorship(self, edge: AdvisorshipEdge):
        """Create advisorship relationship."""
        with self.driver.session() as session:
            session.run("""
                MATCH (student:Mathematician {global_id: $student_id})
                MATCH (advisor:Mathematician {global_id: $advisor_id})
                MERGE (student)-[r:ADVISED_BY]->(advisor)
                SET r.year = $year,
                    r.institution = $institution,
                    r.thesis_title = $thesis_title,
                    r.confidence = $confidence
            """, **edge.__dict__)
    
    def calculate_betweenness_centrality(self) -> Dict[str, float]:
        """Calculate betweenness centrality for all nodes."""
        with self.driver.session() as session:
            result = session.run("""
                CALL algo.betweenness.stream('Mathematician', 'ADVISED_BY')
                YIELD nodeId, centrality
                RETURN algo.getNodeById(nodeId).global_id AS global_id, centrality
                ORDER BY centrality DESC
            """)
            
            return {record["global_id"]: record["centrality"] 
                    for record in result}
    
    def detect_cycles(self, max_length: int = 3) -> List[List[str]]:
        """Detect cycles of length <= max_length."""
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH path = (m:Mathematician)-[:ADVISED_BY*1..{max_length}]->(m)
                RETURN [node IN nodes(path) | node.global_id] AS cycle
            """)
            
            cycles = []
            for record in result:
                cycle = record["cycle"]
                if len(cycle) <= max_length + 1:  # +1 because start=end
                    cycles.append(cycle)
            
            return cycles
    
    def get_lineage(self, global_id: str, generations: int = 5) -> Dict[str, Any]:
        """Get academic lineage tree."""
        with self.driver.session() as session:
            # Get ancestors (advisors)
            ancestors = session.run("""
                MATCH path = (m:Mathematician {global_id: $global_id})-[:ADVISED_BY*1..$gens]->(advisor)
                RETURN path
            """, global_id=global_id, gens=generations)
            
            # Get descendants (students)
            descendants = session.run("""
                MATCH path = (m:Mathematician {global_id: $global_id})<-[:ADVISED_BY*1..$gens]-(student)
                RETURN path
            """, global_id=global_id, gens=generations)
            
            return {
                "ancestors": [self._path_to_dict(record["path"]) for record in ancestors],
                "descendants": [self._path_to_dict(record["path"]) for record in descendants]
            }
    
    def _path_to_dict(self, path) -> List[Dict[str, Any]]:
        """Convert Neo4j path to dictionary."""
        nodes = []
        for node in path.nodes:
            nodes.append({
                "global_id": node["global_id"],
                "canonical_latin": node["canonical_latin"],
                "region_code": node.get("region_code"),
                "birth_year": node.get("birth_year")
            })
        return nodes
    
    def compute_graph_coherence_score(self) -> float:
        """
        Compute graph coherence score as per V7 spec.
        
        Coherence = weighted average of:
        - Component connectivity (largest component size / total nodes)
        - Betweenness distribution (1 - gini coefficient)
        - Cycle absence (1 - cycles/nodes)
        """
        with self.driver.session() as session:
            # Get total nodes
            total_nodes = session.run(
                "MATCH (n:Mathematician) RETURN count(n) as count"
            ).single()["count"]
            
            if total_nodes == 0:
                return 0.0
            
            # Get largest connected component size
            components = session.run("""
                CALL algo.unionFind.stream('Mathematician', 'ADVISED_BY')
                YIELD nodeId, setId
                RETURN setId, count(*) as size
                ORDER BY size DESC
                LIMIT 1
            """)
            
            largest_component = 0
            for record in components:
                largest_component = record["size"]
                break
            
            connectivity_score = largest_component / total_nodes
            
            # Get betweenness centrality distribution
            centralities = list(self.calculate_betweenness_centrality().values())
            if centralities:
                # Calculate Gini coefficient
                centralities.sort()
                n = len(centralities)
                index = range(1, n + 1)
                gini = (2 * sum(index[i] * centralities[i] for i in range(n))) / (n * sum(centralities)) - (n + 1) / n
                distribution_score = 1 - gini
            else:
                distribution_score = 0.0
            
            # Count cycles
            cycles = self.detect_cycles(max_length=3)
            cycle_score = 1 - (len(cycles) / max(total_nodes, 1))
            
            # Weighted average
            coherence = (
                0.4 * connectivity_score +
                0.3 * distribution_score +
                0.3 * cycle_score
            )
            
            return coherence


def setup_memgraph_docker():
    """Set up Memgraph using Docker."""
    client = docker.from_env()
    
    # Check if container already exists
    try:
        container = client.containers.get("gmnap-memgraph")
        if container.status != "running":
            container.start()
            logger.info("Started existing Memgraph container")
        else:
            logger.info("Memgraph container already running")
        return container
    except docker.errors.NotFound:
        pass
    
    # Create new container
    logger.info("Creating new Memgraph container...")
    
    container = client.containers.run(
        "memgraph/memgraph-platform:2.12",
        name="gmnap-memgraph",
        ports={
            "7687/tcp": 7687,  # Bolt
            "7444/tcp": 7444,  # Monitoring
            "3000/tcp": 3000   # Lab UI
        },
        volumes={
            "gmnap-memgraph-data": {"bind": "/var/lib/memgraph", "mode": "rw"}
        },
        environment={
            "MEMGRAPH_USER": os.getenv("MEMGRAPH_USER", "gmnap"),
            "MEMGRAPH_PASSWORD": os.getenv("MEMGRAPH_PASSWORD", ""),
        },
        detach=True,
        remove=False
    )
    
    logger.info(f"Created Memgraph container: {container.id[:12]}")
    logger.info("Memgraph Lab UI available at http://localhost:3000")
    
    return container


if __name__ == "__main__":
    # Test setup
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Setting up Memgraph for GMNAP V7...")
    
    # Start Docker container
    try:
        container = setup_memgraph_docker()
        print("✅ Memgraph Docker container ready")
    except Exception as e:
        print(f"❌ Failed to setup Docker: {e}")
        sys.exit(1)
    
    # Wait for Memgraph to be ready
    import time
    time.sleep(5)
    
    # Connect and create schema
    manager = MemgraphManager(
        bolt_uri="bolt://localhost:7687",
        auth=("", "")  # Memgraph CE doesn't require auth by default
    )
    
    try:
        manager.connect()
        print("✅ Connected to Memgraph")
        
        manager.create_schema()
        print("✅ Created schema")
        
        # Test with sample data
        mathematician = MathematicianNode(
            global_id="TEST001",
            canonical_latin="Euler, Leonhard",
            canonical_native="Euler, Leonhard",
            birth_year=1707,
            death_year=1783,
            region_code="A2",
            msc_codes=["11-XX", "26-XX"]
        )
        
        manager.create_mathematician(mathematician)
        print("✅ Created test mathematician node")
        
        manager.close()
        
    except Exception as e:
        print(f"❌ Memgraph operations failed: {e}")
        sys.exit(1)
    
    print("\n🎉 Memgraph setup complete!")
    print("   Access Memgraph Lab at: http://localhost:3000")
    print("   Bolt connection at: bolt://localhost:7687")