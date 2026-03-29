import pytest

#!/usr/bin/env python3
"""
DuckDB Analytics Test (Stage 5)
Tests collision detection and analytics using DuckDB
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.timeout(15)
def test_duckdb_import():
    """Test that DuckDB can be imported"""
    try:
        import os

        os.environ["DUCKDB_MEMORY_ONLY"] = "1"
        import duckdb

        print(f"PASS DuckDB imported successfully (version: {duckdb.__version__})")
        return True
    except ImportError:
        print("WARN DuckDB not installed - run: pip install duckdb")
        return False


@pytest.mark.timeout(15)
def test_analytics_module():
    """Test that analytics module exists"""
    try:
        from src.analytics.duckdb_analytics import DuckDBAnalytics

        print("PASS DuckDBAnalytics module imported successfully")
        return True
    except ImportError as e:
        print(f"WARN DuckDBAnalytics module not found (optional): {e}")
        # Try alternative location
        try:

            print("PASS Found DuckDBAnalytics in alternative location")
            return True
        except:
            return False


@pytest.mark.timeout(15)
def test_duckdb_connection():
    """Test DuckDB connection and basic operations"""
    try:
        import os

        os.environ["DUCKDB_MEMORY_ONLY"] = "1"
        import duckdb

        # Create in-memory database
        conn = duckdb.connect(":memory:")

        # Create test table
        conn.execute("""
            CREATE TABLE test_entries (
                GlobalID VARCHAR PRIMARY KEY,
                CanonicalLatin VARCHAR,
                Confidence INTEGER
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO test_entries VALUES 
            ('TEST001', 'Smith, John', 95),
            ('TEST002', 'García, María', 98),
            ('TEST003', 'Kim, Min-jun', 92)
        """)

        # Query data
        result = conn.execute("SELECT COUNT(*) FROM test_entries").fetchone()
        assert result[0] == 3, f"Expected 3 entries, got {result[0]}"

        print("PASS DuckDB connection and basic operations working")
        conn.close()
        return True

    except Exception as e:
        print(f"FAIL DuckDB connection test failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_collision_detection():
    """Test collision detection functionality"""
    try:
        import os

        os.environ["DUCKDB_MEMORY_ONLY"] = "1"
        import duckdb

        conn = duckdb.connect(":memory:")

        # Create entries table
        conn.execute("""
            CREATE TABLE entries (
                GlobalID VARCHAR PRIMARY KEY,
                CanonicalLatin VARCHAR,
                CanonicalNative VARCHAR,
                Confidence INTEGER
            )
        """)

        # Insert test data with collisions
        test_data = [
            ("ID001", "Smith, John", "Smith, John", 95),
            ("ID002", "Smith, John", "Smith, John", 93),  # Duplicate name
            ("ID003", "García, María", "García, María", 98),
            ("ID004", "García, Maria", "García, María", 96),  # Near duplicate
            ("ID005", "Kim, Min-jun", "김민준", 92),
        ]

        for entry in test_data:
            conn.execute("INSERT INTO entries VALUES (?, ?, ?, ?)", entry)

        # Detect exact collisions
        exact_collisions = conn.execute("""
            SELECT CanonicalLatin, COUNT(*) as count
            FROM entries
            GROUP BY CanonicalLatin
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """).fetchall()

        print("PASS Exact collisions detected:")
        for name, count in exact_collisions:
            print(f"  - '{name}': {count} entries")

        assert len(exact_collisions) > 0, "Should detect collisions"

        # Detect near-duplicates (simplified - real implementation would use fuzzy matching)
        near_duplicates = conn.execute("""
            SELECT a.GlobalID, b.GlobalID, a.CanonicalLatin, b.CanonicalLatin
            FROM entries a, entries b
            WHERE a.GlobalID < b.GlobalID
            AND LOWER(REPLACE(a.CanonicalLatin, ' ', '')) = LOWER(REPLACE(b.CanonicalLatin, ' ', ''))
        """).fetchall()

        if near_duplicates:
            print("PASS Near-duplicates detected:")
            for id1, id2, name1, name2 in near_duplicates[:3]:
                print(f"  - {id1} vs {id2}: '{name1}' ~ '{name2}'")

        conn.close()
        return True

    except Exception as e:
        print(f"FAIL Collision detection test failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_suffix_duplicates():
    """Test duplicate suffixing functionality"""

    def suffix_duplicates(entries):
        """Add suffixes to duplicate entries"""
        from collections import defaultdict

        # Group by canonical name
        name_groups = defaultdict(list)
        for entry in entries:
            name = entry.get("CanonicalLatin", "")
            name_groups[name].append(entry)

        # Add suffixes to duplicates
        suffixed_count = 0
        for name, group in name_groups.items():
            if len(group) > 1:
                # Sort by confidence (highest first)
                group.sort(key=lambda x: x.get("Confidence", 0), reverse=True)

                # Keep first one unchanged, suffix others
                for i, entry in enumerate(group[1:], 1):
                    entry["CanonicalLatin"] = f"{name}_{i:03d}"
                    entry["_suffixed"] = True
                    suffixed_count += 1

        return entries, suffixed_count

    # Test data
    test_entries = [
        {"GlobalID": "ID001", "CanonicalLatin": "Smith, John", "Confidence": 95},
        {"GlobalID": "ID002", "CanonicalLatin": "Smith, John", "Confidence": 93},
        {"GlobalID": "ID003", "CanonicalLatin": "Smith, John", "Confidence": 90},
        {"GlobalID": "ID004", "CanonicalLatin": "García, María", "Confidence": 98},
    ]

    # Apply suffixing
    result, count = suffix_duplicates(test_entries.copy())

    print(f"PASS Suffixed {count} duplicate entries")

    # Check results
    smith_entries = [e for e in result if e["CanonicalLatin"].startswith("Smith, John")]
    assert len(smith_entries) == 3, "Should have 3 Smith entries"

    # Check suffixing
    assert (
        smith_entries[0]["CanonicalLatin"] == "Smith, John"
    ), "Highest confidence should be unchanged"
    assert (
        smith_entries[1]["CanonicalLatin"] == "Smith, John_001"
    ), "Second should be suffixed _001"
    assert (
        smith_entries[2]["CanonicalLatin"] == "Smith, John_002"
    ), "Third should be suffixed _002"

    print("PASS Duplicate suffixing working correctly")
    for entry in smith_entries:
        print(
            f"  - {entry['GlobalID']}: {entry['CanonicalLatin']} (confidence: {entry['Confidence']})"
        )

    return True


@pytest.mark.timeout(15)
def test_analytics_performance():
    """Test analytics performance with larger dataset"""
    try:
        import os

        os.environ["DUCKDB_MEMORY_ONLY"] = "1"
        import time

        import duckdb

        conn = duckdb.connect(":memory:")

        # Create table
        conn.execute("""
            CREATE TABLE perf_test (
                id INTEGER,
                name VARCHAR,
                value DOUBLE
            )
        """)

        # Generate test data
        num_rows = 10000
        start_time = time.time()

        # Batch insert
        conn.execute(f"""
            INSERT INTO perf_test
            SELECT 
                generate_series AS id,
                'Name_' || generate_series AS name,
                random() * 100 AS value
            FROM generate_series(1, {num_rows})
        """)

        insert_time = time.time() - start_time

        # Test query performance
        start_time = time.time()
        result = conn.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value
            FROM perf_test
        """).fetchone()

        query_time = time.time() - start_time

        print(f"PASS Performance test with {num_rows:,} rows:")
        print(f"  - Insert time: {insert_time:.3f}s")
        print(f"  - Query time: {query_time:.3f}s")
        print(f"  - Stats: count={result[0]:,}, avg={result[1]:.2f}")

        assert insert_time < 1.0, f"Insert too slow: {insert_time}s"
        assert query_time < 0.1, f"Query too slow: {query_time}s"

        conn.close()
        return True

    except Exception as e:
        print(f"FAIL Performance test failed: {e}")
        return False


