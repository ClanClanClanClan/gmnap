#!/usr/bin/env python3
import json, os, sys
from src.pipeline.stage5_duckdb_analytics import stage5_duckdb

if __name__ == "__main__":
    batch = [
        {"GlobalID": "A", "CanonicalLatin": "Euler, Leonhard", "BirthYear": 1707, "Advisors": []},
        {
            "GlobalID": "B",
            "CanonicalLatin": "Euler, Leonhard",
            "BirthYear": 1707,
            "Advisors": ["A"],
        },
        {"GlobalID": "C", "CanonicalLatin": "Gauss, Carl F.", "BirthYear": 1777, "Advisors": []},
    ]
    out, m, csv = stage5_duckdb(batch, workdir="work_stage5")
    print(json.dumps({"metrics": m, "csv": csv}, indent=2))
