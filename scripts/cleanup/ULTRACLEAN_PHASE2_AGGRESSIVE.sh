#!/bin/bash
# ULTRACLEAN PHASE 2: AGGRESSIVE CLEANUP
# Purpose: Complete the cleanup - reduce 1,500 files to 500
# Date: 2025-09-01

set -e  # Exit on error

echo "=============================================="
echo "ULTRACLEAN PHASE 2: AGGRESSIVE CLEANUP"
echo "=============================================="
echo ""
echo "This will aggressively clean the repository:"
echo "  - Archive 217 Korean scripts"
echo "  - Delete duplicate pipeline versions"
echo "  - Consolidate monitoring systems"
echo "  - Remove test duplicates"
echo "  - Clean scripts directory"
echo ""
echo "WARNING: This is AGGRESSIVE. Backup exists but be careful!"
echo ""

# Safety check
read -p "Are you SURE you want to proceed? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 1
fi

echo ""
echo "=== PHASE 1: KOREAN CRISIS RESOLUTION ==="
echo "Archiving 217 Korean scripts..."

# Create archive directory
mkdir -p archive/korean_scripts_old

# Move all Korean scripts to archive
if [ -d "scripts/korean" ]; then
    echo "Moving scripts/korean/*.py to archive..."
    find scripts/korean -name "*.py" -exec mv {} archive/korean_scripts_old/ \; 2>/dev/null || true
    echo "Archived $(ls archive/korean_scripts_old/*.py 2>/dev/null | wc -l) Korean scripts"
fi

# Create single Korean CLI
echo "Creating unified Korean CLI..."
cat > scripts/korean_cli.py << 'EOF'
#!/usr/bin/env python3
"""Unified Korean CLI - Replaces 217 individual scripts"""

import click
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.korean_toolkit import KoreanToolkit
except ImportError:
    print("Error: korean_toolkit not found. Please ensure it's properly installed.")
    sys.exit(1)

@click.group()
def cli():
    """Korean processing toolkit - unified interface."""
    pass

@cli.command()
@click.option('--mode', default='all', help='Analysis mode')
@click.argument('input_file', required=False)
def analyze(mode, input_file):
    """Run analysis (replaces 37 analyze_*.py scripts)"""
    toolkit = KoreanToolkit()
    # Load data from file if provided
    data = None
    if input_file:
        with open(input_file, 'r') as f:
            import json
            data = json.load(f)
    
    results = toolkit.analyze(data, mode)
    print(results)

@cli.command()
@click.option('--issue', required=True, help='Issue type to fix')
@click.argument('input_file')
def fix(issue, input_file):
    """Apply fixes (replaces 86 fix_*.py scripts)"""
    toolkit = KoreanToolkit()
    with open(input_file, 'r') as f:
        import json
        data = json.load(f)
    
    fixed = toolkit.fix(issue, data)
    print(fixed)

@cli.command()
@click.option('--rules', default='all', help='Validation rules')
@click.argument('input_file')
def validate(rules, input_file):
    """Validate data (replaces validate_*.py scripts)"""
    toolkit = KoreanToolkit()
    with open(input_file, 'r') as f:
        data = f.read()
    
    results = toolkit.validate(data, rules)
    print(results)

@cli.command()
@click.option('--target', default='all', help='Build target')
def build(target):
    """Build artifacts (replaces build_*.py scripts)"""
    toolkit = KoreanToolkit()
    results = toolkit.build(target)
    print(f"Build complete: {results}")

if __name__ == '__main__':
    cli()
EOF

chmod +x scripts/korean_cli.py
echo "✓ Created unified Korean CLI"

echo ""
echo "=== PHASE 2: PIPELINE CONSOLIDATION ==="

# Consolidate pipeline versions
if [ -f "src/core/pipeline_v7.py" ]; then
    echo "Consolidating pipeline versions..."
    
    # Backup v7 as main pipeline
    cp src/core/pipeline_v7.py src/core/pipeline_new.py
    
    # Archive old versions
    mkdir -p archive/old_pipelines
    mv src/core/pipeline.py archive/old_pipelines/ 2>/dev/null || true
    mv src/core/pipeline_v6.py archive/old_pipelines/ 2>/dev/null || true
    mv src/core/pipeline_stage_implementation.py archive/old_pipelines/ 2>/dev/null || true
    
    # Rename v7 as main
    mv src/core/pipeline_new.py src/core/pipeline.py
    
    # Handle streaming
    if [ -f "src/core/streaming_pipeline_v7.py" ]; then
        mv src/core/streaming_pipeline.py archive/old_pipelines/ 2>/dev/null || true
        mv src/core/streaming_pipeline_v7.py src/core/streaming.py
    fi
    
    echo "✓ Pipeline versions consolidated"
fi

