# Motes — Development Master Plan
# Open-source, model-agnostic alternative to OpenAI Dots

## Vision

Motes is an open-source platform for always-on personal AI agents that connect
to your services (email, calendar, GitHub, maps, etc.) and work autonomously on
your behalf. Unlike OpenAI Dots ($100+/mo, GPT-6 only, blocked in EU/UK), Motes
is self-hosted, model-agnostic, and works everywhere.

## Target users

1. Developers who want a self-hosted Dots-like experience with model choice
2. EU/UK users locked out of OpenAI Dots
3. Privacy-conscious users who want agents on their own infrastructure
4. Teams who need customizable agent workflows without vendor lock-in

## Competitive landscape

| Feature              | OpenAI Dots    | Meta Muse      | Open Dots      | Motes (ours)     |
|----------------------|----------------|----------------|----------------|------------------|
| Price                | $100+/mo       | Free tier      | Free           | Free (self-host) |
| Model                | GPT-6 only     | Llama only     | Any (Responses)| Any provider     |
| EU/UK available      | No (personal)  | Yes            | Yes            | Yes              |
| Self-hosted          | No             | No             | Yes            | Yes              |
| Connectors           | 4,000+ plugins | Limited        | ~2 (Composio)  | MCP ecosystem    |
| Memory               | Yes            | Yes            | No             | Yes              |
| Scheduled tasks      | Limited        | Unknown        | No             | Cron-based       |
| Multi-channel        | ChatGPT/Slack  | Messenger      | Web only       | Web/TG/Discord/+ |
| Approval system      | Auto-review    | Unknown        | Basic          | Policy engine    |
| Multi-agent          | Future         | No             | No             | Phase 2          |
| Production-ready     | Yes            | Yes            | No (prototype) | Goal             |

## Architecture (from Cogentrex)

```
User → Web UI / Telegram / Discord / Slack / Email
  ↓
API Gateway (FastAPI)
  ↓
Agent Orchestrator
  ├── PolicyEngine (deterministic action rules)
  ├── ApprovalBroker (auto / manual / never per action)
  ├── ProviderAdapter (OpenAI / Anthropic / local / any)
  ├── SecureToolRegistry (MCP tools + built-in tools)
  ├── MemoryService (persistent, scoped, encrypted)
  ├── SchedulerService (cron-based autonomous tasks)
  ├── RunLedger (append-only audit trail)
  └── EventSink → SSE → Frontend (live activity view)
```

## Phase 1 — MVP (4-6 weeks)

### 1.1 Core Agent Loop
- [ ] Model-agnostic provider adapter (OpenAI, Anthropic, local via base_url)
- [ ] ReAct-style reasoning loop with tool calling
- [ ] Streaming responses via SSE
- [ ] Configurable system prompts per agent

### 1.2 Persistent Memory
- [ ] Cross-session memory store (PostgreSQL-backed)
- [ ] Scoped memory (per-agent, per-user)
- [ ] Memory retrieval during agent reasoning
- [ ] Memory management API (view, edit, delete)

### 1.3 Core Connectors (MCP-based)
- [ ] Gmail (read, send, search, label)
- [ ] Google Calendar (read, create, update events)
- [ ] GitHub (issues, PRs, repos, notifications)
- [ ] Google Maps (directions, places, geocoding)
- [ ] Slack (read/send messages, channels)

### 1.4 Approval System
- [ ] Action classification (safe / needs-approval / forbidden)
- [ ] Per-connector permission config
- [ ] Real-time approval requests via WebSocket
- [ ] Approval history and audit log

### 1.5 Web UI
- [ ] Agent creation and configuration
- [ ] Chat interface with streaming
- [ ] Live activity view (watch the agent work)
- [ ] Connector setup (OAuth flows)
- [ ] Approval management dashboard
- [ ] Memory viewer

### 1.6 Infrastructure
- [ ] Docker Compose (PostgreSQL, Redis, backend, frontend)
- [ ] One-command setup: `docker compose up`
- [ ] Environment configuration via .env
- [ ] Health check endpoints
- [ ] API documentation (auto-generated)

### 1.7 Scheduled Tasks
- [ ] Cron-based task scheduler
- [ ] Agent can create/manage its own schedules
- [ ] Background execution with result delivery
- [ ] Schedule management UI

