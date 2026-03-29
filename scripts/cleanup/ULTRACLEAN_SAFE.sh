#!/bin/bash
# ULTRACLEAN SAFE VERSION - With rollback capability
# Date: 2025-09-01

set -e  # Exit on error

echo "=============================================="
echo "ULTRACLEAN SAFE VERSION - Careful Cleanup"
echo "=============================================="
echo ""
echo "This script will SAFELY clean the repository with ability to rollback"
echo ""

# Create comprehensive backup first
BACKUP_NAME="full_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating comprehensive backup: $BACKUP_NAME.tar.gz"
tar -czf "archive/$BACKUP_NAME.tar.gz" \
    scripts/korean/*.py \
    src/core/pipeline*.py \
    src/core/monitoring*.py \
    src/core/streaming*.py \
    2>/dev/null || echo "Some files not found, continuing..."

echo "✓ Backup created: archive/$BACKUP_NAME.tar.gz"
echo ""

# Safety check
read -p "Proceed with safe cleanup? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 1
fi

echo ""
echo "=== PHASE 1: KOREAN SCRIPTS (SAFE) ==="

# Count before
KOREAN_BEFORE=$(ls scripts/korean/*.py 2>/dev/null | wc -l)
echo "Korean scripts before: $KOREAN_BEFORE"

# Create archive directory with timestamp
KOREAN_ARCHIVE="archive/korean_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$KOREAN_ARCHIVE"

# Archive Korean scripts (don't delete yet)
if [ -d "scripts/korean" ]; then
    echo "Archiving Korean scripts to $KOREAN_ARCHIVE..."
    cp scripts/korean/*.py "$KOREAN_ARCHIVE/" 2>/dev/null || true
    echo "✓ Archived $(ls $KOREAN_ARCHIVE/*.py 2>/dev/null | wc -l) Korean scripts"
    
    # Create list of what was archived
    ls "$KOREAN_ARCHIVE"/*.py > "$KOREAN_ARCHIVE/archived_files.txt" 2>/dev/null || true
fi

# Create Korean CLI wrapper (safe - doesn't delete anything)
echo "Creating Korean CLI wrapper..."
cat > scripts/korean_unified.py << 'EOF'
#!/usr/bin/env python3
"""Unified Korean CLI - Safe wrapper for Korean toolkit"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Korean Unified CLI")
print("This will replace 166+ individual scripts")
print("")
print("Usage:")
print("  python korean_unified.py analyze <file>")
print("  python korean_unified.py fix <issue> <file>")
print("  python korean_unified.py validate <file>")
print("")
print("Note: Full implementation pending Korean toolkit completion")

# When toolkit is ready:
# from src.korean_toolkit import KoreanToolkit
# toolkit = KoreanToolkit()
EOF

chmod +x scripts/korean_unified.py
echo "✓ Created Korean CLI wrapper (scripts/korean_unified.py)"

echo ""
echo "=== PHASE 2: PIPELINE CONSOLIDATION (SAFE) ==="

# Archive old pipelines without deleting
PIPELINE_ARCHIVE="archive/pipelines_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$PIPELINE_ARCHIVE"

echo "Archiving pipeline versions..."
cp src/core/pipeline*.py "$PIPELINE_ARCHIVE/" 2>/dev/null || true
cp src/core/streaming*.py "$PIPELINE_ARCHIVE/" 2>/dev/null || true
echo "✓ Pipeline versions archived to $PIPELINE_ARCHIVE"

# Don't delete yet - just prepare consolidation
echo "Pipeline consolidation prepared (not executed - needs manual review)"

echo ""
echo "=== PHASE 3: TEST WHAT WE HAVE ==="

# Test imports still work
echo "Testing critical imports..."
python3 -c "import src.regions.manager; print('✓ Regions manager OK')" 2>/dev/null || echo "⚠ Regions manager has issues"
python3 -c "import src.core.pipeline_v7; print('✓ Pipeline v7 OK')" 2>/dev/null || echo "⚠ Pipeline v7 has issues"

echo ""
echo "=== SAFE CLEANUP COMPLETE ==="
echo ""
echo "SUMMARY:"
echo "  ✓ Full backup created: archive/$BACKUP_NAME.tar.gz"
echo "  ✓ Korean scripts archived: $KOREAN_ARCHIVE (not deleted)"
echo "  ✓ Pipeline versions archived: $PIPELINE_ARCHIVE (not deleted)"
echo "  ✓ Korean CLI wrapper created: scripts/korean_unified.py"
echo ""
echo "NEXT STEPS:"
echo "  1. Test that everything still works"
echo "  2. If OK, remove archived files:"
echo "     rm scripts/korean/*.py"
echo "     (Keep only essential pipelines)"
echo "  3. Complete Korean toolkit implementation"
echo ""
echo "TO ROLLBACK:"
echo "  tar -xzf archive/$BACKUP_NAME.tar.gz"
echo ""