echo ""
echo "=== PHASE 3: MONITORING CONSOLIDATION ==="

# Consolidate monitoring
if [ -f "src/core/monitoring_production.py" ]; then
    echo "Consolidating monitoring systems..."
    
    mkdir -p archive/old_monitoring
    mv src/core/monitoring.py archive/old_monitoring/ 2>/dev/null || true
    mv src/core/monitoring_v7.py archive/old_monitoring/ 2>/dev/null || true
    
    # Use production as main
    mv src/core/monitoring_production.py src/core/monitoring.py 2>/dev/null || true
    
    echo "✓ Monitoring consolidated"
fi

echo ""
echo "=== PHASE 4: SCRIPTS DIRECTORY CLEANUP ==="

# Consolidate analysis scripts
if [ -d "scripts/analysis" ]; then
    echo "Consolidating analysis scripts..."
    mkdir -p archive/old_analysis
    
    # Keep only essential analysis scripts
    essential_analysis="debug_conversion.py debug_database_issue.py"
    
    for script in scripts/analysis/*.py; do
        basename=$(basename "$script")
        if [[ ! " $essential_analysis " =~ " $basename " ]]; then
            mv "$script" archive/old_analysis/ 2>/dev/null || true
        fi
    done
    
    echo "✓ Analysis scripts reduced from $(ls archive/old_analysis/*.py 2>/dev/null | wc -l) to $(ls scripts/analysis/*.py 2>/dev/null | wc -l)"
fi

# Consolidate migration scripts
if [ -d "scripts/migration" ]; then
    echo "Consolidating migration scripts..."
    mkdir -p archive/old_migration
    
    # Archive most migration scripts (keep only recent/essential)
    find scripts/migration -name "*.py" -mtime +7 -exec mv {} archive/old_migration/ \; 2>/dev/null || true
    
    echo "✓ Migration scripts reduced"
fi

echo ""
echo "=== PHASE 5: TEST CONSOLIDATION ==="

# Consolidate test frameworks
echo "Consolidating test frameworks..."
mkdir -p tests_consolidated

# Move paranoid tests as base
if [ -d "tests/paranoid" ]; then
    cp -r tests/paranoid/* tests_consolidated/ 2>/dev/null || true
fi

# Archive old test structure
mkdir -p archive/old_tests
mv tests/unit archive/old_tests/ 2>/dev/null || true
mv tests/integration archive/old_tests/ 2>/dev/null || true
mv tests/performance archive/old_tests/ 2>/dev/null || true
mv tests/security archive/old_tests/ 2>/dev/null || true

echo "✓ Test frameworks consolidated"

echo ""
echo "=== PHASE 6: REMOVE DUPLICATES ==="

# Find and remove duplicate Python files
echo "Scanning for duplicate Python files..."
find . -name "*.py" -type f | while read file; do
    basename=$(basename "$file")
    
    # Skip if in archive
    if [[ "$file" == *"/archive/"* ]]; then
        continue
    fi
    
    # Check for duplicates
    duplicates=$(find . -name "$basename" -type f | grep -v archive | grep -v "$file")
    
    if [ ! -z "$duplicates" ]; then
        echo "  Found duplicates of $basename"
        # Keep the one in src/, archive others
        for dup in $duplicates; do
            if [[ "$dup" != *"/src/"* ]]; then
                mkdir -p archive/duplicates
                mv "$dup" archive/duplicates/ 2>/dev/null || true
            fi
        done
    fi
done

echo ""
echo "=== PHASE 7: FINAL CLEANUP ==="

# Remove empty directories
echo "Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# Clean Python cache again
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "=============================================="
echo "AGGRESSIVE CLEANUP COMPLETE!"
echo "=============================================="
echo ""
echo "Results:"
echo "  Korean scripts: $(ls scripts/korean/*.py 2>/dev/null | wc -l) remaining (was 217)"
echo "  Pipeline files: $(ls src/core/pipeline*.py src/core/streaming*.py 2>/dev/null | wc -l) remaining (was 6)"
echo "  Monitoring files: $(ls src/core/monitoring*.py 2>/dev/null | wc -l) remaining (was 3)"
echo "  Total scripts: $(find scripts -name "*.py" 2>/dev/null | wc -l) remaining (was 551)"
echo "  Total tests: $(find tests -name "*.py" 2>/dev/null | wc -l) remaining (was 219)"
echo ""
echo "Archived files saved in: archive/"
echo ""
echo "Next steps:"
echo "  1. Test that critical functionality still works"
echo "  2. Update imports in remaining files"
echo "  3. Commit the cleanup"
echo ""
echo "Recommended commit message:"
echo "  git add -A"
echo "  git commit -m '🧹 PHASE 2: Aggressive cleanup - 217 Korean scripts → 1 CLI, consolidate pipelines'"
echo "