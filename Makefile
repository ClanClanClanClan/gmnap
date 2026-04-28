# GMNAP Makefile - Specs v6 Compliance

.PHONY: help setup install-fasttext install-hooks quick full extreme test lint update-sources clean audit browser-test lock

help:
	@echo "GMNAP - Global Mathematician-Name Authority Project"
	@echo ""
	@echo "Available targets:"
	@echo "  setup        - One-time setup (pip install + compile fasttext + install git hooks)"
	@echo "  install-fasttext - Compile the fasttext CLI binary"
	@echo "  install-hooks - Install git pre-commit hook(s) into .git/hooks/"
	@echo "  quick        - Run pipeline in Quick mode (tier-0 APIs only)"
	@echo "  full         - Run pipeline in Full mode (tier-0 + tier-1)"
	@echo "  extreme      - Run pipeline in Extreme mode (all tiers)"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run code linting"
	@echo "  audit        - Run comprehensive audit"
	@echo "  update-sources - Update authority source configurations"
	@echo "  clean        - Clean cache and temporary files"

# One-time setup for a fresh clone
setup:
	pip install -r requirements.txt
	@bash scripts/install_fasttext.sh || \
		echo "⚠️  fasttext install skipped; rules-only detection will be used."
	@bash scripts/install_hooks.sh || \
		echo "⚠️  pre-commit hook install skipped (not a git checkout?)"
	@echo ""
	@echo "Setup complete. Try:  gmnap query \"Euler, Leonhard\""

install-fasttext:
	@bash scripts/install_fasttext.sh

install-hooks:
	@bash scripts/install_hooks.sh

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

# Adversarial browser-smoke harness. Spawns uvicorn on a free port, drives
# Chromium through ~25 scenarios, writes docs/browser_audit.md.
browser-test:
	pip install -r requirements-dev.txt
	playwright install --with-deps chromium
	PYTHONPATH=. python3 tools/browser_smoke.py --headless

# Regenerate the pinned-transitive-deps lockfile from requirements.txt.
# Run after editing requirements.txt; commit both files together so a
# fresh `pip install -r requirements.lock` reproduces the dependency
# graph the CI ran against. Requires `pip install pip-tools`.
lock:
	pip-compile --strip-extras --output-file=requirements.lock requirements.txt

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
