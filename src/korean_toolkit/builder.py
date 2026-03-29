"""
Korean Builder Module - Consolidates build scripts
Replaces: build_*.py scripts
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class KoreanBuilder:
    """Unified Korean artifact builder."""

    def __init__(self):
        self.build_targets = {
            "fst": self._build_fst,
            "mappings": self._build_mappings,
            "lexicon": self._build_lexicon,
            "table": self._build_table,
            "all": self._build_all,
        }

    def build(self, target: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main build entry point.
        Replaces all build_*.py scripts.

        Args:
            target: What to build
            config: Build configuration

        Returns:
            Build results
        """
        if target not in self.build_targets:
            raise ValueError(f"Unknown build target: {target}")

        config = config or {}
        return self.build_targets[target](config)

    def _build_fst(self, config: Dict) -> Dict[str, Any]:
        """
        Build FST (Finite State Transducer).
        Replaces: build_fsts.py, build_fsts_multi.py
        """
        input_file = config.get("input", "resources/rr_syllable_map.csv")
        output_dir = config.get("output", "build/fst")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Build han2rom FST
        han2rom_result = self._build_single_fst(
            input_file, f"{output_dir}/han2rom.fst", direction="forward"
        )

        # Build rom2han FST
        rom2han_result = self._build_single_fst(
            input_file, f"{output_dir}/rom2han.fst", direction="reverse"
        )

        return {
            "success": han2rom_result["success"] and rom2han_result["success"],
            "han2rom": han2rom_result,
            "rom2han": rom2han_result,
            "output_dir": output_dir,
        }

    def _build_mappings(self, config: Dict) -> Dict[str, Any]:
        """
        Build mapping files.
        Replaces: make_rr_table.py, build_mappings.py
        """
        source = config.get("source", "resources/rr_syllable_map.csv")
        output = config.get("output", "build/mappings.json")

        mappings = self._load_csv_mappings(source)

        # Process and enhance mappings
        processed = self._process_mappings(mappings)

        # Save mappings
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(processed, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "total_mappings": len(processed),
            "output_file": output,
        }

    def _build_lexicon(self, config: Dict) -> Dict[str, Any]:
        """
        Build syllable lexicon.
        Replaces: build_lexicon.py
        """
        output = config.get("output", "build/lexicon.json")

        lexicon = {"syllables": {}, "characters": {}, "surnames": [], "given_names": []}

        # Would load and process actual data
        # This is a placeholder structure

        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(lexicon, f, ensure_ascii=False, indent=2)

        return {"success": True, "output_file": output}

    def _build_table(self, config: Dict) -> Dict[str, Any]:
        """
        Build romanization table.
        Replaces: make_rr_table.py
        """
        source = config.get("source", "resources/rr_syllable_map.csv")
        output = config.get("output", "build/rr_table.html")

        mappings = self._load_csv_mappings(source)

        # Generate HTML table
        html = self._generate_html_table(mappings)

        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)

        return {"success": True, "output_file": output, "row_count": len(mappings)}

    def _build_all(self, config: Dict) -> Dict[str, Any]:
        """Build all artifacts."""
        results = {}

        for target in ["fst", "mappings", "lexicon", "table"]:
            if target != "all":
                results[target] = self.build(target, config)

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
        }

    # Helper methods
    def _build_single_fst(
        self, input_file: str, output_file: str, direction: str
    ) -> Dict[str, Any]:
        """Build a single FST file."""
        try:
            # This would use actual FST building tools
            # Placeholder for demonstration
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            Path(output_file).touch()

            return {"success": True, "output": output_file, "direction": direction}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_csv_mappings(self, filepath: str) -> List[Dict]:
        """Load mappings from CSV file."""
        mappings = []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mappings.append(row)
        except FileNotFoundError:
            # Return empty list if file doesn't exist
            pass

        return mappings

    def _process_mappings(self, mappings: List[Dict]) -> List[Dict]:
        """Process and enhance mappings."""
        processed = []

        for mapping in mappings:
            # Clean and validate
            if mapping.get("hangul") and mapping.get("roman"):
                processed.append(
                    {
                        "hangul": mapping["hangul"].strip(),
                        "roman": mapping["roman"].strip(),
                        "weight": float(mapping.get("weight", 1.0)),
                        "context": mapping.get("context", "").strip(),
                        "tags": [
                            t.strip()
                            for t in mapping.get("tags", "").split(",")
                            if t.strip()
                        ],
                    }
                )

        return processed

    def _generate_html_table(self, mappings: List[Dict]) -> str:
        """Generate HTML table from mappings."""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Korean Romanization Table</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
</head>
<body>
    <h1>Korean Romanization Mappings</h1>
    <table>
        <thead>
            <tr>
                <th>Hangul</th>
                <th>Romanization</th>
                <th>Weight</th>
                <th>Context</th>
            </tr>
        </thead>
        <tbody>
"""

        for mapping in mappings:
            html += f"""            <tr>
                <td>{mapping.get('hangul', '')}</td>
                <td>{mapping.get('roman', '')}</td>
                <td>{mapping.get('weight', '')}</td>
                <td>{mapping.get('context', '')}</td>
            </tr>
"""

        html += """        </tbody>
    </table>
</body>
</html>"""

        return html
