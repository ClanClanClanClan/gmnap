from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any, Dict, List


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def write_yaml_sorted(entries: List[Dict[str, Any]], out_path: str) -> None:
    # R56: stream with json.dump instead of materialising canonical(entries)
    # as one Python string — at 1M entries that string is multi-GB and the
    # dumps+write_text peak doubles it. json.dump with identical arguments
    # produces byte-identical output.
    with Path(out_path).open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


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
