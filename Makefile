.DEFAULT_GOAL := help

SHELL := /bin/bash
DOCKER_COMPOSE ?= docker compose

# Entorno: dev (default) o prod
ENV ?= dev
DC := $(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.$(ENV).yml

.PHONY: help env up up-build down stop start restart ps logs logs-api logs-worker logs-frontend logs-db build pull reset clean prune ensure-api ensure-frontend migrate makemigrations seed bootstrap test test-backend lint-frontend build-frontend pre-push shell-api shell-worker shell-frontend db-shell

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target> [ENV=dev|prod]\n\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created from .env.example"; else echo ".env already exists"; fi

up: env ## Start full stack in background
	$(DC) up -d

up-build: env ## Start stack rebuilding images
	$(DC) up -d --build

down: ## Stop and remove containers
	$(DC) down

stop: ## Stop containers without removing them
	$(DC) stop

start: ## Start existing containers
	$(DC) start

restart: ## Restart all services
	$(DC) restart

ps: ## Show stack status
	$(DC) ps

logs: ## Follow all service logs
	$(DC) logs -f --tail=150

logs-api: ## Follow API logs
	$(DC) logs -f --tail=150 api

logs-worker: ## Follow Celery worker logs
	$(DC) logs -f --tail=150 worker

logs-frontend: ## Follow frontend logs
	$(DC) logs -f --tail=150 frontend

logs-db: ## Follow Postgres logs
	$(DC) logs -f --tail=150 postgres

build: ## Build all images
	$(DC) build

pull: ## Pull latest base images
	$(DC) pull

ensure-api:
	$(DC) up -d postgres redis api

ensure-frontend:
	$(DC) up -d frontend

migrate: ensure-api ## Run database migrations (upgrade)
	@has_alembic="$$( $(DC) exec -T postgres psql -U facturador -d facturador -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version';" )"; \
	has_tenant="$$( $(DC) exec -T postgres psql -U facturador -d facturador -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='tenant';" )"; \
	if [ "$${has_alembic}" = "0" ] && [ "$${has_tenant}" = "1" ]; then \
		echo "alembic_version no existe y hay tablas base: aplicando flask db stamp 001_initial"; \
		$(DC) exec api flask db stamp 001_initial; \
	fi
	$(DC) exec api flask db upgrade

makemigrations: ensure-api ## Create migration (usage: make makemigrations m="desc")
	$(DC) exec api flask db migrate -m "$(m)"

seed: ensure-api ## Seed initial tenant/admin data
	$(DC) exec api python seed.py

bootstrap: up migrate seed ## Start stack + migrate + seed

test: test-backend ## Run default test suite

test-backend: ensure-api ## Run backend tests in container
	$(DC) exec -T api sh -lc "python -m pip show pytest >/dev/null 2>&1 || python -m pip install pytest; cd /app; python -m pytest -q --junitxml=/tmp/pytest.xml; pytest_exit=$$?; python scripts/pytest_table_report.py /tmp/pytest.xml; exit $$pytest_exit"

lint-frontend: ensure-frontend ## Run frontend lint in container
	$(DC) exec -T frontend npm run lint

build-frontend: ensure-frontend ## Run frontend production build in container
	$(DC) exec -T frontend npm run build

pre-push: test-backend lint-frontend build-frontend ## Run checks before pushing

shell-api: ## Open shell in API container
	$(DC) exec api bash

shell-worker: ## Open shell in worker container
	$(DC) exec worker bash

shell-frontend: ## Open shell in frontend container
	$(DC) exec frontend sh

db-shell: ## Open psql shell in Postgres container
	$(DC) exec postgres psql -U facturador -d facturador

reset: ## Remove containers and volumes (DANGER)
	$(DC) down -v --remove-orphans

clean: down ## Stop stack and remove local volumes
	$(DC) down -v --remove-orphans

prune: ## Remove dangling Docker resources
	docker system prune -f
