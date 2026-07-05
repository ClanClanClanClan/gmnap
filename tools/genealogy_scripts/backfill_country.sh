#!/usr/bin/env bash
set -euo pipefail
COUNTRY=${1:-FR}
echo "[backfill] Country=${COUNTRY} (edit config/sources.yml and enable desired source)"
python3 -m pipeline.ingest
