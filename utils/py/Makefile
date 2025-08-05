# Komodo DeFi Framework Documentation Tools - Development Makefile
# ================================================================

.PHONY: help clean install install-dev test lint format type-check pre-commit setup-dev
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
VENV := .venv
VENV_BIN := $(VENV)/bin
PACKAGE := lib

help: ## Show this help message
	@echo "Komodo DeFi Framework Documentation Tools - Development Commands"
	@echo "================================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment Setup
setup-dev: ## Set up development environment with virtual environment
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip setuptools wheel
	$(VENV_BIN)/pip install -r requirements-dev.txt
	$(VENV_BIN)/pip install -e .
	$(VENV_BIN)/pre-commit install
	@echo "✅ Development environment set up successfully!"
	@echo "   Activate with: source $(VENV)/bin/activate"

install: ## Install package in production mode
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

install-dev: ## Install package in development mode with all dependencies
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e ."[dev,performance,docs]"

# Code Quality
format: ## Format code with black and isort
	@echo "🎨 Formatting code..."
	black $(PACKAGE) kdf_tools.py
	isort $(PACKAGE) kdf_tools.py
	@echo "✅ Code formatted successfully!"

lint: ## Run linting with flake8
	@echo "🔍 Running linter..."
	flake8 $(PACKAGE) kdf_tools.py
	@echo "✅ Linting completed!"

type-check: ## Run type checking with mypy
	@echo "🔎 Running type checker..."
	mypy $(PACKAGE) kdf_tools.py
	@echo "✅ Type checking completed!"

# Testing
test: ## Run tests with pytest
	@echo "🧪 Running tests..."
	pytest -v
	@echo "✅ Tests completed!"

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	pytest --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html
	@echo "✅ Tests with coverage completed!"
	@echo "📊 Coverage report available in htmlcov/index.html"

test-fast: ## Run tests excluding slow tests
	@echo "🧪 Running fast tests..."
	pytest -v -m "not slow"
	@echo "✅ Fast tests completed!"

# Development Workflow
check: lint type-check test ## Run all checks (lint, type-check, test)
	@echo "✅ All checks completed successfully!"

pre-commit: ## Run pre-commit hooks
	@echo "🔧 Running pre-commit hooks..."
	pre-commit run --all-files
	@echo "✅ Pre-commit hooks completed!"

# Cleaning
clean: ## Clean up build artifacts and cache files
	@echo "🧹 Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup completed!"

clean-venv: ## Remove virtual environment
	@echo "🧹 Removing virtual environment..."
	rm -rf $(VENV)
	@echo "✅ Virtual environment removed!"

# Package Management
build: ## Build distribution packages
	@echo "📦 Building packages..."
	$(PYTHON) -m build
	@echo "✅ Packages built successfully!"

# Documentation
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	sphinx-build -b html docs docs/_build/html
	@echo "✅ Documentation generated!"

docs-live: ## Start live documentation server
	@echo "📚 Starting live documentation server..."
	sphinx-autobuild docs docs/_build/html

# KDF Tools Commands
tools-help: ## Show KDF tools help
	@echo "🛠️  KDF Tools Commands:"
	$(PYTHON) kdf_tools.py --help

tools-openapi: ## Convert MDX to OpenAPI (v2)
	@echo "🔄 Converting MDX to OpenAPI..."
	$(PYTHON) kdf_tools.py openapi --version v2

tools-openapi-clean: ## Convert MDX to OpenAPI with cleanup
	@echo "🔄 Converting MDX to OpenAPI (with cleanup)..."
	$(PYTHON) kdf_tools.py openapi --version v2 --clean-before

tools-scan: ## Scan repository for methods
	@echo "🔍 Scanning repository..."
	$(PYTHON) kdf_tools.py scan --branch dev

tools-map: ## Generate method mapping
	@echo "🗺️  Generating method mapping..."
	$(PYTHON) kdf_tools.py map

tools-postman: ## Generate Postman collections
	@echo "📮 Generating Postman collections..."
	$(PYTHON) kdf_tools.py postman --versions v2

tools-postman-clean: ## Generate Postman collections with cleanup
	@echo "📮 Generating Postman collections (with cleanup)..."
	$(PYTHON) kdf_tools.py postman --versions v2 --clean-before

tools-cleanup: ## Clean up old temporary files
	@echo "🧹 Cleaning up old temporary files..."
	$(PYTHON) kdf_tools.py cleanup

tools-cleanup-generated: ## Clean up generated files before regeneration
	@echo "🧹 Cleaning up generated files..."
	$(PYTHON) kdf_tools.py cleanup-generated

tools-cleanup-generated-dry: ## Dry run of generated files cleanup
	@echo "🧹 Dry run: Cleaning up generated files..."
	$(PYTHON) kdf_tools.py cleanup-generated --dry-run

tools-cleanup-stale: ## Clean up stale generated files
	@echo "🧹 Cleaning up stale files..."
	$(PYTHON) kdf_tools.py cleanup-stale

tools-cleanup-stale-dry: ## Dry run of stale files cleanup
	@echo "🧹 Dry run: Cleaning up stale files..."
	$(PYTHON) kdf_tools.py cleanup-stale --dry-run

