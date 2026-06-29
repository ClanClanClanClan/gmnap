#!/usr/bin/env bash
set -euo pipefail
echo "[rebuild] Re-creating graph indexes & loading fixture edges"
python3 -m pipeline.load_graph
