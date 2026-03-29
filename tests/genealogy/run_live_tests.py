#!/usr/bin/env python3
"""
Direct comprehensive testing without pytest mocking
Runs all tests against live API and database
"""

import concurrent.futures
import time

import requests
from neo4j import GraphDatabase

BASE_URL = "http://localhost:8080"
DB_URI = "bolt://localhost:7688"


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def add_pass(self, test_name, details=""):
        self.passed.append((test_name, details))
        print(f"✅ PASS: {test_name}")
        if details:
            print(f"   {details}")

    def add_fail(self, test_name, error):
        self.failed.append((test_name, str(error)))
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")

    def add_skip(self, test_name, reason):
        self.skipped.append((test_name, reason))
        print(f"⏭️  SKIP: {test_name} - {reason}")

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print(f"\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⏭️  Skipped: {len(self.skipped)}")
        print(f"Success Rate: {len(self.passed)/total*100:.1f}%")
        return len(self.failed) == 0


def run_tests():
    results = TestResults()

    # Setup
    print("Setting up test environment...")
    driver = GraphDatabase.driver(DB_URI)

    # Get sample data
    with driver.session() as s:
        sample_result = s.run("""
            MATCH (student:Person)-[:DOCTORAL_ADVISOR]->(advisor:Person)
            RETURN
                student.global_id as student_id,
                student.canonical_name as student_name,
                advisor.global_id as advisor_id,
                advisor.canonical_name as advisor_name
            LIMIT 5
        """)
        sample_data = list(sample_result)

    print(f"Found {len(sample_data)} sample relationships for testing\n")
    print("=" * 70)

    # 1. Health Endpoints
    print("\n1. HEALTH & BASIC ENDPOINTS")
    print("-" * 70)

    try:
        r = requests.get(f"{BASE_URL}/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        results.add_pass(
            "healthz_endpoint", f"Response time: {r.elapsed.total_seconds():.3f}s"
        )
    except Exception as e:
        results.add_fail("healthz_endpoint", e)

    try:
        r = requests.get(f"{BASE_URL}/readyz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ready"
        results.add_pass("readyz_endpoint")
    except Exception as e:
        results.add_fail("readyz_endpoint", e)

    try:
        r = requests.get(f"{BASE_URL}/metrics")
        assert r.status_code == 200
        assert b"# HELP" in r.content
        results.add_pass("metrics_endpoint", f"Size: {len(r.content)} bytes")
    except Exception as e:
        results.add_fail("metrics_endpoint", e)

    # 2. Stats Endpoint
    print("\n2. GENEALOGY STATS ENDPOINT")
    print("-" * 70)

    try:
        r = requests.get(f"{BASE_URL}/genealogy/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["statistics"]["persons"] > 0
        assert data["statistics"]["relationships"] > 0
        results.add_pass(
            "stats_basic",
            f"Persons: {data['statistics']['persons']}, Edges: {data['statistics']['relationships']}",
        )
    except Exception as e:
        results.add_fail("stats_basic", e)

    try:
        r = requests.get(f"{BASE_URL}/genealogy/stats")
        data = r.json()
        dist = data["statistics"]["confidence_distribution"]
        assert "high" in dist and "medium" in dist and "low" in dist
        dist["high"] + dist["medium"] + dist["low"]
        results.add_pass(
            "stats_confidence",
            f"High: {dist['high']}, Medium: {dist['medium']}, Low: {dist['low']}",
        )
    except Exception as e:
        results.add_fail("stats_confidence", e)

    try:
        start = time.time()
        r = requests.get(f"{BASE_URL}/genealogy/stats")
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 0.5
        results.add_pass("stats_performance", f"Response time: {elapsed:.3f}s")
    except Exception as e:
        results.add_fail("stats_performance", e)

    # 3. Lineage Endpoint
    print("\n3. LINEAGE ENDPOINT (ANCESTORS)")
    print("-" * 70)

    if not sample_data:
        results.add_skip("lineage_tests", "No sample data")
    else:
        student_id = sample_data[0]["student_id"]
        advisor_id = sample_data[0]["advisor_id"]

        try:
            r = requests.get(f"{BASE_URL}/genealogy/lineage/{student_id}")
            assert r.status_code == 200
            data = r.json()
            assert "start" in data
            assert "paths" in data
            results.add_pass("lineage_basic", f"Found {len(data['paths'])} paths")
        except Exception as e:
            results.add_fail("lineage_basic", e)

        try:
            r = requests.get(
                f"{BASE_URL}/genealogy/lineage/{student_id}", params={"max_depth": 3}
            )
            assert r.status_code == 200
            data = r.json()
            assert data["depth"] == 3
            results.add_pass("lineage_with_depth")
        except Exception as e:
            results.add_fail("lineage_with_depth", e)

        try:
            r = requests.get(
                f"{BASE_URL}/genealogy/lineage/{student_id}", params={"max_depth": 100}
            )
            data = r.json()
            assert data["depth"] <= 50
            results.add_pass("lineage_max_depth_limit", f"Capped at {data['depth']}")
        except Exception as e:
            results.add_fail("lineage_max_depth_limit", e)

        try:
            r = requests.get(f"{BASE_URL}/genealogy/lineage/INVALIDXXXXXXXXXXXXXX")
            assert r.status_code == 200
            data = r.json()
            assert "paths" in data
            results.add_pass(
                "lineage_invalid_id", f"Returned {len(data['paths'])} paths (empty)"
            )
        except Exception as e:
            results.add_fail("lineage_invalid_id", e)

    # 4. Descendants Endpoint
    print("\n4. DESCENDANTS ENDPOINT (STUDENTS)")
    print("-" * 70)

    if not sample_data:
        results.add_skip("descendants_tests", "No sample data")
    else:
        try:
            r = requests.get(f"{BASE_URL}/genealogy/descendants/{advisor_id}")
            assert r.status_code == 200
            data = r.json()
            assert "start" in data
            assert "paths" in data
            results.add_pass("descendants_basic", f"Found {len(data['paths'])} paths")
        except Exception as e:
            results.add_fail("descendants_basic", e)

        try:
            r = requests.get(
                f"{BASE_URL}/genealogy/descendants/{advisor_id}",
                params={"max_depth": 2},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["depth"] == 2
            results.add_pass("descendants_with_depth")
        except Exception as e:
            results.add_fail("descendants_with_depth", e)

    # 5. Data Integrity
    print("\n5. DATA INTEGRITY")
    print("-" * 70)

    if sample_data:
        try:
            r = requests.get(f"{BASE_URL}/genealogy/lineage/{student_id}")
            data = r.json()
            if len(data["paths"]) > 0:
                path = data["paths"][0]
                assert "length" in path
                assert "nodes" in path
                assert len(path["nodes"]) == path["length"] + 1
                results.add_pass(
                    "path_structure",
                    f"Path length: {path['length']}, nodes: {len(path['nodes'])}",
                )
        except Exception as e:
            results.add_fail("path_structure", e)

        try:
            r = requests.get(f"{BASE_URL}/genealogy/lineage/{student_id}")
            data = r.json()
            for path in data["paths"]:
                for node_id in path["nodes"]:
                    assert len(node_id) == 22
                    assert node_id.isalnum()
            results.add_pass("node_ids_valid")
        except Exception as e:
            results.add_fail("node_ids_valid", e)

    # 6. Performance Tests
    print("\n6. PERFORMANCE TESTS")
    print("-" * 70)

    try:

        def make_request():
            return requests.get(f"{BASE_URL}/genealogy/stats")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in responses)
        results.add_pass("concurrent_requests", "20 concurrent requests succeeded")
    except Exception as e:
        results.add_fail("concurrent_requests", e)

    try:
        times = []
        for _ in range(10):
            start = time.time()
            requests.get(f"{BASE_URL}/genealogy/stats")
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)
        max_time = max(times)
        assert avg_time < 0.5
        assert max_time < 2.0
        results.add_pass(
            "response_consistency", f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s"
        )
    except Exception as e:
        results.add_fail("response_consistency", e)

    if sample_data:
        try:
            start = time.time()
            r = requests.get(
                f"{BASE_URL}/genealogy/lineage/{student_id}", params={"max_depth": 20}
            )
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 5.0
            results.add_pass("deep_query_performance", f"Depth 20: {elapsed:.3f}s")
        except Exception as e:
            results.add_fail("deep_query_performance", e)

    # 7. Error Handling
    print("\n7. ERROR HANDLING")
    print("-" * 70)

    if sample_data:
        try:
            r = requests.get(f"{BASE_URL}/genealogy/lineage/{student_id}")
            data = r.json()
            assert data["depth"] == 10  # Default
            results.add_pass("default_depth")
        except Exception as e:
            results.add_fail("default_depth", e)

        try:
            r = requests.get(
                f"{BASE_URL}/genealogy/lineage/{student_id}", params={"max_depth": -5}
            )
            assert r.status_code == 200
            data = r.json()
            assert data["depth"] >= 1
            results.add_pass("negative_depth_normalized")
        except Exception as e:
            results.add_fail("negative_depth_normalized", e)

    # 8. Database Consistency
    print("\n8. CROSS-VALIDATION WITH DATABASE")
    print("-" * 70)

    if sample_data:
        try:
            r = requests.get(
                f"{BASE_URL}/genealogy/lineage/{student_id}", params={"max_depth": 1}
            )
            api_paths = r.json()["paths"]

            with driver.session() as s:
                db_result = s.run(
                    """
                    MATCH (s:Person {global_id: $id})
                    MATCH path = (s)-[:DOCTORAL_ADVISOR*1..1]->(advisor)
                    RETURN length(path) as len, [n IN nodes(path) | n.global_id] as ids
                """,
                    id=student_id,
                )
                db_paths = list(db_result)

            if len(db_paths) > 0:
                assert len(api_paths) == len(db_paths)
                results.add_pass(
                    "database_consistency",
                    f"API paths: {len(api_paths)}, DB paths: {len(db_paths)}",
                )
        except Exception as e:
            results.add_fail("database_consistency", e)

    # Cleanup
    driver.close()

    # Summary
    return results.summary()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("COMPREHENSIVE GENEALOGY API TEST SUITE")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Database: {DB_URI}")
    print("=" * 70)

    success = run_tests()

    if success:
        print("\n🎉 ALL TESTS PASSED!")
        exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED - See details above")
        exit(1)
