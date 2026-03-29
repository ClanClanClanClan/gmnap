#!/usr/bin/env python3
"""
V7 Graph Coherence Scoring System (Stage 6 & 8)
Implements V7 requirements for graph consistency and coherence validation

V7 Quality Gates:
- Quick mode: ≥0.85 coherence score
- Full mode: ≥0.92 coherence score  
- Extreme mode: ≥0.97 coherence score
"""

import logging
import networkx as nx
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import statistics

logger = logging.getLogger(__name__)


@dataclass
class GraphCoherenceMetrics:
    """Detailed metrics for graph coherence analysis"""

    total_nodes: int
    total_edges: int
    connected_components: int
    largest_component_size: int
    cycles_detected: int
    orphaned_nodes: int

    # Coherence-specific metrics
    betweenness_scores: Dict[str, float] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    consistency_violations: List[str] = field(default_factory=list)

    # Quality indicators
    avg_betweenness: float = 0.0
    avg_confidence: float = 0.0
    density: float = 0.0
    clustering_coefficient: float = 0.0


@dataclass
class GraphCoherenceResult:
    """Results of graph coherence analysis"""

    coherence_score: float  # 0.0 to 1.0
    mode: str  # quick, full, extreme
    v7_threshold: float
    v7_compliant: bool
    timestamp: datetime
    metrics: GraphCoherenceMetrics
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)


