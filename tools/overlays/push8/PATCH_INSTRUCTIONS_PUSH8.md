
# GMNAP V7 — Push 8 (Stage 9 Write&Diff, Secure DB Client, Retention, Alerts)

This push implements **Stage 9 — Write&Diff** and adds a secure DB client, retention utilities, and diff alerts.

## Install
```bash
pip install -r requirements.push8.txt
```

## Stage 9 — Write&Diff
- Module: `src/pipeline/stage9_write_and_diff.py`
- Capabilities:
  - Deterministic **YAML snapshot**: one file per entry `<GlobalID>.yaml` under `out/yaml/run-<hash>/`.
  - **HTML diff**: `out/yaml/run-<hash>/diff/index.html` with per‑file diffs.
  - **SQL changelog**: `out/yaml/run-<hash>/diff/changelog.sql` with deterministic `INSERT/UPDATE/DELETE` on `gmnap_changelog`.
  - **Prometheus metrics**: added/removed/modified counters + latest change gauge.

### Wire Stage 9 into pipeline
Apply `patches/pipeline_stage9.patch`. If patching fails, place this at the end of `pipeline_v7.py` run (after Stage 8, before Stage 10/11):
```python
from src.pipeline.stage9_write_and_diff import write_snapshot, diff_snapshots, generate_sql_changelog

snapshot_dir = write_snapshot(batch, out_root=os.getenv("GMNAP_SNAPSHOT_DIR","out/yaml"))
prev = os.getenv("GMNAP_PREV_SNAPSHOT_DIR")
if prev:
    diff = diff_snapshots(prev, snapshot_dir)
    generate_sql_changelog(prev, snapshot_dir)
```

## Streaming schema gate
Apply `patches/streaming_v7_schema_gate.patch` to enforce **Stage 8 GlobalValidate** inside the streaming runner before writes.

## Secure Memgraph client
- `src/core/memgraph_client_secure.py` loads `GMNAP_DB_URI`, `GMNAP_DB_USER`, `GMNAP_DB_PASS`, `GMNAP_DB_CA` and builds an SSL context (TLS ≥ 1.2). Replace your current client with this when moving to auth+TLS.
- Test: `tests/security/test_memgraph_client_secure.py`

## Snapshot retention
- Utility: `src/ops/retention.py` with `rotate_snapshots(root, keep_days=…, keep_n=…)`.
- Use in cron: `python -c "from src.ops.retention import rotate_snapshots; print(rotate_snapshots('out/yaml', keep_days=60, keep_n=30))"`

## Alerts
Import `grafana/alerts/gmnap_v7_write_diff_alerts.json` alongside previous alert groups.

## Demos
- `scripts/run_stage9_demo.py` – creates two snapshots, diffs them, and emits SQL.
- `scripts/check_idempotency_bytes.py` – computes canonical hash of a batch JSON to cross‑check idempotency.

## Run tests
```bash
pytest -q tests/stage9/test_write_and_diff.py tests/security/test_memgraph_client_secure.py
```

— End.
