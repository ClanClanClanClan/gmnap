#!/bin/bash
# ULTRATHINK Document Cleanup Script
# Date: 2025-09-17
# Purpose: Archive duplicate and obsolete documentation

echo "========================================"
echo "ULTRATHINK DOCUMENT CLEANUP"
echo "========================================"
echo ""

# Create archive directory with timestamp
ARCHIVE_DIR="docs/archive/2025-09-17-ultrathink-cleanup"
mkdir -p "$ARCHIVE_DIR"

echo "Creating archive at: $ARCHIVE_DIR"
echo ""

# Archive duplicate audit reports (keep only latest)
echo "Archiving duplicate audit reports..."
mkdir -p "$ARCHIVE_DIR/audits"

# Move older audit reports, keeping the most recent
find docs/audits -name "*AUDIT*.md" -type f ! -name "ULTRATHINK_FINAL_AUDIT_2025_09_17.md" \
    -exec mv {} "$ARCHIVE_DIR/audits/" \; 2>/dev/null

# Archive V7 compliance duplicates (keep executive summary)
echo "Archiving V7 compliance duplicates..."
mkdir -p "$ARCHIVE_DIR/v7_compliance"

find docs -name "V7_COMPLIANCE*.md" -type f ! -path "*/archive/*" \
    -exec mv {} "$ARCHIVE_DIR/v7_compliance/" \; 2>/dev/null

# Archive Korean processor reports (keep expert feedback)
echo "Archiving Korean processor reports..."
mkdir -p "$ARCHIVE_DIR/korean"

find docs -name "KOREAN*.md" -type f ! -name "KOREAN_PROCESSOR_EXPERT_FEEDBACK*.md" \
    ! -path "*/archive/*" -exec mv {} "$ARCHIVE_DIR/korean/" \; 2>/dev/null

# Archive old handover documents
echo "Archiving old handover documents..."
mkdir -p "$ARCHIVE_DIR/handover"

find docs/handover -name "*.md" -type f -mtime +7 \
    -exec mv {} "$ARCHIVE_DIR/handover/" \; 2>/dev/null

# Archive test results
echo "Archiving test results..."
mkdir -p "$ARCHIVE_DIR/test_results"

find . -maxdepth 1 -name "*test_results*.json" -o -name "*audit*.json" \
    -exec mv {} "$ARCHIVE_DIR/test_results/" \; 2>/dev/null

# Archive backup files
echo "Archiving backup files..."
mkdir -p "$ARCHIVE_DIR/backups"

find . -name "*.bak" -o -name "*backup*" -o -name "*.trackB_*" \
    -exec mv {} "$ARCHIVE_DIR/backups/" \; 2>/dev/null

# Clean up empty directories
echo "Removing empty directories..."
find docs -type d -empty -delete 2>/dev/null

# Generate manifest
echo "Generating archive manifest..."
MANIFEST="$ARCHIVE_DIR/MANIFEST.md"
cat > "$MANIFEST" << EOF
# Archive Manifest - ULTRATHINK Cleanup
*Date: $(date)*
*Total Files Archived: $(find "$ARCHIVE_DIR" -type f | wc -l)*

## Contents

### Audit Reports ($(find "$ARCHIVE_DIR/audits" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/audits" -type f -exec basename {} \; 2>/dev/null | sort)

### V7 Compliance ($(find "$ARCHIVE_DIR/v7_compliance" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/v7_compliance" -type f -exec basename {} \; 2>/dev/null | sort)

### Korean Processor ($(find "$ARCHIVE_DIR/korean" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/korean" -type f -exec basename {} \; 2>/dev/null | sort)

### Handover Documents ($(find "$ARCHIVE_DIR/handover" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/handover" -type f -exec basename {} \; 2>/dev/null | sort)

### Test Results ($(find "$ARCHIVE_DIR/test_results" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/test_results" -type f -exec basename {} \; 2>/dev/null | sort)

### Backup Files ($(find "$ARCHIVE_DIR/backups" -type f 2>/dev/null | wc -l) files)
$(find "$ARCHIVE_DIR/backups" -type f -exec basename {} \; 2>/dev/null | wc -l) backup files archived

## Summary
All duplicate and obsolete documentation has been archived to preserve history while cleaning the active workspace.
EOF

echo ""
echo "========================================"
echo "CLEANUP COMPLETE"
echo "========================================"
echo "Files archived to: $ARCHIVE_DIR"
echo "Manifest created at: $MANIFEST"
echo ""
echo "Statistics:"
echo "  Audit reports archived: $(find "$ARCHIVE_DIR/audits" -type f 2>/dev/null | wc -l)"
echo "  V7 compliance docs archived: $(find "$ARCHIVE_DIR/v7_compliance" -type f 2>/dev/null | wc -l)"
echo "  Korean docs archived: $(find "$ARCHIVE_DIR/korean" -type f 2>/dev/null | wc -l)"
echo "  Total files archived: $(find "$ARCHIVE_DIR" -type f | wc -l)"
echo ""
echo "Cleanup script completed successfully!"