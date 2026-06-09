# Paper-List Makefile — common commands for fork developers
#
# Usage:
#   make help          Show all available targets
#   make dry-run       Preview what would be fetched
#   make fetch         Fetch papers for today
#   make fetch-week    Fetch papers for the past week
#   make validate      Validate config.yaml
#   make audit         Show filter efficiency report
#   make setup         Run the fork setup wizard
#   make health-check  One-stop pre-flight diagnostic
#   make doctor        Health check with auto-fix
#   make init-fork     Non-interactive fork initialization
#   make serve         Serve GitHub Pages locally
#   make regenerate    Regenerate markdown from existing JSON data

.PHONY: help dry-run fetch fetch-week validate audit setup health-check doctor init-fork serve regenerate clean

PYTHON ?= python3
CONFIG ?= config.yaml

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dry-run: ## Preview what would be fetched (no file writes)
	$(PYTHON) get_paper.py --dry-run --start_date $$(date -v-7d +%Y-%m-%d) --end_date $$(date +%Y-%m-%d)

fetch: ## Fetch papers for today
	$(PYTHON) get_paper.py --start_date $$(date +%Y-%m-%d) --end_date $$(date +%Y-%m-%d)

fetch-week: ## Fetch papers for the past week
	$(PYTHON) get_paper.py --start_date $$(date -v-7d +%Y-%m-%d) --end_date $$(date +%Y-%m-%d)

fetch-topic: ## Fetch a single topic: make fetch-topic TOPIC="Object Detection"
	$(PYTHON) get_paper.py --topic "$(TOPIC)" --start_date $$(date -v-7d +%Y-%m-%d) --end_date $$(date +%Y-%m-%d)

validate: ## Validate config.yaml
	$(PYTHON) scripts/validate_config.py --config $(CONFIG)

audit: ## Show filter efficiency report
	$(PYTHON) scripts/filter_audit.py --config $(CONFIG)

audit-zombie: ## Show only zero-hit (zombie) filters
	$(PYTHON) scripts/filter_audit.py --config $(CONFIG) --zombie

setup: ## Run the fork setup wizard
	$(PYTHON) scripts/setup_fork.py

health-check: ## One-stop pre-flight diagnostic (API, config, data, env)
	$(PYTHON) scripts/health_check.py --config $(CONFIG)

doctor: ## Health check with auto-fix where possible
	$(PYTHON) scripts/health_check.py --config $(CONFIG) --fix --verbose

init-fork: ## Non-interactive fork initialization (auto-detect from git)
	$(PYTHON) scripts/setup_fork.py --non-interactive

serve: ## Serve GitHub Pages locally
	cd docs && bundle exec jekyll serve --livereload || \
		echo "Install Jekyll: gem install bundler && cd docs && bundle install"

regenerate: ## Regenerate markdown from existing JSON data
	$(PYTHON) regenerate_readme.py

clean: ## Remove generated output files
	rm -f output.json output_web.json output.md output_web.md