class GraphCoherenceScorer:
    """
    V7 Graph Coherence Scoring Implementation

    Analyzes genealogy graphs for consistency, reliability, and structural integrity.
    Implements betweenness-scaled confidence scoring as per V7 spec.
    """

    def __init__(self):
        # V7 coherence thresholds
        self.v7_thresholds = {"quick": 0.85, "full": 0.92, "extreme": 0.97}

        logger.info("Graph coherence scorer initialized with V7 thresholds")

    def score_graph_coherence(self, graph: nx.Graph, mode: str = "quick") -> GraphCoherenceResult:
        """
        Calculate comprehensive graph coherence score

        Args:
            graph: NetworkX graph representing genealogy/relationships
            mode: V7 mode (quick/full/extreme) determining threshold

        Returns:
            GraphCoherenceResult with detailed analysis
        """
        if mode not in self.v7_thresholds:
            raise ValueError(f"Invalid mode: {mode}. Must be: {list(self.v7_thresholds.keys())}")

        logger.info(f"Calculating graph coherence for mode: {mode}")

        start_time = datetime.now()

        # Calculate comprehensive metrics
        metrics = self._calculate_graph_metrics(graph)

        # Calculate coherence components
        structural_score = self._calculate_structural_coherence(graph, metrics)
        consistency_score = self._calculate_consistency_score(graph, metrics)
        confidence_score = self._calculate_confidence_score(graph, metrics)
        betweenness_score = self._calculate_betweenness_coherence(graph, metrics)

        # Weighted final score (V7 methodology)
        final_score = self._combine_coherence_scores(
            structural_score, consistency_score, confidence_score, betweenness_score
        )

        v7_threshold = self.v7_thresholds[mode]
        v7_compliant = final_score >= v7_threshold

        # Detailed analysis
        detailed_analysis = {
            "structural_score": structural_score,
            "consistency_score": consistency_score,
            "confidence_score": confidence_score,
            "betweenness_score": betweenness_score,
            "component_weights": {
                "structural": 0.25,
                "consistency": 0.30,
                "confidence": 0.25,
                "betweenness": 0.20,
            },
            "analysis_duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }

        result = GraphCoherenceResult(
            coherence_score=final_score,
            mode=mode,
            v7_threshold=v7_threshold,
            v7_compliant=v7_compliant,
            timestamp=datetime.now(),
            metrics=metrics,
            detailed_analysis=detailed_analysis,
        )

        self._log_coherence_result(result)
        return result

    def create_genealogy_graph_from_entries(self, entries: List[Dict[str, Any]]) -> nx.Graph:
        """
        Create genealogy graph from processing entries

        Args:
            entries: List of processed name entries with relationships

        Returns:
            NetworkX graph representing relationships
        """
        graph = nx.Graph()

        for entry in entries:
            # Add node for this person
            person_id = entry.get("GlobalID", f"unknown_{len(graph)}")
            canonical_name = entry.get("CanonicalLatin", "Unknown")

            graph.add_node(
                person_id, canonical_name=canonical_name, confidence=entry.get("Confidence", 50.0)
            )

            # Add relationships if available
            relationships = entry.get("GenealogyRelation", [])
            if isinstance(relationships, list):
                for rel in relationships:
                    if isinstance(rel, dict):
                        target_id = rel.get("target_id")
                        relation_type = rel.get("relation_type", "unknown")
                        rel_confidence = rel.get("confidence", 50.0)

                        if target_id:
                            graph.add_edge(
                                person_id,
                                target_id,
                                relation_type=relation_type,
                                confidence=rel_confidence,
                            )

            # Infer relationships from name patterns (simplified)
            self._infer_relationships_from_names(graph, person_id, entry)

        logger.info(
            f"Created genealogy graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )
        return graph

    def _calculate_graph_metrics(self, graph: nx.Graph) -> GraphCoherenceMetrics:
        """Calculate comprehensive graph structure metrics"""
        if graph.number_of_nodes() == 0:
            return GraphCoherenceMetrics(
                total_nodes=0,
                total_edges=0,
                connected_components=0,
                largest_component_size=0,
                cycles_detected=0,
                orphaned_nodes=0,
            )

        # Basic structure
        total_nodes = graph.number_of_nodes()
        total_edges = graph.number_of_edges()

        # Component analysis
        components = list(nx.connected_components(graph))
        connected_components = len(components)
        largest_component_size = max(len(comp) for comp in components) if components else 0

        # Cycle detection
        try:
            cycles = list(nx.simple_cycles(graph.to_directed()))
            cycles_detected = len(cycles)
        except:
            cycles_detected = 0  # Fallback for undirected graphs

        # Orphaned nodes (degree 0)
        orphaned_nodes = sum(1 for node, degree in graph.degree() if degree == 0)

        # Advanced metrics
        betweenness_scores = nx.betweenness_centrality(graph) if total_nodes > 1 else {}

        # Extract confidence scores from node/edge attributes
        confidence_scores = {}
        for node, data in graph.nodes(data=True):
            confidence_scores[node] = data.get("confidence", 50.0) / 100.0

        # Quality indicators
        avg_betweenness = (
            statistics.mean(betweenness_scores.values()) if betweenness_scores else 0.0
        )
        avg_confidence = statistics.mean(confidence_scores.values()) if confidence_scores else 0.0

        # Density and clustering
        density = nx.density(graph)
        try:
            clustering_coefficient = nx.average_clustering(graph)
        except:
            clustering_coefficient = 0.0

        # Consistency violations (placeholder - would implement specific genealogy rules)
        consistency_violations = self._detect_consistency_violations(graph)

        return GraphCoherenceMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            connected_components=connected_components,
            largest_component_size=largest_component_size,
            cycles_detected=cycles_detected,
            orphaned_nodes=orphaned_nodes,
            betweenness_scores=betweenness_scores,
            confidence_scores=confidence_scores,
            consistency_violations=consistency_violations,
            avg_betweenness=avg_betweenness,
            avg_confidence=avg_confidence,
            density=density,
            clustering_coefficient=clustering_coefficient,
        )

    def _calculate_structural_coherence(
        self, graph: nx.Graph, metrics: GraphCoherenceMetrics
    ) -> float:
        """Calculate structural coherence score (0.0 to 1.0)"""
        if metrics.total_nodes == 0:
            return 0.0

        # Component connectivity (fewer components = better)
        connectivity_score = 1.0 - (metrics.connected_components - 1) / max(
            1, metrics.total_nodes - 1
        )

        # Size balance (larger main component = better)
        balance_score = metrics.largest_component_size / metrics.total_nodes

        # Orphan penalty (fewer orphans = better)
        orphan_score = 1.0 - (metrics.orphaned_nodes / metrics.total_nodes)

        # Density consideration (moderate density preferred)
        optimal_density = 0.1  # Genealogy graphs should be moderately sparse
        density_score = 1.0 - abs(metrics.density - optimal_density) / optimal_density
        density_score = max(0.0, min(1.0, density_score))

        # Combine with weights
        structural_score = (
            0.3 * connectivity_score
            + 0.3 * balance_score
            + 0.2 * orphan_score
            + 0.2 * density_score
        )

        return max(0.0, min(1.0, structural_score))

    def _calculate_consistency_score(
        self, graph: nx.Graph, metrics: GraphCoherenceMetrics
    ) -> float:
        """Calculate logical consistency score (0.0 to 1.0)"""
        if metrics.total_nodes <= 1:
            return 1.0  # Single node is trivially consistent

        # Cycle penalty (genealogy should be mostly acyclic)
        cycle_penalty = min(0.5, metrics.cycles_detected / max(1, metrics.total_nodes))
        cycle_score = 1.0 - cycle_penalty

        # Consistency violation penalty
        violation_penalty = min(
            0.3, len(metrics.consistency_violations) / max(1, metrics.total_nodes)
        )
        violation_score = 1.0 - violation_penalty

        # Clustering coherence (related people should cluster)
        clustering_score = metrics.clustering_coefficient

        # Combine consistency factors
        consistency_score = 0.4 * cycle_score + 0.4 * violation_score + 0.2 * clustering_score

        return max(0.0, min(1.0, consistency_score))

    def _calculate_confidence_score(self, graph: nx.Graph, metrics: GraphCoherenceMetrics) -> float:
        """Calculate confidence-based coherence score (0.0 to 1.0)"""
        if not metrics.confidence_scores:
            return 0.5  # Neutral score for no confidence data

        # Average confidence of all nodes
        avg_confidence = metrics.avg_confidence

        # Confidence distribution (prefer consistent high confidence)
        confidence_values = list(metrics.confidence_scores.values())
        confidence_std = statistics.stdev(confidence_values) if len(confidence_values) > 1 else 0.0

        # Lower standard deviation = more consistent confidence
        consistency_bonus = max(0.0, 1.0 - confidence_std)

        # Combine confidence factors
        confidence_score = 0.7 * avg_confidence + 0.3 * consistency_bonus

        return max(0.0, min(1.0, confidence_score))

    def _calculate_betweenness_coherence(
        self, graph: nx.Graph, metrics: GraphCoherenceMetrics
    ) -> float:
        """Calculate betweenness-scaled coherence score as per V7 spec"""
        if not metrics.betweenness_scores:
            return 0.5  # Neutral score for trivial graphs

        # V7 spec mentions "betweenness-scaled confidence"
        betweenness_values = list(metrics.betweenness_scores.values())

        # Balanced betweenness distribution preferred (no single super-central node)
        if len(betweenness_values) <= 1:
            return 1.0

        avg_betweenness = statistics.mean(betweenness_values)
        max_betweenness = max(betweenness_values)

        # Penalty for excessive centralization (one node dominates)
        centralization_penalty = max_betweenness - avg_betweenness
        centralization_score = max(0.0, 1.0 - centralization_penalty)

        # Average betweenness indicates good connectivity
        connectivity_score = min(1.0, avg_betweenness * 2)  # Scale appropriately

        # Combine betweenness factors
        betweenness_score = 0.6 * centralization_score + 0.4 * connectivity_score

        return max(0.0, min(1.0, betweenness_score))

    def _combine_coherence_scores(
        self, structural: float, consistency: float, confidence: float, betweenness: float
    ) -> float:
        """Combine component scores using V7 methodology"""
        # V7-inspired weighting (can be tuned based on requirements)
        weights = {
            "structural": 0.25,  # Graph structure quality
            "consistency": 0.30,  # Logical consistency (most important)
            "confidence": 0.25,  # Data confidence
            "betweenness": 0.20,  # Centrality balance
        }

        final_score = (
            weights["structural"] * structural
            + weights["consistency"] * consistency
            + weights["confidence"] * confidence
            + weights["betweenness"] * betweenness
        )

        return max(0.0, min(1.0, final_score))

    def _detect_consistency_violations(self, graph: nx.Graph) -> List[str]:
        """Detect logical consistency violations in genealogy graph"""
        violations = []

        # Check for impossible relationship patterns
        for node in graph.nodes():
            # Example: person can't be advisor and advisee of same person
            advisors = set()
            advisees = set()

            for neighbor in graph.neighbors(node):
                edge_data = graph.get_edge_data(node, neighbor)
                if edge_data:
                    rel_type = edge_data.get("relation_type", "")
                    if "advisor" in rel_type.lower():
                        if node < neighbor:  # Consistent direction
                            advisees.add(neighbor)
                        else:
                            advisors.add(neighbor)

            # Check for cycles in advisor relationships
            mutual_advisors = advisors & advisees
            if mutual_advisors:
                violations.append(f"Mutual advisor relationship: {node} <-> {mutual_advisors}")

        # Check for impossible temporal relationships (placeholder)
        # In a real implementation, this would check degree dates, birth years, etc.

        return violations

    def _infer_relationships_from_names(
        self, graph: nx.Graph, person_id: str, entry: Dict[str, Any]
    ):
        """Infer relationships from name patterns (simplified implementation)"""
        # This is a placeholder for more sophisticated relationship inference
        # In production, this would analyze:
        # - Shared surnames (family relationships)
        # - Institution affiliations (advisor relationships)
        # - Publication co-authorship patterns
        # - Temporal patterns (degree dates, etc.)

        canonical_name = entry.get("CanonicalLatin", "")
        if "," in canonical_name:
            surname = canonical_name.split(",")[0].strip()

            # Look for others with same surname (potential family)
            for other_node, other_data in graph.nodes(data=True):
                if other_node != person_id:
                    other_name = other_data.get("canonical_name", "")
                    if "," in other_name:
                        other_surname = other_name.split(",")[0].strip()
                        if surname == other_surname and not graph.has_edge(person_id, other_node):
                            # Add potential family relationship with low confidence
                            graph.add_edge(
                                person_id,
                                other_node,
                                relation_type="potential_family",
                                confidence=30.0,
                            )

    def _log_coherence_result(self, result: GraphCoherenceResult):
        """Log graph coherence analysis results"""
        status = "PASS" if result.v7_compliant else "FAIL"

        logger.info(f"Graph coherence analysis: {status}")
        logger.info(f"  Score: {result.coherence_score:.3f} (threshold: {result.v7_threshold:.3f})")
        logger.info(f"  Mode: {result.mode}")
        logger.info(f"  Nodes: {result.metrics.total_nodes}, Edges: {result.metrics.total_edges}")
        logger.info(f"  Components: {result.metrics.connected_components}")
        logger.info(f"  Avg confidence: {result.metrics.avg_confidence:.3f}")

        if result.metrics.consistency_violations:
            logger.warning(
                f"  Consistency violations: {len(result.metrics.consistency_violations)}"
            )

    def generate_coherence_report(self, results: List[GraphCoherenceResult]) -> Dict[str, Any]:
        """Generate comprehensive coherence analysis report"""
        if not results:
            return {"error": "No results to analyze"}

        # Summary statistics
        scores = [r.coherence_score for r in results]
        v7_compliant_count = sum(1 for r in results if r.v7_compliant)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_analyses": len(results),
                "v7_compliant": v7_compliant_count,
                "compliance_rate": v7_compliant_count / len(results),
                "avg_coherence_score": statistics.mean(scores),
                "min_coherence_score": min(scores),
                "max_coherence_score": max(scores),
                "std_coherence_score": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            },
            "by_mode": {},
            "detailed_results": [],
        }

        # Group by mode
        mode_groups = defaultdict(list)
        for result in results:
            mode_groups[result.mode].append(result)

        for mode, mode_results in mode_groups.items():
            mode_scores = [r.coherence_score for r in mode_results]
            mode_compliant = sum(1 for r in mode_results if r.v7_compliant)

            report["by_mode"][mode] = {
                "count": len(mode_results),
                "v7_threshold": self.v7_thresholds[mode],
                "compliant": mode_compliant,
                "compliance_rate": mode_compliant / len(mode_results),
                "avg_score": statistics.mean(mode_scores),
                "min_score": min(mode_scores),
                "max_score": max(mode_scores),
            }

        # Detailed results (last 5)
        for result in results[-5:]:
            report["detailed_results"].append(
                {
                    "coherence_score": result.coherence_score,
                    "mode": result.mode,
                    "v7_compliant": result.v7_compliant,
                    "nodes": result.metrics.total_nodes,
                    "edges": result.metrics.total_edges,
                    "components": result.metrics.connected_components,
                    "violations": len(result.metrics.consistency_violations),
                }
            )

        return report


if __name__ == "__main__":
    # Example usage
    scorer = GraphCoherenceScorer()

    # Create sample graph
    sample_graph = nx.Graph()
    sample_graph.add_node("person1", canonical_name="Smith, John", confidence=80.0)
    sample_graph.add_node("person2", canonical_name="Smith, Jane", confidence=75.0)
    sample_graph.add_edge("person1", "person2", relation_type="advisor", confidence=85.0)

    result = scorer.score_graph_coherence(sample_graph, mode="quick")
    print(f"Graph coherence score: {result.coherence_score:.3f}")
    print(f"V7 compliant: {result.v7_compliant}")
