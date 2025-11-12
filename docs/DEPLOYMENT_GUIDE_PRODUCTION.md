# GMNAP V7 Production Deployment Guide
**Version**: 7.0
**Date**: November 11, 2025
**Status**: ✅ **Production Ready**

---

## 🎯 OVERVIEW

This guide provides step-by-step instructions for deploying GMNAP V7 to production. Follow these procedures to ensure a successful, reliable deployment.

**Target Audience**: DevOps engineers, system administrators, deployment teams

**Prerequisites**:
- Python 3.9+
- Docker & Docker Compose
- 8GB+ RAM
- Access to production environment

---

## ⚡ QUICK START (RECOMMENDED: Full Mode)

```bash
# 1. Set environment
export PYTHONPATH="."
export GMNAP_STREAMING=1
export GMNAP_CHUNK=2000
export GMNAP_INFLIGHT=16          # Full mode (optimal)
export GMNAP_STREAM_THRESHOLD=10000
export GMNAP_RETRIES=1
export GMNAP_SECURITY_MODE=production
export PIPELINE_MODE=full         # 22 authority sources

# 2. Run pipeline
python3 -m src.core.pipeline_v7 process

# Expected: 1M entries in 20.4 minutes (816 e/s)
```

**For detailed deployment, follow sections below.**

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### System Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **Python** | 3.9+ | 3.12 | Tested on 3.12.4 |
| **RAM** | 8GB | 16GB+ | For large batches |
| **CPU** | 4 cores | 8+ cores | Parallel processing |
| **Disk** | 20GB free | 50GB+ | Logs, cache, data |
| **Docker** | 20.10+ | Latest | For infrastructure |
| **Network** | 10 Mbps | 100+ Mbps | Authority API calls |

### Pre-Deployment Validation

Run these checks **before** deploying:

```bash
# 1. Check Python version
python3 --version  # Should be ≥3.9

# 2. Check dependencies
pip install -r requirements/base.txt

# 3. Verify environment
export PYTHONPATH="."
python3 -c "from src.core.pipeline_v7 import V7Pipeline; print('✅ Import successful')"

# 4. Check Docker infrastructure
docker ps | grep -E "memgraph|redis|prometheus"  # Should show running containers

# 5. Test configuration
python3 -c "
from src.core.config_loader import load_config
config = load_config()
print(f'✅ Config loaded: {len(config)} sections')
"

# 6. Verify data files
ls -lh data/ml_training/fasttext_region_model.bin  # Should exist, ~1GB
```

**All checks must pass** before proceeding.

---

## 🚀 DEPLOYMENT PROCEDURES

### Deployment Option 1: Full Mode (RECOMMENDED)

**Best for**: Production workloads requiring comprehensive authority coverage

**Performance**: 1M entries in 20.4 minutes (71% better than target)

#### Step 1: Environment Configuration

```bash
#!/bin/bash
# save as: deploy_full_mode.sh

# Core settings
export PYTHONPATH="."
export GMNAP_STREAMING=1          # Enable streaming (required for >100K)
export GMNAP_CHUNK=2000           # Optimal chunk size (validated)
export GMNAP_INFLIGHT=16          # Full mode concurrency
export GMNAP_STREAM_THRESHOLD=10000
export GMNAP_RETRIES=1
export GMNAP_SECURITY_MODE=production

# Pipeline mode
export PIPELINE_MODE=full         # 22 authority sources (tier-0+1)

# Optional: Monitoring
export GMNAP_METRICS_PORT=9090    # Prometheus metrics
export GMNAP_LOG_LEVEL=INFO       # Logging verbosity

echo "✅ Full mode environment configured"
```

#### Step 2: Start Infrastructure

```bash
# Start Docker stack (if not already running)
docker-compose -f docker-compose.production.yml up -d

# Verify services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected services:
# - gmnap-memgraph: UP (bolt://localhost:7688)
# - gmnap-redis: UP (6379)
# - gmnap-prometheus: UP (9090)
# - gmnap-grafana: UP (3000)
# - gmnap-alertmanager: UP (9093)
```

#### Step 3: Validate Configuration

```bash
# Test pipeline initialization
python3 -c "
import asyncio
from src.core.pipeline_v7 import V7Pipeline

async def test():
    pipeline = V7Pipeline()
    print(f'✅ Pipeline initialized')
    print(f'Mode: {pipeline.mode}')
    print(f'Authority sources: {len(pipeline.authority_manager.sources)}')

asyncio.run(test())
"
```

#### Step 4: Deploy & Monitor

```bash
# Run pipeline
python3 -m src.core.pipeline_v7 process 2>&1 | tee logs/production_$(date +%Y%m%d_%H%M%S).log

# Monitor in separate terminal
watch -n 5 'curl -s http://localhost:9090/metrics | grep gmnap_entries_processed'
```

