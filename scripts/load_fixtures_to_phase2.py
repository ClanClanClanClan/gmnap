#!/usr/bin/env python3
"""
Load Fixture Data to Phase 2 Memgraph

Reads the validated fixture edges and loads them into Phase 2 database.
This completes Step 3 of the expert plan.

Usage:
    python3 scripts/load_fixtures_to_phase2.py
"""

import json
from neo4j import GraphDatabase
from datetime import datetime

# Fixture data (from validated_edges.jsonl)
FIXTURE_EDGES = [
    {
        "student_global_id": "GMN-PPRQPSUTHAI3N6LMUG7UVI",
        "student_name": "Dupont, Marie",
        "advisor_global_id": "GMN-ISH5C4SIJOD7ZGXDD5JASK",
        "advisor_name": "Martin, Jean",
        "degree_date": "2019",
        "institution": "Sorbonne University",
        "degree_type": "PhD",
        "confidence": 0.92,
        "sources": ["FR_THESIS"],
        "verified": False,
        "provenance_hash": "WRUI2PK3GESRMYOICGSGBDLPQJ",
    },
    {
        "student_global_id": "GMN-PPRQPSUTHAI3N6LMUG7UVI",
        "student_name": "Dupont, Marie",
        "advisor_global_id": "GMN-DZFUEXC3TSUXHCE47TAK3Q",
        "advisor_name": "Bernard, Claire",
        "degree_date": "2019",
        "institution": "Sorbonne University",
        "degree_type": "PhD",
        "confidence": 0.92,
        "sources": ["FR_THESIS"],
        "verified": False,
        "provenance_hash": "5R7YGSF7MGJVXQTBOZ6WMG3S32",
    },
    {
        "student_global_id": "GMN-BTF2FMC2QCGZBMZPRQRRDP",
        "student_name": "García López, Miguel",
        "advisor_global_id": "GMN-7WXO6LAEBIOY7HRWIGQVGG",
        "advisor_name": "Pérez, Ana",
        "degree_date": "2018-06-15",
        "institution": "Universidad Complutense de Madrid",
        "degree_type": "PhD",
        "confidence": 0.92,
        "sources": ["ES_TESIS"],
        "verified": False,
        "provenance_hash": "PM66ENT24PTAXB3PV4JFQ7VNDS",
    },
    {
        "student_global_id": "GMN-4BEPQLVCZ2RN6X3OSZDYRA",
        "student_name": "Silva, João",
        "advisor_global_id": "GMN-IRYCIJEEIBEP7AUR4DWD23",
        "advisor_name": "Souza, Carlos",
        "degree_date": "2017-12",
        "institution": "University of São Paulo",
        "degree_type": "PhD",
        "confidence": 0.92,
        "sources": ["BR_BDTD"],
        "verified": False,
        "provenance_hash": "MQGVOJYVGYH236XZSJ3ZEESWSP",
    },
]


def load_fixtures():
    """Load fixture nodes and edges to Phase 2"""
    driver = GraphDatabase.driver("bolt://localhost:7688", auth=None)

    print("=" * 70)
    print("Loading Fixture Data to Phase 2")
    print("=" * 70)
    print()

    with driver.session() as session:
        # Create fixture nodes and relationships
        for edge in FIXTURE_EDGES:
            # Create student node
            session.run(
                """
                MERGE (student:Mathematician {global_id: $student_gid})
                ON CREATE SET
                    student.canonical_latin = $student_name,
                    student.is_fixture = true,
                    student.created_at = datetime()
                ON MATCH SET
                    student.canonical_latin = COALESCE(student.canonical_latin, $student_name)
            """,
                student_gid=edge["student_global_id"],
                student_name=edge["student_name"],
            )

            # Create advisor node
            session.run(
                """
                MERGE (advisor:Mathematician {global_id: $advisor_gid})
                ON CREATE SET
                    advisor.canonical_latin = $advisor_name,
                    advisor.is_fixture = true,
                    advisor.created_at = datetime()
                ON MATCH SET
                    advisor.canonical_latin = COALESCE(advisor.canonical_latin, $advisor_name)
            """,
                advisor_gid=edge["advisor_global_id"],
                advisor_name=edge["advisor_name"],
            )

            # Create DOCTORAL_ADVISOR relationship
            session.run(
                """
                MATCH (student:Mathematician {global_id: $student_gid})
                MATCH (advisor:Mathematician {global_id: $advisor_gid})
                MERGE (student)-[r:DOCTORAL_ADVISOR]->(advisor)
                SET r.degree_date = $degree_date,
                    r.institution = $institution,
                    r.degree_type = $degree_type,
                    r.confidence = $confidence,
                    r.sources = $sources,
                    r.verified = $verified,
                    r.provenance_hash = $provenance_hash,
                    r.is_fixture = true,
                    r.created_at = datetime()
            """,
                student_gid=edge["student_global_id"],
                advisor_gid=edge["advisor_global_id"],
                degree_date=edge["degree_date"],
                institution=edge["institution"],
                degree_type=edge["degree_type"],
                confidence=edge["confidence"],
                sources=edge["sources"],
                verified=edge["verified"],
                provenance_hash=edge["provenance_hash"],
            )

        # Count results
        fixture_nodes = session.run(
            """
            MATCH (n:Mathematician)
            WHERE n.is_fixture = true
            RETURN count(n) as count
        """
        ).single()["count"]

        all_nodes = session.run("MATCH (n:Mathematician) RETURN count(n) as count").single()[
            "count"
        ]

        fixture_edges = session.run(
            """
            MATCH ()-[r:DOCTORAL_ADVISOR]->()
            WHERE r.is_fixture = true
            RETURN count(r) as count
        """
        ).single()["count"]

        all_edges = session.run(
            "MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) as count"
        ).single()["count"]

        print(f"✅ Fixture nodes created: {fixture_nodes}")
        print(f"✅ DOCTORAL_ADVISOR edges created: {fixture_edges}")
        print()
        print(f"Total Phase 2 database:")
        print(f"  Nodes: {all_nodes} ({all_nodes - fixture_nodes} V7 + {fixture_nodes} fixtures)")
        print(f"  Edges: {all_edges}")
        print()

        # Verify Step 3 requirements
        print("Step 3 Verification:")
        print(
            f"  - 8 nodes (4 students + 4 advisors): {'✅' if fixture_nodes >= 8 else '❌'} (have {fixture_nodes})"
        )
        print(
            f"  - 4 DOCTORAL_ADVISOR edges: {'✅' if fixture_edges >= 4 else '❌'} (have {fixture_edges})"
        )
        print()

        if fixture_nodes >= 8 and fixture_edges >= 4:
            print("🎉 Step 3 SUCCESS: Standalone Phase 2 deployed with fixtures!")
        else:
            print(
                f"⚠️ Step 3 INCOMPLETE: Need {8-fixture_nodes} more nodes, {4-fixture_edges} more edges"
            )

    driver.close()


if __name__ == "__main__":
    load_fixtures()
