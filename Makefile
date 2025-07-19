# GMNAP Makefile - Specs v6 Compliance

.PHONY: help quick full extreme test lint update-sources clean audit

help:
	@echo "GMNAP - Global Mathematician-Name Authority Project"
	@echo ""
	@echo "Available targets:"
	@echo "  quick        - Run pipeline in Quick mode (tier-0 APIs only)"
	@echo "  full         - Run pipeline in Full mode (tier-0 + tier-1)"
	@echo "  extreme      - Run pipeline in Extreme mode (all tiers)"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run code linting"
	@echo "  audit        - Run comprehensive audit"
	@echo "  update-sources - Update authority source configurations"
	@echo "  clean        - Clean cache and temporary files"

# Pipeline execution modes
quick:
	PYTHONPATH=. python3 -m src.core.pipeline_v6 --mode quick

full:
	PYTHONPATH=. python3 -m src.core.pipeline_v6 --mode full

extreme:
	PYTHONPATH=. python3 -m src.core.pipeline_v6 --mode extreme --force-extreme

# Testing
test:
	PYTHONPATH=. pytest tests/ -v

test-hardcore:
	PYTHONPATH=. pytest tests/hardcore/ -v

test-integration:
	PYTHONPATH=. pytest tests/integration/ -v

# Code quality
lint:
	black src/ tests/
	ruff check src/ tests/
	isort src/ tests/
	yamllint docs/ config/

# Analysis
audit:
	PYTHONPATH=. python3 analysis/comprehensive_audit.py

audit-quick:
	PYTHONPATH=. python3 analysis/comprehensive_audit.py --quick-test

# Maintenance
update-sources:
	PYTHONPATH=. python3 scripts/update_source_manifest.py

clean:
	rm -rf cache/output/*
	rm -rf cache/bad_json/*
	rm -rf test_results/realistic_test_results_*.json
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Development setup
setup-dev:
	pip install -r requirements.txt
	python3 scripts/setup_dev.sh

# Stats and reporting
stats:
	PYTHONPATH=. python3 scripts/generate_stats.py

report:
	PYTHONPATH=. python3 scripts/generate_test_report.py
