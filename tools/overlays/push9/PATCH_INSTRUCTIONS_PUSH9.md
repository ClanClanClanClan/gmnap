
# GMNAP V7 — Push 9 (Security & Ops Hardening + Write‑Plane Parity)

**Adds**
- `src/api/security_middleware.py` — FastAPI/Starlette middleware enforcing **JWT (paid)** or **Hashcash (free)**, with per‑tier rate limiting and RBAC. Exposes Prometheus counters.
- `src/ops/hashcash.py` — Hashcash v1 parser/validator; default **18‑bit** as per spec.
- `src/ops/rate_limit.py` — Token bucket (in‑memory, Redis optional via `REDIS_URL`).
- `src/ops/audit_log.py` — Hash‑chained JSONL audit log with optional HMAC.
- `src/ops/metrics_security.py` — Prometheus metrics for security events.
- `src/db/changelog_expand.py` — Stage 9 expanded Cypher for **arrays** and **edges** (Advisors/Students/Collaborators).
- `patches/stage9_edges.patch` — Wires expanded changelog into Stage 9 so `changelog_arrays.cypher` and `changelog_edges.cypher` are emitted.
- Grafana alerts: `grafana/alerts/gmnap_v7_security_alerts.json`.
- Config: `config/security.push9.yaml`.
- Tests: `tests/security/*`, `tests/db/test_changelog_edges.py`.
- Script: `scripts/writepath_smoke.py`.

**Install**
```bash
pip install -r requirements.push9.txt
```

**Wire**
1) **API security** (Starlette / FastAPI):
```python
from starlette.applications import Starlette
from src.api.security_middleware import SecurityMiddleware

app = Starlette()
app.add_middleware(SecurityMiddleware, required_role="operator")  # or None
```

Env knobs (aligns with *specs_v7.yaml → ops.rate_limit*):
```
GMNAP_HASHCASH_BITS=18
GMNAP_RPM_FREE=60
GMNAP_RPM_PAID=10000
GMNAP_JWT_SECRET=...           # or GMNAP_JWT_PUBLIC_PEM="-----BEGIN PUBLIC KEY-----..."
REDIS_URL=redis://localhost:6379/0
AUDIT_HMAC_KEY=...
```

2) **Stage 9 expansion**:
Apply `patches/stage9_edges.patch`. After a run, expect:
```
snapshots/run-<hash>/
  ├─ entries.yaml
  ├─ entries.json
  ├─ diff.html
  ├─ changelog.cypher
  ├─ changelog_arrays.cypher    # NEW
  └─ changelog_edges.cypher     # NEW
```

3) **Audit trail**:
```python
from src.ops.audit_log import AuditLogger
al = AuditLogger("logs/audit.log")
al.log("system","startup",{"pid":1234})
assert al.verify_chain()
```

4) **Smoke the write‑plane**:
```bash
python scripts/writepath_smoke.py
```

**Notes**
- Hashcash: classic **v1 stamp** with SHA‑1 and leading‑zero‑bits; default freshness window 1 h. This matches *ops.rate_limit.free_tier.hashcash_bits=18*. 
- RBAC: checks `role` (or `roles`) claim in JWT; set `GMNAP_REQUIRED_ROLE` to require a role globally.
- Arrays/edges Cypher is conservative by design; tailor to Memgraph/Neo4j as needed (e.g., indexes, constraints).
