# Motes — Development Master Plan

## Vision

Motes is an open-source platform for always-on personal AI agents that connect
to your services (email, calendar, GitHub, maps, etc.) and work autonomously on
your behalf. Unlike OpenAI Dots ($200/mo, GPT only, blocked in EU/UK), Motes
is self-hosted, model-agnostic, and works everywhere.

## Target Users

1. Developers who want a self-hosted Dots-like experience with model choice
2. EU/UK users locked out of OpenAI Dots
3. Privacy-conscious users who want agents on their own infrastructure
4. Teams who need customizable agent workflows without vendor lock-in

## Competitive Landscape

| Feature              | OpenAI Dots    | Meta Muse      | Open Dots      | Motes          |
|----------------------|----------------|----------------|----------------|----------------|
| Price                | $200/mo        | Free tier      | Free           | Free (self-host) |
| Model                | GPT only       | Llama only     | Any (Responses)| Any provider   |
| EU/UK available      | No (personal)  | Yes            | Yes            | Yes            |
| Self-hosted          | No             | No             | Yes            | Yes            |
| Connectors           | 4,000+ plugins | Limited        | ~2 (Composio)  | 20 + MCP       |
| Memory               | Yes            | Yes            | No             | Yes            |
| Scheduled tasks      | Limited        | Unknown        | No             | Cron-based     |
| Voice calls          | Yes            | No             | No             | Yes (Azure RT) |
| Native iOS app       | No             | No             | No             | Yes (SwiftUI)  |
| Multi-channel        | ChatGPT/Slack  | Messenger      | Web only       | Web + planned  |
| Approval system      | Auto-review    | Unknown        | Basic          | Auto/Manual/Never |
| Production-ready     | Yes            | Yes            | No (prototype) | Goal           |

## Architecture Heritage

Motes evolved from **Cogentrex**, an AI agent governance framework designed for
enterprise orchestration. The production patterns that carry forward:

| Pattern | Origin (Cogentrex) | Implementation (Motes) |
|---------|-------------------|----------------------|
| Policy engine | Deterministic action rules | Approval system (auto/manual/never) |
| Tool registry | Schema + permissions + sandbox | 20 built-in tools + MCP proxy |
| Approval broker | Human-in-the-loop review | iOS + web approval UI |
| Run ledger | Append-only audit trail | PostgreSQL message/tool history |
| Event sink | Real-time activity streaming | SSE event bus + proactive push |
| Structured logging | structlog + OTEL | JSON logs + Jaeger traces |
| Provider adapter | Multi-model orchestration | OpenAI/Anthropic/Azure/local |
| TDD discipline | 1200+ tests | 229 tests (pytest + vitest + XCTest) |

```
User → Web UI / iOS App / API Client
  ↓
API Gateway (FastAPI :8001)
  ↓
Agent Orchestrator
  ├── ProviderAdapter (OpenAI / Anthropic / Azure / local)
  ├── ApprovalBroker (auto / manual / never per action)
  ├── SecureToolRegistry (20 built-in + MCP connectors)
  ├── MemoryService (persistent, categorized, recall-on-demand)
  ├── SchedulerService (cron-based autonomous tasks)
  ├── ProactiveScanner (Gmail/Calendar every 60s)
  └── EventBus → SSE → Clients (real-time notifications)
```

## Phase 1 — MVP ✅

### 1.1 Core Agent Loop ✅
- [x] Model-agnostic provider adapter (OpenAI, Anthropic, local via base_url)
- [x] ReAct-style reasoning loop with tool calling
- [x] Streaming responses via SSE
- [x] Configurable system prompts per agent

### 1.2 Persistent Memory ✅
- [x] Cross-session memory store (PostgreSQL-backed)
- [x] Scoped memory (per-agent, per-user)
- [x] Memory retrieval during agent reasoning
- [x] Memory management API (view, edit, delete)
- [x] Memory categories: personal, work, preference, family, health

### 1.3 Integrations ✅ (20 services)
- [x] Gmail (read, send, search) — OAuth
- [x] Google Calendar (list, create events) — OAuth
- [x] GitHub (issues, PRs, repos)
- [x] Maps (directions, places, geocoding)
- [x] Slack (read/send messages)
- [x] Weather, Web Search, News — built-in
- [x] Apple Reminders, Apple Notes — AppleScript
- [x] Todoist, Notion, Spotify, Home Assistant, Outlook
- [x] Flights & Hotels (Amadeus), Telegram
- [x] Local file system access
- [x] MCP protocol support (stdio + HTTP transports)

