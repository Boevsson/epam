.DEFAULT_GOAL := help
.PHONY: help setup check test test-slow eval ask ingest frontend-check up down docker-check

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Install backend (uv) and frontend (npm) dependencies
	cd backend && uv sync
	cd frontend && npm ci

check: ## Backend gate: lint, format, strict types, architecture rules, fast tests
	cd backend && uv run sh scripts/check.sh

test: ## Fast backend tests only; filter with ARGS="-k fusion"
	cd backend && uv run pytest $(ARGS)

test-slow: ## Tests that load the real embedding model
	cd backend && uv run pytest -m slow

ingest: ## Parse the PDFs and publish an index snapshot (local)
	cd backend && uv run filings-qa ingest

eval: ## Retrieval evaluation on the FinanceBench golden set (local)
	cd backend && uv run filings-qa eval --output ../docs/evaluation-results.md

ask: ## Ask from the terminal: make ask Q="What drove AMD's revenue change in FY2022?"
	cd backend && uv run filings-qa ask "$(Q)"

frontend-check: ## Frontend tests, type-check and production build
	cd frontend && npm test && npm run build

up: ## Build and start ingest -> api -> web (http://localhost:$${WEB_PORT:-8080})
	docker compose up --build -d

down: ## Stop the stack
	docker compose down

docker-check: ## Backend gate inside Docker
	docker compose run --rm --build tests