### 1.8 Voice I/O
- [ ] Speech-to-text: user speaks, audio transcribed, sent as message
- [ ] Text-to-speech: agent response converted to audio, playable in UI
- [ ] Provider-agnostic voice providers (OpenAI Whisper/TTS, ElevenLabs, Azure Speech, Edge TTS, local Whisper)
- [ ] Voice provider CRUD (same pattern as LLM providers: add, test, save)
- [ ] Streaming TTS for long responses

## Phase 2 — Differentiation (4 weeks)

### 2.1 Multi-Agent
- [ ] Specialist agents with different roles/permissions/models
- [ ] Agent-to-agent delegation
- [ ] Team management UI

### 2.2 Proactive Mode
- [ ] Background monitoring of connected services
- [ ] Configurable triggers (new email from X, calendar conflict, etc.)
- [ ] Notification system for proactive suggestions

### 2.3 More Connectors
- [ ] Microsoft 365 (Outlook, Teams, OneDrive)
- [ ] Notion
- [ ] Linear
- [ ] Jira
- [ ] Trello
- [ ] Todoist
- [ ] Weather APIs
- [ ] News APIs
- [ ] Financial data (stock prices, crypto)

### 2.4 Multi-Channel
- [ ] Telegram bot gateway
- [ ] Discord bot gateway
- [ ] Email gateway (inbound/outbound)
- [ ] Voice interaction (STT/TTS)
- [ ] WhatsApp gateway

### 2.5 Enhanced Memory
- [ ] Semantic search over memory (embeddings)
- [ ] Automatic memory extraction from conversations
- [ ] Memory categories and tagging
- [ ] Import/export

## Phase 3 — Community & Growth (ongoing)

### 3.1 Connector Marketplace
- [ ] Community MCP server registry
- [ ] One-click connector installation
- [ ] Connector development SDK and docs
- [ ] Rating/review system

### 3.2 Deployment
- [ ] One-click deploy to Railway
- [ ] One-click deploy to Fly.io
- [ ] Helm chart for Kubernetes
- [ ] ARM support (Raspberry Pi)

### 3.3 Enterprise
- [ ] Multi-user with RBAC
- [ ] SSO (SAML, OIDC)
- [ ] Team workspaces
- [ ] Compliance and data retention policies
- [ ] Usage analytics dashboard

### 3.4 Polish
- [ ] Mobile-friendly PWA
- [ ] Browser extension
- [ ] Desktop app (Electron/Tauri)
- [ ] Comprehensive documentation
- [ ] Video tutorials

## Reuse from Cogentrex

These modules can be extracted/adapted directly:

| Cogentrex Module       | Motes Usage                        |
|------------------------|------------------------------------|
| backend/app/agents/    | Agent loop, provider adapters      |
| backend/app/runtime/   | Typed runtime, events, budgets     |
| backend/app/tools/     | Tool registry, sandbox             |
| backend/app/mcp/       | MCP client, inventory              |
| backend/app/security/  | Policy engine, approvals           |
| backend/app/memory/    | Persistent, encrypted memory       |
| backend/app/services/  | Run ledger, effect ledger          |
| backend/app/routes/    | API route patterns                 |
| frontend/              | SvelteKit patterns, components     |

## Key differentiators vs Open Dots (existing OSS clone)

1. Production architecture (not a weekend prototype)
2. Real persistent memory (not just SQLite chat logs)
3. Policy engine with configurable approval tiers
4. MCP-based connectors (community-extensible, not hardcoded)
5. Multi-channel from day 1 (not web-only)
6. Cron scheduler for autonomous background work
7. Built on proven patterns from Cogentrex (1200+ tests)

## Success metrics

- Phase 1: Working self-hosted agent that can read Gmail, manage calendar,
  interact with GitHub, with approval system and persistent memory
- Phase 2: 10+ connectors, multi-agent support, 2+ chat channels
- Phase 3: Active community contributions, 1000+ GitHub stars

## Client strategy

1. **Phase 1 (MVP)**: SvelteKit web UI — mobile-responsive, installable as PWA on iOS/Android
2. **Phase 2**: Native iOS app (Swift/SwiftUI) — push notifications, Siri Shortcuts, background refresh
3. **Future**: Android app (Kotlin), desktop app (Tauri)

The backend is API-first: every client (web, iOS, Android, CLI) talks to the same FastAPI REST + WebSocket API. The iOS app is a thin SwiftUI client, not a separate product.

## Non-goals (for now)

- Managed cloud hosting (SaaS)
- Voice-first interface
- Payments/transactions
- Enterprise sales
