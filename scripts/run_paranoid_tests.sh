#!/bin/bash
set -e

# GMNAP Paranoid Testing Script
# Runs comprehensive hell-level testing with detailed reporting

echo "🔥 GMNAP PARANOID TESTING SUITE 🔥"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=3600  # 1 hour timeout
MAX_MEMORY_GB=4
REPORT_DIR="paranoid-test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}Timestamp: $TIMESTAMP${NC}"
echo -e "${BLUE}Report Directory: $REPORT_DIR${NC}"
echo -e "${BLUE}Max Memory: ${MAX_MEMORY_GB}GB${NC}"
echo -e "${BLUE}Timeout: ${TIMEOUT}s${NC}"
echo ""

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to run command with timeout and logging
run_test() {
    local test_name="$1"
    local command="$2"
    local log_file="$REPORT_DIR/${test_name}_${TIMESTAMP}.log"
    
    log "${BLUE}🧪 Running $test_name...${NC}"
    
    if timeout "$TIMEOUT" bash -c "$command" > "$log_file" 2>&1; then
        log "${GREEN}✅ $test_name PASSED${NC}"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log "${RED}⏰ $test_name TIMED OUT (${TIMEOUT}s)${NC}"
        else
            log "${RED}❌ $test_name FAILED (exit code: $exit_code)${NC}"
        fi
        
        # Show last few lines of log on failure
        echo -e "${YELLOW}Last 10 lines of output:${NC}"
        tail -n 10 "$log_file" | sed 's/^/  /'
        echo ""
        
        return $exit_code
    fi
}

# Function to check memory usage
check_memory() {
    local available_gb=$(free -g | awk '/^Mem:/{print $7}')
    if [ "$available_gb" -lt "$MAX_MEMORY_GB" ]; then
        log "${YELLOW}⚠️  Warning: Only ${available_gb}GB memory available, tests may be limited${NC}"
    fi
}

# Function to run with memory monitoring
run_with_memory_monitor() {
    local test_name="$1"
    local command="$2"
    local memory_log="$REPORT_DIR/${test_name}_memory_${TIMESTAMP}.log"
    
    # Start memory monitoring in background
    (
        while true; do
            ps aux --sort=-%mem | head -n 20 >> "$memory_log"
            echo "---" >> "$memory_log"
            free -h >> "$memory_log"
            echo "===" >> "$memory_log"
            sleep 5
        done
    ) &
    local monitor_pid=$!
    
    # Run the actual test
    run_test "$test_name" "$command"
    local result=$?
    
    # Stop memory monitoring
    kill $monitor_pid 2>/dev/null || true
    
    return $result
}

# Check prerequisites
log "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Python version
python_version=$(python3.12 --version 2>/dev/null || python3 --version 2>/dev/null || python --version 2>/dev/null)
log "Python: $python_version"

# Check available memory
check_memory

# Check disk space
disk_space=$(df -h . | tail -1 | awk '{print $4}')
log "Available disk space: $disk_space"

# Check dependencies
log "Checking dependencies..."
if ! python -c "import pytest, hypothesis, psutil, duckdb" 2>/dev/null; then
    log "${RED}❌ Missing dependencies. Run 'make install' first.${NC}"
    exit 1
fi

log "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

# Initialize test results tracking
declare -A test_results
total_tests=0
passed_tests=0
failed_tests=0

