#!/usr/bin/env python3
"""
Comprehensive Genealogy API Testing Suite
Tests all endpoints, edge cases, performance, and data integrity
"""

import pytest
import requests
import time
from typing import Dict, List, Optional
from neo4j import GraphDatabase

BASE_URL = "http://localhost:8080"
DB_URI = "bolt://localhost:7688"


class TestGenealogyAPI:
    """Comprehensive test suite for genealogy API"""

    @classmethod
    def setup_class(cls):
        """Setup test fixtures"""
        cls.base_url = BASE_URL
        cls.driver = GraphDatabase.driver(DB_URI)

        # Get sample IDs from database
        with cls.driver.session() as s:
            result = s.run("""
                MATCH (student:Person)-[:DOCTORAL_ADVISOR]->(advisor:Person)
                RETURN
                    student.global_id as student_id,
                    student.canonical_name as student_name,
                    advisor.global_id as advisor_id,
                    advisor.canonical_name as advisor_name
                LIMIT 5
            """)
            cls.sample_data = list(result)

    @classmethod
    def teardown_class(cls):
        """Cleanup"""
        cls.driver.close()

    # ========================================
    # 1. HEALTH & BASIC ENDPOINTS
    # ========================================

    def test_healthz_endpoint(self):
        """Test /healthz returns OK"""
        response = requests.get(f"{self.base_url}/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_readyz_endpoint(self):
        """Test /readyz returns ready"""
        response = requests.get(f"{self.base_url}/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_metrics_endpoint(self):
        """Test /metrics returns prometheus format"""
        response = requests.get(f"{self.base_url}/metrics")
        assert response.status_code == 200
        assert b"# HELP" in response.content

    # ========================================
    # 2. GENEALOGY STATS ENDPOINT
    # ========================================

    def test_stats_basic(self):
        """Test /genealogy/stats returns valid data"""
        response = requests.get(f"{self.base_url}/genealogy/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "statistics" in data

        stats = data["statistics"]
        assert stats["persons"] > 0
        assert stats["relationships"] > 0

    def test_stats_confidence_distribution(self):
        """Test confidence distribution is valid"""
        response = requests.get(f"{self.base_url}/genealogy/stats")
        data = response.json()

        dist = data["statistics"]["confidence_distribution"]
        assert "high" in dist
        assert "medium" in dist
        assert "low" in dist

        total = dist["high"] + dist["medium"] + dist["low"]
        assert total > 0

    def test_stats_performance(self):
        """Test stats endpoint response time"""
        start = time.time()
        response = requests.get(f"{self.base_url}/genealogy/stats")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should be under 500ms

    # ========================================
    # 3. LINEAGE ENDPOINT (ANCESTORS)
    # ========================================

    def test_lineage_basic(self):
        """Test lineage endpoint with valid ID"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(f"{self.base_url}/genealogy/lineage/{student_id}")

        assert response.status_code == 200
        data = response.json()
        assert "start" in data
        assert "paths" in data
        assert data["start"] == student_id

    def test_lineage_with_depth(self):
        """Test lineage with custom depth parameter"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == 3

    def test_lineage_max_depth_limit(self):
        """Test lineage respects max depth of 50"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}",
            params={"max_depth": 100},  # Request 100
        )

        assert response.status_code == 200
        data = response.json()
        assert data["depth"] <= 50  # Should be capped at 50

    def test_lineage_min_depth(self):
        """Test lineage with minimum depth of 1"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 0}  # Request 0
        )

        assert response.status_code == 200
        data = response.json()
        assert data["depth"] >= 1  # Should be at least 1

    def test_lineage_invalid_id(self):
        """Test lineage with non-existent ID"""
        response = requests.get(f"{self.base_url}/genealogy/lineage/INVALIDXXXXXXXXXXXXXX")

        assert response.status_code == 200
        data = response.json()
        # Should return empty paths, not error
        assert "paths" in data
        assert len(data["paths"]) == 0

    def test_lineage_malformed_id(self):
        """Test lineage with malformed ID"""
        response = requests.get(f"{self.base_url}/genealogy/lineage/SHORT")

        # Should handle gracefully (either 400 or return empty)
        assert response.status_code in [200, 400]

    # ========================================
    # 4. DESCENDANTS ENDPOINT (STUDENTS)
    # ========================================

    def test_descendants_basic(self):
        """Test descendants endpoint with valid ID"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        advisor_id = self.sample_data[0]["advisor_id"]
        response = requests.get(f"{self.base_url}/genealogy/descendants/{advisor_id}")

        assert response.status_code == 200
        data = response.json()
        assert "start" in data
        assert "paths" in data

    def test_descendants_with_depth(self):
        """Test descendants with custom depth"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        advisor_id = self.sample_data[0]["advisor_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/descendants/{advisor_id}", params={"max_depth": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == 2

    def test_descendants_invalid_id(self):
        """Test descendants with non-existent ID"""
        response = requests.get(f"{self.base_url}/genealogy/descendants/INVALIDXXXXXXXXXXXXXX")

        assert response.status_code == 200
        data = response.json()
        assert "paths" in data

    # ========================================
    # 5. BIDIRECTIONAL CONSISTENCY
    # ========================================

    def test_bidirectional_consistency(self):
        """Test lineage and descendants are inverses"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        advisor_id = self.sample_data[0]["advisor_id"]

        # Get lineage from student
        lineage = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 1}
        ).json()

        # Get descendants from advisor
        descendants = requests.get(
            f"{self.base_url}/genealogy/descendants/{advisor_id}", params={"max_depth": 1}
        ).json()

        # Student should appear in advisor's descendants
        desc_ids = set()
        for path in descendants["paths"]:
            desc_ids.update(path["nodes"])

        assert student_id in desc_ids

    # ========================================
    # 6. DATA INTEGRITY
    # ========================================

    def test_path_structure(self):
        """Test path objects have required fields"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(f"{self.base_url}/genealogy/lineage/{student_id}")

        data = response.json()
        if len(data["paths"]) > 0:
            path = data["paths"][0]
            assert "length" in path
            assert "nodes" in path
            assert isinstance(path["nodes"], list)
            assert len(path["nodes"]) == path["length"] + 1

    def test_node_ids_valid_format(self):
        """Test all node IDs are valid GlobalIDs"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(f"{self.base_url}/genealogy/lineage/{student_id}")

        data = response.json()
        for path in data["paths"]:
            for node_id in path["nodes"]:
                # GlobalID should be 22 characters
                assert len(node_id) == 22
                # Should be alphanumeric
                assert node_id.isalnum()

    # ========================================
    # 7. PERFORMANCE TESTS
    # ========================================

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures

        def make_request():
            return requests.get(f"{self.base_url}/genealogy/stats")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in results)

    def test_response_time_consistency(self):
        """Test response times are consistent"""
        times = []
        for _ in range(10):
            start = time.time()
            requests.get(f"{self.base_url}/genealogy/stats")
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Average should be under 500ms
        assert avg_time < 0.5
        # No outliers over 2 seconds
        assert max_time < 2.0

    def test_deep_query_performance(self):
        """Test performance with deep queries"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]

        start = time.time()
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 20}
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Deep queries should complete in reasonable time
        assert elapsed < 5.0

    # ========================================
    # 8. ERROR HANDLING
    # ========================================

    def test_missing_depth_parameter(self):
        """Test default depth when parameter omitted"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(f"{self.base_url}/genealogy/lineage/{student_id}")

        assert response.status_code == 200
        data = response.json()
        # Should use default depth (10)
        assert data["depth"] == 10

    def test_negative_depth(self):
        """Test handling of negative depth"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": -5}
        )

        assert response.status_code == 200
        data = response.json()
        # Should normalize to at least 1
        assert data["depth"] >= 1

    def test_non_numeric_depth(self):
        """Test handling of non-numeric depth"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]
        response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": "abc"}
        )

        # Should either use default or return error
        assert response.status_code in [200, 400]

    # ========================================
    # 9. SPECIAL CASES
    # ========================================

    def test_person_with_no_advisor(self):
        """Test person with no known advisors"""
        # Find a person with no advisors
        with self.driver.session() as s:
            result = s.run("""
                MATCH (p:Person)
                WHERE NOT (p)-[:DOCTORAL_ADVISOR]->()
                RETURN p.global_id as id
                LIMIT 1
            """)
            record = result.single()

            if record:
                person_id = record["id"]
                response = requests.get(f"{self.base_url}/genealogy/lineage/{person_id}")

                assert response.status_code == 200
                data = response.json()
                # Should return empty paths
                assert len(data["paths"]) == 0

    def test_person_with_no_students(self):
        """Test person with no known students"""
        # Find a person with no students
        with self.driver.session() as s:
            result = s.run("""
                MATCH (p:Person)
                WHERE NOT (p)<-[:DOCTORAL_ADVISOR]-()
                RETURN p.global_id as id
                LIMIT 1
            """)
            record = result.single()

            if record:
                person_id = record["id"]
                response = requests.get(f"{self.base_url}/genealogy/descendants/{person_id}")

                assert response.status_code == 200
                data = response.json()
                assert len(data["paths"]) == 0

    def test_person_with_multiple_advisors(self):
        """Test person with multiple advisors"""
        # Find someone with 2+ advisors
        with self.driver.session() as s:
            result = s.run("""
                MATCH (student:Person)-[:DOCTORAL_ADVISOR]->(advisor:Person)
                WITH student, count(advisor) as advisor_count
                WHERE advisor_count >= 2
                RETURN student.global_id as id
                LIMIT 1
            """)
            record = result.single()

            if record:
                student_id = record["id"]
                response = requests.get(
                    f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 1}
                )

                assert response.status_code == 200
                data = response.json()
                # Should have multiple paths
                assert len(data["paths"]) >= 2

    # ========================================
    # 10. CROSS-VALIDATION WITH DATABASE
    # ========================================

    def test_database_consistency(self):
        """Test API results match direct database queries"""
        if not self.sample_data:
            pytest.skip("No sample data available")

        student_id = self.sample_data[0]["student_id"]

        # Get from API
        api_response = requests.get(
            f"{self.base_url}/genealogy/lineage/{student_id}", params={"max_depth": 1}
        ).json()

        # Get from database
        with self.driver.session() as s:
            db_result = s.run(
                """
                MATCH (s:Person {global_id: $id})
                MATCH path = (s)-[:DOCTORAL_ADVISOR*1..1]->(advisor)
                RETURN length(path) as len, [n IN nodes(path) | n.global_id] as ids
            """,
                id=student_id,
            )
            db_paths = list(db_result)

        # Should have same number of direct advisors
        if len(db_paths) > 0:
            assert len(api_response["paths"]) == len(db_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
