#!/bin/bash

# Safe add function for Korean variants
function safe_add () {
  echo "Adding variant: $1"
  
  # Add to variant_map.csv
  echo "$1" >> src/gmnap/regions/e_groups/e4_korea/resources/variant_map.csv
  
  # Build FSTs
  cd src/gmnap/regions/e_groups/e4_korea
  python3 scripts/build_fsts_multi.py
  
  # Add and commit
  git add resources models
  git commit -m "add variant: $1"
  
  if [ $? -eq 0 ]; then
    echo "✓ Successfully added: $1"
  else
    echo "✗ Failed to add: $1 (blocked by pre-commit hook)"
    git restore --staged .
    # Remove the line we just added
    sed -i '' -e '$d' resources/variant_map.csv
  fi
  
  cd -
}

# Test the suggested variants
safe_add "류,ryu,SURNAME_0"
safe_add "래,rae,GIVEN_0"
safe_add "종,jong,GIVEN_0" 
safe_add "년,nyeon,GIVEN_RARE"