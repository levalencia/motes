# Motes — Your agents, your models, your data

Open-source, model-agnostic, self-hosted personal AI agents. An alternative to OpenAI Dots that works with any LLM, runs on your infrastructure, and respects your privacy.

## Why Motes?

| Feature | OpenAI Dots | Motes |
|---|---|---|
| Model choice | GPT only | Any LLM (OpenAI, Anthropic, local) |
| Data location | OpenAI servers | Your server |
| EU/UK | Not available | Works everywhere |
| Integrations | Limited | 20 services, community-driven |
| Voice calls | Yes | Yes (Azure Realtime API) |
| iOS app | No | Native SwiftUI |
| Self-hosted | No | Docker Compose |
| Open source | No | MIT License |

## Features

### Chat
- SSE streaming responses with tool calling
- Markdown rendering (tables, code blocks, lists)
- Conversation history (rename, delete, resume)
- Proactive notifications IN the conversation

### Voice Calls
- Real-time voice via Azure OpenAI Realtime API
- Semantic VAD (knows when you're done talking)
- Echo cancellation on iOS
- Configurable voice personality and accent
- Speaker/earpiece toggle, mute, captions

### 20 Integrations
**Built-in (free):** Weather, Web Search, Apple Reminders, Apple Notes, Maps, News, Local Files

**OAuth:** Gmail, Google Calendar

**API Key:** GitHub, Slack, Todoist, Notion, Spotify, Home Assistant, Outlook, Flights & Hotels, Telegram

### Proactive Intelligence
- Background scanner checks Gmail/Calendar every 60 seconds
- Notifications appear directly in your conversation
- Pattern learning (knows when you check email)

### Memory
- Say "remember that I live in Brussels" — agent saves it persistently
- Memory works in both chat and voice calls
- Agent recalls facts when relevant to the conversation
- Memory categories: personal, work, preference, family, health

### How Proactive Works

```
Background Scanner (every 60s)
  ├─ scan_gmail() → new email? → notify in chat
  ├─ scan_calendar() → upcoming event? → notify in chat
  └─ check_patterns() → time-based suggestion? → notify in chat
                              │
               ┌──────────────┼──────────────┐
               │              │              │
          💬 Chat         📞 Voice Call    🔔 Stored
          (SSE push)      (TTS speech)    (for later)
```

**Pattern Learning**: Every message (chat or voice) is analyzed for topics.
After 3+ messages about "email" at the same hour, Motes proactively suggests
checking your inbox at that time.

**Memory Tools**: The agent has `memory_save` and `memory_recall` tools.
When you say "recuerda que mi hija se llama Victoria", the agent calls
`memory_save(fact="User's daughter is named Victoria", category="family")`.
Next time you ask about family, it recalls this fact.

### iOS Native App
- Pure SwiftUI (no WebView)
- Chat with streaming, voice calls with AVAudioEngine
- Connects via Tailscale HTTPS

## Quick Start

### Prerequisites
- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+, npm
- Docker & Docker Compose
- An LLM API key (OpenAI, Anthropic, Azure, or any OpenAI-compatible)

### 1. Clone and setup

```bash
git clone https://github.com/levalencia/motes.git
cd motes
```

### 2. Start infrastructure

```bash
docker compose up -d  # PostgreSQL + Redis + Jaeger
```

### 3. Start the backend

```bash
cd backend
cp .env.example .env  # Edit with your API keys
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

### 5. First login

Open http://localhost:5173. Create your account (first user = admin).

## Configuration

### Environment Variables

All config via `MOTES_` prefix or `.env` file in `backend/`:

```bash
# Required: at least one LLM provider
MOTES_DATABASE_URL=postgresql+asyncpg://motes:motes_dev@localhost:5433/motes
MOTES_REDIS_URL=redis://localhost:6380/0
MOTES_SECRET_KEY=your-secret-key-here  # Auto-generated if not set, but set it to survive restarts

# LLM Provider (example: Azure AI Foundry with Anthropic)
# Configure via the web UI at /providers
```

### LLM Providers

Go to **Settings → Providers** in the web UI. Motes supports:
- **OpenAI** (GPT-4, GPT-4o)
- **Anthropic** (Claude Opus, Sonnet, Haiku)
- **Azure AI Foundry** (any model via Azure)
- **OpenRouter** (100+ models)
- **Any OpenAI-compatible endpoint** (Ollama, LM Studio, vLLM)

### Voice Call Provider

For voice calls, you need Azure OpenAI Realtime API:

1. Go to **Settings** in the web UI
2. Under "Realtime Voice Calls", enter:
   - **WebSocket URL**: `wss://your-resource.openai.azure.com/openai/v1/realtime?model=gpt-realtime-2.1-mini`
   - **API Key**: Your Azure OpenAI key

Recommended model: `gpt-realtime-2.1-mini` (fastest, cheapest for voice)

### Voice Personality

Set a custom voice personality per user. Go to **Settings** or call the API:

```bash
curl -X POST http://localhost:8001/api/voice/voice-personality \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"personality": "Colombian paisa accent, warm and casual"}'
```

### Connecting Services

Go to **Services** in the web UI:
- **Gmail/Calendar**: Click "Connect" → OAuth flow
- **GitHub/Slack/etc**: Click "Setup" → follow the guide → paste API key

## iOS App

### Prerequisites
- Xcode 26+ (iOS 26 SDK)
- Tailscale installed on both Mac and iPhone
- Tailscale HTTPS cert for your Mac

### Setup Tailscale HTTPS

The iOS app requires HTTPS (App Transport Security). Tailscale provides free, trusted HTTPS certs:

```bash
# Get your Tailscale domain
tailscale status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['CertDomains'])"
# Output: ['your-machine.tailXXXXX.ts.net']

# Generate cert
cd backend
tailscale cert --cert-file ts-cert.pem --key-file ts-key.pem your-machine.tailXXXXX.ts.net

# Start backend with HTTPS
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload \
  --ssl-keyfile ts-key.pem --ssl-certfile ts-cert.pem
```

### Build and Run

```bash
cd MotesiOS/MotesiOS
open MotesiOS.xcodeproj
```

1. Select your iPhone as the build target
2. Build and Run (Cmd+R)
3. On the login screen, enter:
   - **Server URL**: `https://your-machine.tailXXXXX.ts.net:8001`
   - **Username/Password**: Your Motes credentials

### Troubleshooting iOS

**"App Transport Security" error**: The server must use HTTPS with a trusted cert. Use `tailscale cert` as described above. Self-signed certs do NOT work on iOS.

**"Agent not found" on Call tab**: Make sure you've created at least one agent (happens automatically on first login).

**Call audio not working**: Ensure microphone permission is granted. Echo cancellation requires `setVoiceProcessingEnabled(true)` on AVAudioEngine (already implemented).

**Login screen doesn't appear after reinstall**: Keychain persists across installs. The app auto-clears stale tokens when the server URL isn't configured.

## Viewing Logs

### Backend logs
```bash
# If running with tee
tail -f /tmp/motes-backend.log

# Or check uvicorn output directly
# Logs use structlog JSON format with correlation IDs
```

### Key log events
```
scanner_gmail_notification  — New email detected
event_bus_published         — Proactive notification sent
realtime_call_connected     — Voice call established
realtime_call_audio_forwarded — iOS audio forwarded to Azure
realtime_call_wav_sent      — Agent audio sent to client
realtime_call_tool_call     — Agent used a tool during call
```

### iOS logs
In Xcode console, look for `[Motes]` prefix:
```
[Motes] Audio sent OK: 12345 chars
[Motes] WebSocket send error: ...
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Clients                                │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ SvelteKit│  │ iOS (SwiftUI)│  │ Any HTTP client   │  │
│  │ :5173    │  │ via Tailscale│  │                   │  │
│  └────┬─────┘  └──────┬───────┘  └─────────┬─────────┘  │
│       │               │                     │            │
└───────┼───────────────┼─────────────────────┼────────────┘
        │               │                     │
   ┌────▼───────────────▼─────────────────────▼────┐
   │           FastAPI Backend (:8001)              │
   │                                                │
   │  ┌──────────┐  ┌───────────┐  ┌────────────┐  │
   │  │ Chat SSE │  │ Voice WS  │  │ Tools (20) │  │
   │  │ Streaming│  │ Realtime  │  │ Gmail,Cal, │  │
   │  │          │  │ Azure API │  │ Weather,...│  │
   │  └──────────┘  └───────────┘  └────────────┘  │
   │                                                │
   │  ┌──────────┐  ┌───────────┐  ┌────────────┐  │
   │  │ structlog│  │   OTEL    │  │  Proactive │  │
   │  │ + PII    │  │  Jaeger   │  │  Scanner   │  │
   │  │ redaction│  │  traces   │  │  (60s)     │  │
   │  └──────────┘  └───────────┘  └────────────┘  │
   └────────────────────┬──────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
   ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
   │PostgreSQL│  │  Redis  │  │ Jaeger  │
   │  :5433   │  │  :6380  │  │ :16687  │
   └──────────┘  └─────────┘  └─────────┘
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), structlog, OTEL
- **Frontend**: SvelteKit 5, Tailwind v4, TypeScript
- **iOS**: SwiftUI, AVAudioEngine, URLSession
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis
- **Observability**: Jaeger (traces), structlog (JSON logs)
- **Voice**: Azure OpenAI Realtime API, Edge TTS, faster-whisper

## Docker Ports

| Service | Port | Description |
|---|---|---|
| Backend | 8001 | FastAPI + WebSocket |
| Frontend | 5173 | SvelteKit dev server |
| PostgreSQL | 5433 | Database |
| Redis | 6380 | Cache |
| Jaeger | 16687 | Trace UI |

## Contributing

1. Fork the repo
2. Create a feature branch
3. Run tests: `cd backend && uv run pytest -m unit`
4. Run lint: `cd backend && uv run ruff check .`
5. Frontend check: `cd frontend && npx svelte-check`
6. Submit a PR

### Code Quality Standards
- **structlog** for all logging (no `print()`)
- **OTEL** spans for LLM and tool calls
- **TDD**: write test → red → implement → green
- **No secrets** in code, logs, or commits
- **Type hints** on all functions

## License

MIT
