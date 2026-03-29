
# GMNAP V7 — Push 11 (Stage 11 IdempotencyCheck gate + report)

Adds:
- `src/pipeline/stage11_idempotency_check.py` — computes **canonical bytes** and compares (shuffled/self/previous).
- Extends `src/ops/metrics.py` — adds idempotency gauges/counters + histograms.
- Alert: `grafana/alerts/gmnap_v7_idempotency_alerts.json` — fires on non-zero diff.
- Patch: `patches/pipeline_stage11.patch` — invokes Stage 11 **after** Stage 10 and gates on `idempotent_diff_bytes_max` from specs.

Usage:
```bash
pip install -r requirements.push11.txt
git apply patches/pipeline_stage11.patch
python3 scripts/run_stage11_demo.py
pytest -q tests/stage11 -k "not liveapi"
```

Env knobs:
- `GMNAP_IDEMPOTENCY_MODE` ∈ {shuffled, previous, self} (default: shuffled)
- `GMNAP_IDEMPOTENCY_STRICT` ∈ {"1","0"} (default: "1")
- `GMNAP_IDEMPOTENT_DIFF_BYTES_MAX` (default: 0; spec gate overrides when available)
