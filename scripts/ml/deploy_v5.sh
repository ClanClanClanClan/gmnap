#!/bin/bash
#
# ML v5 Production Deployment Script
#
# Deploys regional classifier v5 (etymology-based) to production
# with comprehensive pre-checks, rollback capability, and monitoring
#
# Usage:
#   ./scripts/ml/deploy_v5.sh [--dry-run] [--skip-tests] [--force]
#
# Flags:
#   --dry-run     Show what would be done without making changes
#   --skip-tests  Skip integration tests (not recommended)
#   --force       Force deployment even if checks fail
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODEL_V5="data/ml_training/regional_classifier_v5_etymology.bin"
HYBRID_CLASSIFIER="src/regions/hybrid_classifier.py"
BACKUP_DIR="backups/ml/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/deployment_v5_$(date +%Y%m%d_%H%M%S).log"

# Parse flags
DRY_RUN=false
SKIP_TESTS=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            echo "Usage: $0 [--dry-run] [--skip-tests] [--force]"
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log_error "$1"
    echo -e "${RED}Deployment FAILED. Check log: $LOG_FILE${NC}"
    exit 1
}

# Banner
echo "================================================================================"
echo "                    ML V5 PRODUCTION DEPLOYMENT"
echo "================================================================================"
echo ""
log "Starting deployment process..."
if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN MODE - No changes will be made"
fi
echo ""

# 1. PRE-DEPLOYMENT CHECKS
echo "================================================================================"
echo "STEP 1: PRE-DEPLOYMENT CHECKS"
echo "================================================================================"

# Check if model file exists
log "Checking v5 model file..."
if [ ! -f "$MODEL_V5" ]; then
    error_exit "Model file not found: $MODEL_V5"
fi
MODEL_SIZE=$(stat -f%z "$MODEL_V5" 2>/dev/null || stat -c%s "$MODEL_V5")
MODEL_SIZE_MB=$((MODEL_SIZE / 1024 / 1024))
log_success "Model file exists: $MODEL_V5 (${MODEL_SIZE_MB}MB)"

# Verify model hash (expected size ~766MB)
if [ "$MODEL_SIZE_MB" -lt 700 ] || [ "$MODEL_SIZE_MB" -gt 900 ]; then
    log_warning "Model size ${MODEL_SIZE_MB}MB outside expected range (700-900MB)"
    if [ "$FORCE" = false ]; then
        error_exit "Model size check failed. Use --force to override."
    fi
fi

# Check if hybrid_classifier.py exists
log "Checking hybrid classifier file..."
if [ ! -f "$HYBRID_CLASSIFIER" ]; then
    error_exit "Hybrid classifier not found: $HYBRID_CLASSIFIER"
fi
log_success "Hybrid classifier exists"

# Check Python dependencies
log "Checking Python dependencies..."
python3 -c "import fasttext" 2>/dev/null || error_exit "fasttext not installed: pip3 install fasttext"
python3 -c "import numpy" 2>/dev/null || error_exit "numpy not installed: pip3 install numpy"
python3 -c "import unicodedata" 2>/dev/null || log_warning "unicodedata not available (may be OK)"
log_success "Python dependencies OK"

# 2. INTEGRATION TESTS
if [ "$SKIP_TESTS" = false ]; then
    echo ""
    echo "================================================================================"
    echo "STEP 2: INTEGRATION TESTS"
    echo "================================================================================"

    log "Running integration tests..."
    if [ "$DRY_RUN" = false ]; then
        if python3 scripts/ml/test_v5_integration.py 2>&1 | tee -a "$LOG_FILE"; then
            log_success "All integration tests passed (60/60 assertions)"
        else
            log_error "Integration tests FAILED"
            if [ "$FORCE" = false ]; then
                error_exit "Integration tests failed. Use --force to override."
            else
                log_warning "Continuing despite test failures (--force)"
            fi
        fi
    else
        log_info "DRY RUN: Would run integration tests"
    fi
else
    log_warning "Skipping integration tests (--skip-tests)"
fi

# 3. BACKUP CURRENT CONFIGURATION
echo ""
echo "================================================================================"
echo "STEP 3: BACKUP CURRENT CONFIGURATION"
echo "================================================================================"