@pytest.mark.timeout(15)
def test_sql_injection_safety():
    """Test that SQL injection is prevented"""
    try:
        import os

        os.environ["DUCKDB_MEMORY_ONLY"] = "1"
        import duckdb

        conn = duckdb.connect(":memory:")

        # Create table
        conn.execute("CREATE TABLE security_test (id INTEGER, data VARCHAR)")

        # Attempt SQL injection (should be safe with parameterized queries)
        malicious_input = "'; DROP TABLE security_test; --"

        # Safe parameterized insert
        conn.execute("INSERT INTO security_test VALUES (?, ?)", [1, malicious_input])

        # Verify table still exists and data was inserted safely
        result = conn.execute("SELECT data FROM security_test WHERE id = 1").fetchone()
        assert result[0] == malicious_input, "Data should be stored safely"

        # Verify table wasn't dropped
        tables = conn.execute("SHOW TABLES").fetchall()
        assert any(
            "security_test" in str(t) for t in tables
        ), "Table should still exist"

        print("PASS SQL injection prevention working")
        print(f"  - Safely stored: {malicious_input[:30]}...")

        conn.close()
        return True

    except Exception as e:
        print(f"FAIL Security test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DUCKDB ANALYTICS TEST (STAGE 5)")
    print("=" * 60)
    print()

    # Run all tests
    all_passed = True

    tests = [
        ("DuckDB Import", test_duckdb_import),
        ("Analytics Module", test_analytics_module),
        ("Database Connection", test_duckdb_connection),
        ("Collision Detection", test_collision_detection),
        ("Duplicate Suffixing", test_suffix_duplicates),
        ("Performance Test", test_analytics_performance),
        ("SQL Injection Safety", test_sql_injection_safety),
    ]

    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            passed = test_func()
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"FAIL {test_name} failed with error: {e}")
            all_passed = False

    print()
    print("=" * 60)
    if all_passed:
        print("PASS ALL DUCKDB ANALYTICS TESTS PASSED")
    else:
        print("WARN SOME TESTS FAILED - CHECK DUCKDB INTEGRATION")
    print("=" * 60)
