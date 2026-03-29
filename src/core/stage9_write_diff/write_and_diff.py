from __future__ import annotations
from typing import Any, List, Dict
from pathlib import Path
import json
import difflib


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml_sorted(entries: List[Dict[str, Any]], out_path: str) -> None:
    Path(out_path).write_text(canonical(entries), encoding="utf-8")


class DeterministicWriter:
    """Deterministic writer for Stage 9 - ensures consistent output formatting."""

    def write_entries(self, entries: List[Dict[str, Any]], output_path: str) -> None:
        """Write entries in canonical, sorted format."""
        write_yaml_sorted(entries, output_path)

    def generate_diff(
        self, old_entries: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]
    ) -> str:
        """Generate diff between old and new entries."""
        old_str = canonical(old_entries)
        new_str = canonical(new_entries)

        diff = difflib.unified_diff(
            old_str.splitlines(keepends=True),
            new_str.splitlines(keepends=True),
            fromfile="old_entries",
            tofile="new_entries",
        )
        return "".join(diff)

    def write_html_diff(
        self,
        old_entries: List[Dict[str, Any]],
        new_entries: List[Dict[str, Any]],
        output_path: str,
    ) -> None:
        """Generate HTML diff report."""
        old_str = canonical(old_entries)
        new_str = canonical(new_entries)

        differ = difflib.HtmlDiff()
        html = differ.make_file(
            old_str.splitlines(), new_str.splitlines(), "Old Entries", "New Entries"
        )

        Path(output_path).write_text(html, encoding="utf-8")
