#!/usr/bin/env python3
"""
genealogy/normalize_names.py
Normalize student and advisor names for GMNAP ID matching.
Handles French diacritics, particles, format standardization.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime


class NameNormalizer:
    def __init__(self):
        """Initialize name normalizer."""

        # French particles (lowercase in normalized form)
        self.french_particles = {"de", "du", "des", "de la", "de l", "d", "le", "la", "les", "l"}

        # Other European particles
        self.particles = {
            "von",
            "van",
            "vander",
            "van der",
            "van de",
            "de",
            "del",
            "della",
            "di",
            "da",
            "mc",
            "mac",
            "o",
            "fitz",
        }

        # Hyphenated name patterns
        self.hyphen_pattern = re.compile(r"[\u2010-\u2015\-]")  # Various hyphens/dashes

    def normalize_edge_names(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize all names in edge list.

        Args:
            edges: List of edge dictionaries

        Returns:
            List of edges with normalized names added
        """
        print("=" * 80)
        print("NAME NORMALIZATION")
        print("=" * 80)
        print()
        print(f"Processing {len(edges):,} edges...")
        print()

        normalized_edges = []
        stats = {
            "total_edges": len(edges),
            "unique_students_raw": 0,
            "unique_advisors_raw": 0,
            "unique_students_normalized": 0,
            "unique_advisors_normalized": 0,
            "names_with_accents": 0,
            "names_with_particles": 0,
            "names_with_hyphens": 0,
        }

        students_raw = set()
        advisors_raw = set()
        students_norm = set()
        advisors_norm = set()

        for edge in edges:
            # Normalize student name
            student_raw = edge["student_raw"]
            student_norm = self.normalize_name(student_raw)

            # Normalize advisor name
            advisor_raw = edge["advisor_raw"]
            advisor_norm = self.normalize_name(advisor_raw)

            # Track statistics
            students_raw.add(student_raw)
            advisors_raw.add(advisor_raw)
            students_norm.add(student_norm["canonical"])
            advisors_norm.add(advisor_norm["canonical"])

            if student_norm["has_accents"] or advisor_norm["has_accents"]:
                stats["names_with_accents"] += 1
            if student_norm["has_particles"] or advisor_norm["has_particles"]:
                stats["names_with_particles"] += 1
            if student_norm["has_hyphens"] or advisor_norm["has_hyphens"]:
                stats["names_with_hyphens"] += 1

            # Create normalized edge
            norm_edge = edge.copy()
            norm_edge.update(
                {
                    "student_normalized": student_norm["canonical"],
                    "student_parse": student_norm,
                    "advisor_normalized": advisor_norm["canonical"],
                    "advisor_parse": advisor_norm,
                }
            )
            normalized_edges.append(norm_edge)

        stats["unique_students_raw"] = len(students_raw)
        stats["unique_advisors_raw"] = len(advisors_raw)
        stats["unique_students_normalized"] = len(students_norm)
        stats["unique_advisors_normalized"] = len(advisors_norm)

        self._print_stats(stats)

        return normalized_edges

    def normalize_name(self, name: str) -> Dict[str, Any]:
        """
        Normalize a single name.

        Args:
            name: Raw name string

        Returns:
            Dictionary with normalized name and metadata
        """
        if not name:
            return {
                "canonical": "",
                "family": "",
                "given": "",
                "has_accents": False,
                "has_particles": False,
                "has_hyphens": False,
                "original": name,
            }

        # Detect accents before normalization
        has_accents = bool(re.search(r"[àâäæçéèêëïîôùûüÿœÀÂÄÆÇÉÈÊËÏÎÔÙÛÜŸŒ]", name))

        # Detect hyphens
        has_hyphens = bool(self.hyphen_pattern.search(name))

        # Parse name (assume "Family, Given" format)
        if "," in name:
            parts = [p.strip() for p in name.split(",", 1)]
            family_raw = parts[0]
            given_raw = parts[1] if len(parts) > 1 else ""
        else:
            # No comma - assume "Given Family" or single name
            words = name.split()
            if len(words) >= 2:
                family_raw = words[-1]
                given_raw = " ".join(words[:-1])
            else:
                family_raw = name
                given_raw = ""

        # Normalize family name
        family_norm, has_particles = self._normalize_family_name(family_raw)

        # Normalize given name
        given_norm = self._normalize_given_name(given_raw)

        # Create canonical form: "FAMILY, Given"
        canonical = f"{family_norm}, {given_norm}".strip(", ")

        return {
            "canonical": canonical,
            "family": family_norm,
            "given": given_norm,
            "has_accents": has_accents,
            "has_particles": has_particles,
            "has_hyphens": has_hyphens,
            "original": name,
        }

    def _normalize_family_name(self, family: str) -> Tuple[str, bool]:
        """
        Normalize family name.

        Args:
            family: Raw family name

        Returns:
            (normalized_name, has_particles)
        """
        if not family:
            return "", False

        # Normalize Unicode (NFD decomposition for accent removal if needed)
        # But KEEP accents for French names
        family = family.strip()

        # Detect particles
        words = family.split()
        particles_found = []
        name_words = []
        has_particles = False

        for word in words:
            word_lower = word.lower()
            # Check if word is a particle
            if word_lower in self.french_particles or word_lower in self.particles:
                particles_found.append(word_lower)
                has_particles = True
            else:
                name_words.append(word)

        # Reconstruct: particles (lowercase) + name (Title Case)
        if particles_found and name_words:
            # Particles stay lowercase, name in title case
            family_norm = " ".join(particles_found + [w.title() for w in name_words])
        else:
            # Just the name, title case
            family_norm = family.title()

        return family_norm, has_particles

    def _normalize_given_name(self, given: str) -> str:
        """
        Normalize given name.

        Args:
            given: Raw given name

        Returns:
            Normalized given name
        """
        if not given:
            return ""

        # Title case, preserve hyphens
        # Handle hyphenated names: "Jean-Pierre" → "Jean-Pierre"
        parts = self.hyphen_pattern.split(given)
        normalized_parts = [p.strip().title() for p in parts if p.strip()]

        # Join with standard hyphen
        return "-".join(normalized_parts)

    def _print_stats(self, stats: Dict):
        """Print normalization statistics."""
        print("-" * 80)
        print("NORMALIZATION STATISTICS")
        print("-" * 80)
        print()

        print(f"📊 NAME COUNTS:")
        print(f"  Unique students (raw): {stats['unique_students_raw']:,}")
        print(f"  Unique students (normalized): {stats['unique_students_normalized']:,}")
        print(f"  Unique advisors (raw): {stats['unique_advisors_raw']:,}")
        print(f"  Unique advisors (normalized): {stats['unique_advisors_normalized']:,}")
        print()

        print(f"📝 NAME FEATURES:")
        print(
            f"  Edges with accented names: {stats['names_with_accents']:,} "
            f"({stats['names_with_accents']/stats['total_edges']*100:.1f}%)"
        )
        print(
            f"  Edges with particles: {stats['names_with_particles']:,} "
            f"({stats['names_with_particles']/stats['total_edges']*100:.1f}%)"
        )
        print(
            f"  Edges with hyphens: {stats['names_with_hyphens']:,} "
            f"({stats['names_with_hyphens']/stats['total_edges']*100:.1f}%)"
        )
        print()

        print("=" * 80)

    def save_normalized_edges(self, edges: List[Dict], output_file: str):
        """
        Save normalized edges to JSON file.

        Args:
            edges: List of normalized edge dictionaries
            output_file: Path to output file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metadata": {
                        "normalization_date": datetime.now().isoformat(),
                        "total_edges": len(edges),
                        "source": "FR_STAR_OAI",
                    },
                    "edges": edges,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✅ Normalized edges saved: {output_path}")
        print(f"   Total edges: {len(edges):,}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Normalize edge names")
    parser.add_argument("--input", required=True, help="Input edges JSON file")
    parser.add_argument("--output", required=True, help="Output normalized edges JSON file")

    args = parser.parse_args()

    # Load edges
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    edges = data.get("edges", [])

    # Normalize
    normalizer = NameNormalizer()
    normalized_edges = normalizer.normalize_edge_names(edges)
    normalizer.save_normalized_edges(normalized_edges, args.output)


if __name__ == "__main__":
    main()
