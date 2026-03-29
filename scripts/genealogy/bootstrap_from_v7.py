#!/usr/bin/env python3
"""
Bootstrap Phase 2 Genealogy Database from V7 Data

Migrates mathematician nodes and DOCTORAL_ADVISOR relationships from the
V7 Memgraph database (port 7687) to the Phase 2 Memgraph database (port 7688).

This script:
1. Connects to both V7 and Phase 2 Memgraph instances
2. Exports all Mathematician nodes from V7
3. Exports all DOCTORAL_ADVISOR relationships from V7
4. Imports nodes to Phase 2 (preserving GlobalIDs)
5. Imports relationships to Phase 2
6. Verifies data integrity

Usage:
    python3 scripts/genealogy/bootstrap_from_v7.py [--dry-run] [--batch-size 1000]

Options:
    --dry-run        Show what would be migrated without actually migrating
    --batch-size N   Number of records to process per batch (default: 1000)
    --v7-uri URI     V7 Memgraph URI (default: bolt://localhost:7687)
    --phase2-uri URI Phase 2 Memgraph URI (default: bolt://localhost:7688)
"""

import argparse
import logging
from typing import Dict, List, Tuple
from datetime import datetime
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GenealogyBootstrapper:
    """Handles migration of genealogy data from V7 to Phase 2"""

    def __init__(
        self,
        v7_uri: str = "bolt://localhost:7687",
        phase2_uri: str = "bolt://localhost:7688",
        batch_size: int = 1000,
        dry_run: bool = False,
    ):
        self.v7_uri = v7_uri
        self.phase2_uri = phase2_uri
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Connect to both databases
        self.v7_driver = GraphDatabase.driver(v7_uri, auth=None)
        self.phase2_driver = GraphDatabase.driver(phase2_uri, auth=None)

        logger.info(f"Connected to V7: {v7_uri}")
        logger.info(f"Connected to Phase 2: {phase2_uri}")
        if dry_run:
            logger.warning("DRY RUN MODE - No data will be written")

    def close(self):
        """Close database connections"""
        if hasattr(self, "v7_driver"):
            self.v7_driver.close()
        if hasattr(self, "phase2_driver"):
            self.phase2_driver.close()
        logger.info("Connections closed")

    def export_nodes(self) -> List[Dict]:
        """Export all Mathematician nodes from V7 with ALL properties"""
        logger.info("Exporting nodes from V7...")

        query = """
            MATCH (m:Mathematician)
            RETURN properties(m) as props
        """

        with self.v7_driver.session() as session:
            result = session.run(query)
            nodes = []

            for record in result:
                # Get all properties from V7
                props = dict(record["props"])

                # Ensure global_id exists
                if not props.get("global_id"):
                    logger.warning(f"Node missing global_id, skipping: {props}")
                    continue

                nodes.append(props)

            logger.info(
                f"✅ Exported {len(nodes)} Mathematician nodes with all properties"
            )
            if nodes:
                sample = nodes[0]
                logger.info(f"   Sample properties: {list(sample.keys())}")
            return nodes

    def export_relationships(self) -> List[Dict]:
        """Export all DOCTORAL_ADVISOR relationships from V7"""
        logger.info("Exporting relationships from V7...")

        query = """
            MATCH (student:Mathematician)-[r:DOCTORAL_ADVISOR]->(advisor:Mathematician)
            RETURN student.global_id as student_id,
                   advisor.global_id as advisor_id,
                   r.degree_date as degree_date,
                   r.institution as institution,
                   r.degree_type as degree_type,
                   r.confidence as confidence,
                   r.sources as sources,
                   r.verified as verified,
                   r.provenance_hash as provenance_hash,
                   properties(r) as props
        """

        with self.v7_driver.session() as session:
            result = session.run(query)
            relationships = []

            for record in result:
                relationships.append(
                    {
                        "student_id": record["student_id"],
                        "advisor_id": record["advisor_id"],
                        "degree_date": record.get("degree_date"),
                        "institution": record.get("institution"),
                        "degree_type": record.get("degree_type"),
                        "confidence": record.get("confidence"),
                        "sources": record.get("sources"),
                        "verified": record.get("verified"),
                        "provenance_hash": record.get("provenance_hash"),
                        "props": dict(record["props"]),
                    }
                )

            logger.info(
                f"✅ Exported {len(relationships)} DOCTORAL_ADVISOR relationships"
            )
            return relationships

    def import_nodes(self, nodes: List[Dict]) -> int:
        """Import nodes to Phase 2 with ALL properties"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would import {len(nodes)} nodes")
            return len(nodes)

        logger.info(f"Importing {len(nodes)} nodes to Phase 2 with all properties...")

        imported = 0
        with self.phase2_driver.session() as session:
            for i in range(0, len(nodes), self.batch_size):
                batch = nodes[i : i + self.batch_size]

                for node in batch:
                    # Build SET clause dynamically for all properties
                    # Exclude global_id (used in MATCH) and datetime fields (set automatically)
                    props_to_set = {
                        k: v
                        for k, v in node.items()
                        if k != "global_id" and not k.endswith("_at")
                    }

                    session.run(
                        """
                        MERGE (m:Mathematician {global_id: $global_id})
                        SET m += $props,
                            m.migrated_at = datetime(),
                            m.migrated_from = 'v7'
                    """,
                        global_id=node["global_id"],
                        props=props_to_set,
                    )
                    imported += 1

                if (i + len(batch)) % 100 == 0 or (i + len(batch)) == len(nodes):
                    logger.info(f"  Imported {imported}/{len(nodes)} nodes...")

        logger.info(f"✅ Imported {imported} nodes with complete V7 data")
        return imported

    def import_relationships(self, relationships: List[Dict]) -> int:
        """Import relationships to Phase 2"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would import {len(relationships)} relationships")
            return len(relationships)

        logger.info(f"Importing {len(relationships)} relationships to Phase 2...")

        imported = 0
        with self.phase2_driver.session() as session:
            for i in range(0, len(relationships), self.batch_size):
                batch = relationships[i : i + self.batch_size]

                for rel in batch:
                    session.run(
                        """
                        MATCH (student:Mathematician {global_id: $student_id})
                        MATCH (advisor:Mathematician {global_id: $advisor_id})
                        MERGE (student)-[r:DOCTORAL_ADVISOR]->(advisor)
                        SET r.degree_date = $degree_date,
                            r.institution = $institution,
                            r.degree_type = $degree_type,
                            r.confidence = $confidence,
                            r.sources = $sources,
                            r.verified = $verified,
                            r.provenance_hash = $provenance_hash,
                            r.updated_at = datetime()
                    """,
                        student_id=rel["student_id"],
                        advisor_id=rel["advisor_id"],
                        degree_date=rel.get("degree_date"),
                        institution=rel.get("institution"),
                        degree_type=rel.get("degree_type"),
                        confidence=rel.get("confidence"),
                        sources=rel.get("sources"),
                        verified=rel.get("verified"),
                        provenance_hash=rel.get("provenance_hash"),
                    )
                    imported += 1

                logger.info(
                    f"  Imported {imported}/{len(relationships)} relationships..."
                )

        logger.info(f"✅ Imported {imported} relationships")
        return imported

    def verify_migration(self, expected_nodes: int, expected_rels: int) -> bool:
        """Verify migration completed successfully"""
        logger.info("Verifying migration...")

        with self.phase2_driver.session() as session:
            # Count nodes
            result = session.run("MATCH (m:Mathematician) RETURN count(m) as count")
            actual_nodes = result.single()["count"]

            # Count relationships
            result = session.run(
                "MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) as count"
            )
            actual_rels = result.single()["count"]

        success = (actual_nodes == expected_nodes) and (actual_rels == expected_rels)

        if success:
            logger.info(f"✅ VERIFICATION PASSED")
            logger.info(f"   Nodes: {actual_nodes}/{expected_nodes}")
            logger.info(f"   Relationships: {actual_rels}/{expected_rels}")
        else:
            logger.error(f"❌ VERIFICATION FAILED")
            logger.error(f"   Nodes: {actual_nodes}/{expected_nodes} (expected)")
            logger.error(f"   Relationships: {actual_rels}/{expected_rels} (expected)")

        return success

    def run(self) -> bool:
        """Execute the complete migration"""
        logger.info("=" * 70)
        logger.info("Starting V7 → Phase 2 Genealogy Bootstrap")
        logger.info("=" * 70)

        try:
            # Export from V7
            nodes = self.export_nodes()
            relationships = self.export_relationships()

            if not nodes:
                logger.warning("No nodes to migrate!")
                return False

            # Import to Phase 2
            imported_nodes = self.import_nodes(nodes)
            imported_rels = self.import_relationships(relationships)

            # Verify
            if not self.dry_run:
                success = self.verify_migration(imported_nodes, imported_rels)
                return success
            else:
                logger.info("[DRY RUN] Skipping verification")
                return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

        finally:
            logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Phase 2 from V7 data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without writing",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000, help="Records per batch (default: 1000)"
    )
    parser.add_argument(
        "--v7-uri", default="bolt://localhost:7687", help="V7 Memgraph URI"
    )
    parser.add_argument(
        "--phase2-uri", default="bolt://localhost:7688", help="Phase 2 Memgraph URI"
    )

    args = parser.parse_args()

    bootstrapper = GenealogyBootstrapper(
        v7_uri=args.v7_uri,
        phase2_uri=args.phase2_uri,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    try:
        success = bootstrapper.run()
        if success:
            logger.info("🎉 Migration completed successfully!")
            return 0
        else:
            logger.error("❌ Migration failed")
            return 1

    finally:
        bootstrapper.close()


if __name__ == "__main__":
    import sys

    sys.exit(main())
