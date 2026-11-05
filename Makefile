.DEFAULT_GOAL := help
.PHONY: help

help: ## List the project commands
	@grep -hE '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

.PHONY: setup test test-backend test-responder test-frontend lint

setup: ## Install backend and frontend dependencies for local development
	python3 -m venv .venv
	.venv/bin/pip install --quiet -e 'backend[dev]' -e 'responder[dev]'
	cd frontend && npm ci

test: test-backend test-responder test-frontend ## Run unit, integration, agent and frontend tests

test-backend: ## Run backend unit and integration tests
	cd backend && ../.venv/bin/pytest -q

test-responder: ## Run on-call agent tests
	cd responder && ../.venv/bin/pytest -q

test-frontend: ## Run frontend tests
	cd frontend && npm test

lint: ## Lint the Python code
	.venv/bin/ruff check backend responder scripts

.PHONY: up down

up: ## Start the whole system in Docker
	docker compose up --build

down: ## Stop the system (add -v by hand to erase data)
	docker compose down
