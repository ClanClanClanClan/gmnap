# Systematic Improvement Framework - Usage Guide

## Overview

This framework provides a **deterministic, regression-proof method** for adding new Korean name mappings without breaking existing functionality.

**Key Principle**: Every change must maintain ≥94% performance across all test datasets or be automatically rolled back.

---

## 🚀 Quick Start

### 1. Capture Current Baseline
```bash
python3 scripts/systematic_improvement_framework.py baseline
```
**Output**: Current performance across all 3 datasets (1,098 test cases)

### 2. Add New Mappings Systematically
```bash
python3 scripts/systematic_improvement_framework.py add "New Surnames"
```
**Interactive Process**:
- Enter mappings: `hangul,roman,weight`
- Provide rationale for changes
- Automatic validation and rollback if needed

### 3. Validate Anytime
```bash
python3 scripts/systematic_improvement_framework.py validate
```
**Output**: Performance check against thresholds

---

## 📋 Practical Example

### Scenario: Adding New Korean Mathematician Names

```bash
# Step 1: Capture baseline
$ python3 scripts/systematic_improvement_framework.py baseline
=== CAPTURING BASELINE PERFORMANCE ===
Testing math_dataset...
  math_dataset: 94.27% (691/733)
Testing diverse_dataset...
  diverse_dataset: 97.00% (194/200)  
Testing independent_dataset...
  independent_dataset: 92.73% (153/165)
✅ Baseline captured: baseline_20250731_101530.json

# Step 2: Add new mathematician surnames systematically
$ python3 scripts/systematic_improvement_framework.py add "Korean Mathematicians"
Adding mappings for category: Korean Mathematicians
Enter mappings in format: hangul,roman,weight
Enter empty line to finish:
> 장,jang,-0.8
> 배,bae,-0.8  
> 서,seo,-0.8
> 권,kwon,-0.8
> 

Rationale for these mappings: Adding common Korean mathematician surnames from Seoul National University faculty list

=== ADDING SYSTEMATIC MAPPINGS: Korean Mathematicians ===
Rationale: Adding common Korean mathematician surnames from Seoul National University faculty list
=== CAPTURING BASELINE PERFORMANCE ===
...
Added 4 mappings to Korean Mathematicians
Rebuilding FSTs...
Validating performance after changes...
Testing math_dataset...
  math_dataset: 94.41% (692/733)  # +1 case improvement!
Testing diverse_dataset...
  diverse_dataset: 97.00% (194/200)  # Maintained
Testing independent_dataset...
  independent_dataset: 92.73% (153/165)  # Maintained
✅ VALIDATION PASSED - Changes accepted
📝 Improvement logged: improvement_log_20250731_101545.json
✅ Systematic improvement completed successfully!
```

### Result: +1 math case improvement with zero regressions!

---

## 🔧 Advanced Usage

### Bulk Addition from File

Create `new_mappings.csv`:
```csv
hangul,roman,weight,category
장,jang,-0.8,Korean Mathematicians
배,bae,-0.8,Korean Mathematicians
서,seo,-0.8,Korean Mathematicians
권,kwon,-0.8,Korean Mathematicians
```

Then process programmatically:
```python
from systematic_improvement_framework import SystematicImprovementFramework

framework = SystematicImprovementFramework()

# Load mappings from file
mappings = [
    ("장", "jang", "-0.8"),
    ("배", "bae", "-0.8"), 
    ("서", "seo", "-0.8"),
    ("권", "kwon", "-0.8")
]

success = framework.add_systematic_mappings(
    category="Korean Mathematicians",
    mappings=mappings,
    rationale="SNU Mathematics faculty surnames from official directory"
)
```

---

## 🛡 Safety Mechanisms

### Automatic Rollback Example
```bash
$ python3 scripts/systematic_improvement_framework.py add "Problematic Test"
> 김,smith,-2.0  # This would break Korean → Smith mapping
> 

=== VALIDATION FAILED - Rolling back changes ===
Threshold violation: math_dataset dropped to 89.23% (below 94.0% threshold)
Rollback complete - original performance restored
❌ Systematic improvement failed - changes rolled back
```

### Performance Thresholds
- **Math Dataset**: Must maintain ≥94.0%
- **Diverse Dataset**: Must maintain ≥96.0%  
- **Independent Dataset**: Must maintain ≥92.0%
- **Regression Tolerance**: Maximum 1.0% drop from baseline

---

## 📊 Monitoring and Tracking

### Improvement Logs
Every successful change creates detailed logs in `data/improvement_tracking/`:

```json
{
  "timestamp": "2025-07-31T10:15:45",
  "category": "Korean Mathematicians", 
  "rationale": "SNU Mathematics faculty surnames",
  "mappings_added": 4,
  "baseline_performance": {
    "math_dataset": {"accuracy": 94.27}
  },
  "final_performance": {
    "math_dataset": {"accuracy": 94.41}
  },
  "improvement_summary": {
    "math_dataset": {"change": +0.14}
  }
}
```

### Baseline Tracking
All baselines stored with timestamps for historical comparison:
- `baselines/rr_syllable_map_20250731_101530.csv`
- `data/improvement_tracking/baseline_20250731_101530.json`

---

## 🎯 Best Practices

### 1. **Systematic Categories, Not Individual Cases**
✅ **Good**: "Korean Mathematicians", "Academic Titles", "Regional Surnames"  
❌ **Bad**: "Fix Lee Min-Ho", "Add Park case"

### 2. **Conservative Weights for New Mappings**
- Start with `-0.8` to `-0.3` range
- Only strengthen if validation passes
- Avoid extreme weights (< -2.0 or > 0.0)

### 3. **Clear Rationale Documentation**
✅ **Good**: "Adding surnames from Korean Mathematical Society member directory"  
❌ **Bad**: "These names failed"

### 4. **Batch Related Changes**
- Add surname sets together
- Group by linguistic patterns
- Test comprehensive changes, not incremental fixes

### 5. **Regular Baseline Capture**
```bash
# Weekly baseline capture for production monitoring
python3 scripts/systematic_improvement_framework.py baseline
```

---

## 🔄 Production Integration

### CI/CD Integration
```yaml
# .github/workflows/korean_improvements.yml
name: Korean Systematic Improvements
on:
  pull_request:
    paths: ['resources/rr_syllable_map.csv']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate Korean Improvements
        run: |
          python3 scripts/systematic_improvement_framework.py validate
          # Must pass all thresholds or fail the PR
```

### Operational Monitoring
```bash
# Daily production health check
python3 scripts/systematic_improvement_framework.py baseline > daily_health_check.log

# Alert if performance drops below thresholds
if [[ $(grep "THRESHOLD VIOLATION" daily_health_check.log) ]]; then
    echo "ALERT: Korean processor performance degraded"
    # Trigger rollback to last known good state
fi
```

---

## 🏆 Success Metrics

### Framework Effectiveness
- **Zero Regressions**: All changes validated before deployment
- **Systematic Improvements**: +0.1-0.5% accuracy per improvement cycle
- **Rollback Safety**: Failed changes automatically reverted
- **Audit Trail**: Complete history of all improvements

### Production Readiness Indicators
- ✅ **94.54% average performance** across 1,098 test cases
- ✅ **Deterministic improvement process** with automatic validation
- ✅ **Regression prevention** with automatic rollback
- ✅ **Comprehensive logging** for operational visibility

This framework ensures **systematic excellence** while maintaining the robustness needed for production mathematician name processing at scale.

---

*Systematic Improvement Framework v1.0  
Designed for production-grade Korean name processing*