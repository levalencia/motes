# AGENTS.md — Motes agent instruction file

> This file orients any AI coding agent working in this repository.

## What this is

Motes is an open-source, model-agnostic, self-hosted personal agent platform.
Think "OpenAI Dots but you own it, choose your model, and it works in the EU."

## Tech stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, structlog, Redis, PostgreSQL
- **Frontend:** SvelteKit 5, Tailwind v4, TypeScript, Vite
- **Connectors:** MCP protocol (Model Context Protocol)
- **Infra:** Docker Compose (PostgreSQL + pgvector, Redis, Jaeger)
- **Testing:** pytest (unit/integration), vitest (frontend), Playwright (E2E)
- **Observability:** OpenTelemetry + Jaeger
- **Package management:** `uv` (backend), `npm` (frontend)

## Hard rules

1. One feature at a time. Finish and verify before starting the next.
2. Tests before commit. `make lint && make test` must pass.
3. No secrets. Never read, print, commit, or log `.env`, API keys, or credentials.
4. TDD workflow. Write test -> red -> implement -> green -> refactor.
5. Use `uv`, not `pip`. All Python deps via `uv sync`, `uv run pytest`.
6. No framework lock-in. Pure Python + Protocols. No LangChain/AutoGen/CrewAI.
7. Evidence over confidence. Do not claim done without runnable proof.
8. No commit/push without explicit instruction.

## Architecture

```
User -> Web UI / Telegram / Discord / Slack
  |
FastAPI -> AgentOrchestrator
  +-- PolicyEngine (action rules)
  +-- ApprovalBroker (human-in-the-loop)
  +-- ProviderAdapter (any OpenAI-compatible LLM)
  +-- SecureToolRegistry (MCP + built-in tools)
  +-- MemoryService (persistent, scoped)
  +-- Scheduler (cron tasks)
  +-- RunLedger (audit trail)
  +-- EventSink -> SSE -> Frontend
```

## Key directories

```
backend/app/           Python application code
  main.py              FastAPI app factory + lifespan
  config.py            Pydantic Settings (env-based config)
  models.py            SQLAlchemy ORM models
  database.py          Async engine + session factory
  auth.py              Scrypt passwords, JWT tokens, first-run setup
  providers.py         LLM provider CRUD + connection testing
  agent_loop.py        ReAct reasoning loop with streaming SSE
  tools.py             Tool registry + built-in demo tools
  dependencies.py      FastAPI DI (sessions, auth, settings)
  logging.py           structlog setup
  observability.py     OpenTelemetry tracing
  routes/              API routes (auth, providers, agents, chat)

backend/tests/         pytest test suite (47 tests)
backend/alembic/       Database migrations

frontend/src/          SvelteKit application
  routes/              Page routes (+page.svelte, +layout.svelte)
  lib/                 Shared components and utilities

docs/                  Documentation
  MASTER-PLAN.md       Development roadmap
```

## Verification commands

```bash
make lint              # ruff check
make test              # pytest -m unit with coverage
make fmt               # ruff format
make frontend-check    # svelte-check + TypeScript
make docker-up         # Start PostgreSQL, Redis, Jaeger
make docker-down       # Stop services
make dev               # Run backend dev server (port 8001)
make frontend-dev      # Run frontend dev server (port 5173)
```

## API endpoints

- GET  /health                        - Liveness probe
- GET  /api/auth/setup-status         - Check if first-user setup is done
- POST /api/auth/setup                - First-run: create admin user
- POST /api/auth/login                - Login, get JWT
- POST /api/providers/test            - Test an LLM endpoint (no auth required)
- POST /api/providers                 - Add verified LLM provider
- GET  /api/providers                 - List providers
- DELETE /api/providers/{id}          - Delete provider
- POST /api/agents                    - Create agent
- GET  /api/agents                    - List agents
- DELETE /api/agents/{id}             - Delete agent
- POST /api/agents/{id}/chat          - Chat with agent (SSE streaming)
- GET  /api/agents/{id}/conversations - List conversations
- GET  /api/conversations/{id}/messages - Get messages
- GET  /docs                          - Swagger UI (auto-generated)

## Development plan

See `docs/MASTER-PLAN.md` for the full roadmap.
Current phase: **Phase 1 — MVP**
