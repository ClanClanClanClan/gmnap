
# GMNAP V7 — Push 5 (Stage 5 DuckDB analytics: duplicates & genealogy edges)

Adds:
- `src/pipeline/stage5_duckdb_analytics.py`: optional Stage 5 using DuckDB to detect collisions and emit a genealogy edges CSV.
- `config/duckdb_stage5.sql`: example analytics query.
- `patches/pipeline_stage5_duckdb.patch`: prefer DuckDB Stage 5 when available; fallback to existing suffixer.
- `grafana/alerts/gmnap_v7_stage5_alerts.json`: optional alert (uses Write&Diff changed entries as a proxy signal).
- Tests under `tests/stage5/`; demo script `scripts/run_stage5_duckdb_demo.py`.
- `requirements.push5.txt`.

Spec alignment: Stage 5 performs collision analytics (DuckDB) and writes genealogy edges; this complements the suffix‑and‑remap in Push 4 and prepares inputs for Stage 6 coherence.