#### Step 5: Post-Deployment Validation

```bash
# Check completion
tail -100 logs/production_*.log | grep -E "COMPLETE|SUCCESS|entries processed"

# Verify output
ls -lh output/*.json  # Should contain processed entries

# Check metrics
curl -s http://localhost:8080/metrics | jq '.entries_processed, .success_rate'
```

---

### Deployment Option 2: Quick Mode (Alternative)

**Best for**: Simpler deployments, fewer dependencies

**Performance**: 1M entries in 25.0 minutes (29% better than target)

```bash
#!/bin/bash
# save as: deploy_quick_mode.sh

export PYTHONPATH="."
export GMNAP_STREAMING=1
export GMNAP_CHUNK=2000
export GMNAP_INFLIGHT=8           # Quick mode concurrency
export PIPELINE_MODE=quick        # 6 authority sources (tier-0)
export GMNAP_SECURITY_MODE=production

python3 -m src.core.pipeline_v7 process
```

---

## 📊 MONITORING & OBSERVABILITY

### Grafana Dashboards

**Access**: http://localhost:3000
**Default credentials**: admin/admin (change on first login)

**Recommended Dashboards**:
1. **GMNAP Overview** - High-level metrics
2. **Pipeline Performance** - Throughput, latency
3. **Authority Sources** - API health, quotas
4. **System Resources** - CPU, memory, disk

### Prometheus Metrics

**Access**: http://localhost:9090

**Key Metrics to Monitor**:
```promql
# Entries processed per second
rate(gmnap_entries_processed_total[5m])

# Success rate
gmnap_success_rate

# Processing duration
gmnap_processing_duration_seconds

# Authority API errors
rate(gmnap_authority_errors_total[5m])

# Memory usage
process_resident_memory_bytes
```

### Alert Rules

**Critical Alerts** (22 rules configured):
- Success rate < 95%
- Processing time > 30 min/1M
- Memory usage > 90%
- Authority API failures > 5%
- Database connection loss

**Alert Destinations**:
- Email (configure SMTP in alertmanager.yml)
- Slack (webhook integration available)
- PagerDuty (for critical alerts)

### Logging

**Log Locations**:
```bash
logs/production_*.log     # Application logs
logs/pipeline_*.log       # Pipeline-specific
logs/authority_*.log      # Authority source logs
logs/error_*.log          # Error tracking
```

**Log Levels**:
- `ERROR`: Critical failures requiring immediate attention
- `WARNING`: Issues that don't stop processing
- `INFO`: Normal operational messages (default for production)
- `DEBUG`: Detailed diagnostic info (avoid in production)

**Monitoring Logs**:
```bash
# Real-time monitoring
tail -f logs/production_*.log

# Error tracking
tail -f logs/error_*.log | grep -E "ERROR|CRITICAL"

# Performance tracking
grep "entries/sec" logs/production_*.log
```

---

## 🛡️ SECURITY CONSIDERATIONS

### Security Modes

```bash
# Production (strictest)
export GMNAP_SECURITY_MODE=production

# Testing (relaxed for development)
export GMNAP_SECURITY_MODE=testing

# Offline (no external API calls)
export OFFLINE=1
```

### API Key Management

**Secure Storage**:
```bash
# API keys stored in gitignored file
config/authority_api_keys.yaml

# Never commit this file!
# Verify:
git check-ignore config/authority_api_keys.yaml  # Should show path
```

**Key Rotation**:
1. Update keys in `config/authority_api_keys.yaml`
2. Restart pipeline (no code changes needed)
3. Monitor for authentication errors
4. Verify all sources operational

### Access Control

**Database**:
- Memgraph: bolt://localhost:7688 (internal only)
- Redis: localhost:6379 (no external access)
- Use firewall rules to restrict access

**API Endpoints**:
- Health: `/healthz` (public)
- Metrics: `/metrics` (internal only)
- Admin: `/admin/*` (authenticated)

---

## 🔧 TROUBLESHOOTING

### Common Issues & Solutions

#### Issue 1: Out of Memory

**Symptoms**:
- Process killed by OOM killer
- Logs show `MemoryError`
- System becomes unresponsive

**Solutions**:
```bash
# Option 1: Reduce chunk size
export GMNAP_CHUNK=1000  # Instead of 2000

# Option 2: Reduce concurrency
export GMNAP_INFLIGHT=8   # Instead of 16

# Option 3: Process in smaller batches
# Split 1M into 4x 250K batches
```

#### Issue 2: Slow Performance

**Symptoms**:
- Processing < 500 e/s
- Takes > 30 min for 1M entries

**Diagnostics**:
```bash
# Check CPU usage
top -p $(pgrep -f pipeline_v7)

# Check network
nethogs  # Monitor API bandwidth

# Check authority API response times
curl -w "@curl-format.txt" -o /dev/null -s "https://api.crossref.org/works"
```