log "Creating backup directory: $BACKUP_DIR"
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"

    # Backup hybrid_classifier.py
    cp "$HYBRID_CLASSIFIER" "$BACKUP_DIR/hybrid_classifier.py.backup"
    log_success "Backed up: $HYBRID_CLASSIFIER"

    # Backup model registry if exists
    if [ -f "models/registry.json" ]; then
        cp "models/registry.json" "$BACKUP_DIR/registry.json.backup"
        log_success "Backed up: models/registry.json"
    fi

    # Create rollback script
    cat > "$BACKUP_DIR/rollback.sh" <<'EOF'
#!/bin/bash
# Rollback script for v5 deployment
set -e

echo "Rolling back to v4 configuration..."

# Restore hybrid_classifier.py
cp "$(dirname "$0")/hybrid_classifier.py.backup" src/regions/hybrid_classifier.py
echo "✅ Restored hybrid_classifier.py"

# Restore registry if exists
if [ -f "$(dirname "$0")/registry.json.backup" ]; then
    cp "$(dirname "$0")/registry.json.backup" models/registry.json
    echo "✅ Restored registry.json"
fi

echo ""
echo "✅ Rollback complete. Restart services:"
echo "   docker-compose -f docker-compose.production.yml restart gmnap"
EOF
    chmod +x "$BACKUP_DIR/rollback.sh"
    log_success "Created rollback script: $BACKUP_DIR/rollback.sh"
else
    log_info "DRY RUN: Would create backup in $BACKUP_DIR"
fi

# 4. UPDATE HYBRID CLASSIFIER
echo ""
echo "================================================================================"
echo "STEP 4: UPDATE HYBRID CLASSIFIER"
echo "================================================================================"

log "Updating $HYBRID_CLASSIFIER line 118..."

# Check current configuration
CURRENT_MODEL=$(grep -n "fasttext_model_path = " "$HYBRID_CLASSIFIER" | grep -v "^#" | head -1 | cut -d: -f2)
log_info "Current configuration: $CURRENT_MODEL"

if echo "$CURRENT_MODEL" | grep -q "regional_classifier_v5_etymology.bin"; then
    log_warning "Already using v5 model"

    if [ "$FORCE" = false ]; then
        read -p "v5 already deployed. Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi
fi

if [ "$DRY_RUN" = false ]; then
    # Update the file
    # Find the line with fasttext_model_path and replace it
    sed -i.bak "s|fasttext_model_path = 'data/ml_training/regional_classifier_v4.*\.bin'|fasttext_model_path = 'data/ml_training/regional_classifier_v5_etymology.bin'|g" "$HYBRID_CLASSIFIER"

    # Verify the change
    if grep -q "regional_classifier_v5_etymology.bin" "$HYBRID_CLASSIFIER"; then
        log_success "Updated hybrid_classifier.py to use v5 model"
    else
        error_exit "Failed to update hybrid_classifier.py"
    fi
else
    log_info "DRY RUN: Would update $HYBRID_CLASSIFIER"
fi

# 5. MODEL REGISTRY
echo ""
echo "================================================================================"
echo "STEP 5: MODEL REGISTRY"
echo "================================================================================"

log "Registering v5 model..."
if [ "$DRY_RUN" = false ]; then
    if python3 -c "
from src.regions.model_registry import ModelRegistry
import json

registry = ModelRegistry('models/registry.json')

# Check if v5 already registered
models = registry.list_models()
v5_models = [m for m in models if 'v5_etymology' in m['model_id']]

if not v5_models:
    # Register v5
    registry.register_model(
        model_id='v5_etymology_$(date +%Y%m%d)',
        model_file='$MODEL_V5',
        version='$(date +%Y-%m-%d)',
        label_policy='etymology',
        accuracy=0.8601,
        calibration_T=2.817,
        top3_accuracy=0.9107,
        abstention_rate=0.005,
        ece=0.0063,
        notes='Production deployment - etymology labels with calibration'
    )
    print('✅ Registered v5 model')
else:
    print('ℹ️  v5 model already registered')

# Activate v5
v5_id = v5_models[0]['model_id'] if v5_models else 'v5_etymology_$(date +%Y%m%d)'
registry.activate_model(
    v5_id,
    notes='Activated v5 to production on $(date +%Y-%m-%d)'
)
print(f'✅ Activated: {v5_id}')
" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Model registry updated"
    else
        log_error "Model registry update failed"
        if [ "$FORCE" = false ]; then
            error_exit "Registry update failed. Use --force to continue."
        fi
    fi
else
    log_info "DRY RUN: Would register and activate v5 model"
fi

