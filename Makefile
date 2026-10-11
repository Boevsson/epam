.DEFAULT_GOAL := help
.PHONY: help setup check test docker-check

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup: ## Create the local Python 3.12 environment (uv)
	cd backend && uv sync

check: ## Lint, format, strict type-check, architecture rules and tests (local)
	cd backend && uv run sh scripts/check.sh

test: ## Tests only (local); filter with ARGS="-k fusion"
	cd backend && uv run pytest $(ARGS)

docker-check: ## The same quality gate inside Docker
	docker compose run --rm --build tests
