#!/usr/bin/env python3
"""Apply graph schema to Memgraph."""
import os
from neo4j import GraphDatabase

# Read schema
schema_path = "src/graph/graph_schema.cypher"
with open(schema_path, "r") as f:
    schema = f.read()

# Connect to Memgraph
uri = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
driver = GraphDatabase.driver(uri, auth=None)

# Apply schema
with driver.session() as session:
    for line in schema.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("//"):
            print(f"Executing: {line}")
            session.run(line)
            print("✅ Success")

driver.close()
print("\n✅ Graph schema applied successfully")