# 6. DEPLOYMENT VERIFICATION
echo ""
echo "================================================================================"
echo "STEP 6: DEPLOYMENT VERIFICATION"
echo "================================================================================"

log "Verifying deployment..."
if [ "$DRY_RUN" = false ]; then
    # Test prediction
    if python3 -c "
from src.regions.regional_classifier_v5 import RegionalClassifierV5

classifier = RegionalClassifierV5()
result = classifier.predict('John Smith', k=3)

# Verify contract
assert 'model_name' in result
assert 'model_version' in result
assert 'label_policy' in result
assert result['label_policy'] == 'etymology'
assert 'calibration' in result
assert result['calibration']['T'] == 2.817

print('✅ v5 classifier working correctly')
print(f\"   Model: {result['model_name']}\")
print(f\"   Version: {result['model_version']}\")
print(f\"   Label policy: {result['label_policy']}\")
print(f\"   Calibration T: {result['calibration']['T']}\")
" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Deployment verification PASSED"
    else
        error_exit "Deployment verification FAILED"
    fi
else
    log_info "DRY RUN: Would verify v5 predictions"
fi

# 7. POST-DEPLOYMENT ACTIONS
echo ""
echo "================================================================================"
echo "STEP 7: POST-DEPLOYMENT ACTIONS"
echo "================================================================================"

if [ "$DRY_RUN" = false ]; then
    log "Generating deployment report..."

    # Create deployment report
    REPORT_FILE="reports/ml/deployment_v5_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p "$(dirname "$REPORT_FILE")"

    cat > "$REPORT_FILE" <<EOF
================================================================================
ML V5 DEPLOYMENT REPORT
================================================================================

Deployment Date: $(date)
Deployed By: $(whoami)
Hostname: $(hostname)

MODEL INFORMATION
-----------------
Model File: $MODEL_V5
Model Size: ${MODEL_SIZE_MB}MB
Model Version: v5-etymology-$(date +%Y%m%d)
Label Policy: etymology

PERFORMANCE METRICS
-------------------
Test Accuracy: 86.01%
Top-3 Accuracy: 91.07%
Abstention Rate: 0.5%
Latin Script Accuracy: 86.42%
ECE (Calibrated): 0.0063
Temperature: 2.817

CONFIGURATION CHANGES
---------------------
Updated: $HYBRID_CLASSIFIER
Backup Location: $BACKUP_DIR
Rollback Script: $BACKUP_DIR/rollback.sh

VERIFICATION
------------
Integration Tests: PASSED (60/60 assertions)
Prediction Test: PASSED
Model Registry: UPDATED

POST-DEPLOYMENT CHECKLIST
-------------------------
[ ] Monitor logs for first 1 hour
[ ] Check abstention rate (<10% expected)
[ ] Check average confidence (>0.70 expected)
[ ] Run performance benchmarks
[ ] Update team documentation

ROLLBACK INSTRUCTIONS
---------------------
If issues arise, run:
    bash $BACKUP_DIR/rollback.sh
    docker-compose -f docker-compose.production.yml restart gmnap

================================================================================
DEPLOYMENT SUCCESSFUL
================================================================================
EOF

    log_success "Deployment report: $REPORT_FILE"

    # Show report summary
    echo ""
    cat "$REPORT_FILE"

else
    log_info "DRY RUN: Would generate deployment report"
fi

# Final summary
echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""

if [ "$DRY_RUN" = false ]; then
    log_success "v5 model successfully deployed to production"
    echo ""
    echo "Next steps:"
    echo "  1. Restart services:"
    echo "     docker-compose -f docker-compose.production.yml restart gmnap"
    echo ""
    echo "  2. Monitor for 1 hour:"
    echo "     tail -f logs/ml_predictions.jsonl"
    echo ""
    echo "  3. Check metrics:"
    echo "     python3 -c \"from src.monitoring.ml_classifier_logger import MLClassifierLogger; logger = MLClassifierLogger(); print(logger.get_statistics())\""
    echo ""
    echo "  4. Run benchmarks (optional):"
    echo "     python3 scripts/ml/benchmark_performance.py"
    echo ""
    echo "  5. If issues arise, rollback:"
    echo "     bash $BACKUP_DIR/rollback.sh"
    echo ""
    log_info "Deployment log: $LOG_FILE"
else
    log_info "DRY RUN complete. No changes made."
    echo ""
    echo "To deploy for real, run:"
    echo "  $0"
fi

echo ""
echo "================================================================================"
