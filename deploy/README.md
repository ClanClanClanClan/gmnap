# Deployment recipes

Two paths to run GMNAP in a real cluster:

| Path | When | Files |
|---|---|---|
| **Kubernetes manifests** | Raw `kubectl apply` for ad-hoc clusters, kind/minikube, or teams that don't want Helm | [`k8s/`](k8s/) |
| **Helm chart** | Production-grade with values overrides, upgrades, rollbacks | [`helm/gmnap/`](helm/gmnap/) |

Both produce the same runtime topology (gmnap-api + memgraph +
nginx) and read the same env vars documented in
[../.env.example](../.env.example).

## Quick start — Kubernetes manifests

```bash
# Create the namespace + secrets first (one-time)
kubectl apply -f deploy/k8s/00-namespace.yaml
kubectl create secret generic gmnap-secrets \
  --namespace gmnap \
  --from-literal=memgraph-password="$(openssl rand -hex 16)" \
  --from-literal=api-token="$(openssl rand -hex 24)"

# Deploy the stack
kubectl apply -f deploy/k8s/

# Watch it come up (memgraph takes ~10 s to be ready)
kubectl -n gmnap get pods -w

# Hit the API via the ingress (or port-forward for local dev)
kubectl -n gmnap port-forward svc/gmnap-api 8080:8080
curl http://localhost:8080/healthz
```

## Quick start — Helm

```bash
# Render once to inspect (dry run)
helm template gmnap deploy/helm/gmnap/ -n gmnap

# Install
helm install gmnap deploy/helm/gmnap/ \
  --namespace gmnap \
  --create-namespace \
  --set memgraph.password="$(openssl rand -hex 16)" \
  --set api.bearerTokens="$(openssl rand -hex 24)"

# Upgrade (e.g. after a config change)
helm upgrade gmnap deploy/helm/gmnap/ -n gmnap \
  --set api.replicas=3
```

## What's in the box

- **gmnap-api** Deployment (3 replicas by default) — the FastAPI
  service from the project root Dockerfile. Reads
  `MEMGRAPH_PASSWORD`, `GMNAP_API_TOKENS`, `GMNAP_LOG_FORMAT`,
  `GMNAP_REQUIRE_HASHCASH`, `CORS_ALLOWED_ORIGINS` from a
  Kubernetes Secret + ConfigMap. Liveness probe hits `/healthz`,
  readiness hits `/readyz`. SIGTERM drains in-flight requests for
  up to 60 s before the pod gets reaped.
- **memgraph** StatefulSet (1 replica, persistent volume) — the
  graph DB. Bolt on 7687. The `gmnap-api` pods point at
  `memgraph.gmnap.svc.cluster.local:7687`.
- **nginx** Deployment (2 replicas) — TLS termination + request
  rate limiting at the edge (the same Mozilla-intermediate cipher
  list and 60/min free-tier limit as the docker-compose path).
- **Ingress** + TLS — optional `gmnap-ingress` that maps your
  hostname to the nginx service. TLS via cert-manager if you have
  it; otherwise self-signed for staging.

## Production checklist

Per the `SECURITY.md` and `DATA_SOURCES.md` documents in the repo
root, before shipping prod traffic:

- [ ] Set `GMNAP_REQUIRE_HASHCASH=1` (the default) on the api
  Deployment — DO NOT disable in multi-tenant prod.
- [ ] Lock `CORS_ALLOWED_ORIGINS` to your specific frontend
  domain(s); never leave the localhost-fallback default.
- [ ] Issue real TLS certs via cert-manager / Let's Encrypt; the
  Helm chart has the values knobs for both.
- [ ] Provision a backup schedule for the memgraph PV (built-in
  velero hook, or external snapshot tooling).
- [ ] Mount a separate PV for `/app/cache` (the authority-response
  + cost-tracker file) — defaults to ephemeral, which loses spend
  history across pod restarts.
- [ ] Configure your monitoring to scrape `/metrics` from inside
  the cluster — the app-layer auth check (defense-in-depth, post-
  round-34) accepts any 10/8 / 172.16-31/16 / 192.168/16 source
  without a token, so private-cluster Prometheus works out of the
  box.

## Validation

```bash
# Smoke-test the rendered manifests for schema validity
kubectl apply --dry-run=client -f deploy/k8s/

# Verify Helm chart renders
helm template gmnap deploy/helm/gmnap/ | kubectl apply --dry-run=client -f -

# Run the lint pass
helm lint deploy/helm/gmnap/
```

The `make refresh-data` target documented in the project Makefile
runs against a local clone, not the cluster — if you need to refresh
the bundled `data/genealogy_enrichment.json` inside the cluster,
re-build the image with a fresh harvest baked in and run
`helm upgrade --set image.tag=…`.
