#!/usr/bin/env python3
"""
genealogy/extract_edges.py
Extract DOCTORAL_ADVISOR edges from harvested thesis metadata.
Filters institutions, creates student-advisor pairs with metadata.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
from datetime import datetime


class EdgeExtractor:
    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize edge extractor.

        Args:
            min_confidence: Minimum confidence score to include edge
        """
        self.min_confidence = min_confidence

        # Institution patterns to filter out (more comprehensive)
        self.institution_patterns = [
            # French institutions
            r"\bparis\s+\d+\b",
            r"\btoulouse\s+\d+\b",
            r"\blyon\s+\d+\b",
            r"\bbordeaux\s+\d+\b",
            r"\bstrasbourg\b",
            r"\bmulhouse\b",
            r"\bnancy\s+\d+\b",
            r"\binsa\b",
            r"\bisae\b",
            r"\bcomuE\b",
            # Generic patterns
            r"^\d+$",  # Just numbers
            r"\b(université|university)\b",
            r"\b(institut|institute)\b",
        ]

    def extract_from_harvest(self, harvest_file: str) -> List[Dict[str, Any]]:
        """
        Extract edges from harvest JSON file.

        Args:
            harvest_file: Path to harvest JSON file

        Returns:
            List of edge dictionaries
        """
        print("=" * 80)
        print("DOCTORAL_ADVISOR EDGE EXTRACTION")
        print("=" * 80)
        print()
        print(f"Input: {harvest_file}")
        print(f"Min confidence: {self.min_confidence}")
        print()
        print("-" * 80)

        # Load harvest data
        with open(harvest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle both 'records' and 'sample_records' keys
        records = data.get("records", [])
        if not records:
            records = data.get("sample_records", [])
        metadata = data.get("metadata", {})

        print(f"Loaded {len(records):,} records")
        print()

        # Extract edges
        edges = []
        stats = {
            "total_records": len(records),
            "records_with_edges": 0,
            "total_edges_raw": 0,
            "edges_after_filtering": 0,
            "filtered_out_institutions": 0,
            "filtered_out_low_confidence": 0,
        }

        for i, record in enumerate(records):
            record_edges = self._extract_from_record(record)

            if record_edges:
                stats["records_with_edges"] += 1
                stats["total_edges_raw"] += len(record_edges)

                # Filter edges
                filtered_edges = []
                for edge in record_edges:
                    if self._is_institution(edge["advisor_raw"]):
                        stats["filtered_out_institutions"] += 1
                        continue

                    if edge["confidence"] < self.min_confidence:
                        stats["filtered_out_low_confidence"] += 1
                        continue

                    filtered_edges.append(edge)

                edges.extend(filtered_edges)
                stats["edges_after_filtering"] += len(filtered_edges)

            # Progress
            if (i + 1) % 1000 == 0:
                print(
                    f"  Processed {i+1:,}/{len(records):,} records... "
                    f"({len(edges):,} edges so far)"
                )

        print()
        print("-" * 80)
        print("EXTRACTION COMPLETE")
        print("-" * 80)
        print()

        self._print_stats(stats, edges)

        return edges

    def _extract_from_record(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract edges from a single thesis record.

        Args:
            record: Thesis metadata record

        Returns:
            List of edges (may be empty)
        """
        creators = record.get("creators", [])
        advisors = record.get("advisors_text", [])
        date = record.get("date", "")
        title = record.get("title", "")

        if not creators or not advisors:
            return []

        edges = []
        year = self._extract_year(date)

        for creator in creators:
            for advisor in advisors:
                # Create edge
                edge = {
                    "student_raw": creator,
                    "advisor_raw": advisor,
                    "thesis_year": year,
                    "thesis_title": title,
                    "confidence": self._calculate_confidence(creator, advisor, year),
                    "source": "FR_STAR_OAI",
                    "metadata": {"date": date, "country": "FR"},
                }
                edges.append(edge)

        return edges

    def _extract_year(self, date_str: str) -> int:
        """Extract year from date string."""
        if not date_str:
            return None
        if len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None

    def _calculate_confidence(self, student: str, advisor: str, year: int) -> float:
        """
        Calculate confidence score for edge.

        Factors:
        - Name format quality
        - Presence of year
        - Not obviously institution
        """
        score = 1.0

        # Check student name format
        if not self._is_valid_name(student):
            score *= 0.7

        # Check advisor name format
        if not self._is_valid_name(advisor):
            score *= 0.7

        # Missing year reduces confidence
        if not year:
            score *= 0.8

        # Names that look like institutions
        if self._is_institution(student):
            score *= 0.3
        if self._is_institution(advisor):
            score *= 0.3

        return score

    def _is_valid_name(self, name: str) -> bool:
        """Check if name looks valid (has comma or multiple words)."""
        if not name:
            return False
        # Good format: "Lastname, Firstname"
        if "," in name:
            return True
        # Alternative: Multiple capitalized words
        words = name.split()
        if len(words) >= 2 and all(w[0].isupper() for w in words if w):
            return True
        return False

    def _is_institution(self, name: str) -> bool:
        """Check if name looks like institution rather than person."""
        if not name:
            return False

        name_lower = name.lower()

        for pattern in self.institution_patterns:
            if re.search(pattern, name_lower):
                return True

        return False

    def _print_stats(self, stats: Dict, edges: List[Dict]):
        """Print extraction statistics."""
        print("📊 EXTRACTION STATISTICS:")
        print()
        print(f"  Input:")
        print(f"    Total records: {stats['total_records']:,}")
        if stats["total_records"] > 0:
            print(
                f"    Records with edges: {stats['records_with_edges']:,} "
                f"({stats['records_with_edges']/stats['total_records']*100:.1f}%)"
            )
        else:
            print(f"    Records with edges: 0 (no records loaded)")
        print()
        print(f"  Edges:")
        print(f"    Raw edges extracted: {stats['total_edges_raw']:,}")
        print(f"    Filtered out (institutions): {stats['filtered_out_institutions']:,}")
        print(f"    Filtered out (low confidence): {stats['filtered_out_low_confidence']:,}")
        print(f"    Final edges: {stats['edges_after_filtering']:,}")
        print()

        # Confidence distribution
        if edges:
            confidences = [e["confidence"] for e in edges]
            print(f"  Confidence Distribution:")
            print(f"    Min: {min(confidences):.2f}")
            print(f"    Max: {max(confidences):.2f}")
            print(f"    Mean: {sum(confidences)/len(confidences):.2f}")
            print(
                f"    High (≥0.90): {sum(1 for c in confidences if c >= 0.9):,} "
                f"({sum(1 for c in confidences if c >= 0.9)/len(confidences)*100:.1f}%)"
            )
            print()

        # Year distribution
        years = [e["thesis_year"] for e in edges if e["thesis_year"]]
        if years:
            year_counts = Counter(years)
            print(f"  Temporal Coverage:")
            print(f"    Year range: {min(years)} - {max(years)}")
            print(
                f"    Records with years: {len(years):,}/{len(edges):,} "
                f"({len(years)/len(edges)*100:.1f}%)"
            )
            print(f"    Top years:")
            for year, count in year_counts.most_common(5):
                print(f"      {year}: {count:,} edges")
            print()

        # Top advisors
        if edges:
            advisor_counts = Counter(e["advisor_raw"] for e in edges)
            print(f"  Top Advisors (by edge count):")
            for i, (advisor, count) in enumerate(advisor_counts.most_common(10), 1):
                print(f"    {i:2d}. {advisor[:40]:40s} ({count:,} students)")
            print()

        print("=" * 80)

    def save_edges(self, edges: List[Dict], output_file: str):
        """
        Save extracted edges to JSON file.

        Args:
            edges: List of edge dictionaries
            output_file: Path to output file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "extraction_date": datetime.now().isoformat(),
                        "total_edges": len(edges),
                        "min_confidence": self.min_confidence,
                        "source": "FR_STAR_OAI",
                    },
                    "edges": edges,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✅ Edges saved: {output_path}")
        print(f"   Total edges: {len(edges):,}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract doctoral advisor edges")
    parser.add_argument("--input", required=True, help="Input harvest JSON file")
    parser.add_argument("--output", required=True, help="Output edges JSON file")
    parser.add_argument(
        "--min-confidence", type=float, default=0.5, help="Minimum confidence score (default: 0.5)"
    )

    args = parser.parse_args()

    extractor = EdgeExtractor(min_confidence=args.min_confidence)
    edges = extractor.extract_from_harvest(args.input)
    extractor.save_edges(edges, args.output)


if __name__ == "__main__":
    main()
