# GMNAP Makefile - Specs v6 Compliance

.PHONY: help setup install-fasttext install-hooks quick full extreme test lint update-sources clean audit audit-repo browser-test eval-authority eval-orcid-live harvest-mgp api-docs bench-real lock refresh-data refresh-data-wikidata refresh-data-mgp refresh-data-merge

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
	@echo "  audit-repo   - Run repo-invariant audit (18 checks; CI gate)"
	@echo "  update-sources - Update authority source configurations"
	@echo "  refresh-data - Re-harvest Wikidata + MGP and rebuild data/genealogy_enrichment.json"
	@echo "                 (≈30 min Wikidata + optional ~780h MGP; see Makefile header)"
	@echo "  refresh-data-wikidata, refresh-data-mgp, refresh-data-merge — sub-targets"
	@echo "  clean        - Clean cache and temporary files"

# One-time setup for a fresh clone. Uses `python3 -m pip` so it works
# on systems where `pip` itself isn't on PATH (common on macOS with
# the system Python). `-e .` installs the project itself so the
# `gmnap` console script lands on PATH alongside the deps — that
# unblocks every CLI example in README/CLAUDE.md/DEMO.md.
#
# Pre-flight: a virtualenv is strongly recommended. Apple's system
# Python (macOS default) ships pip 21.2 with read-only site-packages,
# which fails both PEP-660 editable installs AND `--user` writes. We
# detect that case and bail with a clear venv recipe rather than
# silently dropping you into a broken state.
setup:
	@python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" 2>/dev/null || { \
		echo ""; \
		echo "❌ You are not inside a virtual environment."; \
		echo "   The system Python's site-packages is typically read-only"; \
		echo "   (macOS especially), which breaks both pip and the"; \
		echo "   editable install of gmnap. Set up a venv first:"; \
		echo ""; \
		echo "     python3 -m venv .venv"; \
		echo "     source .venv/bin/activate"; \
		echo "     make setup"; \
		echo ""; \
		exit 1; \
	}
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt
	# --no-deps: requirements.txt above is the source-of-truth for
	# versions. pyproject.toml's `>=X.Y` deps would otherwise let pip
	# upgrade past the pinned line (round-34 hit this: fastapi 0.115
	# → 0.137 silently, which changed openapi.json output and tripped
	# the I1 idempotency audit). `-e .` here is just installing the
	# `gmnap` console script entry point, nothing else needed.
	python3 -m pip install -e . --no-deps
	@bash scripts/install_fasttext.sh || { \
		echo ""; \
		echo "❌ fasttext install FAILED."; \
		echo "   Region detection will fall back to RULES-ONLY mode."; \
		echo "   This reduces accuracy materially on the name-origin"; \
		echo "   branch; the 0.95 confidence scores in 'gmnap query'"; \
		echo "   are still meaningful but coverage drops by ~28 % at"; \
		echo "   the abstention rate."; \
		echo ""; \
		echo "   Retry with: make install-fasttext"; \
		echo "   Or install build tools first:"; \
		echo "     macOS: xcode-select --install"; \
		echo "     Linux: apt-get install build-essential git"; \
		echo ""; \
	}
	@bash scripts/install_hooks.sh || \
		echo "⚠️  pre-commit hook install skipped (not a git checkout?)"
	@echo ""
	@command -v gmnap >/dev/null 2>&1 && \
		echo "✅ Setup complete. Try:  gmnap query \"Euler, Leonhard\"" || \
		echo "⚠️  Setup complete but 'gmnap' is not on PATH. Try: python3 -m src.cli.gmnap query \"Euler, Leonhard\""

install-fasttext:
	@bash scripts/install_fasttext.sh

install-hooks:
	@bash scripts/install_hooks.sh

# API reference docs (tools/gen_api_reference.py). Pulls the
# OpenAPI schema from the FastAPI app and renders it to
# docs/api_reference.md (markdown for humans) + docs/openapi.json
# (machine-readable for tooling).
api-docs:
	PYTHONPATH=. python3 tools/gen_api_reference.py

# Real-name benchmark (Tier 2.3 follow-up). Sample from the curated
# genealogy_enrichment.json instead of synthetic entries — exercises
# the rule fast-path and produces realistic-workload throughput.
bench-real:
	PYTHONPATH=. python3 tools/run_benchmark.py --real-names --sizes 1000,10000

# Live-authority quality harness (tools/eval_authority.py).
# Hits OpenAlex / Crossref / ORCID_ETD against 30 hand-curated
# mathematicians and reports hit rate, BirthYear ±1 accuracy, and
# institution-keyword match. NOT run in CI (network-dependent +
# rate-limited). Refuses to run with OFFLINE=1 unless you pass
# `--allow-offline` (useful for testing the harness shape against a
# warm cache).
eval-authority:
	OFFLINE=0 PYTHONPATH=. python3 tools/eval_authority.py

# Round-21: live ORCID-ETD regression test (round-14 chain).
# Hits real ORCID; gated by `live` marker + OFFLINE=0. Catches the
# class-of-bug round 14 fixed (name→ORCID resolve, dataclass field
# names, FetchResult wrapping) — mocks won't see real-API drift.
eval-orcid-live:
	OFFLINE=0 PYTHONPATH=. pytest tests/integration/test_orcid_etd_live.py \
		-v -m live --timeout=60

