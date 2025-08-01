# Korean Name System - Production Release Checklist

## Pre-Release Validation
- [ ] `make validate-all` passes (exit code 0)
- [ ] All regression locks validate successfully  
- [ ] Performance ≥ 97% on math dataset
- [ ] No dangerous weights without position qualifiers
- [ ] Memory usage < 2GB during FST builds
- [ ] Runtime < 10 minutes for full validation

## Git Status
- [ ] All changes committed to main branch
- [ ] Pre-commit hooks installed and working
- [ ] Green tag created: `make tag-green`
- [ ] No unstaged changes in production files

## Production Readiness
- [ ] Lock files are read-only (444 permissions)
- [ ] No race condition testing conflicts
- [ ] Atomic operations tested (FST + CSV)
- [ ] Emergency rollback procedure tested

## Documentation
- [ ] All new weights documented with rationale
- [ ] Performance impact assessed and documented
- [ ] Rollback procedures updated if needed

## Deployment Commands
```bash
# Final validation
make validate-all

# Create immutable baseline
make tag-green

# Deploy to production
git push origin main --tags
```

## Emergency Procedures
```bash
# Emergency rollback
git checkout krp-green-YYYY-MM-DD
make build-fsts
make validate-all

# Quick fixes
make restore-backup
make add-weight WEIGHT="fix,fix,-1.0,GN,G"
```

## Post-Deployment
- [ ] Monitor first 24 hours for issues
- [ ] Update regression locks if new cases added
- [ ] Archive old performance baselines
- [ ] Update team documentation