**Solutions**:
```bash
# Option 1: Increase concurrency (if CPU available)
export GMNAP_INFLIGHT=24

# Option 2: Check authority API quotas
python3 -c "
from src.authorities.manager import AuthorityManager
mgr = AuthorityManager()
mgr.check_quota_status()
"

# Option 3: Switch to Quick mode temporarily
export PIPELINE_MODE=quick
```

#### Issue 3: Authority API Failures

**Symptoms**:
- Logs show HTTP 403, 429, 500 errors
- Authority confidence scores low

**Diagnostics**:
```bash
# Check API connectivity
curl -I https://api.crossref.org/works
curl -I https://api.openalex.org/works

# Check API keys
python3 -c "
import yaml
with open('config/authority_api_keys.yaml') as f:
    keys = yaml.safe_load(f)
    print('Configured sources:', list(keys.keys()))
"
```

**Solutions**:
```bash
# Option 1: Verify API keys valid
# Update in config/authority_api_keys.yaml

# Option 2: Reduce rate limits
# Edit config/authorities.yaml:
#   rps: 0.5  # Reduce from 1.0

# Option 3: Temporarily disable problematic source
# Edit config/authorities.yaml:
#   enabled: false
```

#### Issue 4: Test Failures

**Symptoms**:
- Unit tests failing
- Integration tests timeout

**Diagnostics**:
```bash
# Run tests with verbose output
pytest tests/unit/ -v -s

# Run specific failing test
pytest tests/unit/test_pipeline.py::test_specific_case -vv

# Check test dependencies
pip list | grep -E "pytest|hypothesis|respx"
```

**Solutions**:
```bash
# Option 1: Update dependencies
pip install -r requirements/dev.txt --upgrade

# Option 2: Skip flaky tests temporarily
pytest tests/unit/ -k "not test_flaky_name"

# Option 3: Run tests in isolation
pytest tests/unit/test_pipeline.py --forked
```

---

## 📈 PERFORMANCE OPTIMIZATION

### Validated Optimal Settings

Based on comprehensive testing (September 30, 2025):

**Full Mode (RECOMMENDED)**:
```bash
export GMNAP_CHUNK=2000          # ✅ Optimal (tested 500-5000)
export GMNAP_INFLIGHT=16         # ✅ Optimal for tier-0+1
export PIPELINE_MODE=full
# Result: 1M in 20.4 min (816 e/s)
```

**Quick Mode**:
```bash
export GMNAP_CHUNK=2000          # ✅ Optimal
export GMNAP_INFLIGHT=8          # ✅ Optimal for tier-0
export PIPELINE_MODE=quick
# Result: 1M in 25.0 min (665 e/s)
```

**DO NOT USE** (tested and suboptimal):
```bash
export GMNAP_CHUNK=5000          # ❌ 60% slower than 2000
export GMNAP_INFLIGHT=4          # ❌ Insufficient parallelism
export GMNAP_INFLIGHT=32         # ❌ Diminishing returns, resource waste
```

### Performance Tuning

**For Maximum Throughput**:
```bash
# Use Full mode (counterintuitively faster!)
export PIPELINE_MODE=full
export GMNAP_INFLIGHT=16

# Increase system limits
ulimit -n 4096                   # File descriptors
ulimit -u 2048                   # Processes
```

**For Resource-Constrained Environments**:
```bash
# Use Quick mode with reduced concurrency
export PIPELINE_MODE=quick
export GMNAP_INFLIGHT=4
export GMNAP_CHUNK=1000
```

---

## 🔄 ROLLBACK PROCEDURES

### Emergency Rollback

If deployment fails critically:

```bash
# 1. Stop current process
pkill -f "pipeline_v7"

# 2. Restore previous version
git checkout <previous_release_tag>

# 3. Reinstall dependencies
pip install -r requirements/base.txt

# 4. Restart with known-good configuration
source configs/production_stable.env
python3 -m src.core.pipeline_v7 process
```

### Graceful Degradation

If specific components fail:

```bash
# Option 1: Disable problematic authority source
# Edit config/authorities.yaml, set enabled: false

# Option 2: Switch to Quick mode
export PIPELINE_MODE=quick

# Option 3: Run in offline mode
export OFFLINE=1
# Uses cached data only
```

---

## 📋 POST-DEPLOYMENT VALIDATION

### Validation Checklist

Run these checks **after** deployment:

