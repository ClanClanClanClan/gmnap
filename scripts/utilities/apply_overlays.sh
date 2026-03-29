#!/bin/bash
# Apply all overlay files from pushes 1-12
set -e

echo "🚀 Applying GMNAP V7 overlays..."

# Create directories if they don't exist
mkdir -p src/pipeline
mkdir -p src/ops
mkdir -p src/security
mkdir -p src/authority
mkdir -p src/llm
mkdir -p schemas
mkdir -p templates
mkdir -p grafana/alerts
mkdir -p grafana/dashboards
mkdir -p config
mkdir -p tests/stage{1..12}

# Function to copy files with overwrite
copy_files() {
    local push_num=$1
    local overlay_dir="overlays/push${push_num}"
    
    if [ ! -d "$overlay_dir" ]; then
        echo "⚠️  Push $push_num overlay not found, skipping..."
        return
    fi
    
    echo "📦 Applying push $push_num..."
    
    # Copy src files
    if [ -d "$overlay_dir/src" ]; then
        cp -r "$overlay_dir/src/"* src/ 2>/dev/null || true
    fi
    
    # Copy test files
    if [ -d "$overlay_dir/tests" ]; then
        cp -r "$overlay_dir/tests/"* tests/ 2>/dev/null || true
    fi
    
    # Copy schema files
    if [ -d "$overlay_dir/schemas" ]; then
        cp -r "$overlay_dir/schemas/"* schemas/ 2>/dev/null || true
    fi
    
    # Copy template files
    if [ -d "$overlay_dir/templates" ]; then
        cp -r "$overlay_dir/templates/"* templates/ 2>/dev/null || true
    fi
    
    # Copy grafana files
    if [ -d "$overlay_dir/grafana" ]; then
        cp -r "$overlay_dir/grafana/"* grafana/ 2>/dev/null || true
    fi
    
    # Copy config files
    if [ -d "$overlay_dir/config" ]; then
        cp -r "$overlay_dir/config/"* config/ 2>/dev/null || true
    fi
    
    # Copy scripts
    if [ -d "$overlay_dir/scripts" ]; then
        cp -r "$overlay_dir/scripts/"* scripts/ 2>/dev/null || true
    fi
}

# Apply each push in order
for i in {1..12}; do
    copy_files $i
done

# Also copy from the initial patch folder if it exists
if [ -d "overlays/patch" ]; then
    echo "📦 Applying initial patch..."
    cp -r overlays/patch/src/* src/ 2>/dev/null || true
    cp -r overlays/patch/tests/* tests/ 2>/dev/null || true
    cp -r overlays/patch/schemas/* schemas/ 2>/dev/null || true
fi

# Copy requirements files
echo "📝 Consolidating requirements..."
cat overlays/push*/requirements*.txt 2>/dev/null | sort -u > requirements.v7.complete.txt || true

echo "✅ Overlays applied successfully!"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.v7.complete.txt"
echo "2. Apply patches: bash overlays/apply_all_patches.sh"
echo "3. Run tests: pytest tests/ -k 'not liveapi'"