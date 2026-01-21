# OEUF DNS - Professional Makefile

.PHONY: help install venv test run clean

PYTHON   := python3
DOMAIN   ?= example.com
ARGS     ?= # Extra flags (e.g. --graph, --verbose, --no-blacklist)

CYAN  := \033[36m
GREEN := \033[32m
RESET := \033[0m

.DEFAULT_GOAL := help

help:
	@echo "🥚 $(GREEN)OEUF DNS$(RESET) - DNS Mapping Tool"
	@echo ""
	@echo "Usage: make run DOMAIN=target.com [ARGS='--verbose --graph']"
	@echo ""
	@echo "  $(CYAN)install$(RESET)         Install the project (editable mode)"
	@echo "  $(CYAN)venv$(RESET)            Create virtual environment"
	@echo "  $(CYAN)test$(RESET)            Run tests"
	@echo "  $(CYAN)run$(RESET)             Run the scanner"
	@echo "  $(CYAN)clean$(RESET)           Remove temporary files"
	@echo ""
	@echo "Parameters (via ARGS='...'):"
	@echo "  --depth, -d N       Recursion depth (default: 2)"
	@echo "  --parallel, -p N    Number of workers (default: 5)"
	@echo "  --graph, -g         Generate JPG graph image (radial)"
	@echo "  --markdown, -md     Generate Markdown report"
	@echo "  --exclude, -e       Exclude patterns (e.g. -e google facebook)"
	@echo "  --no-blacklist      Disable default blacklist"
	@echo "  --verbose, -v       Enable verbose logging"

venv:
	$(PYTHON) -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)Environment created. Run 'source .venv/bin/activate'$(RESET)"

install:
	$(PYTHON) -m pip install -e .

run:
	$(PYTHON) -m src $(DOMAIN) $(ARGS)

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	find . -type f -name "*.jpg" -delete
	find . -type f -name "*.dot" -delete
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	@echo "$(GREEN)Cleaned up successfully. ✨$(RESET)"