#!/usr/bin/env python3
"""
genealogy/match_person_ids.py
Match normalized names to GMNAP GlobalIDs for genealogy edges.
Supports both lookup (existing DB) and generate (new data) modes.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

# Import GMNAP components
from src.core.global_id import global_id

logger = logging.getLogger(__name__)


class PersonIDMatcher:
    """
    Match genealogy edge names to GMNAP GlobalIDs.

    Modes:
    - generate: Generate new GlobalIDs for all persons (initial load)
    - lookup: Query Memgraph for existing persons (future)
    """

    def __init__(
        self,
        mode: str = "generate",
        bolt_uri: Optional[str] = None,
        birth_year_window: int = 50,
    ):
        """
        Initialize ID matcher.

        Args:
            mode: 'generate' or 'lookup'
            bolt_uri: Memgraph connection URI (for lookup mode)
            birth_year_window: Year window for disambiguation (±years)
        """
        self.mode = mode
        self.bolt_uri = bolt_uri
        self.birth_year_window = birth_year_window

        # Cache for generated IDs (canonical_name -> GlobalID)
        self.name_to_id: Dict[str, str] = {}

        # Statistics
        self.stats = {
            "total_edges": 0,
            "unique_persons": 0,
            "students_processed": 0,
            "advisors_processed": 0,
            "ids_generated": 0,
            "ids_reused": 0,
        }

    def match_edges(self, edges_file: str) -> List[Dict[str, Any]]:
        """
        Match all persons in edges to GlobalIDs.

        Args:
            edges_file: Path to normalized edges JSON file

        Returns:
            List of edges with GlobalIDs added
        """
        print("=" * 80)
        print("PERSON ID MATCHING")
        print("=" * 80)
        print()
        print(f"Input: {edges_file}")
        print(f"Mode: {self.mode}")
        print()
        print("-" * 80)

        # Load edges
        with open(edges_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        edges = data.get("edges", [])
        metadata = data.get("metadata", {})

        print(f"Loaded {len(edges):,} edges")
        print()

        # Process each edge
        matched_edges = []
        for i, edge in enumerate(edges):
            matched_edge = self._match_edge(edge)
            matched_edges.append(matched_edge)

            # Progress
            if (i + 1) % 1000 == 0:
                print(f"  Processed {i+1:,}/{len(edges):,} edges...")

        print()
        print("-" * 80)
        print("MATCHING COMPLETE")
        print("-" * 80)
        print()

        self._print_stats()

        return matched_edges

    def _match_edge(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match persons in a single edge to GlobalIDs.

        Args:
            edge: Edge with normalized names

        Returns:
            Edge with GlobalIDs added
        """
        self.stats["total_edges"] += 1

        # Extract normalized data
        student_canonical = edge.get("student_normalized", "")
        advisor_canonical = edge.get("advisor_normalized", "")
        thesis_year = edge.get("thesis_year")

        # Get or generate GlobalIDs
        student_id = self._get_or_generate_id(
            student_canonical, thesis_year, is_student=True
        )
        advisor_id = self._get_or_generate_id(
            advisor_canonical, thesis_year, is_student=False
        )

        # Add to edge
        edge["student_global_id"] = student_id
        edge["advisor_global_id"] = advisor_id

        # Track statistics
        self.stats["students_processed"] += 1
        self.stats["advisors_processed"] += 1

        return edge

    def _get_or_generate_id(
        self, canonical_name: str, thesis_year: Optional[int], is_student: bool
    ) -> str:
        """
        Get existing or generate new GlobalID for a person.

        Args:
            canonical_name: Canonical form "FAMILY, Given"
            thesis_year: Year of thesis (for birth year estimation)
            is_student: True if student, False if advisor

        Returns:
            GlobalID string
        """
        # Check cache first
        if canonical_name in self.name_to_id:
            self.stats["ids_reused"] += 1
            return self.name_to_id[canonical_name]

        # Generate mode: Create new GlobalID
        if self.mode == "generate":
            new_id = self._generate_new_id(canonical_name, thesis_year, is_student)
            self.name_to_id[canonical_name] = new_id
            self.stats["ids_generated"] += 1
            self.stats["unique_persons"] += 1
            return new_id

        # Lookup mode: Query database (future implementation)
        elif self.mode == "lookup":
            # TODO: Implement Memgraph query
            # For now, fall back to generate
            new_id = self._generate_new_id(canonical_name, thesis_year, is_student)
            self.name_to_id[canonical_name] = new_id
            self.stats["ids_generated"] += 1
            self.stats["unique_persons"] += 1
            return new_id

        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _generate_new_id(
        self, canonical_name: str, thesis_year: Optional[int], is_student: bool
    ) -> str:
        """
        Generate new GlobalID using GMNAP algorithm.

        For genealogy data without birth/death years:
        - Use canonical name only (birth=None, death=None)
        - This creates a base ID that can be refined later

        Args:
            canonical_name: "FAMILY, Given"
            thesis_year: Year of thesis
            is_student: Whether this is a student

        Returns:
            22-char Base32 GlobalID
        """
        # For now, we don't have birth/death years from thesis metadata
        # Use thesis year to estimate birth year for disambiguation
        birth_year_estimate = None

        if thesis_year:
            # Rough estimation:
            # - Student: typically 25-35 at PhD, so birth ~thesis_year - 30
            # - Advisor: typically 40-60 at supervision, so birth ~thesis_year - 50
            if is_student:
                birth_year_estimate = thesis_year - 30
            else:
                birth_year_estimate = thesis_year - 50

        # Generate GlobalID
        # NOTE: For pilot, we use birth_year_estimate=None to avoid incorrect data
        # In production, we'd query OpenAlex/ORCID/etc for actual birth years
        gid = global_id(
            canonical_native=canonical_name,
            birth=None,
            death=None,  # Don't use estimates for now
        )

        return gid

    def _print_stats(self):
        """Print matching statistics."""
        print("📊 MATCHING STATISTICS:")
        print()
        print(f"  Edges:")
        print(f"    Total edges processed: {self.stats['total_edges']:,}")
        print()
        print(f"  Persons:")
        print(f"    Unique persons: {self.stats['unique_persons']:,}")
        print(f"    Students: {self.stats['students_processed']:,}")
        print(f"    Advisors: {self.stats['advisors_processed']:,}")
        print()
        print(f"  GlobalIDs:")
        print(f"    New IDs generated: {self.stats['ids_generated']:,}")
        print(f"    Existing IDs reused: {self.stats['ids_reused']:,}")
        if self.stats["ids_generated"] + self.stats["ids_reused"] > 0:
            reuse_pct = (
                self.stats["ids_reused"]
                / (self.stats["ids_generated"] + self.stats["ids_reused"])
                * 100
            )
            print(f"    Reuse rate: {reuse_pct:.1f}%")
        print()

        # Top persons by edge count
        if self.name_to_id:
            # Count occurrences in reverse lookup
            name_counts = defaultdict(int)
            # Note: This is simplified - in practice we'd track this during matching
            print(f"  Total unique canonical names: {len(self.name_to_id):,}")

        print("=" * 80)

    def save_matched_edges(
        self, edges: List[Dict], output_file: str, include_summary: bool = True
    ):
        """
        Save matched edges to JSON file.

        Args:
            edges: List of edges with GlobalIDs
            output_file: Path to output file
            include_summary: Whether to include person summary
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create person summary (unique persons and their IDs)
        person_summary = {}
        if include_summary:
            for canonical_name, gid in self.name_to_id.items():
                person_summary[gid] = {
                    "canonical_name": canonical_name,
                    "global_id": gid,
                }

        # Save
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "matching_date": datetime.now().isoformat(),
                        "mode": self.mode,
                        "total_edges": len(edges),
                        "unique_persons": len(self.name_to_id),
                        "stats": self.stats,
                    },
                    "edges": edges,
                    "persons": person_summary,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✅ Matched edges saved: {output_path}")
        print(f"   Total edges: {len(edges):,}")
        print(f"   Unique persons: {len(self.name_to_id):,}")
        if include_summary:
            print(f"   Person summary included")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Match genealogy persons to GlobalIDs")
    parser.add_argument(
        "--input", required=True, help="Input normalized edges JSON file"
    )
    parser.add_argument(
        "--output", required=True, help="Output matched edges JSON file"
    )
    parser.add_argument(
        "--mode",
        default="generate",
        choices=["generate", "lookup"],
        help="Matching mode (default: generate)",
    )
    parser.add_argument(
        "--bolt-uri", default=None, help="Memgraph Bolt URI (for lookup mode)"
    )

    args = parser.parse_args()

    matcher = PersonIDMatcher(mode=args.mode, bolt_uri=args.bolt_uri)
    edges = matcher.match_edges(args.input)
    matcher.save_matched_edges(edges, args.output)


if __name__ == "__main__":
    main()
