#!/usr/bin/make -f console

MAKEFILE          := $(realpath $(lastword $(MAKEFILE_LIST)))
MAKE              := make
MAKEFLAGS         += --no-print-directory
MAKEFLAGS         += --warn-undefined-variables

.ONESHELL:
SHELL             := /bin/bash
.SHELLFLAGS       := -o errexit -o nounset -o pipefail -u -ec

PATH              := $(PWD)/bin:$(PWD)/venv/bin:$(HOME)/go/bin:$(PATH)
PYTHONPATH        := $(PWD)/venv

APT_INSTALL       := sudo apt install -yyq --no-install-recommends --no-install-suggests

SYSTEM_PIP        := pip3
PYTHON            := $(PWD)/venv/bin/python3
PYTEST            := $(PWD)/venv/bin/pytest
COVERAGE          := $(PWD)/venv/bin/coverage
FLAKE8            := $(PWD)/venv/bin/flake8
BLACK             := $(PWD)/venv/bin/black
PIP3              := $(PWD)/venv/bin/pip3
YQ                := $(PWD)/venv/bin/yq -y
PIPREQS           := $(PWD)/venv/bin/pipreqs

num_cpus  = $(shell lscpu | awk '/^CPU.s/{ print $$2 }')

DEBUG ?= 0
ifeq ($(DEBUG), 1)
	PYTESTFLAGS  =-rA --log-cli-level=DEBUG
	VERBOSITY=5
else
	PYTESTFLAGS =--log-cli-level=CRITICAL
	VERBOSITY=0
endif

.PHONY: help init test requirements venv lint format typecheck quality clean install install-dev uninstall reinstall upgrade check-path

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  sort | awk 'BEGIN {FS = ":.*?## "}; \
	  {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# Legacy venv-based targets retained for backwards compatibility
init-legacy: venv dev requirements ## Initialize legacy virtualenv-based environment
	source venv/bin/activate
	poetry env info || true

venv:
	pip3 install -U pip --break-system-packages
	python3 -mvenv venv/

requirements:
	source venv/bin/activate
	poetry install

dev:
	source venv/bin/activate
	$(PIP3) install poetry setuptools wheel pip
	poetry check || true

# New uv-based targets
uv-init: ## Initialize environment using uv
	uv sync --all-extras
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push
	@echo "✅ Development environment ready!"
	@echo "   pre-commit: ruff + mypy (every commit)"
	@echo "   pre-push:   make test-ci (every push)"

# Default init now points to uv-init
init: uv-init ## Initialize development environment using uv
	@echo "Use 'make init-legacy' to setup the legacy venv-based environment if needed."

test: test-all ## (alias) Run all tests

# --- Test Ladder (Accordion Pattern) ---
# Apertures:
#   Inner Loop (3-5s):  make test-fast  (Rungs 0.0 - 0.5)
#   Outer Loop (2-3m):  make test-ci    (Rungs 0.0 - 3.0)
#   UAT Loop (3-5m):    make test-uat   (Final validation)

test-structure: ## Rung 0.0: Syntax check (blocking)
	uv run ruff check src/ tests/ --select=E9,F63,F7,F82

test-imports: ## Rung 0.25: Import linter (blocking)
	PYTHONPATH=src uv run lint-imports

test-typecheck: ## Rung 0.35: Type check (blocking)
	uv run mypy src/

test-lint: ## Rung 0.5: Full lint (blocking)
	uv run ruff check src/ tests/

audit-patches: ## Rung 0.4: Fail on patches against deprecated stub modules (blocking)
	@# tests must not patch terrapyne.cli.utils.* — that module is a deprecated
	@# stub. The real symbols live in cli/context_helpers.py and the per-command
	@# files; patching the stub silently no-ops. See PLAN.md EPIC-001.
	@if grep -RnE 'patch\(\s*"terrapyne\.cli\.utils\.[A-Za-z_]+"' tests/ src/; then \
		echo ""; \
		echo "❌ Found patch() calls against terrapyne.cli.utils.*"; \
		echo "   That module is a deprecated stub. Patch the real import site instead."; \
		echo "   See docs/how-to/python-and-testing.md and PLAN.md EPIC-001."; \
		exit 1; \
	fi
	@# Tests should use error_console for stderr expectations rather than asserting
	@# on private console attributes; flag drift early. (Informational, non-blocking.)
	@echo "✅ audit-patches: no patches against deprecated stubs"

