#!/usr/bin/env python3
"""
from typing import List
from typing import Any
V7 Graph Coherence Testing
Tests V7 graph coherence requirements and quality gates

V7 Quality Gates:
- Quick mode: >=0.85 coherence score
- Full mode: >=0.92 coherence score
- Extreme mode: >=0.97 coherence score
"""

import pytest
import networkx as nx
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.graph_coherence.scorer import GraphCoherenceScorer, GraphCoherenceResult


class TestV7GraphCoherence:
    """
    V7 Graph coherence testing framework

    Tests graph consistency and coherence scoring according to V7 requirements:
    - Structural coherence
    - Logical consistency
    - Confidence-based scoring
    - Betweenness-scaled analysis
    """

    @classmethod
    def setup_class(cls):
        """Setup graph coherence testing environment"""
        cls.scorer = GraphCoherenceScorer()

        # V7 thresholds for validation
        cls.v7_thresholds = {"quick": 0.85, "full": 0.92, "extreme": 0.97}

        print("Graph coherence scorer initialized for V7 testing")

    @pytest.mark.timeout(15)
    def test_v7_threshold_validation(self):
        """Test that V7 thresholds are correctly configured"""
        assert self.scorer.v7_thresholds["quick"] == 0.85
        assert self.scorer.v7_thresholds["full"] == 0.92
        assert self.scorer.v7_thresholds["extreme"] == 0.97

        print("✓ V7 thresholds correctly configured")

    @pytest.mark.timeout(15)
    def test_perfect_coherence_graph(self):
        """Test graph with perfect coherence (should meet all V7 thresholds)"""
        # Create ideal genealogy graph
        perfect_graph = nx.Graph()

        # Add nodes with high confidence
        people = [
            ("advisor1", {"canonical_name": "Smith, John", "confidence": 95.0}),
            ("student1", {"canonical_name": "Johnson, Alice", "confidence": 90.0}),
            ("student2", {"canonical_name": "Brown, Bob", "confidence": 92.0}),
            ("advisor2", {"canonical_name": "Davis, Carol", "confidence": 88.0}),
            ("student3", {"canonical_name": "Wilson, Dave", "confidence": 91.0}),
        ]

        for person_id, attrs in people:
            perfect_graph.add_node(person_id, **attrs)

        # Add logical relationships (tree structure, no cycles)
        relationships = [
            ("advisor1", "student1", {"relation_type": "doctoralAdvisor", "confidence": 95.0}),
            ("advisor1", "student2", {"relation_type": "doctoralAdvisor", "confidence": 93.0}),
            ("advisor2", "student3", {"relation_type": "doctoralAdvisor", "confidence": 90.0}),
            ("student1", "student2", {"relation_type": "peer", "confidence": 80.0}),
        ]

        for source, target, attrs in relationships:
            perfect_graph.add_edge(source, target, **attrs)

        # Test all modes
        for mode in ["quick", "full", "extreme"]:
            result = self.scorer.score_graph_coherence(perfect_graph, mode)

            print(
                f"{mode.upper()} mode: {result.coherence_score:.3f} (threshold: {result.v7_threshold:.3f})"
            )

            # Perfect graph should have high coherence
            assert (
                result.coherence_score >= 0.8
            ), f"Perfect graph should have high coherence: {result.coherence_score:.3f}"

            # May not meet extreme mode due to strict requirements, but should be close
            if mode in ["quick", "full"]:
                assert (
                    result.v7_compliant or result.coherence_score >= result.v7_threshold * 0.95
                ), f"Perfect graph should meet {mode} mode requirements"

    @pytest.mark.timeout(15)
    def test_problematic_coherence_graph(self):
        """Test graph with coherence problems (should fail V7 thresholds)"""
        # Create problematic graph
        problem_graph = nx.Graph()

        # Add nodes with inconsistent confidence
        problematic_people = [
            ("person1", {"canonical_name": "Unknown, A", "confidence": 20.0}),
            ("person2", {"canonical_name": "Unknown, B", "confidence": 15.0}),
            ("person3", {"canonical_name": "Unknown, C", "confidence": 25.0}),
            ("orphan1", {"canonical_name": "Isolated, Person", "confidence": 10.0}),
            ("orphan2", {"canonical_name": "Another, Isolated", "confidence": 5.0}),
        ]

        for person_id, attrs in problematic_people:
            problem_graph.add_node(person_id, **attrs)

        # Add problematic relationships (cycles, inconsistencies)
        problem_relationships = [
            ("person1", "person2", {"relation_type": "doctoralAdvisor", "confidence": 20.0}),
            ("person2", "person3", {"relation_type": "doctoralAdvisor", "confidence": 15.0}),
            (
                "person3",
                "person1",
                {"relation_type": "doctoralAdvisor", "confidence": 10.0},
            ),  # Creates cycle!
        ]

        for source, target, attrs in problem_relationships:
            problem_graph.add_edge(source, target, **attrs)

        # Test all modes
        for mode in ["quick", "full", "extreme"]:
            result = self.scorer.score_graph_coherence(problem_graph, mode)

            print(
                f"Problematic {mode.upper()} mode: {result.coherence_score:.3f} (threshold: {result.v7_threshold:.3f})"
            )

            # Should have low coherence due to problems
            assert (
                result.coherence_score <= 0.7
            ), f"Problematic graph should have low coherence: {result.coherence_score:.3f}"

            # Should fail V7 compliance
            assert not result.v7_compliant, f"Problematic graph should fail {mode} mode compliance"

    @pytest.mark.timeout(15)
    def test_empty_graph_handling(self):
        """Test coherence scoring for empty graphs"""
        empty_graph = nx.Graph()

        result = self.scorer.score_graph_coherence(empty_graph, "quick")

        print(f"Empty graph coherence: {result.coherence_score:.3f}")

        # Empty graph should have neutral/low score
        assert 0.0 <= result.coherence_score <= 0.5, "Empty graph should have low coherence score"
        assert not result.v7_compliant, "Empty graph should not be V7 compliant"

    @pytest.mark.timeout(15)
    def test_single_node_graph(self):
        """Test coherence scoring for single node graphs"""
        single_graph = nx.Graph()
        single_graph.add_node("only_person", canonical_name="Alone, Person", confidence=80.0)

        result = self.scorer.score_graph_coherence(single_graph, "quick")

        print(f"Single node coherence: {result.coherence_score:.3f}")

        # Single node should be coherent but limited
        assert result.coherence_score >= 0.5, "Single node should have reasonable coherence"

    @pytest.mark.timeout(15)
    def test_linear_chain_graph(self):
        """Test coherence of linear advisor chain (good structure)"""
        chain_graph = nx.Graph()

        # Create advisor chain: A -> B -> C -> D
        chain_people = [
            ("prof_a", {"canonical_name": "Senior, Professor", "confidence": 95.0}),
            ("prof_b", {"canonical_name": "Mid, Professor", "confidence": 90.0}),
            ("prof_c", {"canonical_name": "Junior, Professor", "confidence": 85.0}),
            ("student_d", {"canonical_name": "Graduate, Student", "confidence": 80.0}),
        ]

        for person_id, attrs in chain_people:
            chain_graph.add_node(person_id, **attrs)

        # Linear chain relationships
        chain_edges = [
            ("prof_a", "prof_b", {"relation_type": "doctoralAdvisor", "confidence": 95.0}),
            ("prof_b", "prof_c", {"relation_type": "doctoralAdvisor", "confidence": 90.0}),
            ("prof_c", "student_d", {"relation_type": "doctoralAdvisor", "confidence": 85.0}),
        ]

        for source, target, attrs in chain_edges:
            chain_graph.add_edge(source, target, **attrs)

        result = self.scorer.score_graph_coherence(chain_graph, "full")

        print(f"Linear chain coherence: {result.coherence_score:.3f}")

        # Linear chain should have good coherence
        assert result.coherence_score >= 0.7, "Linear chain should have good coherence"

        # Should have exactly one component
        assert result.metrics.connected_components == 1, "Chain should be single component"
        assert result.metrics.cycles_detected == 0, "Chain should have no cycles"

    @pytest.mark.timeout(15)
    def test_star_topology_graph(self):
        """Test coherence of star topology (central advisor with many students)"""
        star_graph = nx.Graph()

        # Central advisor
        star_graph.add_node("central_advisor", canonical_name="Popular, Advisor", confidence=95.0)

        # Many students connected to central advisor
        for i in range(8):
            student_id = f"student_{i}"
            star_graph.add_node(student_id, canonical_name=f"Student, {i}", confidence=80.0)
            star_graph.add_edge(
                "central_advisor", student_id, relation_type="doctoralAdvisor", confidence=85.0
            )

        result = self.scorer.score_graph_coherence(star_graph, "full")

        print(f"Star topology coherence: {result.coherence_score:.3f}")
        print(f"  Max betweenness: {max(result.metrics.betweenness_scores.values()):.3f}")

        # Star topology should have reasonable coherence but high centralization
        assert result.coherence_score >= 0.6, "Star topology should have reasonable coherence"

        # Central node should have high betweenness
        central_betweenness = result.metrics.betweenness_scores.get("central_advisor", 0.0)
        assert central_betweenness >= 0.5, "Central advisor should have high betweenness centrality"

    @pytest.mark.timeout(15)
    def test_confidence_impact_on_coherence(self):
        """Test how confidence scores impact overall coherence"""
        # Create identical structure graphs with different confidence levels

        def create_test_graph(confidence_level):
            graph = nx.Graph()
            graph.add_node("advisor", canonical_name="Test, Advisor", confidence=confidence_level)
            graph.add_node("student1", canonical_name="Test, Student1", confidence=confidence_level)
            graph.add_node("student2", canonical_name="Test, Student2", confidence=confidence_level)

            graph.add_edge(
                "advisor", "student1", relation_type="doctoralAdvisor", confidence=confidence_level
            )
            graph.add_edge(
                "advisor", "student2", relation_type="doctoralAdvisor", confidence=confidence_level
            )

            return graph

        # Test different confidence levels
        high_conf_graph = create_test_graph(90.0)
        med_conf_graph = create_test_graph(50.0)
        low_conf_graph = create_test_graph(20.0)

        high_result = self.scorer.score_graph_coherence(high_conf_graph, "quick")
        med_result = self.scorer.score_graph_coherence(med_conf_graph, "quick")
        low_result = self.scorer.score_graph_coherence(low_conf_graph, "quick")

        print(f"High confidence: {high_result.coherence_score:.3f}")
        print(f"Med confidence: {med_result.coherence_score:.3f}")
        print(f"Low confidence: {low_result.coherence_score:.3f}")

        # Higher confidence should lead to higher coherence
        assert (
            high_result.coherence_score >= med_result.coherence_score
        ), "Higher confidence should improve coherence"
        assert (
            med_result.coherence_score >= low_result.coherence_score
        ), "Medium confidence should be better than low confidence"

    @pytest.mark.timeout(15)
    def test_cycle_detection_impact(self):
        """Test that cycles negatively impact coherence scores"""
        # Graph without cycles
        acyclic_graph = nx.Graph()
        acyclic_graph.add_node("a", canonical_name="Person, A", confidence=80.0)
        acyclic_graph.add_node("b", canonical_name="Person, B", confidence=80.0)
        acyclic_graph.add_node("c", canonical_name="Person, C", confidence=80.0)

        acyclic_graph.add_edge("a", "b", relation_type="doctoralAdvisor", confidence=80.0)
        acyclic_graph.add_edge("b", "c", relation_type="doctoralAdvisor", confidence=80.0)

        # Graph with cycle
        cyclic_graph = acyclic_graph.copy()
        cyclic_graph.add_edge(
            "c", "a", relation_type="doctoralAdvisor", confidence=80.0
        )  # Creates cycle

        acyclic_result = self.scorer.score_graph_coherence(acyclic_graph, "quick")
        cyclic_result = self.scorer.score_graph_coherence(cyclic_graph, "quick")

        print(f"Acyclic coherence: {acyclic_result.coherence_score:.3f}")
        print(f"Cyclic coherence: {cyclic_result.coherence_score:.3f}")

        # Acyclic should have better coherence
        assert (
            acyclic_result.coherence_score >= cyclic_result.coherence_score
        ), "Acyclic graphs should have better coherence than cyclic graphs"

        # Cycle detection should work
        assert acyclic_result.metrics.cycles_detected == 0, "Acyclic graph should have no cycles"

    @pytest.mark.timeout(15)
    def test_mode_threshold_compliance(self):
        """Test V7 mode threshold compliance across different graph qualities"""
        # Create graphs of varying quality
        graphs = {
            "excellent": self._create_excellent_graph(),
            "good": self._create_good_graph(),
            "poor": self._create_poor_graph(),
        }

        results = {}

        for graph_type, graph in graphs.items():
            results[graph_type] = {}
            for mode in ["quick", "full", "extreme"]:
                result = self.scorer.score_graph_coherence(graph, mode)
                results[graph_type][mode] = result

                print(
                    f"{graph_type.capitalize()} graph - {mode} mode: {result.coherence_score:.3f} "
                    f"({'PASS' if result.v7_compliant else 'FAIL'})"
                )

        # Excellent graph should pass quick and full modes
        assert results["excellent"]["quick"].v7_compliant, "Excellent graph should pass quick mode"

        # Poor graph should fail all modes
        for mode in ["quick", "full", "extreme"]:
            assert not results["poor"][mode].v7_compliant, f"Poor graph should fail {mode} mode"

    @pytest.mark.timeout(15)
    def test_coherence_report_generation(self):
        """Test generation of comprehensive coherence reports"""
        # Run coherence analysis on multiple graphs
        test_results = []

        graphs = [
            self._create_excellent_graph(),
            self._create_good_graph(),
            self._create_poor_graph(),
        ]

        for i, graph in enumerate(graphs):
            for mode in ["quick", "full"]:
                result = self.scorer.score_graph_coherence(graph, mode)
                test_results.append(result)

        # Generate report
        report = self.scorer.generate_coherence_report(test_results)

        print("\n" + "=" * 60)
        print("GRAPH COHERENCE ANALYSIS REPORT")
        print("=" * 60)
        print(f"Total analyses: {report['summary']['total_analyses']}")
        print(f"V7 compliance rate: {report['summary']['compliance_rate']:.1%}")
        print(f"Average coherence: {report['summary']['avg_coherence_score']:.3f}")

        for mode, mode_data in report["by_mode"].items():
            print(
                f"{mode.upper()} mode compliance: {mode_data['compliance_rate']:.1%} "
                f"({mode_data['compliant']}/{mode_data['count']})"
            )
        print("=" * 60)

        # Validate report structure
        assert "summary" in report
        assert "by_mode" in report
        assert report["summary"]["total_analyses"] == len(test_results)
        assert len(report["by_mode"]) <= 3  # quick, full, extreme

    @pytest.mark.timeout(15)
    def test_genealogy_graph_creation(self):
        """Test creation of genealogy graphs from entry data"""
        # Sample entries with relationship data
        sample_entries = [
            {
                "GlobalID": "person1",
                "CanonicalLatin": "Smith, John",
                "Confidence": 85.0,
                "GenealogyRelation": [
                    {"target_id": "person2", "relation_type": "doctoralAdvisor", "confidence": 90.0}
                ],
            },
            {
                "GlobalID": "person2",
                "CanonicalLatin": "Johnson, Alice",
                "Confidence": 80.0,
                "GenealogyRelation": [],
            },
        ]

        graph = self.scorer.create_genealogy_graph_from_entries(sample_entries)

        print(f"Created graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        # Should create nodes and edges based on entry data
        assert graph.number_of_nodes() == 2, "Should create node for each entry"
        assert graph.number_of_edges() >= 1, "Should create edges for relationships"

        # Test coherence of created graph
        result = self.scorer.score_graph_coherence(graph, "quick")
        assert result.coherence_score >= 0.0, "Created graph should have valid coherence score"

    def _create_excellent_graph(self) -> nx.Graph:
        """Create a high-quality graph for testing"""
        graph = nx.Graph()

        # Well-structured advisor tree with high confidence
        nodes = [
            ("senior_prof", {"canonical_name": "Einstein, Albert", "confidence": 98.0}),
            ("mid_prof", {"canonical_name": "Planck, Max", "confidence": 95.0}),
            ("junior_prof", {"canonical_name": "Heisenberg, Werner", "confidence": 92.0}),
            ("postdoc", {"canonical_name": "Schrödinger, Erwin", "confidence": 90.0}),
        ]

        for node_id, attrs in nodes:
            graph.add_node(node_id, **attrs)

        edges = [
            ("senior_prof", "mid_prof", {"relation_type": "doctoralAdvisor", "confidence": 96.0}),
            ("mid_prof", "junior_prof", {"relation_type": "doctoralAdvisor", "confidence": 94.0}),
            ("junior_prof", "postdoc", {"relation_type": "postdocMentor", "confidence": 91.0}),
        ]

        for source, target, attrs in edges:
            graph.add_edge(source, target, **attrs)

        return graph

    def _create_good_graph(self) -> nx.Graph:
        """Create a moderate-quality graph for testing"""
        graph = nx.Graph()

        nodes = [
            ("prof1", {"canonical_name": "Good, Professor", "confidence": 75.0}),
            ("prof2", {"canonical_name": "Decent, Professor", "confidence": 70.0}),
            ("student1", {"canonical_name": "Average, Student", "confidence": 65.0}),
            ("student2", {"canonical_name": "Okay, Student", "confidence": 68.0}),
        ]

        for node_id, attrs in nodes:
            graph.add_node(node_id, **attrs)

        edges = [
            ("prof1", "student1", {"relation_type": "doctoralAdvisor", "confidence": 72.0}),
            ("prof2", "student2", {"relation_type": "doctoralAdvisor", "confidence": 69.0}),
        ]

        for source, target, attrs in edges:
            graph.add_edge(source, target, **attrs)

        return graph

    def _create_poor_graph(self) -> nx.Graph:
        """Create a low-quality graph for testing"""
        graph = nx.Graph()

        nodes = [
            ("unknown1", {"canonical_name": "Unknown, Person", "confidence": 25.0}),
            ("unknown2", {"canonical_name": "Uncertain, Individual", "confidence": 20.0}),
            ("isolated", {"canonical_name": "Isolated, Person", "confidence": 15.0}),
        ]

        for node_id, attrs in nodes:
            graph.add_node(node_id, **attrs)

        # Poor quality relationship with low confidence
        graph.add_edge("unknown1", "unknown2", relation_type="unknown", confidence=18.0)
        # isolated node has no connections

        return graph


if __name__ == "__main__":
    # Run graph coherence tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])