# Test 1: Smoke Tests (Quick validation)
log "${BLUE}Phase 1: Smoke Tests${NC}"
run_test "smoke_tests" "python -m pytest tests/unit/ -m smoke -v --tb=short --durations=5"
test_results["smoke"]=$?
((total_tests++))
[ ${test_results["smoke"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 2: Unit Tests with Coverage
log "${BLUE}Phase 2: Unit Tests${NC}"
run_test "unit_tests" "python -m pytest tests/unit/ -v --cov=src --cov-report=html:$REPORT_DIR/coverage-html --cov-report=xml:$REPORT_DIR/coverage.xml --junitxml=$REPORT_DIR/unit-results.xml --durations=10"
test_results["unit"]=$?
((total_tests++))
[ ${test_results["unit"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 3: Property-Based Tests (Hell Mode)
log "${BLUE}Phase 3: Property-Based Tests (Hell Mode)${NC}"
run_with_memory_monitor "property_tests" "HYPOTHESIS_PROFILE=test python -m pytest tests/property/ -v --tb=short -m property --hypothesis-show-statistics --durations=20"
test_results["property"]=$?
((total_tests++))
[ ${test_results["property"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 4: Security Tests (Injection & Attacks)
log "${BLUE}Phase 4: Security Tests${NC}"
run_test "security_tests" "python -m pytest tests/security/ -v --tb=short -m security --durations=10"
test_results["security"]=$?
((total_tests++))
[ ${test_results["security"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 5: Stress Tests (Resource Exhaustion)
log "${BLUE}Phase 5: Stress Tests${NC}"
run_with_memory_monitor "stress_tests" "python -m pytest tests/stress/ -v --tb=short -m stress --durations=30"
test_results["stress"]=$?
((total_tests++))
[ ${test_results["stress"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 6: Memory and Performance Tests
log "${BLUE}Phase 6: Memory & Performance Tests${NC}"
run_with_memory_monitor "memory_tests" "python -m pytest tests/memory/ -v --tb=short -m memory --durations=30"
test_results["memory"]=$?
((total_tests++))
[ ${test_results["memory"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))

# Test 7: Concurrent Tests (if available)
if [ -d "tests/concurrency" ]; then
    log "${BLUE}Phase 7: Concurrency Tests${NC}"
    run_test "concurrency_tests" "python -m pytest tests/concurrency/ -v --tb=short"
    test_results["concurrency"]=$?
    ((total_tests++))
    [ ${test_results["concurrency"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))
fi

# Test 8: Integration Tests
if [ -d "tests/integration" ]; then
    log "${BLUE}Phase 8: Integration Tests${NC}"
    run_test "integration_tests" "python -m pytest tests/integration/ -v --tb=short -m integration"
    test_results["integration"]=$?
    ((total_tests++))
    [ ${test_results["integration"]} -eq 0 ] && ((passed_tests++)) || ((failed_tests++))
fi

# Additional Security Scans
log "${BLUE}Phase 9: Additional Security Scans${NC}"

# Bandit security scan
if command -v bandit >/dev/null 2>&1; then
    run_test "bandit_scan" "bandit -r src/ -f json -o $REPORT_DIR/bandit-report.json"
    test_results["bandit"]=$?
else
    log "${YELLOW}⚠️  Bandit not available, skipping${NC}"
    test_results["bandit"]=0
fi

# Safety dependency scan
if command -v safety >/dev/null 2>&1; then
    run_test "safety_scan" "safety check --json --output $REPORT_DIR/safety-report.json"
    test_results["safety"]=$?
else
    log "${YELLOW}⚠️  Safety not available, skipping${NC}"
    test_results["safety"]=0
fi

# Performance profiling
log "${BLUE}Phase 10: Performance Profiling${NC}"
run_test "performance_profile" "python -m cProfile -o $REPORT_DIR/profile.stats -m pytest tests/memory/test_performance_memory.py::TestUnicodeNormalizationPerformance::test_normalization_speed_benchmark -v"
test_results["profile"]=$?

# Generate comprehensive test report
log "${BLUE}Phase 11: Generating Test Report${NC}"
if [ -f "scripts/generate_test_report.py" ]; then
    run_test "test_report" "python scripts/generate_test_report.py --output-dir $REPORT_DIR"
    test_results["report"]=$?
else
    log "${YELLOW}⚠️  Test report generator not found${NC}"
    test_results["report"]=0
fi

# Calculate final results
echo ""
echo "=============================="
echo "🏁 PARANOID TESTING COMPLETE"
echo "=============================="

success_rate=$(( passed_tests * 100 / total_tests ))

log "${BLUE}Results Summary:${NC}"
log "  Total Test Phases: $total_tests"
log "  Passed: $passed_tests"
log "  Failed: $failed_tests"
log "  Success Rate: ${success_rate}%"

echo ""
log "${BLUE}Detailed Results:${NC}"
for test_name in "${!test_results[@]}"; do
    result=${test_results[$test_name]}
    if [ $result -eq 0 ]; then
        log "  ${GREEN}✅ $test_name: PASSED${NC}"
    else
        log "  ${RED}❌ $test_name: FAILED (exit $result)${NC}"
    fi
done

echo ""
log "${BLUE}Report Location: $REPORT_DIR${NC}"

# List generated files
echo ""
log "${BLUE}Generated Files:${NC}"
find "$REPORT_DIR" -type f -name "*${TIMESTAMP}*" | sort | while read -r file; do
    size=$(du -h "$file" | cut -f1)
    log "  📄 $file ($size)"
done

# Create summary file
summary_file="$REPORT_DIR/test_summary_${TIMESTAMP}.txt"
{
    echo "GMNAP Paranoid Test Results"
    echo "=========================="
    echo "Timestamp: $TIMESTAMP"
    echo "Total Phases: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $failed_tests"
    echo "Success Rate: ${success_rate}%"
    echo ""
    echo "Phase Results:"
    for test_name in "${!test_results[@]}"; do
        result=${test_results[$test_name]}
        status=$([ $result -eq 0 ] && echo "PASSED" || echo "FAILED")
        echo "  $test_name: $status"
    done
} > "$summary_file"

log "${GREEN}📄 Summary saved to: $summary_file${NC}"

# Final exit code
if [ $failed_tests -eq 0 ]; then
    echo ""
    log "${GREEN}🎉 ALL PARANOID TESTS PASSED! 🎉${NC}"
    log "${GREEN}The code is ready for hell-level production use! 🔥${NC}"
    exit 0
else
    echo ""
    log "${RED}💥 $failed_tests test phases failed!${NC}"
    log "${RED}Please review the detailed logs and fix issues before deployment.${NC}"
    
    # Show which tests failed
    echo ""
    log "${RED}Failed phases:${NC}"
    for test_name in "${!test_results[@]}"; do
        result=${test_results[$test_name]}
        if [ $result -ne 0 ]; then
            log "  ${RED}❌ $test_name${NC}"
        fi
    done
    
    exit 1
fi