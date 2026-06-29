#!/usr/bin/env bash
set -euo pipefail

echo "=== GMNAP Genealogy: fixture run ==="
mkdir -p data/out

echo "[1/4] Harvest (fixtures only for demo)"
cp data/fixtures/theses.jsonl data/out/harvest.jsonl

echo "[2/4] Normalize"
python3 - <<'PY'
import json, os
from pipeline.normalize import init, normalize_thesis
init("config")
rows = []
with open("data/out/harvest.jsonl","r",encoding="utf-8") as f:
    for line in f:
        rows.append(normalize_thesis(json.loads(line)))
with open("data/out/normalized.jsonl","w",encoding="utf-8") as o:
    for r in rows:
        o.write(json.dumps(r, ensure_ascii=False)+"\n")
print(f"[normalize] {len(rows)} records")
PY

echo "[3/4] Extract+Fuse (naive demo)"
python3 - <<'PY'
import json, hashlib, base64
from pipeline.extract import init as ex_init
from pipeline.fuse import init as fu_init, score_edge
from pipeline.validate import temporal_validate
ex_init("config"); fu_init("config")
def gid(name):
    if not name: return None
    h = hashlib.sha256(name.encode("utf-8")).digest()
    return "GMN-" + base64.b32encode(h)[:22].decode("ascii")
edges = []
with open("data/out/normalized.jsonl","r",encoding="utf-8") as f:
    for line in f:
        th = json.loads(line)
        author = th.get("author_name")
        s_gid = gid(author) if author else None
        for adv in th.get("advisors", []):
            a_gid = gid(adv.get("name"))
            cand = {
                "student_global_id": s_gid,
                "advisor_global_id": a_gid,
                "student_name": author,
                "advisor_name": adv.get("name"),
                "degree_date": th.get("defense_date"),
                "institution": th.get("institution"),
                "degree_type": th.get("degree_type"),
                "sources": [th.get("source_name")],
            }
            best = score_edge([cand])
            edges.append(temporal_validate(best))
with open("data/fixtures/edges.jsonl","w",encoding="utf-8") as o:
    for e in edges:
        o.write(json.dumps(e, ensure_ascii=False)+"\n")
print(f"[extract+fuse] edges: {len(edges)}")
PY

echo "[4/4] Load graph"
python3 -m pipeline.load_graph

echo "=== DONE ==="