# Complete regeneration workflow (recommended)
tools-regenerate-all: ## Clean and regenerate all files (RECOMMENDED)
	@echo "🔄 Complete regeneration of all files..."
	$(PYTHON) kdf_tools.py regenerate-all

tools-regenerate-all-dry: ## Dry run of complete regeneration
	@echo "🔄 Dry run: Complete regeneration..."
	$(PYTHON) kdf_tools.py regenerate-all --dry-run

tools-regenerate-all-force: ## Force complete regeneration (ignore errors)
	@echo "🔄 Force complete regeneration..."
	$(PYTHON) kdf_tools.py regenerate-all --force

# Specific regeneration workflows
tools-regenerate-openapi: ## Clean and regenerate OpenAPI files only
	@echo "🔄 Regenerating OpenAPI files..."
	$(PYTHON) kdf_tools.py regenerate-all --skip-postman --skip-mapping

tools-regenerate-postman: ## Clean and regenerate Postman collections only
	@echo "📮 Regenerating Postman collections..."
	$(PYTHON) kdf_tools.py regenerate-all --skip-openapi --skip-mapping

# Environment Info
info: ## Show environment information
	@echo "Environment Information:"
	@echo "======================="
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version)"
	@echo "Virtual Environment: $(if $(wildcard $(VENV)),✅ Active,❌ Not found)"
	@echo "Package Installation: $(if $(shell $(PYTHON) -c 'import lib' 2>/dev/null && echo 'yes'),✅ Installed,❌ Not installed)"

# Quick commands for common workflows
dev: setup-dev ## Alias for setup-dev
quick-check: format lint test-fast ## Quick check (format, lint, fast tests)
full-check: format lint type-check test ## Full check (format, lint, type-check, all tests)

# Example usage information
examples: ## Show example usage commands
	@echo "Example Development Workflow:"
	@echo "============================"
	@echo "1. Set up development environment:"
	@echo "   make setup-dev"
	@echo ""
	@echo "2. Activate virtual environment:"
	@echo "   source .venv/bin/activate"
	@echo ""
	@echo "3. Run quick checks during development:"
	@echo "   make quick-check"
	@echo ""
	@echo "4. Run full checks before committing:"
	@echo "   make full-check"
	@echo ""
	@echo "5. Use KDF tools:"
	@echo "   make tools-openapi"
	@echo "   make tools-postman"

# Quality Analysis
.PHONY: review-draft-quality
review-draft-quality: setup-env  ## Review draft quality by comparing generated docs with live versions
	@echo "🔍 Reviewing draft quality..."
	$(PYTHON) kdf_tools.py review-draft-quality

.PHONY: review-draft-quality-verbose  
review-draft-quality-verbose: setup-env  ## Review draft quality with verbose output
	@echo "🔍 Reviewing draft quality (verbose)..."
	$(PYTHON) kdf_tools.py review-draft-quality --verbose

.PHONY: review-draft-quality-specific
review-draft-quality-specific: setup-env  ## Review specific document pair (requires GENERATED= and LIVE= vars)
	@echo "🔍 Reviewing specific document pair..."
	@if [ -z "$(GENERATED)" ] || [ -z "$(LIVE)" ]; then \
		echo "❌ Error: Both GENERATED and LIVE variables must be set"; \
		echo "   Usage: make review-draft-quality-specific GENERATED=path/to/generated.mdx LIVE=path/to/live.mdx"; \
		exit 1; \
	fi
	$(PYTHON) kdf_tools.py review-draft-quality --generated "$(GENERATED)" --live "$(LIVE)" --verbose

.PHONY: dry-run-quality-review
dry-run-quality-review: setup-env  ## Show what would be analyzed in draft quality review
	@echo "🔍 Showing what would be analyzed in draft quality review..."
	$(PYTHON) kdf_tools.py review-draft-quality --dry-run

# Documentation Generation
.PHONY: scan-existing-docs
scan-existing-docs: setup-env  ## Scan existing KDF documentation to extract method patterns
	@echo "🔍 Scanning existing documentation..."
	$(PYTHON) kdf_tools.py scan-existing-docs

.PHONY: scan-existing-docs-async
scan-existing-docs-async: setup-env  ## Scan existing docs with async processing (faster)
	@echo "🔍 Scanning existing documentation (async)..."
	$(PYTHON) kdf_tools.py scan-existing-docs --async-scan --generate-report

.PHONY: generate-docs
generate-docs: setup-env  ## Generate documentation for missing KDF methods
	@echo "📄 Generating documentation for missing methods..."
	$(PYTHON) kdf_tools.py generate-docs

.PHONY: generate-docs-interactive
generate-docs-interactive: setup-env  ## Generate docs with interactive method selection
	@echo "📄 Generating documentation (interactive)..."
	$(PYTHON) kdf_tools.py generate-docs --interactive --generate-summary

.PHONY: generate-docs-method
generate-docs-method: setup-env  ## Generate docs for specific method (requires METHOD= var)
	@echo "📄 Generating documentation for specific method..."
	@if [ -z "$(METHOD)" ]; then \
		echo "❌ Error: METHOD variable must be set"; \
		echo "   Usage: make generate-docs-method METHOD=task::enable_bch::init"; \
		exit 1; \
	fi
	$(PYTHON) kdf_tools.py generate-docs --method "$(METHOD)" --version "$(VERSION)" 