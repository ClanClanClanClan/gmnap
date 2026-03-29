#!/bin/bash
# Safe add function from recovery protocol
function safe_add () {
  echo "$1" >> resources/variant_map.csv
  python3 scripts/build_fsts_multi.py
  git add resources models
  git commit -m "add variant: $1"
}