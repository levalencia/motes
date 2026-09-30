# Motes — Your agents, your models, your data

Open-source, model-agnostic, self-hosted personal AI agents. An alternative to OpenAI Dots that works with any LLM, runs on your infrastructure, and respects your privacy.

## Why Motes?

| | OpenAI Dots | Motes |
|---|---|---|
| **Model** | GPT-6 only | Any LLM (Anthropic, OpenAI, local) |
| **Hosting** | OpenAI cloud | Self-hosted (your server) |
| **EU/UK** | Not available | Works everywhere |
| **Voice** | OpenAI only | Any provider + free local (Edge TTS, Whisper) |
| **Price** | $100-500/month | Free (bring your own API keys) |
| **Data** | OpenAI servers | Your PostgreSQL |

## Features

### Core Agent
- ReAct-style reasoning with streaming SSE
- Tool calling (Gmail, Calendar, files, web search, calculator)
- Persistent cross-session memory
- Pattern learning from interactions

### Voice
- Voice calls with Azure OpenAI Realtime API (sub-second latency)
- Pipeline fallback: Whisper STT + LLM + Edge TTS (free, no API key)
- Mic input + audio playback in chat
- Full-screen call UI with mascot, status, captions toggle

### Connected Services
- Gmail (read, send, search)
- Google Calendar (list, create events)
- OAuth consent screen flow with step-by-step setup guides
- Auto-refreshing tokens

### Proactive Intelligence
- Learns what you ask, when, and about whom
- Background scanner checks Gmail/Calendar every 5 minutes
- Push notifications: "New email from Diana", "Meeting in 30 min"
- Proactive suggestions: "You usually check email now"
- Notification bell with unread count badge

### Local Computer Access
- Browse, read, search files on your machine
- Inspect and edit PowerPoint presentations
- Download files via browser
- Works remotely via Tailscale

### Approval System
- Action classification: safe / needs_approval / forbidden
- Per-agent, per-tool policies
- Approve/deny flow

### Web UI
- Dashboard with stats, agent cards, service connections
- Chat with markdown rendering, tool call display
- Dark/light theme toggle
- Mascot character (always visible)
- Mobile-friendly via Tailscale

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- **Frontend:** SvelteKit 5, Tailwind v4, TypeScript
- **Voice:** Azure OpenAI Realtime API, faster-whisper, Edge TTS
- **Observability:** structlog, OpenTelemetry, Jaeger
- **Auth:** JWT + scrypt, OAuth2 for services
- **Infra:** Docker Compose

## Quick Start

```bash
# Clone
git clone https://github.com/levalencia/motes.git
cd motes

# Start infrastructure
docker compose up -d

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --port 8001 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — create your account, add a provider, start chatting.

## Configuration

All config via environment variables with `MOTES_` prefix:

```bash
# Required
MOTES_SECRET_KEY=your-secret-key

# LLM Provider (set via UI, or env)
MOTES_LLM_PROVIDER=anthropic

# Voice (optional — works without)
MOTES_REALTIME_URL=wss://your-resource.openai.azure.com/openai/v1/realtime
MOTES_REALTIME_KEY=your-key

# Observability (optional)
MOTES_OTEL_ENABLED=true
MOTES_OTEL_EXPORTER_ENDPOINT=http://localhost:4317
```

## Development

```bash
make lint          # ruff check
make test          # pytest (115 tests)
make fmt           # ruff format
make frontend-check # svelte-check
make docker-up     # start PostgreSQL, Redis, Jaeger
```

## Contributing

Motes follows these patterns (see `docs/CODE-QUALITY-ROADMAP.md`):

1. **Logging:** `structlog.get_logger()` at module level, event-style kwargs
2. **OTEL:** Auto-instrumented FastAPI + custom spans for LLM/tool calls
3. **DI:** `app.state` for singletons, `Depends()` chains, service layer
4. **Tests:** `@pytest.mark.unit`, minimal FastAPI fixtures, mock externals
5. **Security:** No hardcoded secrets, auth on all endpoints, path validation

## License

MIT

## Links

- [Feature Parity Tracker](docs/FEATURE-PARITY.md)
- [Code Quality Roadmap](docs/CODE-QUALITY-ROADMAP.md)
- [Proactive Intelligence Plan](docs/PROACTIVE-PLAN.md)
- [Master Plan](docs/MASTER-PLAN.md)
