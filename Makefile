UV := uv
DOCKER := docker compose

.PHONY: setup dev lint test fmt docker-up docker-down clean frontend-dev frontend-check

## Setup: create venv and install deps
setup:
	cd backend && $(UV) venv --python python3.12 && $(UV) sync --extra dev
	cd frontend && npm install

## Run backend dev server
dev:
	cd backend && $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Run frontend dev server
frontend-dev:
	cd frontend && npm run dev

## Run backend unit tests
test:
	cd backend && $(UV) run pytest -m unit -v --cov --cov-report=term-missing

## Run all backend tests
test-all:
	cd backend && $(UV) run pytest --cov --cov-report=term-missing

## Lint backend
lint:
	cd backend && $(UV) run ruff check .

## Lint and fix
lint-fix:
	cd backend && $(UV) run ruff check --fix .

## Format backend
fmt:
	cd backend && $(UV) run ruff format .

## Type check backend
type-check:
	cd backend && $(UV) run mypy app/

## Check frontend (svelte-check + TypeScript)
frontend-check:
	cd frontend && npx svelte-kit sync && npx svelte-check --tsconfig ./tsconfig.json

## Docker Compose up (PostgreSQL, Redis, Jaeger)
docker-up:
	$(DOCKER) up -d
	@echo "Services: PostgreSQL:5432 Redis:6379 Jaeger:16686"

## Docker Compose down
docker-down:
	$(DOCKER) down

## Docker Compose logs
docker-logs:
	$(DOCKER) logs -f

## Clean build artifacts
clean:
	rm -rf backend/.venv backend/.pytest_cache backend/__pycache__
	rm -rf frontend/node_modules frontend/.svelte-kit frontend/build
