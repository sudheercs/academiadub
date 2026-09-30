.PHONY: dev stop build migrate createsuperuser test-backend lint-backend lint-frontend shell psql logs

# ── Local dev ──────────────────────────────────────────────────────────────
dev:           ## Start all services (builds if needed)
	docker compose -f infra/docker-compose.yml up --build

stop:          ## Stop all running services
	docker compose -f infra/docker-compose.yml down

build:         ## Rebuild images without cache
	docker compose -f infra/docker-compose.yml build --no-cache

logs:          ## Follow logs for all services
	docker compose -f infra/docker-compose.yml logs -f

# ── Database ───────────────────────────────────────────────────────────────
migrate:       ## Run Django migrations
	docker compose -f infra/docker-compose.yml exec api python manage.py migrate

makemigrations: ## Create new migration files
	docker compose -f infra/docker-compose.yml exec api python manage.py makemigrations

createsuperuser: ## Create a Django superuser
	docker compose -f infra/docker-compose.yml exec api python manage.py createsuperuser

psql:          ## Open psql in the db container
	docker compose -f infra/docker-compose.yml exec db psql -U academiadub

# ── Testing ────────────────────────────────────────────────────────────────
test-backend:  ## Run backend test suite
	docker compose -f infra/docker-compose.yml exec api python manage.py test --verbosity=2

test-coverage: ## Run tests with coverage report
	docker compose -f infra/docker-compose.yml exec api sh -c \
		"coverage run manage.py test && coverage report && coverage html"

# ── Linting ────────────────────────────────────────────────────────────────
lint-backend:  ## Lint backend (ruff + black + isort)
	docker compose -f infra/docker-compose.yml exec api sh -c \
		"ruff check . && black --check . && isort --check-only ."

lint-frontend: ## Lint frontend (ESLint + type-check)
	docker compose -f infra/docker-compose.yml exec web sh -c \
		"npm run lint && npm run type-check"

lint: lint-backend lint-frontend ## Lint everything

# ── Shell access ───────────────────────────────────────────────────────────
shell:         ## Django shell (plus)
	docker compose -f infra/docker-compose.yml exec api python manage.py shell

shell-web:     ## Shell in the web container
	docker compose -f infra/docker-compose.yml exec web sh

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
