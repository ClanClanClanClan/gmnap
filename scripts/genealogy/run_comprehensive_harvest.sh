#!/usr/bin/env bash
#
# Comprehensive Genealogy Harvest - Production Runner
# ===================================================
#
# Collects 20,000+ advisor relationships from:
# 1. Wikidata P184 (10,000 doctoral advisor relationships)
# 2. French theses (5,000 records from theses.fr)
# 3. US dissertations (5,000 records from Crossref)
#
# Total target: ~20,000 records
# Estimated time: 2-4 hours (parallel execution)
#

set -e

# Configuration
export PYTHONPATH="$(pwd)"
OUTPUT_DIR="data/genealogy/comprehensive"
LOG_FILE="/tmp/comprehensive_genealogy_harvest.log"

echo "================================================================================"
echo "COMPREHENSIVE GENEALOGY HARVEST - PRODUCTION RUN"
echo "================================================================================"
echo "Timestamp: $(date)"
echo "Output directory: $OUTPUT_DIR"
echo "Log file: $LOG_FILE"
echo ""
echo "SOURCES:"
echo "  1. Wikidata P184: 10,000 advisor relationships"
echo "  2. French theses: 5,000 records"
echo "  3. US Crossref:   5,000 records"
echo ""
echo "Total target: 20,000+ records"
echo "Estimated time: 2-4 hours"
echo "================================================================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run harvest (background)
python3 scripts/genealogy/comprehensive_harvest.py 2>&1 | tee "$LOG_FILE"

echo ""
echo "================================================================================"
echo "HARVEST COMPLETE"
echo "================================================================================"
echo "Check results in: $OUTPUT_DIR"
echo "Log file: $LOG_FILE"
echo "================================================================================"
