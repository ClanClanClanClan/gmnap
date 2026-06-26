#!/usr/bin/env python3
"""
Generate sample nodes/edges Cypher from a tiny batch to smoke the write-plane path.
"""

import json
import os
import pathlib

from src.db.changelog_expand import generate_changelogs_expanded

batch = [
    {
        "GlobalID": "X",
        "CanonicalLatin": "Noether, Emmy",
        "Advisors": ["A1", "A2"],
        "Students": ["S1"],
        "AlternativeLatin": ["E. Noether", "Noether, E."],
        "Publications": ["10.1000/xyz123"],
        "Collaborators": ["H1", "H2"],
    }
]

out_dir = pathlib.Path("snapshots/run-smoke9")
out_dir.mkdir(parents=True, exist_ok=True)
paths = generate_changelogs_expanded(str(out_dir), batch)
print("\\n".join(paths))
