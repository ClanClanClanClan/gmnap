#!/usr/bin/env python3
"""
Load test fixture data into Neo4j for live_api tests.

Seeds the graph database with sample mathematician genealogy data
that test_api_comprehensive.py expects.

Usage:
    python3 tools/load_test_fixtures.py
    python3 tools/load_test_fixtures.py --uri bolt://localhost:7688
"""
from __future__ import annotations

import argparse
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: pip install neo4j")
    sys.exit(1)

DB_URI = "bolt://localhost:7688"

# Sample genealogy data: advisor → student relationships
FIXTURE_DATA = [
    # Root advisor (Gauss-like figure)
    {
        "global_id": "GAUSSCARLFRIEDRICH01",
        "canonical_name": "Gauss, Carl Friedrich",
        "birth_year": 1777,
        "death_year": 1855,
        "country": "DE",
        "advisors": [],
    },
    # Generation 1
    {
        "global_id": "DIRICHLETPETERGUST01",
        "canonical_name": "Dirichlet, Peter Gustav Lejeune",
        "birth_year": 1805,
        "death_year": 1859,
        "country": "DE",
        "advisors": ["GAUSSCARLFRIEDRICH01"],
    },
    {
        "global_id": "RIEMANNBERNHARDGE01",
        "canonical_name": "Riemann, Bernhard",
        "birth_year": 1826,
        "death_year": 1866,
        "country": "DE",
        "advisors": ["GAUSSCARLFRIEDRICH01"],
    },
    # Generation 2
    {
        "global_id": "LIPSCHITZRUDOLPHOT01",
        "canonical_name": "Lipschitz, Rudolf",
        "birth_year": 1832,
        "death_year": 1903,
        "country": "DE",
        "advisors": ["DIRICHLETPETERGUST01"],
    },
    {
        "global_id": "KLEINFELIXCHRISTIA01",
        "canonical_name": "Klein, Felix",
        "birth_year": 1849,
        "death_year": 1925,
        "country": "DE",
        "advisors": ["LIPSCHITZRUDOLPHOT01"],
    },
    # Generation 3
    {
        "global_id": "HILBERTDAVIDWILHEL01",
        "canonical_name": "Hilbert, David",
        "birth_year": 1862,
        "death_year": 1943,
        "country": "DE",
        "advisors": ["KLEINFELIXCHRISTIA01"],
    },
    # Generation 4 (multiple students of Hilbert)
    {
        "global_id": "ZERMELOEERNSTFRIED01",
        "canonical_name": "Zermelo, Ernst",
        "birth_year": 1871,
        "death_year": 1953,
        "country": "DE",
        "advisors": ["HILBERTDAVIDWILHEL01"],
    },
    {
        "global_id": "COURANTRICHARDKURT01",
        "canonical_name": "Courant, Richard",
        "birth_year": 1888,
        "death_year": 1972,
        "country": "US",
        "advisors": ["HILBERTDAVIDWILHEL01"],
    },
    {
        "global_id": "WEYLHERMANNKLAUS01",
        "canonical_name": "Weyl, Hermann",
        "birth_year": 1885,
        "death_year": 1955,
        "country": "US",
        "advisors": ["HILBERTDAVIDWILHEL01"],
    },
    # A person with no advisors (orphan)
    {
        "global_id": "EULERLEEONHARDPAUL01",
        "canonical_name": "Euler, Leonhard",
        "birth_year": 1707,
        "death_year": 1783,
        "country": "CH",
        "advisors": [],
    },
    # A person with no students (leaf)
    {
        "global_id": "FRIEDRICHSKURTOTTO01",
        "canonical_name": "Friedrichs, Kurt",
        "birth_year": 1901,
        "death_year": 1982,
        "country": "US",
        "advisors": ["COURANTRICHARDKURT01"],
    },
    # A person with multiple advisors
    {
        "global_id": "LAXPETERDAVIDHUNG01",
        "canonical_name": "Lax, Peter",
        "birth_year": 1926,
        "death_year": None,
        "country": "US",
        "advisors": ["COURANTRICHARDKURT01", "FRIEDRICHSKURTOTTO01"],
    },
]


def load_fixtures(uri: str):
    """Load fixture data into Neo4j."""
    driver = GraphDatabase.driver(uri)

    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        print(f"Cleared existing data in {uri}")

        # Create constraint for GlobalID uniqueness
        try:
            session.run(
                "CREATE CONSTRAINT person_global_id IF NOT EXISTS "
                "FOR (p:Person) REQUIRE p.global_id IS UNIQUE"
            )
        except Exception:
            pass  # Constraint may already exist

        # Create person nodes
        for person in FIXTURE_DATA:
            session.run(
                """
                CREATE (p:Person {
                    global_id: $gid,
                    canonical_name: $name,
                    birth_year: $birth,
                    death_year: $death,
                    country: $country
                })
                """,
                gid=person["global_id"],
                name=person["canonical_name"],
                birth=person["birth_year"],
                death=person["death_year"],
                country=person["country"],
            )
        print(f"Created {len(FIXTURE_DATA)} person nodes")

        # Create DOCTORAL_ADVISOR edges
        edge_count = 0
        for person in FIXTURE_DATA:
            for advisor_id in person["advisors"]:
                session.run(
                    """
                    MATCH (student:Person {global_id: $sid})
                    MATCH (advisor:Person {global_id: $aid})
                    CREATE (student)-[:DOCTORAL_ADVISOR]->(advisor)
                    """,
                    sid=person["global_id"],
                    aid=advisor_id,
                )
                edge_count += 1
        print(f"Created {edge_count} DOCTORAL_ADVISOR edges")

        # Verify
        result = session.run(
            "MATCH (s:Person)-[:DOCTORAL_ADVISOR]->(a:Person) "
            "RETURN count(*) as edges"
        )
        count = result.single()["edges"]
        print(f"Verified: {count} edges in database")

    driver.close()
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Load test fixtures into Neo4j")
    parser.add_argument("--uri", default=DB_URI, help=f"Neo4j URI (default: {DB_URI})")
    args = parser.parse_args()
    load_fixtures(args.uri)


if __name__ == "__main__":
    main()
