# GMNAP Makefile - V7 Pipeline

.PHONY: help quick full extreme test lint lint-fix update-sources clean audit cost-check setup-dev download-model

help:
	@echo "GMNAP V7 - Global Mathematician-Name Authority Project"
	@echo ""
	@echo "Pipeline targets:"
	@echo "  quick          - Run V7 pipeline in Quick mode (tier-0, INFLIGHT=8)"
	@echo "  full           - Run V7 pipeline in Full mode (tier-0+1, INFLIGHT=16)"
	@echo "  extreme        - Run V7 pipeline in Extreme mode (all tiers)"
	@echo ""
	@echo "Testing targets:"
	@echo "  test           - Run test suite"
	@echo "  test-hardcore  - Run hardcore tests"
	@echo "  test-integration - Run integration tests"
	@echo ""
	@echo "Quality targets:"
	@echo "  lint           - Run code linting (black, ruff, isort, yamllint)"
	@echo "  lint-fix       - Auto-fix lint issues"
	@echo "  audit          - Run comprehensive audit"
	@echo "  cost-check     - Check API spend (CHF 120/month limit)"
	@echo ""
	@echo "Maintenance targets:"
	@echo "  update-sources - Update authority source configurations"
	@echo "  clean          - Clean cache and temporary files"
	@echo "  setup-dev      - Install development dependencies"

# Pipeline execution modes (V7)
quick:
	PYTHONPATH=. GMNAP_STREAMING=1 GMNAP_CHUNK=2000 GMNAP_INFLIGHT=8 \
		PIPELINE_MODE=quick python3 -m src.core.pipeline_v7

full:
	PYTHONPATH=. GMNAP_STREAMING=1 GMNAP_CHUNK=2000 GMNAP_INFLIGHT=16 \
		PIPELINE_MODE=full python3 -m src.core.pipeline_v7

extreme:
	PYTHONPATH=. GMNAP_STREAMING=1 GMNAP_CHUNK=2000 GMNAP_INFLIGHT=24 \
		PIPELINE_MODE=extreme python3 -m src.core.pipeline_v7

# Testing
test:
	PYTHONPATH=. pytest tests/ -v

test-hardcore:
	PYTHONPATH=. pytest tests/hardcore/ -v

test-integration:
	PYTHONPATH=. pytest tests/integration/ -v

# Code quality
lint:
	black src/ tests/ --check
	ruff check src/ tests/
	isort src/ tests/ --check-only --profile black

lint-fix:
	black src/ tests/
	ruff check src/ tests/ --fix
	isort src/ tests/ --profile black

# Cost guard (V7 spec: CHF 120/month limit for API spend)
cost-check:
	@echo "Checking API spend against CHF 120/month limit..."
	@if [ -f cache/api_costs.json ]; then \
		PYTHONPATH=. python3 -c " \
		import json; \
		costs = json.load(open('cache/api_costs.json')); \
		total = sum(costs.values()); \
		limit = 120.0; \
		status = 'OK' if total < limit else 'OVER LIMIT'; \
		print(f'Total API spend: CHF {total:.2f} / {limit:.2f} [{status}]'); \
		exit(0 if total < limit else 1)"; \
	else \
		echo "No API cost tracking file found. Assuming CHF 0."; \
	fi

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
	rm -rf out/yaml/*
	rm -rf work/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Download FastText language identification model (131MB)
download-model:
	@echo "Downloading FastText language identification model (131MB)..."
	@mkdir -p config
	@wget -q --show-progress https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O config/lid.176.bin
	@echo "Model downloaded to config/lid.176.bin"

# Development setup
setup-dev:
	pip install -r requirements.txt
	pip install black ruff isort codespell yamllint pre-commit
	pre-commit install

# Stats and reporting
stats:
	PYTHONPATH=. python3 scripts/generate_stats.py

report:
	PYTHONPATH=. python3 scripts/generate_test_report.py
