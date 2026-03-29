
# GMNAP V7 — Push 10 (Stage 10 Report Hardening)

**Adds**
- `src/pipeline/stage10_report.py` — generates Markdown `report.md`, machine `report.json`, **DataCite DOI draft** (`doi_draft.json`), `archive_manifest.json`, and `ATTRIBUTION.txt`; also archives the snapshot (local zip by default, optional SFTP).
- `templates/report.md.j2` — clean human‑readable report.
- `schemas/datacite_draft.schema.json` — validation for the DOI draft (minimal DataCite subset).
- `src/ops/archive.py` — local zip + optional SFTP upload.
- `src/ops/attribution.py` — SPDX‑style attribution file from spec authority list.
- Metrics: `REPORTS_EMITTED`, `DOI_DRAFTS_CREATED`, `ARCHIVE_UPLOADS_SUCCEEDED/FAILED` (Prometheus optional, no‑op fallback).
- `config/report.push10.yaml` — knobs for archive method and target dirs.
- Tests: `tests/push10/test_stage10_report_and_archive.py`.
- CLI: `scripts/run_stage10_demo_v2.py`.

**Patch**
- `patches/pipeline_stage10_refresh.patch` — keeps Stage 10 call signature in `pipeline_v7.py` ensured; safe no‑op if already present.

**Why this (spec alignment)**
- Stage 10 in the spec requires **Markdown metrics; draft DOI; push snapshot to archive**. This push delivers all three, validates DOI against a schema, and auto‑generates attribution (per spec’s security/legal section).

**Usage**
```bash
pip install -r requirements.push10.txt
git apply patches/pipeline_stage10_refresh.patch  # if needed

# Demo
python3 scripts/run_stage10_demo_v2.py

# Run tests
pytest -q tests/push10
```
