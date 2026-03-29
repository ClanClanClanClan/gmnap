#!/usr/bin/env python3
"""Verify Memgraph graph contents."""

import os
from neo4j import GraphDatabase

uri = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
driver = GraphDatabase.driver(uri, auth=None)

print("🔍 Verifying Memgraph graph...")
print(f"📡 Connected to: {uri}\n")

with driver.session() as session:
    # Count nodes
    result = session.run("MATCH (m:Mathematician) RETURN count(m) AS count")
    node_count = result.single()["count"]
    print(f"✅ Total mathematician nodes: {node_count}")

    # Count edges
    result = session.run("MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) AS count")
    edge_count = result.single()["count"]
    print(f"📊 Total doctoral advisor edges: {edge_count}")

    # Sample nodes
    result = session.run("""
        MATCH (m:Mathematician)
        RETURN m.canonical_latin AS name, m.region_code AS region, m.birth_year AS birth
        LIMIT 10
    """)
    print("\n📋 Sample mathematician nodes:")
    for record in result:
        print(f"  - {record['name']} (Region: {record['region']}, Born: {record['birth']})")

    # Check indexes
    result = session.run("SHOW INDEX INFO")
    print("\n🔑 Indexes:")
    for record in result:
        print(f"  - {record}")

driver.close()
print("\n✅ Graph verification complete")