### 1.4 Approval System ✅
- [x] Action classification (safe / needs-approval / forbidden)
- [x] Per-tool permission configuration
- [x] Real-time approval requests (web + iOS)
- [x] Approval history

### 1.5 Web UI ✅ (SvelteKit)
- [x] Chat interface with SSE streaming
- [x] Agent creation and configuration
- [x] Service connection UI (OAuth flows + API keys)
- [x] Approval management
- [x] Memory viewer
- [x] Provider settings (LLM + voice)
- [x] MCP server management

### 1.6 Infrastructure ✅
- [x] Docker Compose (PostgreSQL, Redis, Jaeger)
- [x] Environment configuration via .env
- [x] Auto-generated API docs (/docs)
- [x] structlog JSON logging + OTEL tracing

### 1.7 Scheduled Tasks ✅
- [x] Cron-based task scheduler
- [x] Background execution with result delivery
- [x] Schedule management UI

### 1.8 Voice ✅
- [x] Real-time voice calls (Azure OpenAI Realtime API)
- [x] Semantic VAD (voice activity detection)
- [x] Echo cancellation on iOS (AVAudioEngine)
- [x] Configurable voice personality
- [x] Edge TTS for text-to-speech
- [x] Local STT via faster-whisper

### 1.9 iOS Native App ✅
- [x] Pure SwiftUI — no WebView
- [x] Chat with SSE streaming
- [x] Voice calls with AVAudioEngine
- [x] Service management, settings, personality presets
- [x] Tailscale HTTPS connectivity
- [x] Image capture and vision analysis

### 1.10 Proactive Intelligence ✅
- [x] Background scanner (Gmail/Calendar every 60s)
- [x] Pattern learning — time-based habit detection
- [x] Proactive notifications in chat and voice calls
- [x] SSE event bus for real-time push

### 1.11 Vision ✅
- [x] Image upload from camera or photo library
- [x] Vision analysis and contextual responses

## Phase 2 — Differentiation (Planned)

### 2.1 Multi-Agent
- [ ] Specialist agents with different roles/permissions/models
- [ ] Agent-to-agent delegation
- [ ] Team management UI

### 2.2 More Integrations
- [ ] Microsoft Graph OAuth (Outlook, Teams, OneDrive)
- [ ] Linear, Jira, Trello
- [ ] Financial data APIs

### 2.3 Multi-Channel
- [ ] Telegram bot gateway
- [ ] Discord bot gateway
- [ ] WhatsApp gateway

### 2.4 Enhanced Memory
- [ ] Semantic search over memory (embeddings via pgvector)
- [ ] Automatic memory extraction from conversations
- [ ] Import/export

## Phase 3 — Community & Growth (Future)

### 3.1 Deployment
- [ ] Production Docker image (all-in-one)
- [ ] One-click deploy to Railway / Fly.io
- [ ] ARM support (Raspberry Pi)

### 3.2 Enterprise
- [ ] Multi-user with RBAC
- [ ] SSO (SAML, OIDC)
- [ ] End-to-end encryption

### 3.3 Platform
- [ ] Android app
- [ ] Plugin/connector marketplace
- [ ] Community MCP server registry

## Key Differentiators vs Alternatives

1. **Full-stack production architecture** — not a weekend prototype
2. **Native iOS app** with voice calls — no other OSS alternative has this
3. **Real persistent memory** with categories and recall
4. **Proactive intelligence** — background scanning with pattern learning
5. **20 service integrations** out of the box
6. **MCP-based connectors** — community-extensible, not hardcoded
7. **Configurable approval system** — auto/manual/never per action
8. **Built on proven architecture patterns** from production AI governance work

## Client Strategy

1. ✅ **SvelteKit web UI** — responsive, full-featured
2. ✅ **Native iOS app** (SwiftUI) — chat, voice calls, services, settings
3. 🔜 **Android app** (Kotlin) — planned
4. 🔜 **Desktop app** (Tauri) — future

The backend is API-first: every client talks to the same FastAPI REST + WebSocket API.
