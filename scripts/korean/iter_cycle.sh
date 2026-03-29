#!/usr/bin/env bash
set -e
python3 scripts/report_failures.py > fail.txt
echo ">>> Edit CSVs now, then press [enter] to rebuild"
read
python3 scripts/build_fsts_multi.py
python3 scripts/validate.py