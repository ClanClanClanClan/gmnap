
# GMNAP V7 — Push 12 (Pipeline Metrics hardening: instrumentation, exporter, dashboards, CI gate)

Adds:
- `src/ops/pipeline_metrics.py` — `stage_timer(stage_name, entries)` context manager; updates histograms and throughput.
- Patch `patches/pipeline_stage12_metrics.patch` — wraps Stages 7/9/10/11 with timers (does not change outputs).
- `scripts/run_metrics_exporter.py` — starts a Prometheus exporter on `GMNAP_METRICS_PORT` (default 9308).
- `scripts/ci_idempotency_gate.py` — CI utility to fail a build if Stage 11 diff exceeds gate.
- `grafana/dashboards/gmnap_pipeline_overview.json` — overview dashboard.

Usage:
```bash
pip install -r requirements.push12.txt
git apply patches/pipeline_stage12_metrics.patch
python3 scripts/run_metrics_exporter.py &
# run pipeline… then in CI:
python3 scripts/ci_idempotency_gate.py snapshots/run-<hash>
pytest -q tests/stage12 -k "not liveapi"
```
