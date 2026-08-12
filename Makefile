COMPOSE ?= docker-compose

.PHONY: up down test lint migrate sync diagnose logs

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

test:
	$(COMPOSE) run --rm api sh -c "alembic upgrade head && pytest"

lint:
	$(COMPOSE) run --rm api ruff check src tests

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

sync:
	$(COMPOSE) run --rm api python -m cataloging_api.sync.cli
diagnose:
	$(COMPOSE) run --rm api python -m cataloging_api.diagnostics.cli


logs:
	$(COMPOSE) logs -f api web