# Round-23: bulk MGP harvest (mathgenealogy.org). Crawl-delay: 10
# per their robots.txt → ~780h for the full ~280k corpus. Use
# --start / --end for chunks, --resume to pick up after Ctrl-C.
# Single-threaded by design (politeness > speed).
harvest-mgp:
	@echo "MGP harvest: respects 10s crawl delay; full corpus ~780h."
	@echo "Run a chunk:    make harvest-mgp ARGS='--start 1 --end 1000'"
	@echo "Resume:         make harvest-mgp ARGS='--resume'"
	PYTHONPATH=. python3 tools/harvest_mgp.py $(ARGS)

# ── Data refresh pipeline ─────────────────────────────────────────────
#
# End-to-end refresh of data/genealogy_enrichment.json — the bundled
# 39 500-entry seed that every gmnap query / lineage / process call
# falls back to when OFFLINE=1 (the default). Three independent
# upstream sources:
#
#   1. Wikidata SPARQL (P184 = doctoral advisor) — decade-partitioned,
#      52 query chunks 1500-2020, ~30 min total wall-clock against the
#      public endpoint. Polite throughout (one HTTP request at a time
#      with the User-Agent / from address required by WMF service
#      ToS); see scripts/data/fetch_wikidata_genealogy.py header.
#
#   2. MGP (Mathematics Genealogy Project) — respects the 10 s
#      Crawl-delay in their robots.txt, so a full corpus walk is
#      ~780 h (a month of continuous crawling). Almost never the
#      right move; use the chunk form below or skip outright.
#
#   3. OpenAlex affiliations — pulled lazily by tools/build_genealogy_
#      enrichment.py itself, since OpenAlex's polite-pool endpoints
#      are fast enough not to warrant a separate harvest stage.
#
# Three sub-targets so the operator can refresh ONE source without
# re-running the whole chain:
#
#   make refresh-data-wikidata    # ~30 min
#   make refresh-data-mgp ARGS='--start 1 --end 1000'   # 10s/entry
#   make refresh-data-merge       # ~5 min, no network
#
# The umbrella target runs all three in dependency order (Wikidata
# then MGP then merge); use it for a full quarterly refresh, but
# expect ~31 min minimum if MGP is skipped.
#
# Output: data/genealogy_enrichment.json (replaces the LFS-tracked
# committed copy in-place). After refresh, run `make audit-repo` to
# confirm D4's 36k–43k entry-count gate still passes and `git diff
# --stat data/genealogy_enrichment.json` to see the delta.
refresh-data: refresh-data-wikidata refresh-data-merge
	@echo ""
	@echo "✅ Refresh complete. Sanity check:"
	@echo "   make audit-repo    # verify D4 entry-count gate"
	@echo "   git diff --stat data/genealogy_enrichment.json"
	@echo "   PYTHONPATH=. python3 -m gmnap query \"Hilbert, David\""

refresh-data-wikidata:
	@echo "──────────────────────────────────────────────────────────────"
	@echo "Wikidata SPARQL harvest (P184 advisor edges, 52 decade buckets)"
	@echo "Expect ~30 min wall-clock. Polite — single sequential request."
	@echo "──────────────────────────────────────────────────────────────"
	PYTHONPATH=. python3 scripts/data/fetch_wikidata_genealogy.py

refresh-data-mgp:
	@echo "──────────────────────────────────────────────────────────────"
	@echo "MGP harvest (respects 10 s Crawl-delay)."
	@echo "Pass a chunk explicitly:  make refresh-data-mgp ARGS='--start 1 --end 1000'"
	@echo "Or resume:                make refresh-data-mgp ARGS='--resume'"
	@echo "──────────────────────────────────────────────────────────────"
	PYTHONPATH=. python3 tools/harvest_mgp.py $(ARGS)

refresh-data-merge:
	@echo "──────────────────────────────────────────────────────────────"
	@echo "Merge harvest outputs → data/genealogy_enrichment.json"
	@echo "──────────────────────────────────────────────────────────────"
	PYTHONPATH=. python3 tools/build_genealogy_enrichment.py

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

# Analysis — the canonical repo-invariant audit (analysis/comprehensive_audit.py
# was removed in R41; tools/audit_repo.py supersedes it).
audit:
	PYTHONPATH=. python3 tools/audit_repo.py

audit-quick:
	PYTHONPATH=. python3 tools/audit_repo.py --fast

# Comprehensive repo-invariant audit (tools/audit_repo.py). 18 checks
# across 10 categories: file-tree integrity, parse, JSON/YAML, doc-vs-
# data numerical claims, version coherence, Make-target resolution,
# CI test references, test-module shadowing, generator idempotency,
# doc cross-references. Wired into CI as a gating job — any failure
# fails the build. Run locally before pushing if you've touched docs,
# numbers, or test layout.
audit-repo:
	PYTHONPATH=. python3 tools/audit_repo.py

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