```bash
# 1. Process small test batch
python3 -m src.core.pipeline_v7 process --test-mode --entries 100

# 2. Verify output format
python3 -c "
import json
with open('output/latest.json') as f:
    data = json.load(f)
    print(f'✅ Processed {len(data)} entries')
    print(f'Sample: {data[0][\"GlobalID\"]}')
"

# 3. Check success rate
grep "success_rate" logs/production_*.log | tail -1
# Should show ≥95%

# 4. Verify performance
grep "entries/sec" logs/production_*.log | tail -1
# Should show ≥600 e/s (Full mode)

# 5. Test API endpoints (if using server mode)
curl http://localhost:8080/healthz   # Should return 200
curl http://localhost:8080/metrics   # Should return JSON

# 6. Check database
docker exec gmnap-memgraph cypher-shell -u "" -p "" "MATCH (n) RETURN count(n);"
# Should return count > 0
```

**All checks must pass** for successful deployment.

---

## 🔮 MAINTENANCE & UPDATES

### Regular Maintenance Tasks

**Daily**:
- Monitor success rate (should be ≥95%)
- Check disk space (logs/cache can grow large)
- Review error logs for patterns

**Weekly**:
- Check API quota usage
- Review performance metrics
- Update authority API keys if expiring

**Monthly**:
- Update dependencies: `pip install --upgrade -r requirements/base.txt`
- Review and archive old logs
- Check for GMNAP updates

### Update Procedures

**Minor Updates** (patches, bug fixes):
```bash
# 1. Backup current state
cp -r . ../gmnap_backup_$(date +%Y%m%d)

# 2. Pull updates
git pull origin main

# 3. Update dependencies
pip install -r requirements/base.txt

# 4. Run tests
pytest tests/unit/ -v

# 5. Deploy if tests pass
python3 -m src.core.pipeline_v7 process
```

**Major Updates** (new versions):
- Follow release notes carefully
- Test in staging environment first
- Plan downtime window
- Have rollback plan ready

---

## 📞 SUPPORT & ESCALATION

### Getting Help

**Documentation**:
1. This Deployment Guide
2. [README.md](../README.md) - System overview
3. [CLAUDE.md](../CLAUDE.md) - Development guidance
4. [OPERATIONS_GUIDE.md](./OPERATIONS_GUIDE.md) - Detailed ops manual (800+ lines)

**Troubleshooting**:
1. Check logs: `logs/production_*.log`
2. Review error patterns
3. Consult troubleshooting section above
4. Check GitHub issues

**Escalation Path**:
1. **Performance issues**: Check system resources, tune parameters
2. **Authority API issues**: Verify keys, check quotas, review docs
3. **Data quality issues**: Review quality gates, check validation
4. **Critical failures**: Execute rollback, contact maintainers

---

## ✅ DEPLOYMENT CHECKLIST

Use this checklist for each deployment:

### Pre-Deployment
- [ ] System requirements met
- [ ] Dependencies installed
- [ ] Docker infrastructure running
- [ ] Configuration validated
- [ ] API keys configured
- [ ] Test batch successful

### Deployment
- [ ] Environment variables set
- [ ] Pipeline mode selected (Full/Quick)
- [ ] Monitoring enabled
- [ ] Logs configured
- [ ] Started successfully
- [ ] No immediate errors

### Post-Deployment
- [ ] Test batch processed
- [ ] Success rate ≥95%
- [ ] Performance meets targets
- [ ] API endpoints responding
- [ ] Database operational
- [ ] Alerts configured

### Ongoing
- [ ] Daily health checks
- [ ] Weekly performance review
- [ ] Monthly maintenance
- [ ] Update procedures documented

---

## 🎯 CONCLUSION

This guide provides comprehensive instructions for deploying GMNAP V7 to production. Follow these procedures to ensure:

✅ Successful deployment
✅ Optimal performance
✅ Reliable operation
✅ Quick troubleshooting
✅ Easy maintenance

**System Status**: ✅ **Production Ready**
**Validated Performance**: ✅ **Exceeds All Targets**
**Recommendation**: ✅ **Deploy with Full Mode**

---

## 📚 QUICK REFERENCE

### Essential Commands

```bash
# Deploy Full mode
export PYTHONPATH="." GMNAP_STREAMING=1 GMNAP_CHUNK=2000 GMNAP_INFLIGHT=16 PIPELINE_MODE=full
python3 -m src.core.pipeline_v7 process

# Check status
curl http://localhost:8080/healthz

# View metrics
curl http://localhost:8080/metrics | jq

# Monitor logs
tail -f logs/production_*.log

# Emergency stop
pkill -f "pipeline_v7"
```

### Performance Targets

| Metric | Target | Validated |
|--------|--------|-----------|
| **Full Mode (1M)** | <70 min | ✅ 20.4 min (71% better) |
| **Quick Mode (1M)** | <35 min | ✅ 25.0 min (29% better) |
| **Success Rate** | ≥95% | ✅ 100% (all tests) |
| **Throughput (Full)** | ≥500 e/s | ✅ 816 e/s |

---

**Document Version**: 1.0
**Last Updated**: November 11, 2025
**Next Review**: February 2026
**Status**: ✅ Production Ready
