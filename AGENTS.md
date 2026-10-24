# AGENTS.md — Motes agent instruction file

> This file orients any AI coding agent working in this repository.

## What this is

Motes is an open-source, model-agnostic, self-hosted personal agent platform —
an alternative to OpenAI Dots. It evolved from **Cogentrex**, an AI agent governance
framework, inheriting production patterns (structured logging, OTEL, tool registry,
approval system, TDD discipline) while adding a consumer-facing UX with voice calls,
native iOS app, proactive intelligence, and 20 service integrations.

## Tech stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), Alembic, structlog, Redis, PostgreSQL (pgvector)
- **Frontend:** SvelteKit 5, Tailwind v4, TypeScript, Vite
- **iOS:** SwiftUI, AVAudioEngine, URLSession, MVVM
- **Connectors:** MCP protocol (stdio + HTTP transports) + 20 built-in tools
- **Voice:** Azure OpenAI Realtime API, Edge TTS, faster-whisper
- **Infra:** Docker Compose (PostgreSQL, Redis, Jaeger)
- **Testing:** pytest (backend), vitest (frontend), XCTest (iOS)
- **Observability:** OpenTelemetry + Jaeger, structlog JSON
- **Package management:** `uv` (backend), `npm` (frontend)

## Hard rules

1. One feature at a time. Finish and verify before starting the next.
2. Tests before commit. `make lint && make test` must pass.
3. No secrets. Never read, print, commit, or log `.env`, API keys, or credentials.
4. TDD workflow. Write test → red → implement → green → refactor.
5. Use `uv`, not `pip`. All Python deps via `uv sync`, `uv run pytest`.
6. No framework lock-in. Pure Python + Protocols. No LangChain/AutoGen/CrewAI.
7. Evidence over confidence. Do not claim done without runnable proof.
8. No commit/push without explicit instruction.

## Architecture

```
User → Web UI (SvelteKit) / iOS App (SwiftUI) / API Client
  │
  ▼
FastAPI Backend (:8001)
  ├── ProviderAdapter (OpenAI / Anthropic / Azure / local)
  ├── AgentLoop (ReAct reasoning with tool calling, SSE streaming)
  ├── ApprovalBroker (auto / manual / never per action)
  ├── SecureToolRegistry (20 built-in + MCP connectors)
  ├── MemoryService (persistent, categorized, recall-on-demand)
  ├── ProactiveScanner (Gmail/Calendar every 60s, pattern learning)
  ├── SchedulerService (cron-based autonomous tasks)
  ├── VoiceService (Azure Realtime API WebSocket relay)
  ├── EventBus → SSE → Clients (real-time notifications)
  └── Logging (structlog JSON + OTEL → Jaeger)
```

## Key directories

```
backend/app/             Python application (71 files, 12,400+ lines)
  main.py                FastAPI app factory + lifespan
  config.py              Pydantic Settings (env-based config)
  models.py              SQLAlchemy ORM models
  database.py            Async engine + session factory
  auth.py                Scrypt passwords, JWT tokens, first-run setup
  providers.py           LLM provider CRUD + connection testing
  agent_loop.py          ReAct loop with SSE streaming (OpenAI format)
  agent_loop_anthropic.py  Anthropic Messages API variant
  tools.py               Tool registry + built-in tools
  apple_tools.py         Apple Reminders + Notes (AppleScript)
  google_tools.py        Gmail + Calendar tools
  mcp_proxy.py           MCP proxy service (stdio + HTTP)
  memory.py              Persistent memory (save/recall/categories)
  voice.py               Voice call pipeline (Azure Realtime relay)
  proactive.py           Pattern extraction from messages
  agentic_proactive.py   LLM-driven proactive notifications
  background_scanner.py  Gmail/Calendar periodic scan
  routes/                API routes (auth, chat, agents, voice, mcp, etc.)

backend/tests/           pytest test suite (229 test functions)
backend/alembic/         Database migrations

frontend/src/            SvelteKit frontend (26 components)
  routes/                Page routes
  lib/                   Shared components + utilities

MotesiOS/                Native iOS app (44 Swift files, 3,700+ lines)
  ViewModels/            MVVM view models
  Views/                 SwiftUI views (chat, call, settings, services)
  Services/              APIClient, audio engine

docs/                    Documentation
  MASTER-PLAN.md         Development roadmap (with completion status)
  FEATURE-PARITY.md      Feature-by-feature Motes vs Dots tracker
  COMPETITIVE-ANALYSIS.md  Competitor landscape
  CODE-QUALITY-ROADMAP.md  Engineering standards + quality plan
```

## Verification commands

```bash
make lint              # ruff check
make test              # pytest -m unit with coverage
make test-all          # pytest (all markers) with coverage
make fmt               # ruff format
make frontend-check    # svelte-check + TypeScript
make frontend-dev      # Run frontend dev server (port 5173)
make docker-up         # Start PostgreSQL, Redis, Jaeger
make docker-down       # Stop services
make dev               # Run backend dev server (port 8001)
```

## API endpoints

### Auth
- `GET  /api/auth/setup-status` — Check if first-user setup is done
- `POST /api/auth/setup` — First-run: create admin user
- `POST /api/auth/login` — Login, get JWT

### Agents & Chat
- `POST /api/agents` — Create agent
- `GET  /api/agents` — List agents
- `POST /api/agents/{id}/chat` — Chat with agent (SSE streaming)
- `GET  /api/agents/{id}/thread` — Get conversation thread
- `GET  /api/agents/{id}/approvals` — Pending tool approvals

### Voice
- `WS   /api/realtime-call/{id}` — Voice call WebSocket
- `POST /api/voice/voice-personality` — Set voice personality

### Services & OAuth
- `GET  /api/oauth/services` — List available/connected services
- `POST /api/oauth/connect/{provider}/{service}` — Start OAuth flow
- `GET  /api/service-keys` — List API key services

### MCP
- `GET  /api/mcp/servers` — List MCP servers
- `POST /api/mcp/servers` — Add MCP server

### Memory
- `GET  /api/memory` — List memories
- `POST /api/memory` — Save memory

### Other
- `GET  /api/events/stream` — SSE event stream (proactive notifications)
- `GET  /docs` — Swagger UI (auto-generated)

## Development status

See `docs/MASTER-PLAN.md` for the full roadmap.
Current status: **Phase 1 — MVP: Complete** (48 features implemented)