audit-ai-markers: ## Rung 0.4: Fail if AI-attribution markers leak into commits or tree (blocking)
	@# The PR template, agent personas, and commits-and-review.md all forbid AI
	@# markers in commits and code. This audits src/, tests/, and the recent
	@# commit log on this branch for the most common offenders.
	@#
	@# docs/ is intentionally excluded: the standards documents describe these
	@# patterns by name (so contributors know what's forbidden) which would
	@# otherwise self-trip the audit.
	@FAIL=0; \
	if grep -RInE 'Co-Authored-By:[[:space:]]*(Claude|GPT|Gemini|Copilot|Cursor)' src/ tests/ 2>/dev/null; then \
		echo "❌ AI co-author markers found in working tree"; \
		FAIL=1; \
	fi; \
	if grep -RInE '🤖[[:space:]]*Generated with' src/ tests/ 2>/dev/null; then \
		echo "❌ '🤖 Generated with' marker found in working tree"; \
		FAIL=1; \
	fi; \
	if [ -d .git ] && git log -n 50 --format='%B' 2>/dev/null | \
		grep -InE 'Co-Authored-By:[[:space:]]*(Claude|GPT|Gemini|Copilot|Cursor)|🤖[[:space:]]*Generated with' >/dev/null; then \
		echo "❌ AI marker found in recent commit messages on this branch"; \
		FAIL=1; \
	fi; \
	if [ "$$FAIL" = "1" ]; then \
		echo ""; \
		echo "   See docs/how-to/commits-and-review.md and the GenAI section of"; \
		echo "   .github/PULL_REQUEST_TEMPLATE.md."; \
		exit 1; \
	fi
	@echo "✅ audit-ai-markers: no AI attribution markers found"

test-last-failed: ## Rung 1.0: Regressions (fast)
	uv run python -m pytest tests/ --lf -x -q --no-header --no-cov || true

test-all: ## Rung 2.0: Logic / Full suite (blocking)
	uv run python -m pytest tests/ -v --no-cov

test-coverage: ## Rung 3.0: Coverage report (informational)
	uv run python -m pytest tests/ --cov=src --cov-report=term --no-header -q --no-cov-on-fail || true

test-fast: test-structure test-imports test-typecheck test-lint audit-patches audit-ai-markers ## Inner Loop: Rungs 0.0 - 0.5 (< 10s)

test-ci: test-fast test-last-failed test-all test-coverage ## Outer Loop: Full ladder accordion

# --- End Test Ladder ---

test-unit: ## Run unit tests only
	uv run python -m pytest tests/unit/ -v --no-cov

test-integration: ## Run integration tests (needs terraform + network)
	uv run python -m pytest tests/ -v --no-cov -m "integration"

test-uat: ## Run UAT tests (needs TFC credentials, read-only)
	uv run pytest tests/uat/ -v --no-cov -m "uat" -o "addopts="

format: ## Format code with ruff
	uv run ruff format src/ tests/

# Aliases for muscle memory
lint: test-lint ## (alias)
typecheck: test-typecheck ## (alias)
quality: test-ci ## (alias)

build: format test-fast ## Validate code
	@echo "✅ Build validation passed!"

clean: ## Clean build artifacts
	rm -rf .venv .pytest_cache .mypy_cache htmlcov .coverage dist/ build/ *.egg-info
	find src tests -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Installation targets
install: ## Install terrapyne CLI to ~/.local/bin using uv (editable mode)
	@echo "📦 Installing terrapyne to ~/.local/bin (editable)..."
	uv tool install -e .
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "📍 Installed to: ~/.local/bin/terrapyne (editable mode)"
	@echo "💡 Ensure ~/.local/bin is in your PATH:"
	@echo "   export PATH=\"\$$HOME/.local/bin:\$$PATH\""
	@echo ""
	@echo "🚀 Try: terrapyne --help"

install-dev: ## Install in editable mode for development
	@echo "📦 Installing terrapyne in editable mode..."
	uv pip install -e ".[dev]"
	@echo "✅ Development installation complete!"
	@echo "💡 Changes to source code will be immediately available"

uninstall: ## Uninstall terrapyne CLI
	@echo "🗑️  Uninstalling terrapyne..."
	uv tool uninstall terrapyne || echo "terrapyne not installed via uv tool"
	@echo "✅ Uninstallation complete!"

reinstall: uninstall install ## Reinstall terrapyne CLI

upgrade: ## Upgrade terrapyne CLI to latest local version
	@echo "⬆️  Upgrading terrapyne..."
	uv tool install --reinstall --force -e .
	@echo "✅ Upgrade complete!"

check-path: ## Check if ~/.local/bin is in PATH
	@if echo "$$PATH" | grep -q "$$HOME/.local/bin"; then \
		echo "✅ ~/.local/bin is in your PATH"; \
	else \
		echo "⚠️  ~/.local/bin is NOT in your PATH"; \
		echo ""; \
		echo "Add it to your shell profile (~/.bashrc, ~/.zshrc, etc.):"; \
		echo "  export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
		echo ""; \
		echo "Then reload your shell or run:"; \
		echo "  source ~/.bashrc  # or source ~/.zshrc"; \
	fi
