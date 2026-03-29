
# GMNAP V7 — Push 1 (Stage 0/1 base: Config + Ingest + Unicode Normalisation)

Adds:
- `src/ops/unicode_norm.py` — NFC→NFKD→fold(exceptions)→NFC; ZW/control scrub; recursive entry normaliser.
- `src/core/config_loader.py` — loads `specs_v7.yaml` / `v7.0.yaml` and exposes runtime profiles.
- `src/pipeline/stage1_ingest.py` — loads YAML/JSON, applies normalisation.
- `scripts/ingest_demo.py` — demo CLI.
- Tests in `tests/stage1/`.
- `requirements.push1.txt`.

Spec alignment: Stage 1 requires Unicode normalisation “NFC→NFKD→fold→NFC”; glossary rule 16 (fold exceptions). Runtime profiles read from spec.